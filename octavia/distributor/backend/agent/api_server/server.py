# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License.

"""HTTP API for the OVS distributor agent."""

import flask
from oslo_config import cfg
from werkzeug import exceptions

from octavia.distributor.backend.agent.api_server import open_flow

CONF = cfg.CONF
CONF.import_group('distributor', 'octavia.common.config')


class Server:
    def __init__(self):
        self.app = flask.Flask(__name__)
        try:
            open_flow.restore_state()
        except Exception:
            # OVS may still be starting. The first control request retries
            # the same restoration path through the plug operation.
            self.app.logger.warning('Distributor state restoration deferred',
                                    exc_info=True)
        self.app.add_url_rule('/0.5/plug/vip/<vip>',
                              view_func=self.post_plug_vip, methods=['POST'])
        self.app.add_url_rule('/0.5/unplug/vip/<vip>',
                              view_func=self.pre_unplug_vip, methods=['POST'])
        self.app.add_url_rule('/0.5/register/vip/<vip>',
                              view_func=self.register_amphora,
                              methods=['POST'])
        self.app.add_url_rule('/0.5/unregister/vip/<vip>',
                              view_func=self.unregister_amphora,
                              methods=['POST'])
        self.app.add_url_rule('/0.5/info', view_func=self.info,
                              methods=['GET'])
        self.app.add_url_rule('/0.5/diagnostics',
                              view_func=self.diagnostics,
                              methods=['GET'])

    @staticmethod
    def _json():
        data = flask.request.get_json(silent=True)
        if not isinstance(data, dict):
            raise exceptions.BadRequest(description='JSON object required')
        return data

    def post_plug_vip(self, vip):
        data = self._json()
        required = ('mac_address', 'lb_id', 'subnet_cidr', 'gateway')
        if any(not data.get(key) for key in required):
            raise exceptions.BadRequest(description='Incomplete VIP data')
        interface = open_flow.interface_for_mac(
            data['mac_address'],
            data.get('interface', CONF.distributor.frontend_interface))
        result = open_flow.post_plug_vip(
            interface, vip, data['mac_address'],
            data['subnet_cidr'], data['gateway'],
            data.get('cluster_min_size', 2),
            bridge=open_flow.bridge_name(data['lb_id']))
        return flask.jsonify(result), 202

    def pre_unplug_vip(self, vip):
        data = self._json()
        interface = data.get('interface', CONF.distributor.frontend_interface)
        if interface == 'auto':
            state = open_flow.get_status(interface).get('state', {})
            vip_state = state.get('vips', {}).get(vip, {})
            interface = vip_state.get('interface', interface)
        open_flow.pre_uplug_vip(
            interface, vip, data.get('mac_address', ''))
        return flask.jsonify({'message': 'OK'}), 202

    def register_amphora(self, vip):
        data = self._json()
        required = ('amphora_mac', 'mac_address', 'subnet_cidr', 'gateway',
                    'lb_id')
        if any(not data.get(key) for key in required):
            raise exceptions.BadRequest(description='Incomplete amphora data')
        interface = open_flow.interface_for_mac(
            data['mac_address'],
            data.get('interface', CONF.distributor.frontend_interface))
        result = open_flow.register_amphora(
            vip, data['mac_address'],
            interface,
            data['subnet_cidr'], data['gateway'], data['amphora_mac'],
            data.get('cluster_min_size', 2),
            bridge=open_flow.bridge_name(data['lb_id']))
        return flask.jsonify(result), 202

    def unregister_amphora(self, vip):
        data = self._json()
        if not data.get('amphora_mac'):
            raise exceptions.BadRequest(description='amphora_mac required')
        interface = data.get('interface', CONF.distributor.frontend_interface)
        if interface == 'auto':
            state = open_flow.get_status(interface).get('state', {})
            vip_state = state.get('vips', {}).get(vip, {})
            interface = vip_state.get('interface', interface)
        result = open_flow.unregister_amphora(
            vip, data.get('mac_address', ''),
            interface,
            data.get('subnet_cidr', ''), data.get('gateway', ''),
            data['amphora_mac'], data.get('cluster_min_size', 2))
        return flask.jsonify(result), 202

    def info(self):
        return flask.jsonify(
            open_flow.get_status(CONF.distributor.frontend_interface))

    def diagnostics(self):
        state = open_flow.get_status(CONF.distributor.frontend_interface)
        return flask.jsonify({
            'api_version': '0.5',
            'bridge': state.get('bridge'),
            'vips': len(state.get('state', {}).get('vips', {})),
        })
