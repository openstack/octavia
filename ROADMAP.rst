===============
Octavia Roadmap
===============
Given the complete lack of any real project management tools in the OpenStack
environment, for the time being we'll be planning and tracking project
progression using this ROADMAP.rst file. (It may be more appropriate to keep
this document in the wiki-- we'll see what people think of this.)

This file consists of three sections:

1. A long-term timeline
2. A short-term timeline (derived from the above, reads like a todo list)
3. Outstanding design questions (things yet to be addressed of near-term to
   medium-term importance)

==================
Long-term timeline
==================


Major milestone: Full-featured Neutron LBaaS in Juno
----------------------------------------------------
Description: Neutron LBaaS API and other interfaces are full-featured enough
to allow for a user interface that delivers most of the features Octavia will
be implementing. Work commenced on Octavia coding.

OpenStack release target: Juno

Neutron LBaaS progress:
* New object model support
* TLS support

Octavia progress:
* Consensus on:
  * Constitution
  * Road map
  * Component design
  * APIs
* Initial code underway (perhaps alpha release?)


Major milestone: Octavia Version 0.5
------------------------------------
Description: First usable release of Octavia. Delivers load balancing services
on multiple Nova VMs. Single, centralized command and control (not scalable).

OpenStack release target: Kilo

Neutron LBaaS progress:
* Flavor support
* L7 switching support
* Updated horizon UI
* Hooks for Heat integration

Octavia progress:
* Octavia delivers all functionality of Neutron LBaaS user API
* Octavia VMs image building scripts
* Octavia operator API
* Horizon UI for operators
* Neutron LBaaS driver interface for Octavia
* Non-voting Neutron third-party CI for Octavia to ensure Neutron code changes
  don't break Octavia
* Command-and-control layer handles:
  * Octavia VM lifecycle maangement
  * Octavia VM monitoring
  * Octavia VM command and control
  * Neutron LBaaS service deployment
* Resilient topologies for Octavia VMs (ie. HA for the VMs)
* "Experimental" project status


Major milestone: Octavia Version 1.0
------------------------------------
Description: Operator-scale release of Octavia. Delivers load balancing
services on multiple Nova VMs, and has scalable command and control layer.

OpenStack release target: "L" release

Octavia progress:
* Possibly becomes reference implementation for Neutron LBaaS
* Project becomes incubated
* Fully scalable and HA command-and-control layer
* Improvements to Horizon UI for operators


Major milestone: Octavia Version 2.0
------------------------------------
Description: "Web scale" release of Octavia. Delivers all the features of
1.0, plus allows for horizontal scaling of individual load-balanced services.
(ie. n-node active-active topologies).

OpenStack release target: ???

Octavia progress:
* "Two layer" load balancing topology implemented where layers 1-4 handled by
  routing infrastructure, and 4-7 handled by Octavia VMs acting in parallel.
* Improvements to Horizon UI for operators


===================
Short-term timeline
===================

Highest priority:
* See Neutron LBaaS work scheduled for Juno through to completion.
* Import google docs describing v0.5, v1.0 and v2.0 Octavia into specs folder
  of this repository
* Get reviews and consensus on the same

Medium priority:
* Define and document Octavia VM <=> Controller RESTful APIs
* Define best practices for credential management between Octavia VM and
  controllers (suggested: bi-direction server / client certificat verification)
* Collect requirements for Operator API
* Start work on Octavia VM image
* Start work on Octavia VM agent
* Start work on controllers
* Create Neutron LBaaS driver for Octavia
* Get Octavia to work in devstack
* Flesh out the above items with more detailed checklists as work commences on
  them

Lower priority:
* Create mock-ups of and start coding Horizon UI for Octavia operators
* Create non-voting CI interface for testing changes relating to Octavia in
  gerrit


============================
Outstanding design questions
============================

* We need to start putting together specifications for the Operator API for
  Octavia.
