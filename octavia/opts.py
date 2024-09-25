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

import itertools

from keystoneauth1 import loading as ks_loading

import octavia.certificates.common.local
import octavia.common.config
from octavia.common import constants


def list_opts():
    return [
        ('DEFAULT',
         itertools.chain(octavia.common.config.core_opts)),
        ('api_settings', octavia.common.config.api_opts),
        ('amphora_agent', octavia.common.config.amphora_agent_opts),
        ('compute', octavia.common.config.compute_opts),
        ('networking', octavia.common.config.networking_opts),
        ('oslo_messaging', octavia.common.config.oslo_messaging_opts),
        ('haproxy_amphora', octavia.common.config.haproxy_amphora_opts),
        ('health_manager', octavia.common.config.health_manager_opts),
        ('controller_worker', octavia.common.config.controller_worker_opts),
        ('task_flow', octavia.common.config.task_flow_opts),
        ('certificates', itertools.chain(
            octavia.common.config.certificate_opts,
            octavia.certificates.common.local.certgen_opts)),
        ('house_keeping', octavia.common.config.house_keeping_opts),
        ('keepalived_vrrp', octavia.common.config.keepalived_vrrp_opts),
        ('nova', octavia.common.config.nova_opts),
        ('cinder', octavia.common.config.cinder_opts),
        ('glance', octavia.common.config.glance_opts),
        ('neutron', itertools.chain(
            octavia.common.config.neutron_opts,
            get_ksa_opts(True))),
        ('quotas', octavia.common.config.quota_opts),
        ('audit', octavia.common.config.audit_opts),
        ('driver_agent', octavia.common.config.driver_agent_opts),
        (constants.SERVICE_AUTH, get_ksa_opts()),
    ]


def get_ksa_opts(adapter=False):
    opts = (
        ks_loading.get_session_conf_options() +
        ks_loading.get_auth_common_conf_options() +
        ks_loading.get_auth_plugin_conf_options('password') +
        ks_loading.get_auth_plugin_conf_options('v2password') +
        ks_loading.get_auth_plugin_conf_options('v3password')
    )
    if adapter:
        opts += ks_loading.get_adapter_conf_options(include_deprecated=False)
    return opts
