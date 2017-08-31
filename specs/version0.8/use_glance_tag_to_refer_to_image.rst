..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===============================================================
Allow to use Glance image tag to refer to desired Amphora image
===============================================================

https://blueprints.launchpad.net/octavia/+spec/use-glance-tags-to-manage-image

Currently, Octavia allows to define the Glance image ID to be used to boot new
Amphoras. This spec suggests another way to define the desired image, by using
Glance tagging mechanism.


Problem description
===================

The need to hardcode image ID in the service configuration file has drawbacks.

Specifically, when an updated image is uploaded into Glance, the operator is
required to orchestrate configuration file update on all Octavia nodes and then
restart all Octavia workers to apply the change. It is both complex and error
prone.


Proposed change
===============

The spec suggests an alternative way to configure the desired Glance image to
be used for Octavia: using Glance image tagging feature.

Glance allows to tag an image with any tag which is represented by a string
value.

With the proposed change, Octavia operator will be able to tell Octavia to use
an image with the specified tag. Then Octavia will talk to Glance to determine
the exact image ID that is marked with the tag, before booting a new Amphora.


Alternatives
------------

Alternatively, we could make Nova talk to Glance to determine the desired image
ID based on the tag provided by Octavia. This approach is not supported by Nova
community because they don't want to impose the complexity into their code
base.

Another alternative is to use image name instead of its ID. Nova is capable of
fetching the right image from Glance by name as long as the name is unique.
This is not optimal in case when the operator does not want to remove the old
Amphora image right after a new image is uploaded (for example, if the operator
wants to test the new image before cleaning up the old one).

Data model impact
-----------------

None.

REST API impact
---------------

None.

Security impact
---------------

Image tags should be managed by the same user that owns the images themselves.

Notifications impact
--------------------

None.

Other end user impact
---------------------

The proposed change should not break existing mechanism. To achieve that, the
new mechanism will be guarded with a new configuration option that will store
the desired Glance tag.

Performance Impact
------------------

If the feature is used, Octavia will need to reach to Glance before booting a
new Amphora. The performance impact is well isolated and is not expected to be
significant.

Other deployer impact
---------------------

The change couples Octavia with Glance. It should not be an issue since there
are no use cases to use Octavia without Glance installed.

The new feature deprecates amp_image_id option. Operators that still use the
old image referencing mechanism will be advised to switch to the new option.

Eventually, the old mechanism will be removed from the tree.

Developer impact
----------------

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  ihrachys (Ihar Hrachyshka)

Work Items
----------

* introduce glanceclient integration into nova compute driver
* introduce new configuration option to store the glance tag
* introduce devstack plugin support to configure the feature
* provide documentation for the new feature


Dependencies
============

None.

Testing
=======

Unit tests will be written to cover the feature.

Octavia plugin will be switched to using the new glance image referencing
mechanism. Tempest tests will be implemented to test the new feature.


Documentation Impact
====================

New feature should be documented in operator visible guides.


References
==========

