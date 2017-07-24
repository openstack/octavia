#    Copyright 2016 Intel
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

from wsme import types as wtypes
from wsmeext import pecan as wsme_pecan

from octavia.api.v2.controllers import amphora
from octavia.api.v2.controllers import base
from octavia.api.v2.controllers import flavor_profiles
from octavia.api.v2.controllers import flavors
from octavia.api.v2.controllers import health_monitor
from octavia.api.v2.controllers import l7policy
from octavia.api.v2.controllers import listener
from octavia.api.v2.controllers import load_balancer
from octavia.api.v2.controllers import pool
from octavia.api.v2.controllers import provider
from octavia.api.v2.controllers import quotas


class BaseV2Controller(base.BaseController):
    loadbalancers = None
    listeners = None
    pools = None
    l7policies = None
    healthmonitors = None
    quotas = None

    def __init__(self):
        super(BaseV2Controller, self).__init__()
        self.loadbalancers = load_balancer.LoadBalancersController()
        self.listeners = listener.ListenersController()
        self.pools = pool.PoolsController()
        self.l7policies = l7policy.L7PolicyController()
        self.healthmonitors = health_monitor.HealthMonitorController()
        self.quotas = quotas.QuotasController()
        self.providers = provider.ProviderController()
        self.flavors = flavors.FlavorsController()
        self.flavorprofiles = flavor_profiles.FlavorProfileController()

    @wsme_pecan.wsexpose(wtypes.text)
    def get(self):
        return "v2"


class OctaviaV2Controller(base.BaseController):
    amphorae = None

    def __init__(self):
        super(OctaviaV2Controller, self).__init__()
        self.amphorae = amphora.AmphoraController()

    @wsme_pecan.wsexpose(wtypes.text)
    def get(self):
        return "v2"


class V2Controller(BaseV2Controller):
    lbaas = None

    def __init__(self):
        super(V2Controller, self).__init__()
        self.lbaas = BaseV2Controller()
        self.octavia = OctaviaV2Controller()
