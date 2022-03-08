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

Both PyCharm Professional edition and Visual Studio Code offer remote debugging
features that can be used for debugging Octavia components.

.. note:: Before running a new Octavia process you should
    make sure that processes of that component are no longer running.
    You can use ``ps aux`` in order to verify that.

PyCharm
-------

.. note:: Remote debugging is a *PyCharm Professional* feature.

PyCharm offers two ways of debugging remotely [1]_. In general, the
"through a remote interpreter" approach is more convenient and should
be preferred.
On the other hand, the "Python debug server" approach is the only
one that works for debugging the API component (because of uWSGI).
Therefore, this guide will explain both approaches.

Using a remote interpreter
~~~~~~~~~~~~~~~~~~~~~~~~~~

First, configure a remote interpreter for the VM as documented in [2]_.
Adding a deployment configuration with correct path mappings allows
PyCharm to upload local changes to the remote host automatically.

Then, create a new *Run/Debug Configuration* by selecting
*Run -> Edit Configurations...* in the menu bar.
Add a new configuration and make sure
*Module name* is selected instead of *Script path*. Enter the module name of
the Octavia component you want to debug, for instance
``octavia.cmd.octavia_worker``. Additionally, add
``--config-file /etc/octavia/octavia.conf`` to *Parameters*.
Then check whether the right remote Python interpreter
is selected. After you confirm the settings by clicking *OK* you should be
able to run/debug the Octavia component with that new run configuration.

Using a Python debug server
~~~~~~~~~~~~~~~~~~~~~~~~~~~

As mentioned above the "remote interpreter" approach does not work with
*Octavia-API* because that process is managed by uWSGI. Here the
Python debug server approach [3]_ needs to be used. You will need to
install the ``pydevd-pycharm`` via ``pip`` as shown when creating the run/debug
configuration. However, it is not necessary to modify the Python code
in any way because Octavia code is already set up for it to work.

Export *DEBUGGER_TYPE*, *DEBUGGER_HOST* and *DEBUGGER_PORT* (host and port of
the system running the IDE, respectively), and start the Octavia service you
want to debug. For example, to debug the Octavia API service::

    $ export DEBUGGER_TYPE=pydev
    $ export DEBUGGER_HOST=192.168.121.1
    $ export DEBUGGER_PORT=5678
    $ uwsgi --ini /etc/octavia/octavia-uwsgi.ini

.. note:: You must run the Octavia/uWSGI command directly. Starting it
    via ``systemctl`` will not work with the debug server.

Visual Studio Code
------------------

While PyCharm synchronizes local changes with
the remote host, Code will work on the remote environment directly
through a SSH tunnel. That means that you don't even need to have
source code on your local machine in order to debug code on the remote.

Detail information about remote debugging over SSH can be found
in the official Visual Studio Code documentation [4]_.
This guide will focus on the essential steps only.

Using the remote development extension pack
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. note:: This approach will not work with the Octavia API component
    because that component is managed by uWSGI.

After installing the *Visual Studio Code Remote Development Extension Pack*
[5]_ you need to open the *Remote Explorer* view and connect to the
SSH target. This will open a new window and on the bottom left of that window
you should see *SSH:* followed by the SSH host name. In the *Explorer*
view you can then choose to either clone a repository or open an
existing folder on the remote. For instance when working with
devstack you might want to open */opt/stack* or */opt/stack/octavia*.

Next, you should configure the *launch.json*, which contains the run
configurations. Use the following template and adjust it to your needs::

    {
        // Use IntelliSense to learn about possible attributes.
        // Hover to view descriptions of existing attributes.
        // For more information, visit: https://go.microsoft.com/fwlink/?linkid=830387
        "version": "0.2.0",
        "configurations": [
            {
                "name": "Octavia Worker",
                "type": "python",
                "request": "launch",
                "module": "octavia.cmd.octavia_worker",
                "args": ["--config-file", "/etc/octavia/octavia.conf"],
                "justMyCode": true
            }
        ]
    }

Make sure that the correct Python interpreter is selected in the status bar.
In a devstack environment the global Python interpreter */usr/bin/python3*
should be the correct one. Now you can start debugging by pressing *F5*.

.. note:: When running this the first time Visual Studio Code might ask you
    to install the Python debugger extension on the remote, which you must
    do. Simply follow the steps shown in the IDE.

Using ptvsd
~~~~~~~~~~~

.. warning:: ptvsd has been deprecated and replaced by debugpy. However, debugpy doesn't seem
    work with uWSGI processes. The information in this section might be outdated.

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

Troubleshooting
===============

Remote process does not connect with local PyCharm debug server
---------------------------------------------------------------

#. Check if the debug server is still running
#. Check if the values of the exported *DEBUGGER_* variables above are correct.
#. Check if the remote machine can reach the port of the debug server::

    $ nc -zvw10 $DEBUGGER_HOST $DEBUGGER_PORT

   If it cannot connect, the connection may be blocked by a firewall.

.. [1] https://www.jetbrains.com/help/pycharm/remote-debugging-with-product.html
.. [2] https://www.jetbrains.com/help/pycharm/remote-debugging-with-product.html#remote-interpreter
.. [3] https://www.jetbrains.com/help/pycharm/remote-debugging-with-product.html#remote-debug-config
.. [4] https://code.visualstudio.com/docs/remote/ssh
.. [5] https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.vscode-remote-extensionpack
