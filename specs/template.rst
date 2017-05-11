..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Example Spec - The title of your blueprint
==========================================

Include the URL of your launchpad blueprint:

https://blueprints.launchpad.net/octavia/+spec/example

Introduction paragraph -- why are we doing anything? A single paragraph of
prose that operators can understand.

Some notes about using this template:

* Your spec should be in ReSTructured text, like this template.

* Please wrap text at 80 columns.

* The filename in the git repository should match the launchpad URL, for
  example a URL of: https://blueprints.launchpad.net/octavia/+spec/awesome-thing
  should be named awesome-thing.rst

* Please do not delete any of the sections in this template.  If you have
  nothing to say for a whole section, just write: None

* For help with syntax, see http://sphinx-doc.org/rest.html

* To test out your formatting, build the docs using tox, or see:
  http://rst.ninjs.org

* If you would like to provide a diagram with your spec, text representations
  are preferred. http://asciiflow.com/ is a very nice tool to assist with
  making ascii diagrams. blockdiag is another tool. These are described below.
  For more complicated diagrams that need "real" graphics, yet still should
  be in the git revision control system, GraphViz .dot files are acceptable.
  If you require an image (screenshot) for your BP, attaching that to the BP
  and checking it in is also accepted. However, text representations are
  preferred.

* Diagram examples

asciiflow::

  +----------+     +-----------+        +----------+
  | A        |     |  B        |        |  C       |
  |          +-----+           +--------+          |
  +----------+     +-----------+        +----------+

blockdiag

.. blockdiag::

  blockdiag sample {
    a -> b -> c;
  }

actdiag

.. actdiag::

   actdiag {
     write -> convert -> image
     lane user {
       label = "User"
       write [label = "Writing reST"];
       image [label = "Get diagram IMAGE"];
     }
     lane actdiag {
       convert [label = "Convert reST to Image"];
     }
   }

nwdiag

.. nwdiag::

  nwdiag {
    network dmz {
      address = "210.x.x.x/24"

      web01 [address = "210.x.x.1"];
      web02 [address = "210.x.x.2"];
    }
    network internal {
      address = "172.x.x.x/24";

      web01 [address = "172.x.x.1"];
      web02 [address = "172.x.x.2"];
      db01;
      db02;
    }
  }

seqdiag

.. seqdiag::

  seqdiag {
    browser  -> webserver [label = "GET /index.html"];
    browser <-- webserver;
    browser  -> webserver [label = "POST /blog/comment"];
    webserver  -> database [label = "INSERT comment"];
    webserver <-- database;
    browser <-- webserver;
  }

graphviz

.. graphviz::

  digraph G {
    label="Sample Graph"

    subgraph cluster_0 {
      style=filled;
      color=lightgrey;
      node [style=filled,color=white];
      a0 -> a1 -> a2 -> a3;
      label = "process #1";
    }

    subgraph cluster_1 {
      node [style=filled];
      b0 -> b1 -> b2 -> b3;
      label = "process #2";
      color=blue
    }

    start -> a0;
    start -> b0;
    a1 -> b3;
    b2 -> a3;
    a3 -> a0;
    a3 -> end;
    b3 -> end;

    start [shape=Mdiamond];
    end [shape=Msquare];
  }

graphviz (external file)

.. graphviz:: example.dot


Problem description
===================

A detailed description of the problem:

* For a new feature this might be use cases. Ensure you are clear about the
  actors in each use case: End User vs Deployer

* For a major reworking of something existing it would describe the
  problems in that feature that are being addressed.


Proposed change
===============

Here is where you cover the change you propose to make in detail. How do you
propose to solve this problem?

If this is one part of a larger effort make it clear where this piece ends. In
other words, what's the scope of this effort?

Alternatives
------------

What other ways could we do this thing? Why aren't we using those? This doesn't
have to be a full literature review, but it should demonstrate that thought has
been put into why the proposed solution is an appropriate one.

Data model impact
-----------------

Changes which require modifications to the data model often have a wider impact
on the system.  The community often has strong opinions on how the data model
should be evolved, from both a functional and performance perspective. It is
therefore important to capture and gain agreement as early as possible on any
proposed changes to the data model.

Questions which need to be addressed by this section include:

* What new data objects and/or database schema changes is this going to
  require?

* What database migrations will accompany this change.

* How will the initial set of new data objects be generated, for example if you
  need to take into account existing instances, or modify other existing data
  describe how that will work.

REST API impact
---------------

Octavia includes several internal APIs (all of which should be versioned).
In defining how API(s) are affected by this change, make sure to
clearly indicate which API(s) specifically are being altered, which version
of the API(s) are being altered, and other pertinent details as described
below.

While we are not using Neutron's attribute map facility since Octavia is
not Neutron, following the tried-and-true guidelines Neutron uses around
API changes is a good idea, including defining attribute map tables. For
reference:

For each API resource to be implemented using Neutron's attribute map
facility (see the neutron.api.v2.attributes), describe the resource
collection and specify the name, type, and other essential details of
each new or modified attribute. A table similar to the following may
be used:

+----------+-------+---------+---------+------------+--------------+
|Attribute |Type   |Access   |Default  |Validation/ |Description   |
|Name      |       |         |Value    |Conversion  |              |
+==========+=======+=========+=========+============+==============+
|id        |string |RO, all  |generated|N/A         |identity      |
|          |(UUID) |         |         |            |              |
+----------+-------+---------+---------+------------+--------------+
|name      |string |RW, all  |''       |string      |human-readable|
|          |       |         |         |            |name          |
+----------+-------+---------+---------+------------+--------------+
|color     |string |RW, admin|'red'    |'red',      |color         |
|          |       |         |         |'yellow', or|indicating    |
|          |       |         |         |'green'     |state         |
+----------+-------+---------+---------+------------+--------------+


Here is the other example of the table using csv-table


.. csv-table:: CSVTable
    :header: Attribute Name,Type,Access,Default Value,Validation Conversion,Description

    id,string (UUID),"RO, all",generated,N/A,identity
    name,string,"RW, all","''",string,human-readable name
    color,string,"RW, admin",red,"'red', 'yellow' or 'green'",color indicating state


Each API method which is either added or changed that does not use
Neutron's attribute map facility should have the following:

* Specification for the method

  * A description of what the method does suitable for use in
    user documentation

  * Method type (POST/PUT/GET/DELETE)

  * Normal http response code(s)

  * Expected error http response code(s)

    * A description for each possible error code should be included
      describing semantic errors which can cause it such as
      inconsistent parameters supplied to the method, or when an
      instance is not in an appropriate state for the request to
      succeed. Errors caused by syntactic problems covered by the JSON
      schema definition do not need to be included.

  * URL for the resource

  * Parameters which can be passed via the url

  * JSON schema definition for the body data if allowed

  * JSON schema definition for the response data if any

* Example use case including typical API samples for both data supplied
  by the caller and the response

* Discuss any API policy changes, and discuss what things a deployer needs to
  think about when defining their API policy. This is in reference to the
  policy.json file.

Note that the schema should be defined as restrictively as
possible. Parameters which are required should be marked as such and
only under exceptional circumstances should additional parameters
which are not defined in the schema be permitted (eg
additionalProperties should be False).

Reuse of existing predefined parameter types such as regexps for
passwords and user defined names is highly encouraged.

Security impact
---------------

Describe any potential security impact on the system.  Some of the items to
consider include:

* Does this change touch sensitive data such as tokens, keys, or user data?

* Does this change alter the API in a way that may impact security, such as
  a new way to access sensitive information or a new way to login?

* Does this change involve cryptography or hashing?

* Does this change require the use of sudo or any elevated privileges?

* Does this change involve using or parsing user-provided data? This could
  be directly at the API level or indirectly such as changes to a cache layer.

* Can this change enable a resource exhaustion attack, such as allowing a
  single API interaction to consume significant server resources? Some examples
  of this include launching subprocesses for each connection, or entity
  expansion attacks in XML.

For more detailed guidance, please see the OpenStack Security Guidelines as
a reference (https://wiki.openstack.org/wiki/Security/Guidelines).  These
guidelines are a work in progress and are designed to help you identify
security best practices.  For further information, feel free to reach out
to the OpenStack Security Group at openstack-security@lists.openstack.org.

Notifications impact
--------------------

Please specify any changes to notifications. Be that an extra notification,
changes to an existing notification, or removing a notification.

Other end user impact
---------------------

Aside from the API, are there other ways a user will interact with this
feature? Keep in mind that 'user' in this context could mean either tenant or
operator.

* Does this change have an impact on python-neutronclient? What does the user
  interface there look like?

Performance Impact
------------------

Describe any potential performance impact on the system, for example
how often will new code be called, and is there a major change to the calling
pattern of existing code.

Examples of things to consider here include:

* A periodic task might look like a small addition but if it calls conductor or
  another service the load is multiplied by the number of nodes in the system.

* A small change in a utility function or a commonly used decorator can have a
  large impacts on performance.

* Calls which result in a database queries (whether direct or via conductor)
  can have a profound impact on performance when called in critical sections
  of the code.

* Will the change include any locking, and if so what considerations are there
  on holding the lock?

Other deployer impact
---------------------

Discuss things that will affect how you deploy and configure OpenStack
that have not already been mentioned, such as:

* What config options are being added? Should they be more generic than
  proposed (for example a flag that other hypervisor drivers might want to
  implement as well)? Are the default values ones which will work well in
  real deployments?

* Is this a change that takes immediate effect after its merged, or is it
  something that has to be explicitly enabled?

* If this change is a new binary, how would it be deployed?

* Please state anything that those doing continuous deployment, or those
  upgrading from the previous release, need to be aware of. Also describe
  any plans to deprecate configuration values or features.  For example, if we
  change the directory name that instances are stored in, how do we handle
  instance directories created before the change landed?  Do we move them?  Do
  we have a special case in the code? Do we assume that the operator will
  recreate all the instances in their cloud?

Developer impact
----------------

Discuss things that will affect other developers working on OpenStack,
such as:

* If the blueprint proposes a change to the API, discussion of how other
  plugins would implement the feature is required.


Implementation
==============

Assignee(s)
-----------

Who is leading the writing of the code? Or is this a blueprint where you're
throwing it out there to see who picks it up?

If more than one person is working on the implementation, please designate the
primary author and contact.

Primary assignee:
  <launchpad-id or None>

Other contributors:
  <launchpad-id or None>

Work Items
----------

Work items or tasks -- break the feature up into the things that need to be
done to implement it. Those parts might end up being done by different people,
but we're mostly trying to understand the timeline for implementation.


Dependencies
============

* Include specific references to specs and/or blueprints in octavia, or in
  other projects, that this one either depends on or is related to.

* If this requires functionality of another project that is not currently used
  by Octavia document that fact.

* Does this feature require any new library dependencies or code otherwise not
  included in OpenStack? Or does it depend on a specific version of library?


Testing
=======

Please discuss how the change will be tested. We especially want to know what
tempest tests will be added. It is assumed that unit test coverage will be
added so that doesn't need to be mentioned explicitly, but discussion of why
you think unit tests are sufficient and we don't need to add more tempest
tests would need to be included.

Is this untestable in gate given current limitations (specific hardware /
software configurations available)? If so, are there mitigation plans (3rd
party testing, gate enhancements, etc).


Documentation Impact
====================

What is the impact on the docs team of this change? Some changes might require
donating resources to the docs team to have the documentation updated. Don't
repeat details discussed above, but please reference them here.


References
==========

Please add any useful references here. You are not required to have any
reference. Moreover, this specification should still make sense when your
references are unavailable. Examples of what you could include are:

* Links to mailing list or IRC discussions

* Links to notes from a summit session

* Links to relevant research, if appropriate

* Related specifications as appropriate (e.g. link any vendor documentation)

* Anything else you feel it is worthwhile to refer to
