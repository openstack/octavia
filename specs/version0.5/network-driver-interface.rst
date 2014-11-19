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
Octavia controller should not know what networking infrastucture is being used
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

New data model:

* class Interface
    * id
    * network_id - (neutron subnet)
    * amphora_id
    * ip_address - (IPv4 or IPv6)

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
* NetworkNotFound
* VIPConfigurationNotFound
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
    * returns VIP instance
    * raises PlugVIPException

* unplug_vip(loadbalancer, vip)

    * Removes the routing of traffic from the vip to the load balancer and its
      amphorae.
    * loadbalancer = instance of a data_models.LoadBalancer
    * vip = instance of a VIP
    * returns None
    * raises UnplugVIPException, PluggedVIPNotFound

* allocate_vip(port_id=None, network_id=None, ip_address=None)

    * Allocates a virtual ip and reserves it for later use as the frontend
      connection of a load balancer.
    * port_id = id of port that has already been created.  If this is
      provided, it will be used regardless of the other parameters.
    * network_id = if port_id is not provided, this should be provided
      to create the virtual IP on this network.
    * ip_address = will attempt to allocate this specific IP address
    * returns VIP instance
    * raises AllocateVIPException, PortNotFound, NetworkNotFound

* deallocate_vip(vip)

    * Removes any resources that reserved this virtual ip.
    * vip = VIP instance
    * returns None
    * raises DeallocateVIPException, VIPInUse, VIPConfigurationNotFound

* plug_network(amphora_id, network_id, ip_address=None)

    * Connects an existing amphora to an existing network.
    * amphora = id of an amphora in the compute service
    * network_id = id of the network to attach
    * ip_address = ip address to attempt to be assigned to interface
    * returns Interface instance
    * raises PlugNetworkException, AmphoraNotFound, NetworkNotFound

* unplug_network(amphora_id, network_id)

    * Disconnects an existing amphora from an existing network.
    * amphora = id of an amphora in the compute service to unplug
    * network_id = id of network to unplug amphora
    * returns None
    * raises UnplugNetworkException, AmphoraNotFound, NetworkNotFound

* get_plugged_networks(amphora_id):

    * Retrieves the current plugged networking configuration
    * amphora_id = id of an amphora in the compute service
    * returns = list of Instance instances
    * raises AmphoraNotFound

Alternatives
------------

* Straight Neutron Interface (networks, subnets, ports, floatingips)
* Straight Nova-Network Interface (network, fixed_ips, floatingips)

Data model impact
-----------------

* The Interface data model defined above will just be a class.  We may later
  decide that it needs to be stored in the database, but we can optimize on
  that in a later review if needed.
* Remove floating_ip_id from VIP model and migration
* Remove floating_ip_network_id from VIP model and migration
* Rename net_port_id to just port_id in VIP model and migration
* Rename subnet_id to network_id in VIP model and migration

REST API impact
---------------

* Remove floating_ip_id from WSME VIP type
* Remove floating_ip_network_id from WSME VIP type

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
