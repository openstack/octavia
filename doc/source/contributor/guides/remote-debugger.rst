..
      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

======================
Debugging Octavia code
======================

This document describes how to setup and debug Octavia code using your favorite
IDE (e.g. PyCharm, Visual Studio Code).

Prerequisites
=============

* Octavia installed.
* IDE installed and Octavia added as project.

Setup
=====

Ensure your OpenStack and IDE environments have the PyDev or ptvsd library
installed.

If you're using PyCharm, you can find it in
*/path/to/pycharm/debug-eggs/pycharm-debug.egg* (Python 2) and
*/path/to/pycharm/debug-eggs/pycharm-debug-py3k.egg* (Python 3). Copy that file
into your OpenStack host and install the library in your Python path:

::

    $ sudo easy_install pycharm-debug.egg

If using Visual Studio Code, simply install ptvsd in both environments:

::

    $ pip install ptvsd

Create a remote debugging configuration in your IDE. In PyCharm, go to *Run ->
Edit Configurations -> Python Remote Debug*. The local host name refers to the
local machine you're running your IDE from and it must be one reachable by your
OpenStack environment. The port can be any available port (e.g. 5678). If the
code on the OpenStack and PyCharm hosts is on different paths (likely), define
a path mapping in the remote debug configuration.

Invoke the debug configuration (*Run -> Debug... -> (config name)*). PyCharm
will begin listening on the specified host and port.

Export *DEBUGGER_TYPE*, *DEBUGGER_HOST* and *DEBUGGER_PORT* (host and port of
the system running the IDE, respectively), and start the Octavia service you
want to debug. It is recommended to run only one uWSGI process/controller
worker. For example, to debug the Octavia Worker service:

::

    $ export DEBUGGER_TYPE=pydev
    $ export DEBUGGER_HOST=192.168.121.1
    $ export DEBUGGER_PORT=5678
    $ /usr/bin/octavia-worker --config-file /etc/octavia/octavia.conf

Another example is debugging the Octavia API service with the ptvsd debugger:

::

    $ export DEBUGGER_TYPE=ptvsd
    $ export DEBUGGER_HOST=192.168.121.1
    $ export DEBUGGER_PORT=5678
    $ /usr/bin/uwsgi --ini /etc/octavia/octavia-uwsgi.ini -p 1

The service will connect to your IDE, at which point remote debugging is
active. Resume the program on the debugger to continue with the initialization
of the service. At this point, the service should be operational and you can
start debugging.
