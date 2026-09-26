# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License.

"""Small, restart-safe Open vSwitch distributor controller.

The distributor presents the VIP on its frontend port and selects one of the
registered amphora MAC addresses for each IP flow.  State is persisted locally
so a distributor-agent restart can reconstruct the OpenFlow group.
"""

import hashlib
import json
import os
import re
import subprocess
import tempfile


STATE_PATH = os.environ.get(
    'OCTAVIA_DISTRIBUTOR_STATE',
    '/var/lib/octavia/distributor/state.json')
DEFAULT_BRIDGE = os.environ.get('OCTAVIA_DISTRIBUTOR_BRIDGE', 'br-int')


def _run(command, check=True):
    return subprocess.run(command, check=check, capture_output=True,
                          text=True)


def _load_state():
    try:
        with open(STATE_PATH) as stream:
            return json.load(stream)
    except FileNotFoundError:
        return {'vips': {}}


def _save_state(state):
    directory = os.path.dirname(STATE_PATH)
    os.makedirs(directory, mode=0o750, exist_ok=True)
    fd, path = tempfile.mkstemp(prefix='.state.', dir=directory, text=True)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(state, stream, sort_keys=True)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(path, STATE_PATH)
    finally:
        if os.path.exists(path):
            os.unlink(path)


def _group_id(vip):
    # OpenFlow group IDs are 32-bit. Keep the value stable across restarts.
    return 1000 + int(hashlib.sha256(vip.encode()).hexdigest()[:7], 16)


def _bridge_for(interface):
    result = _run(['ovs-vsctl', 'port-to-br', interface], check=False)
    bridge = result.stdout.strip()
    return bridge or DEFAULT_BRIDGE


def bridge_name(load_balancer_id):
    """Return a Linux-safe, deterministic bridge name for one LB."""
    if not load_balancer_id:
        return DEFAULT_BRIDGE
    return 'br-aa-' + hashlib.sha256(
        load_balancer_id.encode()).hexdigest()[:8]


def _ensure_frontend_bridge(interface, bridge=None):
    bridge = bridge or _bridge_for(interface)
    _run(['ovs-vsctl', '--may-exist', 'add-br', bridge], check=False)
    _run(['ovs-vsctl', '--may-exist', 'add-port', bridge, interface],
         check=False)
    return bridge


def interface_for_mac(mac_address, fallback='auto'):
    """Resolve a dynamically named Nova/Neutron interface by MAC."""
    if fallback and fallback != 'auto':
        return fallback
    result = _run(['ip', '-o', 'link', 'show'], check=False)
    wanted = mac_address.lower()
    for line in result.stdout.splitlines():
        fields = line.split()
        if 'link/ether' not in fields:
            continue
        mac_index = fields.index('link/ether') + 1
        if mac_index < len(fields) and fields[mac_index].lower() == wanted:
            return fields[1].split('@', 1)[0].rstrip(':')
    result = _run([
        'ovs-vsctl', '--format=csv', '--data=bare', '--no-heading',
        '--columns=name', 'find', 'Interface',
        'mac_in_use="{0}"'.format(mac_address)], check=False)
    for line in result.stdout.splitlines():
        name = line.strip().strip('"')
        if name:
            return name
    raise RuntimeError('No OVS interface found for distributor MAC %s' %
                       mac_address)


def _port_for_interface(interface):
    result = _run([
        'ovs-vsctl', 'get', 'Interface', interface, 'ofport'], check=False)
    port = result.stdout.strip().strip('"')
    if port.isdigit() and int(port) > 0:
        return port
    raise RuntimeError('No OVS port found for distributor interface %s' %
                       interface)


def _gateway_mac(gateway, bridge):
    """Resolve and return the tenant router MAC on the frontend bridge."""
    if not gateway:
        return None
    mac_re = re.compile(r'\b([0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5})\b')
    for _ in range(3):
        result = _run(['ip', 'neigh', 'show', 'to', gateway, 'dev', bridge],
                      check=False)
        match = mac_re.search(result.stdout)
        if match:
            return match.group(1).lower()
        # Trigger a bounded ARP lookup before retrying the neighbor query.
        _run(['ping', '-c', '1', '-W', '1', '-I', bridge, gateway],
             check=False)
    return None


def _delete_group(bridge, group):
    _run(['ovs-ofctl', 'del-groups', bridge, 'group_id={0}'.format(group)],
         check=False)


def _set_bridge_hwaddr(bridge, mac_address):
    """Make the OVS bridge use the Neutron frontend MAC for ARP replies."""
    _run(['ovs-vsctl', 'set', 'Bridge', bridge,
          'other-config:hwaddr={0}'.format(mac_address)])


def _rebuild(vip_state):
    bridge = vip_state['bridge']
    vip = vip_state['vip']
    group = vip_state['group_id']
    _delete_group(bridge, group)
    for match in ('ip,nw_dst={0}'.format(vip), 'ip,nw_src={0}'.format(vip)):
        _run(['ovs-ofctl', 'del-flows', bridge, match], check=False)

    buckets = []
    for mac in sorted(vip_state['amphora_macs']):
        buckets.append(
            'bucket=set_field:{amphora}->eth_dst,'
            'set_field:{frontend}->eth_src,output:in_port'.format(
                amphora=mac,
                frontend=vip_state['frontend_mac']))

    if not buckets:
        return
    _run(['ovs-ofctl', 'add-group', bridge,
          'group_id={0},type=select,selection_method=dp_hash,'
          'selection_method_param=4294967296,{1}'.format(
              group, ','.join(buckets))])
    _run(['ovs-ofctl', 'add-flow', bridge,
          'priority=200,ip,nw_dst={0},actions=group:{1}'.format(vip, group)])
    # In OVN, letting the amphora return directly to the router makes the
    # following client ACK appear as conntrack-invalid.  Hairpin the reverse
    # packet through the same distributor logical port so both directions use
    # the same OVN conntrack path.
    gateway_mac = vip_state.get('gateway_mac')
    if gateway_mac:
        _run(['ovs-ofctl', 'add-flow', bridge,
              'priority=210,ip,nw_src={0},actions='
              'set_field:{1}->eth_dst,set_field:{2}->eth_src,IN_PORT'.format(
                  vip, gateway_mac, vip_state['frontend_mac'])])


def post_plug_vip(interface, vip_ip, mac_address, subnet_cidr, gateway,
                  cluster_min_size, bridge=None):
    # The distributor owns ARP for the VIP.  The OpenFlow rule handles the
    # subsequent IP packet and sends it to a selected amphora.
    bridge = _ensure_frontend_bridge(interface, bridge=bridge)
    # Make the bridge answer ARP with the Neutron port MAC.  OVS internal
    # interfaces do not reliably accept this through ``ip link set``; the
    # Bridge hwaddr is the persistent OVS setting used by the datapath.
    _set_bridge_hwaddr(bridge, mac_address)
    _run(['ip', 'addr', 'add', '{0}/32'.format(vip_ip), 'dev', bridge],
         check=False)
    _run(['ip', 'link', 'set', 'dev', bridge, 'up'], check=False)
    gateway_mac = _gateway_mac(gateway, bridge)
    state = _load_state()
    state['vips'][vip_ip] = {
        'vip': vip_ip,
        'interface': interface,
        'ip_device': bridge,
        'bridge': bridge,
        'frontend_port': _port_for_interface(interface),
        'frontend_mac': mac_address,
        'subnet_cidr': subnet_cidr,
        'gateway': gateway,
        'gateway_mac': gateway_mac,
        'cluster_min_size': cluster_min_size,
        'group_id': _group_id(vip_ip),
        'amphora_macs': [],
    }
    _save_state(state)
    return {'group_id': state['vips'][vip_ip]['group_id']}


def register_amphora(vip, mac, interface, subnet_cidr, gateway,
                     amphora_mac, cluster_min_size, bridge=None):
    state = _load_state()
    if vip not in state['vips']:
        post_plug_vip(interface, vip, mac, subnet_cidr, gateway,
                       cluster_min_size, bridge=bridge)
        state = _load_state()
    vip_state = state['vips'][vip]
    if 'frontend_port' not in vip_state:
        vip_state['bridge'] = _ensure_frontend_bridge(
            vip_state['interface'], bridge=vip_state.get('bridge', bridge))
        vip_state['ip_device'] = vip_state['bridge']
        vip_state['frontend_port'] = _port_for_interface(
            vip_state['interface'])
    if not vip_state.get('gateway_mac'):
        vip_state['gateway_mac'] = _gateway_mac(
            vip_state.get('gateway'), vip_state['bridge'])
    if amphora_mac not in vip_state['amphora_macs']:
        vip_state['amphora_macs'].append(amphora_mac)
    _rebuild(vip_state)
    _save_state(state)
    return {'group_id': vip_state['group_id'],
            'amphora_count': len(vip_state['amphora_macs'])}


def unregister_amphora(vip, mac, interface, subnet_cidr, gateway,
                       amphora_mac, cluster_min_size):
    del interface, subnet_cidr, gateway, cluster_min_size
    state = _load_state()
    vip_state = state['vips'].get(vip)
    if not vip_state:
        return {'amphora_count': 0}
    vip_state['amphora_macs'] = [
        item for item in vip_state['amphora_macs'] if item != amphora_mac]
    if vip_state['amphora_macs']:
        _rebuild(vip_state)
    else:
        _delete_group(vip_state['bridge'], vip_state['group_id'])
        _run(['ovs-ofctl', 'del-flows', vip_state['bridge'],
              'ip,nw_dst={0}'.format(vip)], check=False)
    _save_state(state)
    return {'amphora_count': len(vip_state['amphora_macs'])}


def pre_uplug_vip(interface, vip, mac_address):
    del mac_address
    state = _load_state()
    vip_state = state['vips'].pop(vip, None)
    if vip_state:
        _delete_group(vip_state['bridge'], vip_state['group_id'])
        for match in ('ip,nw_dst={0}'.format(vip),
                      'ip,nw_src={0}'.format(vip)):
            _run(['ovs-ofctl', 'del-flows', vip_state['bridge'], match],
                 check=False)
        _run(['ip', 'addr', 'del', '{0}/32'.format(vip), 'dev',
              vip_state.get('ip_device', vip_state.get('bridge', interface))],
             check=False)
    _save_state(state)


def get_status(interface):
    bridge = _bridge_for(interface)
    return {'bridge': bridge, 'state': _load_state()}


def dump_state(interface):
    return get_status(interface)


def load_state(interface, slot_to_mac):
    state = _load_state()
    for vip_state in state.get('vips', {}).values():
        vip_interface = vip_state.get('interface', interface)
        vip_state['bridge'] = _ensure_frontend_bridge(
            vip_interface, bridge=vip_state.get('bridge'))
        vip_state['ip_device'] = vip_state['bridge']
        vip_state['frontend_port'] = _port_for_interface(vip_interface)
        _set_bridge_hwaddr(vip_state['bridge'], vip_state['frontend_mac'])
        if not vip_state.get('gateway_mac'):
            vip_state['gateway_mac'] = _gateway_mac(
                vip_state.get('gateway'), vip_state['bridge'])
        vip_state['amphora_macs'] = list(slot_to_mac.values())
        _rebuild(vip_state)
    _save_state(state)


def restore_state():
    """Recreate persisted VIP addresses and OpenFlow groups after restart."""
    state = _load_state()
    for vip_state in state.get('vips', {}).values():
        interface = vip_state['interface']
        bridge = _ensure_frontend_bridge(interface,
                                          bridge=vip_state.get('bridge'))
        vip_state['bridge'] = bridge
        vip_state['ip_device'] = bridge
        vip_state['frontend_port'] = _port_for_interface(interface)
        _set_bridge_hwaddr(bridge, vip_state['frontend_mac'])
        if not vip_state.get('gateway_mac'):
            vip_state['gateway_mac'] = _gateway_mac(
                vip_state.get('gateway'), bridge)
        _run(['ip', 'addr', 'add', '{0}/32'.format(vip_state['vip']),
              'dev', bridge], check=False)
        _run(['ip', 'link', 'set', 'dev', bridge, 'up'], check=False)
        _rebuild(vip_state)
    _save_state(state)
