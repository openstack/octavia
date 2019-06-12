# Copyright 2019 Red Hat, Inc. All rights reserved.
#
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

from octavia_lib.common import constants as lib_consts

from octavia.api.drivers import utils as driver_utils
from octavia.common import constants
from octavia.db import api as db_api
from octavia.db import repositories


def process_get(get_data):
    session = db_api.get_session()

    if get_data[constants.OBJECT] == lib_consts.LOADBALANCERS:
        lb_repo = repositories.LoadBalancerRepository()
        db_lb = lb_repo.get(session, id=get_data[lib_consts.ID],
                            show_deleted=False)
        if db_lb:
            provider_lb = (
                driver_utils.db_loadbalancer_to_provider_loadbalancer(db_lb))
            return provider_lb.to_dict(recurse=True, render_unsets=True)
    elif get_data[constants.OBJECT] == lib_consts.LISTENERS:
        listener_repo = repositories.ListenerRepository()
        db_listener = listener_repo.get(
            session, id=get_data[lib_consts.ID], show_deleted=False)
        if db_listener:
            provider_listener = (
                driver_utils.db_listener_to_provider_listener(db_listener))
            return provider_listener.to_dict(recurse=True, render_unsets=True)
    elif get_data[constants.OBJECT] == lib_consts.POOLS:
        pool_repo = repositories.PoolRepository()
        db_pool = pool_repo.get(session, id=get_data[lib_consts.ID],
                                show_deleted=False)
        if db_pool:
            provider_pool = (
                driver_utils.db_pool_to_provider_pool(db_pool))
            return provider_pool.to_dict(recurse=True, render_unsets=True)
    elif get_data[constants.OBJECT] == lib_consts.MEMBERS:
        member_repo = repositories.MemberRepository()
        db_member = member_repo.get(session, id=get_data[lib_consts.ID],
                                    show_deleted=False)
        if db_member:
            provider_member = (
                driver_utils.db_member_to_provider_member(db_member))
            return provider_member.to_dict(recurse=True, render_unsets=True)
    elif get_data[constants.OBJECT] == lib_consts.HEALTHMONITORS:
        hm_repo = repositories.HealthMonitorRepository()
        db_hm = hm_repo.get(session, id=get_data[lib_consts.ID],
                            show_deleted=False)
        if db_hm:
            provider_hm = (
                driver_utils.db_HM_to_provider_HM(db_hm))
            return provider_hm.to_dict(recurse=True, render_unsets=True)
    elif get_data[constants.OBJECT] == lib_consts.L7POLICIES:
        l7policy_repo = repositories.L7PolicyRepository()
        db_l7policy = l7policy_repo.get(session, id=get_data[lib_consts.ID],
                                        show_deleted=False)
        if db_l7policy:
            provider_l7policy = (
                driver_utils.db_l7policy_to_provider_l7policy(db_l7policy))
            return provider_l7policy.to_dict(recurse=True, render_unsets=True)
    elif get_data[constants.OBJECT] == lib_consts.L7RULES:
        l7rule_repo = repositories.L7RuleRepository()
        db_l7rule = l7rule_repo.get(session, id=get_data[lib_consts.ID],
                                    show_deleted=False)
        if db_l7rule:
            provider_l7rule = (
                driver_utils.db_l7rule_to_provider_l7rule(db_l7rule))
            return provider_l7rule.to_dict(recurse=True, render_unsets=True)
    return {}
