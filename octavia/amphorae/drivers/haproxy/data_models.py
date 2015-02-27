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

import octavia.common.data_models as models


class Topology(models.BaseDataModel):

    def __init__(self, hostname=None, uuid=None, topology=None, role=None,
                 ip=None, ha_ip=None):
        self.hostname = hostname
        self.uuid = uuid
        self.topology = topology
        self.role = role
        self.ip = ip
        self.ha_ip = ha_ip


class Info(models.BaseDataModel):

    def __init__(self, hostname=None, uuid=None, version=None,
                 api_version=None):
        self.hostname = hostname
        self.uuid = uuid
        self.version = version
        self.api_version = api_version


class Details(models.BaseDataModel):

    def __init__(self, hostname=None, uuid=None, version=None,
                 api_version=None, network_tx=None, network_rx=None,
                 active=None, haproxy_count=None, cpu=None, memory=None,
                 disk=None, load=None, listeners=None, packages=None):
        self.hostname = hostname
        self.uuid = uuid,
        self.version = version
        self.api_version = api_version
        self.network_tx = network_tx
        self.network_rx = network_rx
        self.active = active
        self.haproxy_count = haproxy_count
        self.cpu = cpu
        self.memory = memory
        self.disk = disk
        self.load = load or []
        self.listeners = listeners or []
        self.packages = packages or []


class CPU(models.BaseDataModel):

    def __init__(self, total=None, user=None, system=None, soft_irq=None):
        self.total = total
        self.user = user
        self.system = system
        self.soft_irq = soft_irq


class Memory(models.BaseDataModel):

    def __init__(self, total=None, free=None, available=None, buffers=None,
                 cached=None, swap_used=None, shared=None, slab=None,
                 committed_as=None):
        self.total = total
        self.free = free
        self.available = available
        self.buffers = buffers
        self.cached = cached
        self.swap_used = swap_used
        self.shared = shared
        self.slab = slab
        self.committed_as = committed_as


class Disk(models.BaseDataModel):

    def __init__(self, used=None, available=None):
        self.used = used
        self.available = available


class ListenerStatus(models.BaseDataModel):

    def __init__(self, status=None, uuid=None, provisioning_status=None,
                 type=None, pools=None):
        self.status = status
        self.uuid = uuid
        self.provisioning_status = provisioning_status
        self.type = type
        self.pools = pools or []


class Pool(models.BaseDataModel):

    def __init__(self, uuid=None, status=None, members=None):
        self.uuid = uuid
        self.status = status
        self.members = members or []
