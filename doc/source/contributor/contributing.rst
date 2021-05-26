So You Want to Contribute...
============================

For general information on contributing to OpenStack, please check out the
`contributor guide <https://docs.openstack.org/contributors/>`_ to get started.
It covers all the basics that are common to all OpenStack projects: the
accounts you need, the basics of interacting with our Gerrit review system,
how we communicate as a community, etc.

Below will cover the more project specific information you need to get started
with Octavia.

Communication
~~~~~~~~~~~~~

IRC
    People working on the Octavia project may be found in the
    ``#openstack-lbaas`` channel on the IRC network described in
    https://docs.openstack.org/contributors/common/irc.html
    during working hours in their timezone.  The channel is logged, so if
    you ask a question when no one is around, you can check the log to see
    if it's been answered:
    http://eavesdrop.openstack.org/irclogs/%23openstack-lbaas/

Weekly Meeting
    The Octavia team meets weekly on IRC. Please see the OpenStack
    meetings page for the current meeting details and ICS file:
    http://eavesdrop.openstack.org/#Octavia_Meeting
    Meetings are logged: http://eavesdrop.openstack.org/meetings/octavia/

Mailing List
    We use the openstack-discuss@lists.openstack.org mailing list for
    asynchronous discussions or to communicate with other OpenStack teams.
    Use the prefix ``[octavia]`` in your subject line (it's a high-volume
    list, so most people use email filters).

    More information about the mailing list, including how to subscribe
    and read the archives, can be found at:
    http://lists.openstack.org/cgi-bin/mailman/listinfo/openstack-discuss

Virtual Meet-ups
    From time to time, the Octavia project will have video meetings to
    address topics not easily covered by the above methods.  These are
    announced well in advance at the weekly meeting and on the mailing
    list.

Physical Meet-ups
    The Octavia project usually has a presence at the OpenDev/OpenStack
    Project Team Gathering that takes place at the beginning of each
    development cycle.  Planning happens on an etherpad whose URL is
    announced at the weekly meetings and on the mailing list.

Contacting the Core Team
~~~~~~~~~~~~~~~~~~~~~~~~

The octavia-core team is an active group of contributors who are responsible
for directing and maintaining the Octavia project.  As a new contributor, your
interaction with this group will be mostly through code reviews, because
only members of octavia-core can approve a code change to be merged into the
code repository.

.. note::
   Although your contribution will require reviews by members of
   octavia-core, these aren't the only people whose reviews matter.
   Anyone with a gerrit account can post reviews, so you can ask
   other developers you know to review your code ... and you can
   review theirs.  (A good way to learn your way around the codebase
   is to review other people's patches.)

   If you're thinking, "I'm new at this, how can I possibly provide
   a helpful review?", take a look at `How to Review Changes the
   OpenStack Way
   <https://docs.openstack.org/project-team-guide/review-the-openstack-way.html>`_.

   There are also some Octavia project specific reviewing guidelines
   in the :ref:`octavia-style-commandments` section of the Octavia Contributor
   Guide.

You can learn more about the role of core reviewers in the OpenStack
governance documentation:
https://docs.openstack.org/contributors/common/governance.html#core-reviewer

The membership list of octavia-core is maintained in gerrit:
https://review.opendev.org/#/admin/groups/370,members

You can also find the members of the octavia-core team at the Octavia weekly
meetings.

New Feature Planning
~~~~~~~~~~~~~~~~~~~~

The Octavia team use both Request For Enhancement (RFE) and Specifications
(specs) processes for new features.

RFE
    When a feature being proposed is easy to understand and will have limited
    scope, the requester will create an RFE in Storyboard. This is a story that
    includes the tag **[RFE]** in the subject prefix and has the "**rfe**" tag
    added to the story.

    Once an RFE story is created, a core reviewer or the Project Team Lead
    (PTL) will approved the RFE by adding the "**rfe-approved**" tag. This
    signals that the core team understands the feature being proposed and
    enough detail has been provided to make sure the core team understands the
    goal of the change.

specs
    If the new feature is a major change or additon to Octavia that will need
    a detailed design to be successful, the Octavia team requires a
    specification (spec) proposal be submitted as a patch.

    Octavia specification documents are stored in the /octavia/specs directory
    in the main Octavia git repository:
    https://opendev.org/openstack/octavia/src/branch/master/specs
    This directory includes a `template.rst <https://opendev.org/openstack/octavia/src/branch/master/specs/template.rst>`_ file that includes instructions for
    creating a new Octavia specification.

    These specification documents are then rendered and included in the
    `Project Specifications <https://docs.openstack.org/octavia/latest/contributor/index.html#project-specifications>`_ section of the Octavia Contributor
    Guide.

Feel free to ask in ``#openstack-lbaas`` or at the weekly meeting if you
have an idea you want to develop and you're not sure whether it requires
an RFE or a specification.

The Octavia project observes the OpenStack-wide deadlines,
for example, final release of non-client libraries (octavia-lib), final
release for client libraries (python-octaviaclient), feature freeze,
etc.  These are noted and explained on the release schedule for the current
development cycle available at: https://releases.openstack.org/

Task Tracking
~~~~~~~~~~~~~

We track our tasks in `Storyboard
<https://storyboard.openstack.org/#!/project/openstack/octavia>`_.

If you're looking for some smaller, easier work item to pick up and get started
on, search for the 'low-hanging-fruit' tag.

When you start working on a bug, make sure you assign it to yourself.
Otherwise someone else may also start working on it, and we don't want to
duplicate efforts.  Also, if you find a bug in the code and want to post a
fix, make sure you file a bug (and assign it to yourself!) just in case someone
else comes across the problem in the meantime.

Reporting a Bug
~~~~~~~~~~~~~~~

You found an issue and want to make sure we are aware of it? You can do so on
`Storyboard
<https://storyboard.openstack.org/#!/project/openstack/octavia>`_.

Please remember to include the following information:

* The version of Octavia and OpenStack you observed the issue in.
* Steps to reproduce.
* Expected behavior.
* Observed behavior.
* The log snippet that contains any error information. Please include the lines
  directly before the error message(s) as they provide context for the error.

Getting Your Patch Merged
~~~~~~~~~~~~~~~~~~~~~~~~~

The Octavia project policy is that a patch must have two +2s reviews from the
core reviewers before it can be merged.

Patches for Octavia projects must include unit and functional tests that cover
the new code. Octavia projects include the "openstack-tox-cover" testing job to
help identify test coverage gaps in a patch. This can also be run locally by
running "tox -e cover".

In addition, some changes may require a release note.  Any patch that
changes functionality, adds functionality, or addresses a significant
bug should have a release note. Release notes can be created using the "reno"
tool by running "reno new <summary-message>".

Keep in mind that the best way to make sure your patches are reviewed in
a timely manner is to review other people's patches.  We're engaged in a
cooperative enterprise here.

Project Team Lead Duties
~~~~~~~~~~~~~~~~~~~~~~~~

All common PTL duties are enumerated in the `PTL guide
<https://docs.openstack.org/project-team-guide/ptl.html>`_.
