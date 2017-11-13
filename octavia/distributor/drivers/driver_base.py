# Copyright 2016 IBM Corp.
# Copyright 2017 Rackspace, US Inc.
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

import abc

import six

# This class describes the abstraction of a distributor interface.
# Distributor implementations may be: a noop, a single hardware device,
# a single amphora, or multiple amphora among other options.


@six.add_metaclass(abc.ABCMeta)
class DistributorDriver(object):
    @abc.abstractmethod
    def get_create_distributor_subflow(self):
        """Get a subflow to create a distributor

        :requires: **load_balancer** (object) - Load balancer object
                   associated with this distributor
        :provides: **distributor_id** (string) - The created distributor ID
        :returns: A TaskFlow Flow that will create the distributor

        This method will setup the TaskFlow Flow required to setup the
        database fields and create a distributor should the driver need to
        instantiate one.
        The flow must store the generated distibutor ID in the flow.
        """
        pass

    @abc.abstractmethod
    def get_delete_distributor_subflow(self):
        """Get a subflow that deletes a distributor

        :requires: **distributor_id** (string) - The ID of the distributor
                   to delete
        :returns: A TaskFlow Flow that will delete the distributor

        This method will return a TaskFlow Flow that deletes the distributor
        (if applicable for the driver) and cleans up any associated database
        records.
        """
        pass

    @abc.abstractmethod
    def get_add_vip_subflow(self):
        """Get a subflow that adds a VIP to a distributor

        :requires: **distributor_id** (string) - The ID of the distributor
                   to create the VIP on.
        :requires: **vip** (object) - The VIP object to create on the
                   distributor.
        :requires: **vip_alg** (string) - The optional algorithm to use for
                   this VIP.
        :requires: **vip_persistence** (string) - The persistence type for
                   this VIP.
        :returns: A TaskFlow Flow that will add a VIP to the distributor

        This method will return a TaskFlow Flow that adds a VIP to the
        distributor by perfoming the necessary steps to plug the VIP and
        configure the distributor to start receiving requests on this VIP.
        """
        pass

    @abc.abstractmethod
    def get_remove_vip_subflow(self):
        """Get a subflow that removes a VIP from a distributor

        :requires: **distributor_id** (string) - The ID of the distributor
                   to remove the VIP from.
        :requires: **vip** (object) - The VIP object to remove from the
                   distributor.
        :returns: A TaskFlow Flow that will remove a VIP from the distributor

        This method will return a TaskFlow Flow that removes the VIP from the
        distributor by reconfiguring the distributor and unplugging the
        associated port.
        """
        pass

    @abc.abstractmethod
    def get_register_amphorae_subflow(self):
        """Get a subflow that Registers amphorae with the distributor

        :requires: **distributor_id** (string) - The ID of the distributor
                   to register the amphora on
        :requires: **amphorae** (tuple) - Tuple of amphora objects to
                   register with the distributor.
        :returns: A TaskFlow Flow that will register amphorae with the
                  distributor

        This method will return a TaskFlow Flow that registers amphorae with
        the distributor so it can begin to receive requests from the
        distributor. Amphora should be ready to receive requests prior to
        this call being made.
        """
        pass

    @abc.abstractmethod
    def get_drain_amphorae_subflow(self):
        """Get a subflow that drains connections from amphorae

        :requires: **distributor_id** (string) - The ID of the distributor
                   to drain amphorae from
        :requires: **amphorae** (tuple) - Tuple of amphora objects to drain
                   from distributor.
        :returns: A TaskFlow Flow that will drain the listed amphorae on the
                  distributor

        This method will return a TaskFlow Flow that configures the
        distributor to stop sending new connections to the amphorae in the
        list. Existing connections will continue to pass traffic to the
        amphorae in this list.
        """
        pass

    @abc.abstractmethod
    def get_unregister_amphorae_subflow(self):
        """Get a subflow that unregisters amphorae from a distributor

        :requires: **distributor_id** (string) - The ID of the distributor
                   to unregister amphorae from
        :requires: **amphorae** (tuple) - Tuple of amphora objects to
                   unregister from distributor.
        :returns: A TaskFlow Flow that will unregister amphorae from the
                  distributor

        This method will return a TaskFlow Flow that unregisters amphorae
        from the distributor. Amphorae in this list will immediately stop
        receiving traffic.
        """
        pass
