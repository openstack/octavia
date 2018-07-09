..
     This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=================================
Provider Flavor Framework
=================================

https://blueprints.launchpad.net/octavia/+spec/octavia-lbaas-flavors

A Provider Flavor framework provides a mechanism for providers to specify
capabilities that are not currently handled via the octavia api. It allows
the operators to enable capabilities that may possibly be unique to a
particular provider or simply just not available at the moment within
octavia.  If it is a common feature it is highly encouraged to have the
non-existing features implemented via the standard Octavia api.  In
addition operators can configure different flavors from a maintained list
of provider capabilities.  This framework enables providers to supply new
features with speed to market and provides operators with an ease of use
experience.


Problem description
===================

Flavors are used in various services for specifying service capabilities
and other parameters.  Having the ability to create loadbalancers with
various capabilities (such as HA, throughput or ddos protection) gives
users a way to better plan their LB services and get a benefit of LBaaS
functions which are not a part of Octavia API.  Since Octavia will become
the new OpenStack LBaaS API, a new flavors API should be developed inside
Octavia.

As for now, Octavia does not support multi providers.  The ability to
define different LBaaS providers is a mandatory feature for Octavia to be
Openstack LbaaS API. Therefore, this spec depends on adding multi providers
support to Octavia.  Service providers will be configured via Octavia
configuration file.

Its important to mention that adding flavors capability to Octavia is not
actually dependent on the work for LBaaS API spinout, from Neutron to
Octavia, to be completed. This capability can be added to Octavia but not
actually used until the API spinout is complete and Octavia becomes the
official OpenStack LBaaS API.

This spec is based on two existing specs from neutron:

`Service Flavor Framework
<http://specs.openstack.org/openstack/neutron-specs/specs/liberty/neutron-flavor-framework.html>`__
`Flavor framework - Templates and meta-data
<http://specs.openstack.org/openstack/neutron-specs/specs/mitaka/neutron-flavor-framework-templates.html>`__

However, this is a spec for the first and basic flavors support.
Following capabilities are not part of this spec:

* Providing parameterized metainfo templates for provider profiles.
* Providing meta data for specific LBaaS object as part of its creation.


Proposed change
===============

The Provider Flavor framework enables the ability to create distinct
provider flavor profiles of supported parameters.  Operators will have the
ability to query the provider driver interface for a list of supported
parameters. Operators can view the said list by provider and create flavors
by selecting one or many parameters from the list. The parameters that will
be used to enable specific functionality will be json type in transit and
at rest. This json payload is assigned to a provider and a flavor name.
Users then have the option of selecting from any of the existing flavors
and submitting the selected flavor upon the creation of the load balancer.
The following flavor name examples can be, but not limited to dev, stage,
prod or bronze, silver, gold.  A provider can have many flavor names and a
flavor name can be used by only one provider.  Each provider/flavor pair is
assigned a group of meta-parameters and forms a flavor profile. The flavor
name or id is submitted when creating a load balancer.

The proposal is to add LBaaS service flavoring to Octavia.
This will include following aspects:

* Adding new flavors API to Octavia API
* Adding flavors models to Octavia
* Adding flavors db tables to Octavia database
* Adding DB migration for new DB objects
* Ensuring backwards compatibility for loadbalancer objects which were
  created before flavors support. This is for both cases, when loadbalancer
  was created before multi providers support and when loadbalancer was
  created with certain provider.
* Adding default entries to DB tables representing the default Octavia
  flavor and default Octavia provider profile.
* Adding "default" flavor to devstack plugin.

A sample use case of the operator flavor workflow would be the following:

* The operator queries the provider capabilities
* The operator create flavor profile
* The flavor profile is validated with provider driver
* The flavor profile is stored in octavia db
* The end user creates lb with the flavor
* The profile is validated against driver once again, upon every lb-create


Alternatives
------------

An alternative is patchset-5 within this very same spec.  While the concept
is the same, the design is different.  Differences with patchset-5 to note
is primarily with the data schemas.  With patchset-5 the metadata that is
passed to the load balancer has a one to one relationship with the
provider.  Also key/values pairs are stored in json as opposed to in
normalized tables. And a list of provider supported capabilities is not
maintained.  That said this alternative design is an option.


Data model impact
-----------------

DB table 'flavor_profile' introduced to represent the profile that is
created when combining a provider with a flavor.

    +--------------------+--------------+------+---------+----------+
    | Field              | Type         | Null | Key     | Default  |
    +--------------------+--------------+------+---------+----------+
    | id                 | varchar(36)  | NO   | PK      | generated|
    +--------------------+--------------+------+---------+----------+
    | provider_name      | varchar(255) | NO   |         |          |
    +--------------------+--------------+------+---------+----------+
    | metadata           | varchar(4096)| NO   |         |          |
    +--------------------+--------------+------+---------+----------+

.. note:: The provider_name is the name the driver is advertised as
          via setuptools entry points.  This will be validated when
          the operator uploads the flavor profile and the metadata
          is validated.

DB table 'flavor' introduced to represent flavors.

    +--------------------+--------------+------+-----+----------+
    | Field              | Type         | Null | Key | Default  |
    +--------------------+--------------+------+-----+----------+
    | id                 | varchar(36)  | NO   | PK  | generated|
    +--------------------+--------------+------+-----+----------+
    | name               | varchar(255) | NO   | UK  |          |
    +--------------------+--------------+------+-----+----------+
    | description        | varchar(255) | YES  |     | NULL     |
    +--------------------+--------------+------+-----+----------+
    | enabled            | tinyint(1)   | NO   |     | True     |
    +--------------------+--------------+------+-----+----------+
    | flavor_profile_id  | varchar(36)  | NO   | FK  |          |
    +--------------------+--------------+------+-----+----------+


DB table attribute 'load_balancer.flavor_id' introduced to link a
flavor to a load_balancer.

    +--------------------+--------------+------+-----+----------+
    | Field              | Type         | Null | Key | Default  |
    +--------------------+--------------+------+-----+----------+
    | flavor_id          | varchar(36)  | YES  | FK1 |  NULL    |
    +--------------------+--------------+------+-----+----------+


REST API impact
---------------

FLAVOR(/flavors)

+-----------------+-------+---------+---------+------------+-----------------+
|Attribute        |Type   |Access   |Default  |Validation/ |Description      |
|Name             |       |         |Value    |Conversion  |                 |
+=================+=======+=========+=========+============+=================+
|id               |string |RO, admin|generated|N/A         |identity         |
|                 |(UUID) |         |         |            |                 |
+-----------------+-------+---------+---------+------------+-----------------+
|name             |string |RO, admin|''       |string      |human-readable   |
|                 |       |         |         |            |name             |
+-----------------+-------+---------+---------+------------+-----------------+
|description      |string |RO, admin|''       |string      |human-readable   |
|                 |       |         |         |            |description      |
+-----------------+-------+---------+---------+------------+-----------------+
|enabled          |bool   |RO, admin|true     |bool        |toggle           |
|                 |       |         |         |            |                 |
+-----------------+-------+---------+---------+------------+-----------------+
|flavor_profile_id|string |RO, admin|         |string      |human-readable   |
|                 |       |         |         |            |flavor_profile_id|
+-----------------+-------+---------+---------+------------+-----------------+

FLAVOR PROFILE(/flavorprofiles)

+-----------------+--------+---------+---------+------------+---------------+
|Attribute        |Type    |Access   |Default  |Validation/ |Description    |
|Name             |        |         |Value    |Conversion  |               |
+=================+========+=========+=========+============+===============+
|id               |string  |admin    |generated|N/A         |identity       |
|                 |(UUID)  |         |         |            |               |
+-----------------+--------+---------+---------+------------+---------------+
|name             |string  |admin    |''       |string      |human-readable |
|                 |        |         |         |            |name           |
+-----------------+--------+---------+---------+------------+---------------+
|provider-id      |string  |admin    |''       |string      |human-readable |
|                 |        |         |         |            |provider-id    |
+-----------------+--------+---------+---------+------------+---------------+
|metadata         |string  |admin    |{}       |json        |flavor meta    |
|                 |        |         |         |            |parameters     |
+-----------------+--------+---------+---------+------------+---------------+

Security impact
---------------

The policy.json will be updated to allow all users to query the flavor
listing and request details about a specific flavor entry, with the
exception of flavor metadata. All other REST points for
create/update/delete operations will be admin only. Additionally, the CRUD
operations for Provider Profiles will be restricted to administrators.


Notifications impact
--------------------

N/A

Other end user impact
---------------------

An existing LB cannot be updated with a different flavor profile.  A flavor
profile can only be applied upon the creation of the LB.  The flavor
profile will be immutable.

Performance Impact
------------------

There will be a minimal overhead incurred when the logical representation is
scheduled onto the actual backend. Once the backend is selected, direct
communications will occur via driver calls.

IPv6 impact
-----------

None

Other deployer impact
---------------------

The deployer will need to craft flavor configurations that they wish to expose
to their users. During migration the existing provider configurations will be
converted into basic flavor types. Once migrated, the deployer will have the
opportunity to modify the flavor definitions.

Developer impact
----------------

The expected developer impact should be minimal as the framework only impacts
the initial scheduling of the logical service onto a backend. The driver
implementations should remain unchanged except for the addition of the metainfo
call.

Community impact
----------------

This proposal allows operators to offer services beyond those
directly implemented, and to do so in a way that does not increase
community maintenance or burden.

Provider driver impact
----------------------

The provider driver should have the following abilities:

* Provide an interface to describe the available supported metadata options
* Provide an interface to validate the flavor metadata
* Be able to accept the flavor metadata parameters
* Exception handling for non-supported metadata

Implementation
==============

Assignee(s)
-----------
* Evgeny Fedoruk (evgenyf)
* Carlos Puga (cpuga)

Work Items
----------
* Implement the new models
* Implement the REST API Extension (including tests)
* Implementation migration script for existing deployments.
* Add client API support
* Add policies to the Octavia RBAC system

Dependencies
============

Depends on provider support and provider drivers that support the validation
interface and accept the flavor profile metadata.

Testing
=======

Tempest Tests

Tempest testing including new API and scenario tests to validate new entities.

Functional Tests

Functional tests will need to be created to cover the API and database
changes.

API Tests

The new API extensions will be tested using functional tests.

Documentation Impact
====================

User Documentation

User documentation will need be included to describe to users how to use
flavors when building their logical topology.

Operator Documentation

Operator documentation will need to be created to detail how to manage
Flavors, Providers and their respective Profiles.

Developer Documentation

Provider driver implementation documentation will need to be updated
to cover the new interfaces expected of provider drivers and the structure
of the metadata provided to the driver.

API Reference

The API reference documentation will need to be updated for the new API
extensions.

References
==========
[1] https://developer.openstack.org/api-ref/load-balancer/v2/index.html
