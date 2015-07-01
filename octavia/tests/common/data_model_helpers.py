#    Copyright 2014 Rackspace
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

from octavia.common import data_models


def generate_load_balancer_tree():
    vip = generate_vip()
    amps = [generate_amphora(), generate_amphora()]
    lb = generate_load_balancer(vip=vip, amphorae=amps)
    return lb


LB_SEED = 0


def generate_load_balancer(vip=None, amphorae=None):
    amphorae = amphorae or []
    global LB_SEED
    LB_SEED += 1
    lb = data_models.LoadBalancer(id='lb{0}-id'.format(LB_SEED),
                                  tenant_id='2',
                                  name='lb{0}'.format(LB_SEED),
                                  description='lb{0}'.format(LB_SEED),
                                  vip=vip,
                                  amphorae=amphorae)
    for amp in lb.amphorae:
        amp.load_balancer = lb
        amp.load_balancer_id = lb.id
    if vip:
        vip.load_balancer = lb
        vip.load_balancer_id = lb.id
    return lb


VIP_SEED = 0


def generate_vip(load_balancer=None):
    global VIP_SEED
    VIP_SEED += 1
    vip = data_models.Vip(ip_address='10.0.0.{0}'.format(VIP_SEED),
                          subnet_id='subnet{0}-id'.format(VIP_SEED),
                          port_id='port{0}-id'.format(VIP_SEED),
                          load_balancer=load_balancer)
    if load_balancer:
        vip.load_balancer_id = load_balancer.id
    return vip


AMP_SEED = 0


def generate_amphora(load_balancer=None):
    global AMP_SEED
    AMP_SEED += 1
    amp = data_models.Amphora(id='amp{0}-id'.format(AMP_SEED),
                              compute_id='compute{0}-id'.format(AMP_SEED),
                              status='ACTIVE',
                              lb_network_ip='11.0.0.{0}'.format(AMP_SEED),
                              vrrp_ip='12.0.0.{0}'.format(AMP_SEED),
                              load_balancer=load_balancer)
    if load_balancer:
        amp.load_balancer_id = load_balancer.id
    return amp