#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from octavia_lib.i18n import _
from oslo_config import cfg
from oslo_log import log as logging
import oslo_messaging as messaging
from oslo_messaging.rpc import dispatcher

LOG = logging.getLogger(__name__)
TRANSPORT = None
NOTIFICATION_TRANSPORT = None
NOTIFIER = None


def init():
    global TRANSPORT, NOTIFICATION_TRANSPORT, NOTIFIER
    TRANSPORT = create_transport(get_transport_url())
    NOTIFICATION_TRANSPORT = messaging.get_notification_transport(cfg.CONF)
    NOTIFIER = messaging.Notifier(NOTIFICATION_TRANSPORT)


def cleanup():
    global TRANSPORT, NOTIFICATION_TRANSPORT, NOTIFIER
    if TRANSPORT is not None:
        TRANSPORT.cleanup()
    if NOTIFICATION_TRANSPORT is not None:
        NOTIFICATION_TRANSPORT.cleanup()
    TRANSPORT = NOTIFICATION_TRANSPORT = NOTIFIER = None


def get_transport_url(url_str=None):
    return messaging.TransportURL.parse(cfg.CONF, url_str)


def get_client(target, version_cap=None, serializer=None,
               call_monitor_timeout=None):

    assert TRANSPORT is not None, _("'TRANSPORT' must not be None")

    return messaging.get_rpc_client(
        TRANSPORT, target, version_cap=version_cap,
        serializer=serializer,
        call_monitor_timeout=call_monitor_timeout)


def get_server(target, endpoints, executor='threading',
               access_policy=dispatcher.DefaultRPCAccessPolicy,
               serializer=None):
    assert TRANSPORT is not None, _("'TRANSPORT' must not be None")

    return messaging.get_rpc_server(TRANSPORT,
                                    target,
                                    endpoints,
                                    executor=executor,
                                    serializer=serializer,
                                    access_policy=access_policy)


def get_notifier(service=None, host=None, publisher_id=None):
    assert NOTIFIER is not None, _("'NOTIFIER' must not be None")

    return NOTIFIER.prepare()


def create_transport(url):
    return messaging.get_rpc_transport(cfg.CONF, url=url)
