..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

========================
Network Driver Interface
========================

Include the URL of your launchpad blueprint:

https://blueprints.launchpad.net/octavia/+spec/network-driver-interface

We need a generic interface in which to create networking resources.  This is
to allow implementations that can support different networking infrastructures
that accomplish frontend and backend connectivity.

Problem description
===================

There is a need to define a generic interface for a networking service.  An
Octavia controller should not know what networking infrastructure is being used
underneath.  It should only know an interface.  This interface is needed to
support differing networking infrastructures.


Proposed change
===============
In order to make the network driver as genericly functional as possible, it is
broken down into methods that Octavia will need at a high level to accomplish
frontend and backend connectivity. The idea is that to implement these methods
it may require multiple requests to the networking service to accomplish the
end result.  The interface is meant to promote stateless implementations and
suffer no issues being run in parallel.

In the future we would like to create a common module that implementations of
this interface can call to setup a taskflow engine to promote using a common
taskflow configuration.  That however, can be left once this has had time
to mature.

Existing data model:

* class VIP
    * load_balancer_id
    * ip_address
    * network_id - (neutron subnet)
    * port_id - (neutron port)

* class Amphora
    * load_balancer_id
    * compute_id
    * lb_network_ip
    * status
    * vrrp_ip - if an active/passive topology, this is the ip where the vrrp
                communication between peers happens
    * ha_ip - this is the highly available IP.  In an active/passive topology
              it most likely exists on the MASTER amphora and on failure
              it will be raised on the SLAVE amphora.  In an active/active
              topology it may exist on both amphorae.  In the end, it is up
              to the amphora driver to decide how to use this.

New data models:

* class Interface
    * id
    * network_id - (neutron subnet)
    * amphora_id
    * fixed_ips

* class Delta
    * amphora_id
    * compute_id
    * add_nics
    * delete_nics

* class Network
    * id
    * name
    * subnets - (list of subnet ids)
    * tenant_id
    * admin_state_up
    * provider_network_type
    * provider_physical_network
    * provider_segmentation_id
    * router_external
    * mtu

* class Subnet
    * id
    * name
    * network_id
    * tenant_id
    * gateway_ip
    * cidr
    * ip_version

* class Port
    * id
    * name
    * device_id
    * device_owner
    * mac_address
    * network_id
    * status
    * tenant_id
    * admin_state_up
    * fixed_ips - list of FixedIP objects

* FixedIP
    * subnet_id
    * ip_address

* AmphoraNetworkConfig
    * amphora - Amphora object
    * vip_subnet - Subnet object
    * vip_port - Port object
    * vrrp_subnet - Subnet object
    * vrrp_port - Port object
    * ha_subnet - Subnet object
    * ha_port - Port object

New Exceptions defined in the octavia.network package:

* NetworkException - Base Exception
* PlugVIPException
* UnplugVIPException
* PluggedVIPNotFound
* AllocateVIPException
* DeallocateVIPException
* PlugNetworkException
* UnplugNetworkException
* VIPInUse
* PortNotFound
* SubnetNotFound
* NetworkNotFound
* AmphoraNotFound


This class defines the methods for a fully functional network driver.
Implementations of this interface can expect a rollback to occur if any of
the non-nullipotent methods raise an exception.

class AbstractNetworkDriver

* plug_vip(loadbalancer, vip)

    * Sets up the routing of traffic from the vip to the load balancer and its
      amphorae.
    * loadbalancer - instance of data_models.LoadBalancer

        * this is to keep the parameters as generic as possible so different
          implementations can use different properties of a load balancer. In
          the future we may want to just take in a list of amphora compute
          ids and the vip data model.

    * vip = instance of a VIP
    * returns list of Amphora
    * raises PlugVIPException, PortNotFound

* unplug_vip(loadbalancer, vip)

    * Removes the routing of traffic from the vip to the load balancer and its
      amphorae.
    * loadbalancer = instance of a data_models.LoadBalancer
    * vip = instance of a VIP
    * returns None
    * raises UnplugVIPException, PluggedVIPNotFound

* allocate_vip(loadbalancer)

    * Allocates a virtual ip and reserves it for later use as the frontend
      connection of a load balancer.
    * loadbalancer = instance of a data_models.LoadBalancer
    * returns VIP instance
    * raises AllocateVIPException, PortNotFound, SubnetNotFound

* deallocate_vip(vip)

    * Removes any resources that reserved this virtual ip.
    * vip = VIP instance
    * returns None
    * raises DeallocateVIPException, VIPInUse

* plug_network(compute_id, network_id, ip_address=None)

    * Connects an existing amphora to an existing network.
    * compute_id = id of an amphora in the compute service
    * network_id = id of the network to attach
    * ip_address = ip address to attempt to be assigned to interface
    * returns Interface instance
    * raises PlugNetworkException, AmphoraNotFound, NetworkNotFound

* unplug_network(compute_id, network_id, ip_address=None)

    * Disconnects an existing amphora from an existing network. If ip_address
      is not specified then all interfaces on that network will be unplugged.
    * compute_id = id of an amphora in the compute service to unplug
    * network_id = id of network to unplug amphora
    * ip_address = ip address of interface to unplug
    * returns None
    * raises UnplugNetworkException, AmphoraNotFound, NetworkNotFound,
             NetworkException

* get_plugged_networks(compute_id):

    * Retrieves the current plugged networking configuration
    * compute_id = id of an amphora in the compute service
    * returns = list of Instance instances

* update_vip(loadbalancer):

    * Hook for the driver to update the VIP information based on the state
      of the passed in loadbalancer
    * loadbalancer: instance of a data_models.LoadBalancer

* get_network(network_id):

    * Retrieves the network from network_id
    * network_id = id of an network to retrieve
    * returns = Network data model
    * raises NetworkException, NetworkNotFound

* get_subnet(subnet_id):

    * Retrieves the subnet from subnet_id
    * subnet_id = id of a subnet to retrieve
    * returns = Subnet data model
    * raises NetworkException, SubnetNotFound

* get_port(port_id):

    * Retrieves the port from port_id
    * port_id = id of a port to retrieve
    * returns = Port data model
    * raises NetworkException, PortNotFound

* failover_preparation(amphora):

    * Prepare an amphora for failover
    * amphora = amphora data model
    * returns = None
    * raises PortNotFound

Alternatives
------------

* Straight Neutron Interface (networks, subnets, ports, floatingips)
* Straight Nova-Network Interface (network, fixed_ips, floatingips)

Data model impact
-----------------

* The Interface data model defined above will just be a class.  We may later
  decide that it needs to be stored in the database, but we can optimize on
  that in a later review if needed.

REST API impact
---------------

None

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

None

Performance Impact
------------------

None

Other deployer impact
---------------------

Need a service account to own the resources these methods create.

Developer impact
----------------

This will be creating an interface in which other code will be creating
network resources.


Implementation
==============

Assignee(s)
-----------

brandon-logan

Work Items
----------

Define interface


Dependencies
============

None


Testing
=======

None


Documentation Impact
====================

Just docstrings on methods.


References
==========

None
