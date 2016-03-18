================================
Octavia configuration options
================================

Use the following options in the /etc/octavia/octavia.conf file.

.. _octavia-config-table:

.. list-table:: Description of Octavia configuration options
   :header-rows: 1
   :class: config-ref-table

   * - Configuration option = Default value
     - Description
   * - **[DEFAULT]**
     -
   * - ``api_handler`` = ``queue_producer``
     - (StrOpt) The handler that the API communicates with
   * - ``bind_host`` = ``0.0.0.0``
     - (IPOpt) The host IP to bind to
   * - ``bind_port`` = ``9876``
     - (PortOpt) The port to bind to
   * - ``debug`` = ``False``
     - (BoolOpt) If set to true, the logging level will be set to DEBUG instead of the default INFO level.
   * - ``host`` = ``localhost``
     - (StrOpt) The hostname Octavia is running on
   * - ``octavia_plugins`` = ``hot_plug_plugin``
     - (StrOpt) Name of the controller plugin to use
   * - ``verbose`` = ``True``
     - (BoolOpt) If set to false, the logging level will be set to WARNING instead of the default INFO level.
   * - **[amphora_agent]**
     -
   * - ``agent_server_ca`` = ``/etc/octavia/certs/client_ca.pem``
     - (StrOpt) The ca which signed the client certificates
   * - ``agent_server_cert`` = ``/etc/octavia/certs/server.pem``
     - (StrOpt) The server certificate for the agent.py server to use
   * - ``agent_server_network_dir`` = ``/etc/network/interfaces.d/``
     - (StrOpt) The directory where new network interfaces are located
   * - ``agent_server_network_file`` = ``None``
     - (StrOpt) The file where the network interfaces are located. Specifying this will override any value set for agent_server_network_dir.
   * - ``amphora_id`` = ``None``
     - (StrOpt) The amphora ID.
   * - **[anchor]**
     -
   * - ``password`` = ``simplepassword``
     - (StrOpt) Anchor password
   * - ``url`` = ``http://localhost:9999/v1/sign/default``
     - (StrOpt) Anchor URL
   * - ``username`` = ``myusername``
     - (StrOpt) Anchor username
   * - **[certificates]**
     -
   * - ``barbican_auth`` = ``barbican_acl_auth``
     - (StrOpt) Name of the Barbican authentication method to use
   * - ``ca_certificate`` = ``/etc/ssl/certs/ssl-cert-snakeoil.pem``
     - (StrOpt) Absolute path to the CA Certificate for signing. Defaults to env[OS_OCTAVIA_TLS_CA_CERT].
   * - ``ca_private_key`` = ``/etc/ssl/private/ssl-cert-snakeoil.key``
     - (StrOpt) Absolute path to the Private Key for signing. Defaults to env[OS_OCTAVIA_TLS_CA_KEY].
   * - ``ca_private_key_passphrase`` = ``None``
     - (StrOpt) Passphrase for the Private Key. Defaults to env[OS_OCTAVIA_CA_KEY_PASS] or None.
   * - ``cert_generator`` = ``local_cert_generator``
     - (StrOpt) Name of the cert generator to use
   * - ``cert_manager`` = ``barbican_cert_manager``
     - (StrOpt) Name of the cert manager to use
   * - ``endpoint_type`` = ``publicURL``
     - (StrOpt) The endpoint_type to be used for barbican service.
   * - ``region_name`` = ``None``
     - (StrOpt) Region in Identity service catalog to use for communication with the barbican service.
   * - ``signing_digest`` = ``sha256``
     - (StrOpt) Certificate signing digest. Defaults to env[OS_OCTAVIA_CA_SIGNING_DIGEST] or "sha256".
   * - ``storage_path`` = ``/var/lib/octavia/certificates/``
     - (StrOpt) Absolute path to the certificate storage directory. Defaults to env[OS_OCTAVIA_TLS_STORAGE].
   * - **[controller_worker]**
     -
   * - ``amp_active_retries`` = ``10``
     - (IntOpt) Retry attempts to wait for Amphora to become active
   * - ``amp_active_wait_sec`` = ``10``
     - (IntOpt) Seconds to wait between checks on whether an Amphora has become active
   * - ``amp_flavor_id`` =
     - (StrOpt) Nova instance flavor id for the Amphora
   * - ``amp_image_id`` =
     - (StrOpt) Glance image id for the Amphora image to boot
   * - ``amp_image_tag`` =
     - (StrOpt) Glance image tag for the Amphora image to boot. Use this option to be able to update the image without reconfiguring Octavia. Ignored if amp_image_id is defined.
   * - ``amp_network`` =
     - (StrOpt) Network to attach to the Amphora
   * - ``amp_secgroup_list`` =
     - (ListOpt) List of security groups to attach to the Amphora
   * - ``amp_ssh_access_allowed`` = ``True``
     - (BoolOpt) Determines whether or not to allow access to the Amphorae
   * - ``amp_ssh_key_name`` =
     - (StrOpt) SSH key name used to boot the Amphora
   * - ``amphora_driver`` = ``amphora_noop_driver``
     - (StrOpt) Name of the amphora driver to use
   * - ``cert_generator`` = ``local_cert_generator``
     - (StrOpt) Name of the cert generator to use
   * - ``client_ca`` = ``/etc/octavia/certs/ca_01.pem``
     - (StrOpt) Client CA for the amphora agent to use
   * - ``compute_driver`` = ``compute_noop_driver``
     - (StrOpt) Name of the compute driver to use
   * - ``loadbalancer_topology`` = ``SINGLE``
     - (StrOpt) Load balancer topology configuration. SINGLE - One amphora per load balancer. ACTIVE_STANDBY - Two amphora per load balancer.
   * - ``network_driver`` = ``network_noop_driver``
     - (StrOpt) Name of the network driver to use
   * - ``user_data_config_drive`` = ``False``
     - (BoolOpt) If True, build cloud-init user-data that is passed to the config drive on Amphora boot instead of personality files. If False, utilize personality files.
   * - **[database]**
     -
   * - ``backend`` = ``sqlalchemy``
     - (StrOpt) The back end to use for the database.
   * - ``connection`` = ``None``
     - (StrOpt) The SQLAlchemy connection string to use to connect to the database.
   * - ``connection_debug`` = ``0``
     - (IntOpt) Verbosity of SQL debugging information: 0=None, 100=Everything.
   * - ``connection_trace`` = ``False``
     - (BoolOpt) Add Python stack traces to SQL as comment strings.
   * - ``db_inc_retry_interval`` = ``True``
     - (BoolOpt) If True, increases the interval between retries of a database operation up to db_max_retry_interval.
   * - ``db_max_retries`` = ``20``
     - (IntOpt) Maximum retries in case of connection error or deadlock error before error is raised. Set to -1 to specify an infinite retry count.
   * - ``db_max_retry_interval`` = ``10``
     - (IntOpt) If db_inc_retry_interval is set, the maximum seconds between retries of a database operation.
   * - ``db_retry_interval`` = ``1``
     - (IntOpt) Seconds between retries of a database transaction.
   * - ``idle_timeout`` = ``3600``
     - (IntOpt) Timeout before idle SQL connections are reaped.
   * - ``max_overflow`` = ``50``
     - (IntOpt) If set, use this value for max_overflow with SQLAlchemy.
   * - ``max_pool_size`` = ``None``
     - (IntOpt) Maximum number of SQL connections to keep open in a pool.
   * - ``max_retries`` = ``10``
     - (IntOpt) Maximum number of database connection retries during startup. Set to -1 to specify an infinite retry count.
   * - ``min_pool_size`` = ``1``
     - (IntOpt) Minimum number of SQL connections to keep open in a pool.
   * - ``mysql_sql_mode`` = ``TRADITIONAL``
     - (StrOpt) The SQL mode to be used for MySQL sessions. This option, including the default, overrides any server-set SQL mode. To use whatever SQL mode is set by the server configuration, set this to no value. Example: mysql_sql_mode=
   * - ``pool_timeout`` = ``None``
     - (IntOpt) If set, use this value for pool_timeout with SQLAlchemy.
   * - ``retry_interval`` = ``10``
     - (IntOpt) Interval between retries of opening a SQL connection.
   * - ``slave_connection`` = ``None``
     - (StrOpt) The SQLAlchemy connection string to use to connect to the slave database.
   * - ``use_db_reconnect`` = ``False``
     - (BoolOpt) Enable the experimental use of database reconnect on connection lost.
   * - **[glance]**
     -
   * - ``ca_certificates_file`` = ``None``
     - (StrOpt) CA certificates file path
   * - ``endpoint`` = ``None``
     - (StrOpt) A new endpoint to override the endpoint in the keystone catalog.
   * - ``endpoint_type`` = ``publicURL``
     - (StrOpt) Endpoint interface in identity service to use
   * - ``insecure`` = ``False``
     - (BoolOpt) Disable certificate validation on SSL connections
   * - ``region_name`` = ``None``
     - (StrOpt) Region in Identity service catalog to use for communication with the OpenStack services.
   * - ``service_name`` = ``None``
     - (StrOpt) The name of the glance service in the keystone catalog
   * - **[haproxy_amphora]**
     -
   * - ``base_cert_dir`` = ``/var/lib/octavia/certs``
     - (StrOpt) Base directory for cert storage.
   * - ``base_path`` = ``/var/lib/octavia``
     - (StrOpt) Base directory for amphora files.
   * - ``bind_host`` = ``0.0.0.0``
     - (IPOpt) The host IP to bind to
   * - ``bind_port`` = ``9443``
     - (PortOpt) The port to bind to
   * - ``client_cert`` = ``/etc/octavia/certs/client.pem``
     - (StrOpt) The client certificate to talk to the agent
   * - ``connection_max_retries`` = ``300``
     - (IntOpt) Retry threshold for connecting to amphorae.
   * - ``connection_retry_interval`` = ``5``
     - (IntOpt) Retry timeout between connection attempts in seconds.
   * - ``haproxy_cmd`` = ``/usr/sbin/haproxy``
     - (StrOpt) The full path to haproxy
   * - ``haproxy_stick_size`` = ``10k``
     - (StrOpt) Size of the HAProxy stick table. Accepts k, m, g suffixes. Example: 10k
   * - ``haproxy_template`` = ``None``
     - (StrOpt) Custom haproxy template.
   * - ``respawn_count`` = ``2``
     - (IntOpt) The respawn count for haproxy's upstart script
   * - ``respawn_interval`` = ``2``
     - (IntOpt) The respawn interval for haproxy's upstart script
   * - ``rest_request_conn_timeout`` = ``10``
     - (FloatOpt) The time in seconds to wait for a REST API to connect.
   * - ``rest_request_read_timeout`` = ``60``
     - (FloatOpt) The time in seconds to wait for a REST API response.
   * - ``server_ca`` = ``/etc/octavia/certs/server_ca.pem``
     - (StrOpt) The ca which signed the server certificates
   * - ``use_upstart`` = ``True``
     - (BoolOpt) If False, use sysvinit.
   * - **[health_manager]**
     -
   * - ``bind_ip`` = ``0.0.0.0``
     - (IPOpt) IP address the controller will listen on for heart beats
   * - ``bind_port`` = ``5555``
     - (PortOpt) Port number the controller will listen onfor heart beats
   * - ``controller_ip_port_list`` =
     - (ListOpt) List of controller ip and port pairs for the heartbeat receivers. Example 127.0.0.1:5555, 192.168.0.1:5555
   * - ``event_streamer_driver`` = ``noop_event_streamer``
     - (StrOpt) Specifies which driver to use for the event_streamer for syncing the octavia and neutron_lbaas dbs. If you don't need to sync the database or are running octavia in stand alone mode use the noop_event_streamer
   * - ``failover_threads`` = ``10``
     - (IntOpt) Number of threads performing amphora failovers.
   * - ``health_check_interval`` = ``3``
     - (IntOpt) Sleep time between health checks in seconds.
   * - ``heartbeat_interval`` = ``10``
     - (IntOpt) Sleep time between sending hearthbeats.
   * - ``heartbeat_key`` = ``None``
     - (StrOpt) key used to validate amphora sendingthe message
   * - ``heartbeat_timeout`` = ``60``
     - (IntOpt) Interval, in seconds, to wait before failing over an amphora.
   * - ``sock_rlimit`` = ``0``
     - (IntOpt) sets the value of the heartbeat recv buffer
   * - ``status_update_threads`` = ``50``
     - (IntOpt) Number of threads performing amphora status update.
   * - **[house_keeping]**
     -
   * - ``amphora_expiry_age`` = ``604800``
     - (IntOpt) Amphora expiry age in seconds
   * - ``cert_expiry_buffer`` = ``1209600``
     - (IntOpt) Seconds until certificate expiration
   * - ``cert_interval`` = ``3600``
     - (IntOpt) Certificate check interval in seconds
   * - ``cert_rotate_threads`` = ``10``
     - (IntOpt) Number of threads performing amphora certificate rotation
   * - ``cleanup_interval`` = ``30``
     - (IntOpt) DB cleanup interval in seconds
   * - ``spare_amphora_pool_size`` = ``0``
     - (IntOpt) Number of spare amphorae
   * - ``spare_check_interval`` = ``30``
     - (IntOpt) Spare check interval in seconds
   * - **[keepalived_vrrp]**
     -
   * - ``vrrp_advert_int`` = ``1``
     - (IntOpt) Amphora role and priority advertisement interval in seconds.
   * - ``vrrp_check_interval`` = ``5``
     - (IntOpt) VRRP health check script run interval in seconds.
   * - ``vrrp_fail_count`` = ``2``
     - (IntOpt) Number of successive failure before transition to a fail state.
   * - ``vrrp_garp_refresh_count`` = ``2``
     - (IntOpt) Number of gratuitous ARP announcements to make on each refresh interval.
   * - ``vrrp_garp_refresh_interval`` = ``5``
     - (IntOpt) Time in seconds between gratuitous ARP announcements from the MASTER.
   * - ``vrrp_success_count`` = ``2``
     - (IntOpt) Number of successive failure before transition to a success state.
   * - **[keystone_authtoken]**
     -
   * - ``admin_password`` = ``None``
     - (StrOpt) Service user password.
   * - ``admin_tenant_name`` = ``admin``
     - (StrOpt) Service tenant name.
   * - ``admin_user`` = ``None``
     - (StrOpt) Service username.
   * - ``auth_uri`` = ``None``
     - (StrOpt) Complete public Identity API endpoint.
   * - ``cafile`` = ``None``
     - (StrOpt) A PEM encoded Certificate Authority to use when verifying HTTPs connections. Defaults to system CAs.
   * - ``certfile`` = ``None``
     - (StrOpt) Required if identity server requires client certificate
   * - ``insecure`` = ``False``
     - (BoolOpt) Verify HTTPS connections.
   * - ``keyfile`` = ``None``
     - (StrOpt) Required if identity server requires client certificate
   * - ``region_name`` = ``None``
     - (StrOpt) The region in which the identity server can be found.
   * - **[keystone_authtoken_v3]**
     -
   * - ``admin_project_domain`` = ``default``
     - (StrOpt) Admin project keystone authentication domain
   * - ``admin_user_domain`` = ``default``
     - (StrOpt) Admin user keystone authentication domain
   * - **[networking]**
     -
   * - ``lb_network_name`` = ``None``
     - (StrOpt) Name of amphora internal network
   * - ``max_retries`` = ``15``
     - (IntOpt) The maximum attempts to retry an action with the networking service.
   * - ``retry_interval`` = ``1``
     - (IntOpt) Seconds to wait before retrying an action with the networking service.
   * - **[neutron]**
     -
   * - ``ca_certificates_file`` = ``None``
     - (StrOpt) CA certificates file path
   * - ``endpoint`` = ``None``
     - (StrOpt) A new endpoint to override the endpoint in the keystone catalog.
   * - ``endpoint_type`` = ``publicURL``
     - (StrOpt) Endpoint interface in identity service to use
   * - ``insecure`` = ``False``
     - (BoolOpt) Disable certificate validation on SSL connections
   * - ``region_name`` = ``None``
     - (StrOpt) Region in Identity service catalog to use for communication with the OpenStack services.
   * - ``service_name`` = ``None``
     - (StrOpt) The name of the neutron service in the keystone catalog
   * - **[nova]**
     -
   * - ``ca_certificates_file`` = ``None``
     - (StrOpt) CA certificates file path
   * - ``enable_anti_affinity`` = ``False``
     - (BoolOpt) Flag to indicate if nova anti-affinity feature is turned on.
   * - ``endpoint`` = ``None``
     - (StrOpt) A new endpoint to override the endpoint in the keystone catalog.
   * - ``endpoint_type`` = ``publicURL``
     - (StrOpt) Endpoint interface in identity service to use
   * - ``insecure`` = ``False``
     - (BoolOpt) Disable certificate validation on SSL connections
   * - ``region_name`` = ``None``
     - (StrOpt) Region in Identity service catalog to use for communication with the OpenStack services.
   * - ``service_name`` = ``None``
     - (StrOpt) The name of the nova service in the keystone catalog
   * - **[oslo_messaging]**
     -
   * - ``event_stream_topic`` = ``neutron_lbaas_event``
     - (StrOpt) topic name for communicating events through a queue
   * - ``topic`` = ``None``
     - (StrOpt) No help text available for this option.
   * - **[oslo_messaging_rabbit]**
     -
   * - ``rabbit_hosts`` = ``$rabbit_host:$rabbit_port``
     - (ListOpt) RabbitMQ HA cluster host:port pairs.
   * - ``rabbit_password`` = ``guest``
     - (StrOpt) The RabbitMQ password.
   * - ``rabbit_port`` = ``5672``
     - (PortOpt) The RabbitMQ broker port where a single node is used.
   * - ``rabbit_userid`` = ``guest``
     - (StrOpt) The RabbitMQ userid.
   * - ``rpc_conn_pool_size`` = ``30``
     - (IntOpt) Size of RPC connection pool.
   * - **[task_flow]**
     -
   * - ``engine`` = ``serial``
     - (StrOpt) TaskFlow engine to use
   * - ``max_workers`` = ``5``
     - (IntOpt) The maximum number of workers
