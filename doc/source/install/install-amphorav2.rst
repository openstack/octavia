.. _install-amphorav2:

Additional configuration steps to configure amphorav2 provider
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you would like to use amphorav2 provider for load-balancer service the
following additional steps are required.


Prerequisites
-------------

Amphorav2 provider requires creation of additional database
``octavia_persistence`` to store info about state of tasks and progress of its
execution.
Also to monitor progress on taskflow jobs amphorav2 provider uses
jobboard. As jobboard backend could be used Redis or Zookeeper key-value
storages. Operator should chose the one that is more preferable for specific
cloud. The default is Redis.

1. Create the database, complete these steps:

   * Use the database access client to connect to the database
     server as the ``root`` user:

     .. code-block:: console

        # mysql

   * Create the ``octavia_persistence`` database:

     .. code-block:: console

        CREATE DATABASE octavia_persistence;

   * Grant proper access to the ``octavia_persistence`` database:

     .. code-block:: console

        GRANT ALL PRIVILEGES ON octavia.* TO 'octavia_persistence'@'localhost' \
        IDENTIFIED BY 'OCTAVIA_DBPASS';
        GRANT ALL PRIVILEGES ON octavia.* TO 'octavia_persistence'@'%' \
        IDENTIFIED BY 'OCTAVIA_DBPASS';

     Replace OCTAVIA_DBPASS with a suitable password.


2. Install desired key-value backend (Redis or Zookeper).

Additional configuration to octavia components
----------------------------------------------

1. Edit the ``/etc/octavia/octavia.conf`` file ``[task_flow]`` section

    * Configure database access for persistence backend:

    .. code-block:: ini

        [task_flow]
        persistence_connection = mysql+pymysql://octavia:OCTAVIA_DBPASS@controller/octavia_persistence

     Replace OCTAVIA_DBPASS with the password you chose for the Octavia databases.

    * Set desired jobboard backend and its configuration:

    .. code-block:: ini

        [task_flow]
        jobboard_backend_driver = 'redis_taskflow_driver'
        jobboard_backend_hosts = KEYVALUE_HOST_IPS
        jobboard_backend_port = KEYVALUE_PORT
        jobboard_backend_password = OCTAVIA_JOBBOARDPASS
        jobboard_backend_namespace = 'octavia_jobboard'

    Replace OCTAVIA_JOBBOARDPASS with the password you chose for the Octavia
    key-value storage.
    Replace KEYVALUE_HOST_IPS and KEYVALUE_PORT with ip and port which
    chosen key-value storage is using.

2. Populate the octavia database:

   .. code-block:: console

      # octavia-db-manage --config-file /etc/octavia/octavia.conf upgrade_persistence
