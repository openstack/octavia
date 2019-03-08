# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy
# of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import copy
import itertools
import operator

from keystoneauth1 import loading as ks_loading
from oslo_config import cfg

import octavia.certificates.common.local
import octavia.common.config
from octavia.common import constants


def list_opts():
    return [
        ('DEFAULT',
         itertools.chain(octavia.common.config.core_opts)),
        ('api_settings', octavia.common.config.api_opts),
        ('amphora_agent', octavia.common.config.amphora_agent_opts),
        ('networking', octavia.common.config.networking_opts),
        ('oslo_messaging', octavia.common.config.oslo_messaging_opts),
        ('haproxy_amphora', octavia.common.config.haproxy_amphora_opts),
        ('health_manager', octavia.common.config.healthmanager_opts),
        ('controller_worker', octavia.common.config.controller_worker_opts),
        ('task_flow', octavia.common.config.task_flow_opts),
        ('certificates', itertools.chain(
            octavia.common.config.certificate_opts,
            octavia.certificates.common.local.certgen_opts)),
        ('house_keeping', octavia.common.config.house_keeping_opts),
        ('keepalived_vrrp', octavia.common.config.keepalived_vrrp_opts),
        ('anchor', octavia.common.config.anchor_opts),
        ('nova', octavia.common.config.nova_opts),
        ('neutron', octavia.common.config.neutron_opts),
        ('glance', octavia.common.config.glance_opts),
        ('quotas', octavia.common.config.quota_opts),
        ('audit', octavia.common.config.audit_opts),
        ('driver_agent', octavia.common.config.driver_agent_opts),
        add_auth_opts(),
    ]


def add_auth_opts():
    opts = ks_loading.register_session_conf_options(
        cfg.CONF, constants.SERVICE_AUTH)
    opt_list = copy.deepcopy(opts)
    opt_list.insert(0, ks_loading.get_auth_common_conf_options()[0])
    # NOTE(mhickey): There are a lot of auth plugins, we just generate
    # the config options for a few common ones
    plugins = ['password', 'v2password', 'v3password']
    for name in plugins:
        for plugin_option in ks_loading.get_auth_plugin_conf_options(name):
            if all(option.name != plugin_option.name for option in opt_list):
                opt_list.append(plugin_option)
    opt_list.sort(key=operator.attrgetter('name'))
    return (constants.SERVICE_AUTH, opt_list)
