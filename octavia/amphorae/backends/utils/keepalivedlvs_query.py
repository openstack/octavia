# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import re
import subprocess

import netaddr
from oslo_log import log as logging

from octavia.amphorae.backends.agent.api_server import util
from octavia.common import constants

LOG = logging.getLogger(__name__)
KERNEL_LVS_PATH = '/proc/net/ip_vs'
KERNEL_LVS_STATS_PATH = '/proc/net/ip_vs_stats'
LVS_KEY_REGEX = re.compile(r"RemoteAddress:Port\s+(.*$)")
V4_RS_VALUE_REGEX = re.compile(r"(\w{8}:\w{4})\s+(.*$)")
V4_HEX_IP_REGEX = re.compile(r"(\w{2})(\w{2})(\w{2})(\w{2})")
V6_RS_VALUE_REGEX = re.compile(r"(\[[[\w{4}:]+\b\]:\w{4})\s+(.*$)")

NS_REGEX = re.compile(r"net_namespace\s(\w+-\w+)")
V4_VS_REGEX = re.compile(r"virtual_server\s([\d+\.]+\b)\s(\d{1,5})")
V4_RS_REGEX = re.compile(r"real_server\s([\d+\.]+\b)\s(\d{1,5})")
V6_VS_REGEX = re.compile(r"virtual_server\s([\w*:]+\b)\s(\d{1,5})")
V6_RS_REGEX = re.compile(r"real_server\s([\w*:]+\b)\s(\d{1,5})")
CONFIG_COMMENT_REGEX = re.compile(
    r"#\sConfiguration\sfor\s(\w+)\s(\w{8}-\w{4}-\w{4}-\w{4}-\w{12})")


def read_kernel_file(ns_name, file_path):
    cmd = ("ip netns exec {ns} cat {lvs_stat_path}".format(
        ns=ns_name, lvs_stat_path=file_path))
    try:
        output = subprocess.check_output(cmd.split(),
                                         stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        LOG.error("Failed to get kernel lvs status in ns %(ns_name)s "
                  "%(kernel_lvs_path)s: %(err)s %(out)s",
                  {'ns_name': ns_name, 'kernel_lvs_path': file_path,
                   'err': e, 'out': e.output})
        raise e
    # py3 treat the output as bytes type.
    if isinstance(output, bytes):
        output = output.decode('utf-8')
    return output


def get_listener_realserver_mapping(ns_name, listener_ip_port):
    # returned result:
    # actual_member_result = {'rs_ip:listened_port': {
    #   'status': 'UP',
    #   'Forward': forward_type,
    #   'Weight': 5,
    #   'ActiveConn': 0,
    #   'InActConn': 0
    # }}
    try:
        listener_ip, listener_port = listener_ip_port.split(':')
    except ValueError:
        start = listener_ip_port.index('[') + 1
        end = listener_ip_port.index(']')
        listener_ip = listener_ip_port[start:end]
        listener_port = listener_ip_port[end + 2:]
    ip_obj = netaddr.IPAddress(listener_ip)
    output = read_kernel_file(ns_name, KERNEL_LVS_PATH).split('\n')
    ip_to_hex_format = ''
    if ip_obj.version == 4:
        for int_str in listener_ip.split('.'):
            if int(int_str) <= 15:
                str_piece = '0' + hex(int(int_str))[2:].upper()
            else:
                str_piece = hex(int(int_str))[2:].upper()
            ip_to_hex_format += str_piece
    elif ip_obj.version == 6:
        piece_list = []
        for word in ip_obj.words:
            str_len = len(hex(word)[2:])
            if str_len < 4:
                str_piece = '0' * (4 - str_len) + hex(word)[2:].lower()
            else:
                str_piece = hex(word)[2:].lower()
            piece_list.append(str_piece)
        ip_to_hex_format = ":".join(piece_list)
        ip_to_hex_format = '\[' + ip_to_hex_format + '\]'
    port_hex_format = hex(int(listener_port))[2:].upper()
    if len(port_hex_format) < 4:
        port_hex_format = ('0' * (4 - len(port_hex_format)) +
                           port_hex_format)
    idex = ip_to_hex_format + ':' + port_hex_format

    def _hit_identify(line):
        m = re.match(r'^UDP\s+%s\s+\w+' % idex, line)
        if m:
            return True
        return False
    actual_member_result = {}
    find_target_block = False
    result_keys = []
    for line in output:
        if 'RemoteAddress:Port' in line:
            result_keys = re.split(r'\s+',
                                   LVS_KEY_REGEX.findall(line)[0].strip())
        elif line.startswith('UDP') and find_target_block:
            break
        elif line.startswith('UDP') and _hit_identify(line):
            find_target_block = True
        elif find_target_block and line:
            rs_is_ipv4 = True
            all_values = V4_RS_VALUE_REGEX.findall(line)
            # If can not get all_values with ipv4 regex, then this line must be
            # a ipv6 real server record.
            if not all_values:
                all_values = V6_RS_VALUE_REGEX.findall(line)
                rs_is_ipv4 = False

            all_values = all_values[0]
            ip_port = all_values[0]
            result_values = re.split(r"\s+", all_values[1].strip())
            if rs_is_ipv4:
                actual_member_ip_port = ip_port.split(':')
                hex_ip_list = V4_HEX_IP_REGEX.findall(
                    actual_member_ip_port[0])[0]
                ip_string = ''
                for hex_ip in hex_ip_list:
                    ip_string = ip_string + str(int(hex_ip, 16)) + '.'
                ip_string = ip_string[:-1]
                port_string = str(int(actual_member_ip_port[1], 16))
                member_ip_port_string = ip_string + ':' + port_string
            else:
                start = ip_port.index('[') + 1
                end = ip_port.index(']')
                ip_string = ip_port[start:end]
                port_string = ip_port[end + 2:]
                member_ip_port_string = '[' + str(
                    netaddr.IPAddress(ip_string)) + ']:' + str(
                    int(port_string, 16))
            result_key_count = len(result_keys)
            for index in range(result_key_count):
                if member_ip_port_string not in actual_member_result:
                    actual_member_result[
                        member_ip_port_string] = {'status': constants.UP,
                                                  result_keys[index]:
                                                      result_values[index]}
                else:
                    # The other values include the weight
                    actual_member_result[
                        member_ip_port_string][
                        result_keys[index]] = result_values[index]
            continue

    return find_target_block, actual_member_result


def get_udp_listener_resource_ipports_nsname(listener_id):
    # resource_ipport_mapping = {'Listener': {'id': listener-id,
    #                                         'ipport': ipport},
    #                            'Pool': {'id': pool-id},
    #                            'Members': [{'id': member-id-1,
    #                                        'ipport': ipport},
    #                                       {'id': member-id-2,
    #                                        'ipport': ipport}],
    #                            'HealthMonitor': {'id': healthmonitor-id}}
    resource_ipport_mapping = {}
    with open(util.keepalived_lvs_cfg_path(listener_id), 'r') as f:
        cfg = f.read()
        ns_name = NS_REGEX.findall(cfg)[0]
        listener_ip_port = V4_VS_REGEX.findall(cfg)
        if not listener_ip_port:
            listener_ip_port = V6_VS_REGEX.findall(cfg)
        listener_ip_port = listener_ip_port[0] if listener_ip_port else []

        if not listener_ip_port:
            # If not get listener_ip_port from the lvs config file,
            # that means the udp listener's default pool have no enabled member
            # yet. But at this moment, we can get listener_id and ns_name, so
            # for this function, we will just return ns_name
            return resource_ipport_mapping, ns_name

        cfg_line = cfg.split('\n')
        rs_ip_port_list = []
        for line in cfg_line:
            if 'real_server' in line:
                res = V4_RS_REGEX.findall(line)
                if not res:
                    res = V6_RS_REGEX.findall(line)
                rs_ip_port_list.append(res[0])

        resource_type_ids = CONFIG_COMMENT_REGEX.findall(cfg)

        for resource_type, resource_id in resource_type_ids:
            value = {'id': resource_id}
            if resource_type == 'Member':
                resource_type = '%ss' % resource_type
                if resource_type not in resource_ipport_mapping:
                    value = [value]
            if resource_type not in resource_ipport_mapping:
                resource_ipport_mapping[resource_type] = value
            elif resource_type == 'Members':
                resource_ipport_mapping[resource_type].append(value)

        if rs_ip_port_list:
            rs_ip_port_count = len(rs_ip_port_list)
            for index in range(rs_ip_port_count):
                if netaddr.IPAddress(
                        rs_ip_port_list[index][0]).version == 6:
                    rs_ip_port_list[index] = (
                        '[' + rs_ip_port_list[index][0] + ']',
                        rs_ip_port_list[index][1])
                resource_ipport_mapping['Members'][index]['ipport'] = (
                    rs_ip_port_list[index][0] + ':' +
                    rs_ip_port_list[index][1])

        if netaddr.IPAddress(listener_ip_port[0]).version == 6:
            listener_ip_port = (
                '[' + listener_ip_port[0] + ']', listener_ip_port[1])
        resource_ipport_mapping['Listener']['ipport'] = (
            listener_ip_port[0] + ':' + listener_ip_port[1])

    return resource_ipport_mapping, ns_name


def get_udp_listener_pool_status(listener_id):
    (resource_ipport_mapping,
     ns_name) = get_udp_listener_resource_ipports_nsname(listener_id)
    if 'Pool' not in resource_ipport_mapping:
        return {}
    elif 'Members' not in resource_ipport_mapping:
        return {'lvs': {
            'uuid': resource_ipport_mapping['Pool']['id'],
            'status': constants.DOWN,
            'members': {}
        }}

    _, realserver_result = get_listener_realserver_mapping(
        ns_name, resource_ipport_mapping['Listener']['ipport'])
    pool_status = constants.UP
    member_results = {}
    if realserver_result:
        member_ip_port_list = [
            member['ipport'] for member in resource_ipport_mapping['Members']]
        down_member_ip_port_set = set(
            member_ip_port_list) - set(list(realserver_result.keys()))

        for member_ip_port in member_ip_port_list:
            member_id = None
            for member in resource_ipport_mapping['Members']:
                if member['ipport'] == member_ip_port:
                    member_id = member['id']
            if member_ip_port in down_member_ip_port_set:
                status = constants.DOWN
            elif int(realserver_result[member_ip_port]['Weight']) == 0:
                status = constants.DRAIN
            else:
                status = realserver_result[member_ip_port]['status']

            if member_id:
                member_results[member_id] = status
    else:
        pool_status = constants.DOWN
        for member in resource_ipport_mapping['Members']:
            member_results[member['id']] = constants.DOWN

    return {
        'lvs':
        {
            'uuid': resource_ipport_mapping['Pool']['id'],
            'status': pool_status,
            'members': member_results
        }
    }


def get_ipvsadm_info(ns_name, is_stats_cmd=False):
    cmd_list = ['ip', 'netns', 'exec', ns_name, 'ipvsadm', '-Ln']
    if is_stats_cmd:
        cmd_list.append('--stats')
    output = subprocess.check_output(cmd_list, stderr=subprocess.STDOUT)
    if isinstance(output, bytes):
        output = output.decode('utf-8')
    output = output.split('\n')
    fields = []
    # mapping = {'listeneripport': {'Linstener': vs_values,
    #                              'members': [rs_values1, rs_values2]}}
    last_key = None
    value_mapping = dict()
    output_line_num = len(output)

    def split_line(line):
        return re.sub(r'\s+', ' ', line.strip()).split(' ')
    for line_num in range(output_line_num):
        # ipvsadm -Ln
        if 'Flags' in output[line_num]:
            fields = split_line(output[line_num])
        elif fields and 'Flags' in fields and fields.index('Flags') == len(
                fields) - 1:
            fields.extend(split_line(output[line_num]))
        # ipvsadm -Ln --stats
        elif 'Prot' in output[line_num]:
            fields = split_line(output[line_num])
        elif 'RemoteAddress' in output[line_num]:
            start = fields.index('LocalAddress:Port') + 1
            temp_fields = fields[start:]
            fields.extend(split_line(output[line_num]))
            fields.extend(temp_fields)
        # here we get the all fields
        elif constants.PROTOCOL_UDP in output[line_num]:
            # if UDP/TCP in this line, we can know this line is
            # VS configuration.
            vs_values = split_line(output[line_num])
            for value in vs_values:
                if ':' in value:
                    value_mapping[value] = {'Listener': vs_values,
                                            'Members': []}
                    last_key = value
                    break
        # here the line must be a RS which belongs to a VS
        elif '->' in output[line_num] and last_key:
            rs_values = split_line(output[line_num])
            rs_values.remove('->')
            value_mapping[last_key]['Members'].append(rs_values)

    index = fields.index('->')
    vs_fields = fields[:index]
    if 'Flags' in vs_fields:
        vs_fields.remove('Flags')
    rs_fields = fields[index + 1:]
    for key in list(value_mapping.keys()):
        value_mapping[key]['Listener'] = [
            i for i in zip(vs_fields, value_mapping[key]['Listener'])]
        member_res = []
        for member_value in value_mapping[key]['Members']:
            member_res.append([i for i in zip(rs_fields, member_value)])
        value_mapping[key]['Members'] = member_res

    return value_mapping


def get_udp_listeners_stats():
    udp_listener_ids = util.get_udp_listeners()
    need_check_listener_ids = [
        listener_id for listener_id in udp_listener_ids
        if util.is_udp_listener_running(listener_id)]
    ipport_mapping = dict()
    for check_listener_id in need_check_listener_ids:
        # resource_ipport_mapping = {'Listener': {'id': listener-id,
        #                                         'ipport': ipport},
        #                            'Pool': {'id': pool-id},
        #                            'Members': [{'id': member-id-1,
        #                                        'ipport': ipport},
        #                                       {'id': member-id-2,
        #                                        'ipport': ipport}],
        #                            'HealthMonitor': {'id': healthmonitor-id}}
        (resource_ipport_mapping,
         ns_name) = get_udp_listener_resource_ipports_nsname(check_listener_id)
        # If we can not read the lvs configuration from file, that means
        # the pool of this listener may own zero enabled member, but the
        # keepalived process is running. So we need to skip it.
        if not resource_ipport_mapping:
            continue
        ipport_mapping.update({check_listener_id: resource_ipport_mapping})

    # So here, if we can not get any ipport_mapping,
    # we do nothing, just return
    if not ipport_mapping:
        return None

    # contains bout, bin, scur, stot, ereq, status
    # bout(OutBytes), bin(InBytes), stot(Conns) from cmd ipvsadm -Ln --stats
    # scur(ActiveConn) from cmd ipvsadm -Ln
    # status, can see configuration in any cmd, treat it as OPEN
    # ereq is still 0, as UDP case does not support it.
    scur_res = get_ipvsadm_info(constants.AMPHORA_NAMESPACE)
    stats_res = get_ipvsadm_info(constants.AMPHORA_NAMESPACE,
                                 is_stats_cmd=True)
    listener_stats_res = dict()
    for listener_id, ipport in ipport_mapping.items():
        listener_ipport = ipport['Listener']['ipport']
        # This would be in Error, wait for the next loop to sync for the
        # listener at this moment. Also this is for skip the case no enabled
        # member in UDP listener, so we don't check it for failover.
        if listener_ipport not in scur_res or listener_ipport not in stats_res:
            continue

        scur, bout, bin, stot, ereq = 0, 0, 0, 0, 0
        # As all results contain this listener, so its status should be OPEN
        status = constants.OPEN
        # Get scur
        for m in scur_res[listener_ipport]['Members']:
            for item in m:
                if item[0] == 'ActiveConn':
                    scur += int(item[1])

        # Get bout, bin, stot
        for item in stats_res[listener_ipport]['Listener']:
            if item[0] == 'Conns':
                stot = int(item[1])
            elif item[0] == 'OutBytes':
                bout = int(item[1])
            elif item[0] == 'InBytes':
                bin = int(item[1])

        listener_stats_res.update({
            listener_id: {
                'stats': {
                    'bout': bout,
                    'bin': bin,
                    'scur': scur,
                    'stot': stot,
                    'ereq': ereq},
                'status': status}})

    return listener_stats_res
