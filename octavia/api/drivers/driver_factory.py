# Copyright 2018 Rackspace, US Inc.
#
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

from oslo_config import cfg
from oslo_log import log as logging
from stevedore import driver as stevedore_driver
from wsme import types as wtypes

from octavia.common import exceptions

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


def get_driver(provider):
    # If this came in None it must be a load balancer that existed before
    # provider support was added. These must be of type 'amphora' and not
    # whatever the current "default" is set to.
    if isinstance(provider, wtypes.UnsetType):
        provider = CONF.api_settings.default_provider_driver
    elif not provider:
        provider = 'amphora'

    if provider not in CONF.api_settings.enabled_provider_drivers:
        LOG.warning("Requested provider driver '%s' was not enabled in the "
                    "configuration file.", provider)
        raise exceptions.ProviderNotEnabled(prov=provider)

    try:
        driver = stevedore_driver.DriverManager(
            namespace='octavia.api.drivers',
            name=provider,
            invoke_on_load=True).driver
        driver.name = provider
    except Exception as e:
        LOG.error('Unable to load provider driver %s due to: %s',
                  provider, e)
        raise exceptions.ProviderNotFound(prov=provider)
    return driver
