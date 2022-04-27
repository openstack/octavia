====================
Testing with Octavia
====================


Unit Testing
------------

Octavia uses tox to manage the virtual environments for running test cases.

Install python-tox:

.. code-block:: bash

    $ pip install tox

To run the full suite of tests maintained within Octavia.

.. code-block:: bash

    $ tox

.. NOTE::

    The first time you run ``tox``, it will take additional time to build
    virtualenvs. You can later use the ``-r`` option with ``tox`` to rebuild
    your virtualenv in a similar manner.


To run tests for one or more specific test environments(for example, the most
common configuration of Python 3.8 and PEP-8), list the environments with the
``-e`` option, separated by spaces:

.. code-block:: bash

    $ tox -e py38,pep8

See ``tox -l`` for the full list of available test environments.

Structure of the Unit Test Tree
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The structure of the unit test tree should match the structure of the
code tree, e.g. ::

 - target module: octavia.common.utils

 - test module: octavia.tests.unit.common.test_utils

Unit test modules should have the same path under octavia/tests/unit/
as the module they target has under octavia/, and their name should be
the name of the target module prefixed by `test_`. This requirement
is intended to make it easier for developers to find the unit tests
for a given module.

Similarly, when a test module targets a package, that module's name
should be the name of the package prefixed by `test_` with the same
path as when a test targets a module, e.g. ::

 - target package: octavia.hacking

 - test module: octavia.tests.unit.test_hacking

The following command can be used to validate whether the unit test
tree is structured according to the above requirements: ::

    ./tools/check_unit_test_structure.sh

Where appropriate, exceptions can be added to the above script. If
code is not part of the Octavia namespace, for example, it's probably
reasonable to exclude their unit tests from the check.

Functional Testing
------------------

Octavia creates a simulated API and handler for its functional tests.
The tests then run requests against the mocked up API.

To run the entire suite of functional tests:

.. code-block:: bash

    $ tox -e functional

To run a specific functional test:

.. code-block:: bash

    $ tox -e functional octavia.tests.functional.api.v2.test_load_balancer

Tests can also be run using partial matching, to run all API tests for v2:

.. code-block:: bash

    $ tox -e functional api.v2

Additional options can be used while running tests. Two useful options that can
be used when running tests are ``-- --until-failure`` which will run the tests
in a loop until the first failure is hit, and ``-- --failing`` which if used
after an initial run will only run the tests that failed in the previous run.

Scenario Testing
----------------

Octavia uses Tempest to cover the scenario tests for the project.
These tests are run against actual cloud deployments.

To run the entire suite of scenario tests:

.. code-block:: bash

    $ tox -e scenario

.. NOTE::

    The first time running the Tempest scenario tests export the
    Tempest configuration directory
    (i.e. TEMPEST_CONFIG_DIR=/opt/stack/tempest/etc)

