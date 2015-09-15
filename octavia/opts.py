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

import octavia.common.config


def list_opts():
    return [
        ('DEFAULT',
         itertools.chain(octavia.common.config.core_opts)),
        ('amphora_agent', octavia.common.config.amphora_agent_opts),
        ('networking', octavia.common.config.networking_opts),
        ('oslo_messaging', octavia.common.config.oslo_messaging_opts),
        ('keystone_authtoken_v3',
         octavia.common.config.keystone_authtoken_v3_opts),
        ('haproxy_amphora', octavia.common.config.haproxy_amphora_opts),
        ('health_manager', octavia.common.config.healthmanager_opts),
        ('controller_worker', octavia.common.config.controller_worker_opts),
        ('task_flow', octavia.common.config.task_flow_opts),
        ('certificates', octavia.common.config.certificate_opts),
        ('house_keeping', octavia.common.config.house_keeping_opts)
    ]
