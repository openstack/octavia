====================
Octavia Constitution
====================

This document defines the guiding principles that project leadership will be
following in creating, improving and maintaining the Octavia project.

Octavia is an OpenStack project
-------------------------------
This means we try to run things the same way other "canonized" OpenStack
projects operate from a procedural perspective. This is because we hope that
Octavia will eventually become a standard part of any OpenStack deployment.

Octavia is as open as OpenStack
-------------------------------
Octavia tries to follow the same standards for openness that the OpenStack
project also strives to follow: https://wiki.openstack.org/wiki/Open
We are committed to open design, development, and community.

Octavia is "free"
-----------------
We mean that both in the "beer" and in the "speech" sense. That is to say, the
reference implementation for Octavia should be made up only of open source
components that share the same kind of unencumbered licensing that OpenStack
uses.

Note that this does not mean we are against having vendors develop products
which can replace some of the components within Octavia. (For example, the
Octavia VM images might be replaced by a vendor's proprietary VM image.)
Rather, it means that:
* The reference implementation should always be open source and unencumbered.
* We are typically not interested in making design compromises in order to work
with a vendor's proprietary product. If a vendor wants to develop a component
for Octavia, then the vendor should bend to Octavia's needs, not the other
way around.

Octavia is a load balancer for large operators
----------------------------------------------
That's not to say that small operators can't use it. (In fact, we expect it to
work well for small deployments, too.) But what we mean here is that if in
creating, improving or maintaining Octavia we somehow make it unable to meet
the needs of a typical large operator (or that operator's users), then we have
failed.

Octavia follows the best coding and design conventions
------------------------------------------------------
For the most part, Octavia tries to follow the coding standards set forth for
the OpenStack project in general: https://docs.openstack.org/hacking/latest
More specific additional standards can be found in the HACKING.rst file in the
same directory as this constitution.

Any exceptions should be well justified and documented. (Comments in or near
the breach in coding standards are usually sufficient documentation.)
