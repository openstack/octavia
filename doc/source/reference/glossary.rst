================
Octavia Glossary
================
As the Octavia project evolves, it's important that people working on Octavia,
users using Octavia, and operators deploying Octavia use a common set of
terminology in order to avoid misunderstandings and confusion. To that end, we
are providing the following glossary of terms.

Note also that many of these terms are expanded upon in design documents in
this same repository. What follows is a brief but necessarily incomplete
description of these terms.

.. glossary:: :sorted:

    Amphora
        Virtual machine, container, dedicated hardware, appliance or device
        that actually performs the task of load balancing in the Octavia
        system. More specifically, an amphora takes requests from clients on
        the front-end and distributes these to back-end systems. Amphorae
        communicate with their controllers over the LB Network through a driver
        interface on the controller.

    Amphora Load Balancer Driver
        Component of the controller that does all the communication with
        amphorae. Drivers communicate with the controller through a generic
        base class and associated methods, and translate these into control
        commands appropriate for whatever type of software is running on the
        back-end amphora corresponding with the driver. This communication
        happens over the LB network.

    Anchor
       Is an OpenStack project for an ephemeral PKI system (see
       https://wiki.openstack.org/wiki/Security/Projects/Anchor). In Octavia
       we can use Anchor to sign the certificates we use to authenticate/secure
       controller <-> amphora communication.

    Apolocation
        Term used to describe when two or more amphorae are not colocated on
        the same physical hardware (which is often essential in HA topologies).
        May also be used to describe two or more loadbalancers which are not
        colocated on the same amphora.

    Controller
        Daemon with access to both the LB Network and OpenStack components
        which coordinates and manages the overall activity of the Octavia load
        balancing system. Controllers will usually use an abstracted driver
        interface (usually a base class) for communicating with various other
        components in the OpenStack environment in order to facilitate loose
        coupling with these other components. These are the "brains" of the
        Octavia system.

    HAProxy
        Load balancing software used in the reference implementation for
        Octavia. (See http://www.haproxy.org/ ). HAProxy processes run on
        amphorae and actually accomplish the task of delivering the load
        balancing service.

    Health Monitor
        An object that defines a check method for each member of the pool.
        The health monitor itself is a pure-db object which describes the
        method the load balancing software on the amphora should use to
        monitor the health of back-end members of the pool with which the
        health monitor is associated.

    L7 Policy
    Layer 7 Policy
        Collection of L7 rules that get logically ANDed together as well as a
        routing policy for any given HTTP or terminated HTTPS client requests
        which match said rules. An L7 Policy is associated with exactly one
        HTTP or terminated HTTPS listener.

        For example, a user could specify an L7 policy that any client request
        that matches the L7 rule "request URI starts with '/api'" should
        get routed to the "api" pool.

    L7 Rule
    Layer 7 Rule
        Single logical expression used to match a condition present in a given
        HTTP or terminated HTTPS request. L7 rules typically match against
        a specific header or part of the URI and are used in conjunction with
        L7 policies to accomplish L7 switching. An L7 rule is associated with
        exactly one L7 policy.

        For example, a user could specify an L7 rule that matches any request
        URI path that begins with "/api"

    L7 Switching
    Layer 7 Switching
        This is a load balancing feature specific to HTTP or terminated HTTPS
        sessions, in which different client requests are routed to different
        back-end pools depending on one or more layer 7 policies the user might
        configure.

        For example, using L7 switching, a user could specify that any
        requests with a URI path that starts with "/api" get routed to the
        "api" back-end pool, and that all other requests get routed to the
        default pool.

    LB Network
        Load Balancer Network. The network over which the controller(s) and
        amphorae communicate. The LB network itself will usually be a nova or
        neutron network to which both the controller and amphorae have access,
        but is not associated with any one tenant. The LB Network is generally
        also *not* part of the undercloud and should not be directly exposed to
        any OpenStack core components other than the Octavia Controller.

    Listener
        Object representing the listening endpoint of a load balanced service.
        TCP / UDP port, as well as protocol information and other protocol-
        specific details are attributes of the listener. Notably, though, the
        IP address is not.

    Load Balancer
        Object describing a logical grouping of listeners on one or more VIPs
        and associated with one or more amphorae. (Our "Loadbalancer" most
        closely resembles a Virtual IP address in other load balancing
        implementations.) Whether the load balancer exists on more than one
        amphora depends on the topology used. The load balancer is also often
        the root object used in various Octavia APIs.

    Load Balancing
        The process of taking client requests on a front-end interface and
        distributing these to a number of back-end servers according to various
        rules. Load balancing allows for many servers to participate in
        delivering some kind TCP or UDP service to clients in an effectively
        transparent and often highly-available and scalable way (from the
        client's perspective).

    Member
        Object representing a single back-end server or system that is a
        part of a pool. A member is associated with only one pool.

    Octavia
        Octavia is an operator-grade open source load balancing solution. Also
        known as the Octavia system or Octavia project. The term by itself
        should be used to refer to the system as a whole and not any
        individual component within the Octavia load balancing system.

    Pool
        Object representing the grouping of members to which the listener
        forwards client requests. Note that a pool is associated with only
        one listener, but a listener might refer to several pools (and switch
        between them using layer 7 policies).

    TLS Termination
    Transport Layer Security Termination
        Type of load balancing protocol where HTTPS sessions are terminated
        (decrypted) on the amphora as opposed to encrypted packets being
        forwarded on to back-end servers without being decrypted on the
        amphora. Also known as SSL termination. The main advantages to this
        type of load balancing are that the payload can be read and / or
        manipulated by the amphora, and that the expensive tasks of handling
        the encryption are off-loaded from the back-end servers. This is
        particularly useful if layer 7 switching is employed in the same
        listener configuration.

    VIP
    Virtual IP Address
        Single service IP address which is associated with a load balancer.
        This is similar to what is described here:
        http://en.wikipedia.org/wiki/Virtual_IP_address
        In a highly available load balancing topology in Octavia, the VIP might
        be assigned to several amphorae, and a layer-2 protocol like CARP,
        VRRP, or HSRP (or something unique to the networking infrastructure)
        might be used to maintain its availability. In layer-3 (routed)
        topologies, the VIP address might be assigned to an upstream networking
        device which routes packets to amphorae, which then load balance
        requests to back-end members.

