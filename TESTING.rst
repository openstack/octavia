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
common configuration of Python 2.7 and PEP-8), list the environments with the
``-e`` option, separated by spaces:

.. code-block:: bash

    $ tox -e py27,pep8

See ``tox -l`` for the full list of available test environments.

Functional Testing
------------------

Octavia creates a simulated API and handler for its functional tests.
The tests then run requests against the mocked up API.

To run the entire suite of functional tests:

.. code-block:: bash

    $ tox -e functional

To run a specific functional test:

.. code-block:: bash

    $ tox -e functional octavia.tests.functional.api.v1.test_load_balancer

Tests can also be run using partial matching, to run all API tests for v1:

.. code-block:: bash

    $ tox -e functional api.v1

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

