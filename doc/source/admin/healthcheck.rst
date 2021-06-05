..
      Copyright 2020 Red Hat, Inc. All rights reserved.

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

=============================
Octavia API Health Monitoring
=============================

The Octavia API provides a health monitoring endpoint that can be used by
external load balancers to manage the Octavia API pool. When properly
configured, the health monitoring endpoint will reflect the full operational
status of the Octavia API.

The Octavia API health monitoring endpoint extends the `OpenStack Oslo
middleware healthcheck <https://docs.openstack.org/oslo.middleware/latest/reference/healthcheck_plugins.html>`_ library to test the Octavia Pecan API framework and associated services.

Oslo Healthcheck Queries
========================

Oslo middleware healthcheck supports HTTP **"GET"** and **"HEAD"** methods.

The response from Oslo middleware healthcheck can be customized by specifying
the acceptable response type for the request.

Oslo middleware healthcheck currently supports the following types:

* text/plain
* text/html
* application/json

If the requested type is not one of the above, it defaults to text/plain.

.. note::

   The content of the response "reasons" will vary based on the backend plugins
   enabled in Oslo middleware healthcheck. It is a best practice to only rely
   on the HTTP status code for Octavia API health monitoring.

Example Responses
-----------------

Example passing output for text/plain with *detailed* False:

.. code-block:: bash

   $ curl -i http://198.51.100.10/load-balancer/healthcheck

     HTTP/1.1 200 OK
     Date: Mon, 16 Mar 2020 18:10:27 GMT
     Server: Apache/2.4.29 (Ubuntu)
     Content-Type: text/plain; charset=UTF-8
     Content-Length: 2
     x-openstack-request-id: req-9c6f4303-63a7-4f30-8afc-39340658702f
     Connection: close
     Vary: Accept-Encoding

     OK

Example failing output for text/plain with *detailed* False:

.. code-block:: bash

   $ curl -i http://198.51.100.10/load-balancer/healthcheck

     HTTP/1.1 503 Service Unavailable
     Date: Mon, 16 Mar 2020 18:42:12 GMT
     Server: Apache/2.4.29 (Ubuntu)
     Content-Type: text/plain; charset=UTF-8
     Content-Length: 36
     x-openstack-request-id: req-84024269-2dfb-41ad-bfda-b3e1da138bba
     Connection: close

Example passing output for text/html with *detailed* False:

.. code-block:: bash

   $ curl -i -H "Accept: text/html" http://198.51.100.10/load-balancer/healthcheck

     HTTP/1.1 200 OK
     Date: Mon, 16 Mar 2020 18:25:11 GMT
     Server: Apache/2.4.29 (Ubuntu)
     Content-Type: text/html; charset=UTF-8
     Content-Length: 239
     x-openstack-request-id: req-b212d619-146f-4b50-91a3-5da16051badc
     Connection: close
     Vary: Accept-Encoding

     <HTML>
     <HEAD><TITLE>Healthcheck Status</TITLE></HEAD>
     <BODY>

     <H2>Result of 1 checks:</H2>
     <TABLE bgcolor="#ffffff" border="1">
     <TBODY>
     <TR>

     <TH>
     Reason
     </TH>
     </TR>
     <TR>

         <TD>OK</TD>

     </TR>
     </TBODY>
     </TABLE>
     <HR></HR>

     </BODY>
     </HTML>

Example failing output for text/html with *detailed* False:

.. code-block:: bash

   $ curl -i -H "Accept: text/html" http://198.51.100.10/load-balancer/healthcheck

     HTTP/1.1 503 Service Unavailable
     Date: Mon, 16 Mar 2020 18:42:22 GMT
     Server: Apache/2.4.29 (Ubuntu)
     Content-Type: text/html; charset=UTF-8
     Content-Length: 273
     x-openstack-request-id: req-c91dd214-85ca-4d33-9fa3-2db81566d9e5
     Connection: close

     <HTML>
     <HEAD><TITLE>Healthcheck Status</TITLE></HEAD>
     <BODY>

     <H2>Result of 1 checks:</H2>
     <TABLE bgcolor="#ffffff" border="1">
     <TBODY>
     <TR>

     <TH>
     Reason
     </TH>
     </TR>
     <TR>

         <TD>The Octavia database is unavailable.</TD>

     </TR>
     </TBODY>
     </TABLE>
     <HR></HR>

     </BODY>
     </HTML>

Example passing output for application/json with *detailed* False:

.. code-block:: bash

   $ curl -i -H "Accept: application/json" http://192.51.100.10/load-balancer/healthcheck

     HTTP/1.1 200 OK
     Date: Mon, 16 Mar 2020 18:34:42 GMT
     Server: Apache/2.4.29 (Ubuntu)
     Content-Type: application/json
     Content-Length: 62
     x-openstack-request-id: req-417dc85c-e64e-496e-a461-494a3e6a5479
     Connection: close

     {
         "detailed": false,
         "reasons": [
             "OK"
         ]
     }

Example failing output for application/json with *detailed* False:

.. code-block:: bash

   $ curl -i -H "Accept: application/json" http://192.51.100.10/load-balancer/healthcheck

     HTTP/1.1 503 Service Unavailable
     Date: Mon, 16 Mar 2020 18:46:28 GMT
     Server: Apache/2.4.29 (Ubuntu)
     Content-Type: application/json
     Content-Length: 96
     x-openstack-request-id: req-de50b057-6105-4fca-a758-c872ef28bbfa
     Connection: close

     {
         "detailed": false,
         "reasons": [
             "The Octavia database is unavailable."
         ]
     }

Example Detailed Responses
--------------------------

Example passing output for text/plain with *detailed* True:

.. code-block:: bash

   $ curl -i http://198.51.100.10/load-balancer/healthcheck

     HTTP/1.1 200 OK
     Date: Mon, 16 Mar 2020 18:10:27 GMT
     Server: Apache/2.4.29 (Ubuntu)
     Content-Type: text/plain; charset=UTF-8
     Content-Length: 2
     x-openstack-request-id: req-9c6f4303-63a7-4f30-8afc-39340658702f
     Connection: close
     Vary: Accept-Encoding

     OK

Example failing output for text/plain with *detailed* True:

.. code-block:: bash

   $ curl -i http://198.51.100.10/load-balancer/healthcheck

     HTTP/1.1 503 Service Unavailable
     Date: Mon, 16 Mar 2020 23:41:23 GMT
     Server: Apache/2.4.29 (Ubuntu)
     Content-Type: text/plain; charset=UTF-8
     Content-Length: 36
     x-openstack-request-id: req-2cd046cb-3a6c-45e3-921d-5f4a9e65c63e
     Connection: close

Example passing output for text/html with *detailed* True:

.. code-block:: bash

   $ curl -i -H "Accept: text/html" http://198.51.100.10/load-balancer/healthcheck

     HTTP/1.1 200 OK
     Date: Mon, 16 Mar 2020 22:11:54 GMT
     Server: Apache/2.4.29 (Ubuntu)
     Content-Type: text/html; charset=UTF-8
     Content-Length: 9927
     x-openstack-request-id: req-ae7404c9-b183-46dc-bb1b-e5f4e4984a57
     Connection: close
     Vary: Accept-Encoding

     <HTML>
     <HEAD><TITLE>Healthcheck Status</TITLE></HEAD>
     <BODY>
     <H1>Server status</H1>
     <B>Server hostname:</B><PRE>devstack2</PRE>
     <B>Current time:</B><PRE>2020-03-16 22:11:54.320529</PRE>
     <B>Python version:</B><PRE>3.6.9 (default, Nov  7 2019, 10:44:02)
     [GCC 8.3.0]</PRE>
     <B>Platform:</B><PRE>Linux-4.15.0-88-generic-x86_64-with-Ubuntu-18.04-bionic</PRE>
     <HR></HR>
     <H2>Garbage collector:</H2>
     <B>Counts:</B><PRE>(28, 10, 4)</PRE>
     <B>Thresholds:</B><PRE>(700, 10, 10)</PRE>
     <HR></HR>
     <H2>Result of 1 checks:</H2>
     <TABLE bgcolor="#ffffff" border="1">
     <TBODY>
     <TR>
     <TH>
     Kind
     </TH>
     <TH>
     Reason
     </TH>
     <TH>
     Details
     </TH>

     </TR>
     <TR>
     <TD>OctaviaDBCheckResult</TD>
         <TD>OK</TD>
     <TD></TD>
     </TR>
     </TBODY>
     </TABLE>
     <HR></HR>
     <H2>1 greenthread(s) active:</H2>
     <TABLE bgcolor="#ffffff" border="1">
     <TBODY>
     <TR>
         <TD><PRE> <...> </PRE></TD>
     </TR>
     </TBODY>
     </TABLE>
     <HR></HR>
     <H2>1 thread(s) active:</H2>
     <TABLE bgcolor="#ffffff" border="1">
     <TBODY>
     <TR>
         <TD><PRE> <...> </PRE></TD>
     </TR>
     </TBODY>
     </TABLE>
     </BODY>
     </HTML>

Example failing output for text/html with *detailed* True:

.. code-block:: bash

   $ curl -i -H "Accept: text/html" http://198.51.100.10/load-balancer/healthcheck

     HTTP/1.1 503 Service Unavailable
     Date: Mon, 16 Mar 2020 23:43:52 GMT
     Server: Apache/2.4.29 (Ubuntu)
     Content-Type: text/html; charset=UTF-8
     Content-Length: 10211
     x-openstack-request-id: req-39b65058-6dc3-4069-a2d5-8a9714dba61d
     Connection: close

     <HTML>
     <HEAD><TITLE>Healthcheck Status</TITLE></HEAD>
     <BODY>
     <H1>Server status</H1>
     <B>Server hostname:</B><PRE>devstack2</PRE>
     <B>Current time:</B><PRE>2020-03-16 23:43:52.411127</PRE>
     <B>Python version:</B><PRE>3.6.9 (default, Nov  7 2019, 10:44:02)
     [GCC 8.3.0]</PRE>
     <B>Platform:</B><PRE>Linux-4.15.0-88-generic-x86_64-with-Ubuntu-18.04-bionic</PRE>
     <HR></HR>
     <H2>Garbage collector:</H2>
     <B>Counts:</B><PRE>(578, 10, 4)</PRE>
     <B>Thresholds:</B><PRE>(700, 10, 10)</PRE>
     <HR></HR>
     <H2>Result of 1 checks:</H2>
     <TABLE bgcolor="#ffffff" border="1">
     <TBODY>
     <TR>
     <TH>
     Kind
     </TH>
     <TH>
     Reason
     </TH>
     <TH>
     Details
     </TH>

     </TR>
     <TR>
     <TD>OctaviaDBCheckResult</TD>
         <TD>The Octavia database is unavailable.</TD>
     <TD>Database health check failed due to: (pymysql.err.OperationalError) (2003, &#34;Can&#39;t connect to MySQL server on &#39;127.0.0.1&#39; ([Errno 111] Connection refused)&#34;)
     [SQL: SELECT 1]
     (Background on this error at: http://sqlalche.me/e/e3q8).</TD>
     </TR>
     </TBODY>
     </TABLE>
     <HR></HR>
     <H2>1 greenthread(s) active:</H2>
     <TABLE bgcolor="#ffffff" border="1">
     <TBODY>
     <TR>
         <TD><PRE> <...> </PRE></TD>
     </TR>
     </TBODY>
     </TABLE>
     <HR></HR>
     <H2>1 thread(s) active:</H2>
     <TABLE bgcolor="#ffffff" border="1">
     <TBODY>
     <TR>
         <TD><PRE> <...> </PRE></TD>
     </TR>
     </TBODY>
     </TABLE>
     </BODY>
     </HTML>

Example passing output for application/json with *detailed* True:

.. code-block:: bash

   $ curl -i -H "Accept: application/json" http://192.51.100.10/load-balancer/healthcheck

     HTTP/1.1 200 OK
     Date: Mon, 16 Mar 2020 22:05:26 GMT
     Server: Apache/2.4.29 (Ubuntu)
     Content-Type: application/json
     Content-Length: 9298
     x-openstack-request-id: req-d3913655-6e3f-4086-a252-8bb297ea5fd6
     Connection: close

     {
         "detailed": true,
         "gc": {
             "counts": [
                 27,
                 10,
                 4
             ],
             "threshold": [
                 700,
                 10,
                 10
             ]
         },
         "greenthreads": [
             <...>
         ],
         "now": "2020-03-16 22:05:26.431429",
         "platform": "Linux-4.15.0-88-generic-x86_64-with-Ubuntu-18.04-bionic",
         "python_version": "3.6.9 (default, Nov  7 2019, 10:44:02) \n[GCC 8.3.0]",
         "reasons": [
             {
                 "class": "OctaviaDBCheckResult",
                 "details": "",
                 "reason": "OK"
             }
         ],
         "threads": [
             <...>
         ]
     }

Example failing output for application/json with *detailed* True:

.. code-block:: bash

   $ curl -i -H "Accept: application/json" http://192.51.100.10/load-balancer/healthcheck

     HTTP/1.1 503 Service Unavailable
     Date: Mon, 16 Mar 2020 23:56:43 GMT
     Server: Apache/2.4.29 (Ubuntu)
     Content-Type: application/json
     Content-Length: 9510
     x-openstack-request-id: req-3d62ea04-9bdb-4e19-b218-1a81ff7d7337
     Connection: close

     {
         "detailed": true,
         "gc": {
             "counts": [
                 178,
                 0,
                 5
             ],
             "threshold": [
                 700,
                 10,
                 10
             ]
         },
         "greenthreads": [
             <...>
         ],
         "now": "2020-03-16 23:58:23.361209",
         "platform": "Linux-4.15.0-88-generic-x86_64-with-Ubuntu-18.04-bionic",
         "python_version": "3.6.9 (default, Nov  7 2019, 10:44:02) \n[GCC 8.3.0]",
         "reasons": [
             {
                 "class": "OctaviaDBCheckResult",
                 "details": "(pymysql.err.OperationalError) (2003, \"Can't connect to MySQL server on '127.0.0.1' ([Errno 111] Connection refused)\")\n(Background on this error at: http://sqlalche.me/e/e3q8)",
                 "reason": "The Octavia database is unavailable."
             }
         ],
         "threads": [
             <...>
         ]
     }

Oslo Healthcheck Plugins
========================

The Octavia API health monitoring endpoint, implemented with Oslo middleware
healthcheck,  is extensible using optional backend plugins. There are currently
plugins provided by the Oslo middleware library and plugins provided by
Octavia.

**Oslo middleware provided plugins**

* `disable_by_file <https://docs.openstack.org/oslo.middleware/latest/reference/healthcheck_plugins.html#disable-by-file>`_
* `disable_by_files_ports <https://docs.openstack.org/oslo.middleware/latest/reference/healthcheck_plugins.html#disable-by-files-ports>`_

**Octavia provided plugins**

* `octavia_db_check`_

.. warning::

   Some plugins may have long timeouts. It is a best practice to configure your
   healthcheck query to have connection, read, and/or data timeouts. The
   appropriate values will be unique to each deployment depending on the cloud
   performance, number of plugins, etc.

Enabling Octavia API Health Monitoring
======================================

To enable the Octavia API health monitoring endpoint, the proper configuration
file settings need to be updated and the Octavia API processes need to be
restarted.

Start by enabling the endpoint:

.. code-block:: ini

    [api_settings]
    healthcheck_enabled = True

When the healthcheck_enabled setting is *False*, queries of the /healthcheck
will receive an HTTP 404 Not Found response.

You will then need to select the desired monitoring backend plugins:

.. code-block:: ini

    [healthcheck]
    backends = octavia_db_check

.. note::

  When no plugins are configured, the behavior of Oslo middleware healthcheck
  changes. Not only does it not run any tests, it will return 204 results
  instead of 200.

The Octavia API health monitoring endpoint does not require a keystone token
for access to allow external load balancers to query the endpoint. For this
reason we recommend you restrict access to it on your external load balancer
to prevent abuse.

As an additional protection, the API will cache results for a configurable
period of time. This means that queries to the health monitoring endpoint
will return cached results until the refresh interval has expired, at which
point the health check plugin will rerun the check.

By default, the refresh interval is five seconds. This can be configured by
adjusting the healthcheck_refresh_interval setting in the Octavia configuration
file:

.. code-block:: ini

    [api_settings]
    healthcheck_refresh_interval = 5

Optionally you can enable the "detailed" mode in Oslo middleware healthcheck.
This will cause Oslo middleware healthcheck to return additional information
about the API instance. It will also provide exception details if one was
raised during the health check. This setting is False and disabled by default
in the Octavia API.

.. code-block:: ini

    [healthcheck]
    detailed = True

.. warning::

   Enabling the 'detailed' setting will expose sensitive details about
   the API process. Do not enabled this unless you are sure it will
   not pose a **security risk** to your API instances.
   We highly recommend you do not enable this.

Using Octavia API Health Monitoring
===================================

The Octavia API health monitoring endpoint can be accessed via the
/healthmonitor path on the `Octavia API endpoint <https://docs.openstack.org/api-ref/load-balancer/v2/index.html#service-endpoints>`_.

For example, if your Octavia (load-balancer) endpoint in keystone is:

.. code-block:: bash

   https://10.21.21.78/load-balancer

You would access the Octavia API health monitoring endpoint via:

.. code-block:: bash

   https://10.21.21.78/load-balancer/healthcheck

A keystone token is not required to access this endpoint.

Octavia Plugins
===============

octavia_db_check
----------------

The octavia_db_check plugin validates the API instance has a working connection
to the Octavia database. It executes a SQL no-op query, 'SELECT 1;',  against
the database.

.. note::

  Many OpenStack services and libraries, such as oslo.db and sqlalchemy, also
  use the no-op query, 'SELECT 1;' for health checks.

The possible octavia_db_check results are:

+---------+--------+-------------+--------------------------------------+
| Request | Result | Status Code | "reason" Message                     |
+=========+========+=============+======================================+
|   GET   |  Pass  |     200     | OK                                   |
+---------+--------+-------------+--------------------------------------+
|   HEAD  |  Pass  |     204     |                                      |
+---------+--------+-------------+--------------------------------------+
|   GET   |  Fail  |     503     | The Octavia database is unavailable. |
+---------+--------+-------------+--------------------------------------+
|   HEAD  |  Fail  |     503     |                                      |
+---------+--------+-------------+--------------------------------------+

When running Oslo middleware healthcheck in "detailed" mode, the "details"
field will have additional information about the error encountered, including
the exception details if they were available.
