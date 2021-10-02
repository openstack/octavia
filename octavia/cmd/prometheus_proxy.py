#!/usr/bin/python3
#    Copyright 2022 Red Hat
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

# This prometheus-proxy is intended to abstract the prometheus metrics
# exported from the reference provider driver load balancing engines (haproxy
# and lvs) such that all of the provider drivers can expose a consistent set
# of metrics. It also aligns the terms to be consistent with Octavia
# terminology.

from http.server import HTTPServer
from http.server import SimpleHTTPRequestHandler
import os
import signal
import socketserver
import sys
import threading
import time
import traceback
import urllib.request

import psutil

from octavia.amphorae.backends.utils import network_namespace
from octavia.common import constants as consts

METRICS_URL = "http://127.0.0.1:9101/metrics"
PRINT_REJECTED = False
EXIT_EVENT = threading.Event()

# A dictionary of prometheus metrics mappings.
# Key: The metric string to match
# Value: A tuple of replacement data.
#    tuple[0]: The string to replace the key with.
#    tuple[1]: If not None, the replacement HELP line for the metric.
#    If tuple[1] is None, the key will be replaced in the HELP string.
#    tuple[2]: If not None, includes a dictionary of additional substitutions.
#    tuple[2] substitutions happen prior to the key replacement in tuple[0].
METRIC_MAP = {
    # Load balancer metrics
    "haproxy_process_pool_allocated_bytes ":
        ("octavia_memory_pool_allocated_bytes ",
         "# HELP octavia_memory_pool_allocated_bytes Total amount of memory "
         "allocated in the memory pools (in bytes).\n", None),
    "haproxy_process_pool_used_bytes ":
        ("octavia_memory_pool_used_bytes ",
         "# HELP octavia_memory_pool_used_bytes Total amount of memory used "
         "in the memory pools (in bytes).\n", None),
    "haproxy_process_pool_failures_total ":
        ("octavia_memory_pool_failures_total ",
         "# HELP octavia_memory_pool_failures_total Total number of failed "
         "memory pool allocations.\n", None),
    "haproxy_process_max_connections ":
        ("octavia_loadbalancer_max_connections ", None, None),
    "haproxy_process_current_connections ":
        ("octavia_loadbalancer_current_connections ", None, None),
    # TODO(johnsom) consider adding in UDP
    "haproxy_process_connections_total ":
        ("octavia_loadbalancer_connections_total ", None, None),
    # TODO(johnsom) consider adding in UDP (and update help string)
    "haproxy_process_requests_total ":
        ("octavia_loadbalancer_requests_total ", None, None),
    "haproxy_process_max_ssl_connections ":
        ("octavia_loadbalancer_max_ssl_connections ", None, None),
    "haproxy_process_current_ssl_connections ":
        ("octavia_loadbalancer_current_ssl_connections ",
         "# HELP octavia_loadbalancer_current_ssl_connections Number of "
         "active SSL connections.\n", None),
    "haproxy_process_ssl_connections_total ":
        ("octavia_loadbalancer_ssl_connections_total ", None, None),
    "haproxy_process_current_connection_rate ":
        ("octavia_loadbalancer_current_connection_rate ", None, None),
    "haproxy_process_limit_connection_rate ":
        ("octavia_loadbalancer_limit_connection_rate ", None, None),
    "haproxy_process_max_connection_rate ":
        ("octavia_loadbalancer_max_connection_rate ", None, None),
    "haproxy_process_current_session_rate ":
        ("octavia_loadbalancer_current_session_rate ", None, None),
    "haproxy_process_limit_session_rate ":
        ("octavia_loadbalancer_limit_session_rate ", None, None),
    "haproxy_process_max_session_rate ":
        ("octavia_loadbalancer_max_session_rate ", None, None),
    "haproxy_process_current_ssl_rate ":
        ("octavia_loadbalancer_current_ssl_rate ", None, None),
    "haproxy_process_limit_ssl_rate ":
        ("octavia_loadbalancer_limit_ssl_rate ", None, None),
    "haproxy_process_max_ssl_rate ":
        ("octavia_loadbalancer_max_ssl_rate ", None, None),
    "haproxy_process_current_frontend_ssl_key_rate ":
        ("octavia_loadbalancer_current_frontend_ssl_key_rate ", None, None),
    "haproxy_process_max_frontend_ssl_key_rate ":
        ("octavia_loadbalancer_max_frontend_ssl_key_rate ", None, None),
    "haproxy_process_frontent_ssl_reuse ":
        ("octavia_loadbalancer_frontent_ssl_reuse ", None, None),
    "haproxy_process_current_backend_ssl_key_rate ":
        ("octavia_loadbalancer_current_backend_ssl_key_rate ", None, None),
    "haproxy_process_max_backend_ssl_key_rate ":
        ("octavia_loadbalancer_max_backend_ssl_key_rate ", None, None),
    "haproxy_process_ssl_cache_lookups_total ":
        ("octavia_loadbalancer_ssl_cache_lookups_total ", None, None),
    "haproxy_process_ssl_cache_misses_total ":
        ("octavia_loadbalancer_ssl_cache_misses_total ", None, None),
    "haproxy_process_http_comp_bytes_in_total ":
        ("octavia_loadbalancer_http_comp_bytes_in_total ", None, None),
    "haproxy_process_http_comp_bytes_out_total ":
        ("octavia_loadbalancer_http_comp_bytes_out_total ", None, None),
    "haproxy_process_limit_http_comp ":
        ("octavia_loadbalancer_limit_http_comp ", None, None),
    "haproxy_process_listeners ":
        ("octavia_loadbalancer_listeners ", None, None),
    "haproxy_process_dropped_logs_total ":
        ("octavia_loadbalancer_dropped_logs_total ", None, None),

    # Listener metrics
    "haproxy_frontend_status ":
        ("octavia_listener_status ",
         "# HELP octavia_listener_status Current status of the listener. "
         "0=OFFLINE, 1=ONLINE, 2=DEGRADED.\n", None),
    "haproxy_frontend_status{":
        ("octavia_listener_status{", None, {"proxy=": "listener="}),
    "haproxy_frontend_current_sessions ":
        ("octavia_listener_current_sessions ", None, None),
    "haproxy_frontend_current_sessions{":
        ("octavia_listener_current_sessions{", None,
         {"proxy=": "listener="}),
    "haproxy_frontend_max_sessions ":
        ("octavia_listener_max_sessions ", None, None),
    "haproxy_frontend_max_sessions{":
        ("octavia_listener_max_sessions{", None, {"proxy=": "listener="}),
    "haproxy_frontend_limit_sessions ":
        ("octavia_listener_limit_sessions ", None, None),
    "haproxy_frontend_limit_sessions{":
        ("octavia_listener_limit_sessions{", None, {"proxy=": "listener="}),
    "haproxy_frontend_sessions_total ":
        ("octavia_listener_sessions_total ", None, None),
    "haproxy_frontend_sessions_total{":
        ("octavia_listener_sessions_total{", None, {"proxy=": "listener="}),
    "haproxy_frontend_limit_session_rate ":
        ("octavia_listener_limit_session_rate ", None, None),
    "haproxy_frontend_limit_session_rate{":
        ("octavia_listener_limit_session_rate{", None,
         {"proxy=": "listener="}),
    "haproxy_frontend_max_session_rate ":
        ("octavia_listener_max_session_rate ", None, None),
    "haproxy_frontend_max_session_rate{":
        ("octavia_listener_max_session_rate{", None,
         {"proxy=": "listener="}),
    "haproxy_frontend_connections_rate_max ":
        ("octavia_listener_connections_rate_max ", None, None),
    "haproxy_frontend_connections_rate_max{":
        ("octavia_listener_connections_rate_max{", None,
         {"proxy=": "listener="}),
    "haproxy_frontend_connections_total ":
        ("octavia_listener_connections_total ", None, None),
    "haproxy_frontend_connections_total{":
        ("octavia_listener_connections_total{", None,
         {"proxy=": "listener="}),
    "haproxy_frontend_bytes_in_total ":
        ("octavia_listener_bytes_in_total ", None, None),
    "haproxy_frontend_bytes_in_total{":
        ("octavia_listener_bytes_in_total{", None, {"proxy=": "listener="}),
    "haproxy_frontend_bytes_out_total ":
        ("octavia_listener_bytes_out_total ", None, None),
    "haproxy_frontend_bytes_out_total{":
        ("octavia_listener_bytes_out_total{", None,
         {"proxy=": "listener="}),
    "haproxy_frontend_requests_denied_total ":
        ("octavia_listener_requests_denied_total ", None, None),
    "haproxy_frontend_requests_denied_total{":
        ("octavia_listener_requests_denied_total{", None,
         {"proxy=": "listener="}),
    "haproxy_frontend_responses_denied_total ":
        ("octavia_listener_responses_denied_total ", None, None),
    "haproxy_frontend_responses_denied_total{":
        ("octavia_listener_responses_denied_total{", None,
         {"proxy=": "listener="}),
    "haproxy_frontend_request_errors_total ":
        ("octavia_listener_request_errors_total ", None, None),
    "haproxy_frontend_request_errors_total{":
        ("octavia_listener_request_errors_total{", None,
         {"proxy=": "listener="}),
    "haproxy_frontend_denied_connections_total ":
        ("octavia_listener_denied_connections_total ",
         "# HELP octavia_listener_denied_connections_total Total number of "
         "requests denied by connection rules.\n", None),
    "haproxy_frontend_denied_connections_total{":
        ("octavia_listener_denied_connections_total{", None,
         {"proxy=": "listener="}),
    "haproxy_frontend_denied_sessions_total ":
        ("octavia_listener_denied_sessions_total ",
         "# HELP octavia_listener_denied_sessions_total Total number of "
         "requests denied by session rules.\n", None),
    "haproxy_frontend_denied_sessions_total{":
        ("octavia_listener_denied_sessions_total{", None,
         {"proxy=": "listener="}),
    "haproxy_frontend_failed_header_rewriting_total ":
        ("octavia_listener_failed_header_rewriting_total ",
         "# HELP octavia_listener_failed_header_rewriting_total Total number "
         "of failed header rewriting rules.\n", None),
    "haproxy_frontend_failed_header_rewriting_total{":
        ("octavia_listener_failed_header_rewriting_total{", None,
         {"proxy=": "listener="}),
    "haproxy_frontend_http_requests_rate_max ":
        ("octavia_listener_http_requests_rate_max ", None, None),
    "haproxy_frontend_http_requests_rate_max{":
        ("octavia_listener_http_requests_rate_max{", None,
         {"proxy=": "listener="}),
    "haproxy_frontend_http_requests_total ":
        ("octavia_listener_http_requests_total ", None, None),
    "haproxy_frontend_http_requests_total{":
        ("octavia_listener_http_requests_total{", None,
         {"proxy=": "listener="}),
    "haproxy_frontend_http_responses_total ":
        ("octavia_listener_http_responses_total ", None, None),
    "haproxy_frontend_http_responses_total{":
        ("octavia_listener_http_responses_total{", None,
         {"proxy=": "listener="}),
    "haproxy_frontend_intercepted_requests_total ":
        ("octavia_listener_intercepted_requests_total ", None, None),
    "haproxy_frontend_intercepted_requests_total{":
        ("octavia_listener_intercepted_requests_total{", None,
         {"proxy=": "listener="}),
    "haproxy_frontend_http_cache_lookups_total ":
        ("octavia_listener_http_cache_lookups_total ", None, None),
    "haproxy_frontend_http_cache_lookups_total{":
        ("octavia_listener_http_cache_lookups_total{", None,
         {"proxy=": "listener="}),
    "haproxy_frontend_http_cache_hits_total ":
        ("octavia_listener_http_cache_hits_total ", None, None),
    "haproxy_frontend_http_cache_hits_total{":
        ("octavia_listener_http_cache_hits_total{", None,
         {"proxy=": "listener="}),
    "haproxy_frontend_http_comp_bytes_in_total ":
        ("octavia_listener_http_comp_bytes_in_total ", None, None),
    "haproxy_frontend_http_comp_bytes_in_total{":
        ("octavia_listener_http_comp_bytes_in_total{", None,
         {"proxy=": "listener="}),
    "haproxy_frontend_http_comp_bytes_out_total ":
        ("octavia_listener_http_comp_bytes_out_total ", None, None),
    "haproxy_frontend_http_comp_bytes_out_total{":
        ("octavia_listener_http_comp_bytes_out_total{", None,
         {"proxy=": "listener="}),
    "haproxy_frontend_http_comp_bytes_bypassed_total ":
        ("octavia_listener_http_comp_bytes_bypassed_total ", None, None),
    "haproxy_frontend_http_comp_bytes_bypassed_total{":
        ("octavia_listener_http_comp_bytes_bypassed_total{", None,
         {"proxy=": "listener="}),
    "haproxy_frontend_http_comp_responses_total ":
        ("octavia_listener_http_comp_responses_total ", None, None),
    "haproxy_frontend_http_comp_responses_total{":
        ("octavia_listener_http_comp_responses_total{", None,
         {"proxy=": "listener="}),

    # Pool Metrics
    "haproxy_backend_status ":
        ("octavia_pool_status ",
         "# HELP octavia_pool_status Current status of the pool. 0=OFFLINE, "
         "1=ONLINE.\n", None),
    "haproxy_backend_status{":
        ("octavia_pool_status{", None, {"proxy=": "pool="}),
    "haproxy_backend_current_sessions ":
        ("octavia_pool_current_sessions ", None, None),
    "haproxy_backend_current_sessions{":
        ("octavia_pool_current_sessions{", None, {"proxy=": "pool="}),
    "haproxy_backend_max_sessions ":
        ("octavia_pool_max_sessions ", None, None),
    "haproxy_backend_max_sessions{":
        ("octavia_pool_max_sessions{", None, {"proxy=": "pool="}),
    "haproxy_backend_limit_sessions ":
        ("octavia_pool_limit_sessions ", None, None),
    "haproxy_backend_limit_sessions{":
        ("octavia_pool_limit_sessions{", None, {"proxy=": "pool="}),
    "haproxy_backend_sessions_total ":
        ("octavia_pool_sessions_total ", None, None),
    "haproxy_backend_sessions_total{":
        ("octavia_pool_sessions_total{", None, {"proxy=": "pool="}),
    "haproxy_backend_max_session_rate ":
        ("octavia_pool_max_session_rate ", None, None),
    "haproxy_backend_max_session_rate{":
        ("octavia_pool_max_session_rate{", None, {"proxy=": "pool="}),
    "haproxy_backend_last_session_seconds ":
        ("octavia_pool_last_session_seconds ",
         "# HELP octavia_pool_last_session_seconds Number of seconds since "
         "last session assigned to a member.\n", None, None),
    "haproxy_backend_last_session_seconds{":
        ("octavia_pool_last_session_seconds{", None, {"proxy=": "pool="}),
    "haproxy_backend_current_queue ":
        ("octavia_pool_current_queue ", None, None),
    "haproxy_backend_current_queue{":
        ("octavia_pool_current_queue{", None, {"proxy=": "pool="}),
    "haproxy_backend_max_queue ":
        ("octavia_pool_max_queue ", None, None),
    "haproxy_backend_max_queue{":
        ("octavia_pool_max_queue{", None, {"proxy=": "pool="}),
    "haproxy_backend_connection_attempts_total ":
        ("octavia_pool_connection_attempts_total ", None, None),
    "haproxy_backend_connection_attempts_total{":
        ("octavia_pool_connection_attempts_total{", None,
         {"proxy=": "pool="}),
    "haproxy_backend_connection_reuses_total ":
        ("octavia_pool_connection_reuses_total ", None, None),
    "haproxy_backend_connection_reuses_total{":
        ("octavia_pool_connection_reuses_total{", None,
         {"proxy=": "pool="}),
    "haproxy_backend_bytes_in_total ":
        ("octavia_pool_bytes_in_total ", None, None),
    "haproxy_backend_bytes_in_total{":
        ("octavia_pool_bytes_in_total{", None, {"proxy=": "pool="}),
    "haproxy_backend_bytes_out_total ":
        ("octavia_pool_bytes_out_total ", None, None),
    "haproxy_backend_bytes_out_total{":
        ("octavia_pool_bytes_out_total{", None, {"proxy=": "pool="}),
    "haproxy_backend_queue_time_average_seconds ":
        ("octavia_pool_queue_time_average_seconds ", None, None),
    "haproxy_backend_queue_time_average_seconds{":
        ("octavia_pool_queue_time_average_seconds{", None,
         {"proxy=": "pool="}),
    "haproxy_backend_connect_time_average_seconds ":
        ("octavia_pool_connect_time_average_seconds ", None, None),
    "haproxy_backend_connect_time_average_seconds{":
        ("octavia_pool_connect_time_average_seconds{", None,
         {"proxy=": "pool="}),
    "haproxy_backend_response_time_average_seconds ":
        ("octavia_pool_response_time_average_seconds ", None, None),
    "haproxy_backend_response_time_average_seconds{":
        ("octavia_pool_response_time_average_seconds{", None,
         {"proxy=": "pool="}),
    "haproxy_backend_total_time_average_seconds ":
        ("octavia_pool_total_time_average_seconds ", None, None),
    "haproxy_backend_total_time_average_seconds{":
        ("octavia_pool_total_time_average_seconds{", None,
         {"proxy=": "pool="}),
    "haproxy_backend_max_queue_time_seconds ":
        ("octavia_pool_max_queue_time_seconds ", None, None),
    "haproxy_backend_max_queue_time_seconds{":
        ("octavia_pool_max_queue_time_seconds{", None, {"proxy=": "pool="}),
    "haproxy_backend_max_connect_time_seconds ":
        ("octavia_pool_max_connect_time_seconds ", None, None),
    "haproxy_backend_max_connect_time_seconds{":
        ("octavia_pool_max_connect_time_seconds{", None,
         {"proxy=": "pool="}),
    "haproxy_backend_max_response_time_seconds ":
        ("octavia_pool_max_response_time_seconds ",
         "# HELP octavia_pool_max_response_time_seconds Maximum observed "
         "time spent waiting for a member response.\n", None),
    "haproxy_backend_max_response_time_seconds{":
        ("octavia_pool_max_response_time_seconds{", None,
         {"proxy=": "pool="}),
    "haproxy_backend_max_total_time_seconds ":
        ("octavia_pool_max_total_time_seconds ", None, None),
    "haproxy_backend_max_total_time_seconds{":
        ("octavia_pool_max_total_time_seconds{", None, {"proxy=": "pool="}),
    "haproxy_backend_requests_denied_total ":
        ("octavia_pool_requests_denied_total ", None, None),
    "haproxy_backend_requests_denied_total{":
        ("octavia_pool_requests_denied_total{", None, {"proxy=": "pool="}),
    "haproxy_backend_responses_denied_total ":
        ("octavia_pool_responses_denied_total ", None, None),
    "haproxy_backend_responses_denied_total{":
        ("octavia_pool_responses_denied_total{", None, {"proxy=": "pool="}),
    "haproxy_backend_connection_errors_total ":
        ("octavia_pool_connection_errors_total ", None, None),
    "haproxy_backend_connection_errors_total{":
        ("octavia_pool_connection_errors_total{", None,
         {"proxy=": "pool="}),
    "haproxy_backend_response_errors_total ":
        ("octavia_pool_response_errors_total ", None, None),
    "haproxy_backend_response_errors_total{":
        ("octavia_pool_response_errors_total{", None, {"proxy=": "pool="}),
    "haproxy_backend_retry_warnings_total ":
        ("octavia_pool_retry_warnings_total ", None, None),
    "haproxy_backend_retry_warnings_total{":
        ("octavia_pool_retry_warnings_total{", None, {"proxy=": "pool="}),
    "haproxy_backend_redispatch_warnings_total ":
        ("octavia_pool_redispatch_warnings_total ", None, None),
    "haproxy_backend_redispatch_warnings_total{":
        ("octavia_pool_redispatch_warnings_total{", None,
         {"proxy=": "pool="}),
    "haproxy_backend_failed_header_rewriting_total ":
        ("octavia_pool_failed_header_rewriting_total ", None, None),
    "haproxy_backend_failed_header_rewriting_total{":
        ("octavia_pool_failed_header_rewriting_total{", None,
         {"proxy=": "pool="}),
    "haproxy_backend_client_aborts_total ":
        ("octavia_pool_client_aborts_total ", None, None),
    "haproxy_backend_client_aborts_total{":
        ("octavia_pool_client_aborts_total{", None, {"proxy=": "pool="}),
    "haproxy_backend_server_aborts_total ":
        ("octavia_pool_member_aborts_total ",
         "# HELP octavia_pool_server_aborts_total Total number of data "
         "transfers aborted by the server.\n", None),
    "haproxy_backend_server_aborts_total{":
        ("octavia_pool_member_aborts_total{", None, {"proxy=": "pool="}),
    "haproxy_backend_active_servers ":
        ("octavia_pool_active_members ",
         "# HELP octavia_pool_active_members Current number of active "
         "members.\n", None),
    "haproxy_backend_active_servers{":
        ("octavia_pool_active_members{", None, {"proxy=": "pool="}),
    "haproxy_backend_backup_servers ":
        ("octavia_pool_backup_members ",
         "# HELP octavia_pool_backup_members Current number of backup "
         "members.\n", None),
    "haproxy_backend_backup_servers{":
        ("octavia_pool_backup_members{", None, {"proxy=": "pool="}),
    "haproxy_backend_check_up_down_total ":
        ("octavia_pool_check_up_down_total ", None, None),
    "haproxy_backend_check_up_down_total{":
        ("octavia_pool_check_up_down_total{", None, {"proxy=": "pool="}),
    "haproxy_backend_check_last_change_seconds ":
        ("octavia_pool_check_last_change_seconds ", None, None),
    "haproxy_backend_check_last_change_seconds{":
        ("octavia_pool_check_last_change_seconds{", None,
         {"proxy=": "pool="}),
    "haproxy_backend_downtime_seconds_total ":
        ("octavia_pool_downtime_seconds_total ",
         "# HELP octavia_pool_downtime_seconds_total Total downtime "
         "(in seconds) for the pool.\n", None),
    "haproxy_backend_downtime_seconds_total{":
        ("octavia_pool_downtime_seconds_total{", None, {"proxy=": "pool="}),
    "haproxy_backend_loadbalanced_total ":
        ("octavia_pool_loadbalanced_total ",
         "# HELP octavia_pool_loadbalanced_total Total number of times a "
         "pool was selected, either for new sessions, or when "
         "redispatching.\n", None),
    "haproxy_backend_loadbalanced_total{":
        ("octavia_pool_loadbalanced_total{", None, {"proxy=": "pool="}),
    "haproxy_backend_http_requests_total ":
        ("octavia_pool_http_requests_total ", None, None),
    "haproxy_backend_http_requests_total{":
        ("octavia_pool_http_requests_total{", None, {"proxy=": "pool="}),
    "haproxy_backend_http_responses_total ":
        ("octavia_pool_http_responses_total ", None, None),
    "haproxy_backend_http_responses_total{":
        ("octavia_pool_http_responses_total{", None, {"proxy=": "pool="}),
    "haproxy_backend_http_cache_lookups_total ":
        ("octavia_pool_http_cache_lookups_total ", None, None),
    "haproxy_backend_http_cache_lookups_total{":
        ("octavia_pool_http_cache_lookups_total{", None,
         {"proxy=": "pool="}),
    "haproxy_backend_http_cache_hits_total ":
        ("octavia_pool_http_cache_hits_total ", None, None),
    "haproxy_backend_http_cache_hits_total{":
        ("octavia_pool_http_cache_hits_total{", None, {"proxy=": "pool="}),
    "haproxy_backend_http_comp_bytes_in_total ":
        ("octavia_pool_http_comp_bytes_in_total ", None, None),
    "haproxy_backend_http_comp_bytes_in_total{":
        ("octavia_pool_http_comp_bytes_in_total{", None,
         {"proxy=": "pool="}),
    "haproxy_backend_http_comp_bytes_out_total ":
        ("octavia_pool_http_comp_bytes_out_total ", None, None),
    "haproxy_backend_http_comp_bytes_out_total{":
        ("octavia_pool_http_comp_bytes_out_total{", None,
         {"proxy=": "pool="}),
    "haproxy_backend_http_comp_bytes_bypassed_total ":
        ("octavia_pool_http_comp_bytes_bypassed_total ", None, None),
    "haproxy_backend_http_comp_bytes_bypassed_total{":
        ("octavia_pool_http_comp_bytes_bypassed_total{", None,
         {"proxy=": "pool="}),
    "haproxy_backend_http_comp_responses_total ":
        ("octavia_pool_http_comp_responses_total ", None, None),
    "haproxy_backend_http_comp_responses_total{":
        ("octavia_pool_http_comp_responses_total{", None,
         {"proxy=": "pool="}),

    # Member Metrics
    "haproxy_server_status ":
        ("octavia_member_status ",
         "# HELP octavia_member_status Current status of the member. "
         "0=ERROR, 1=ONLINE, 2=OFFLINE, 3=DRAIN.\n", None),
    "haproxy_server_status{":
        ("octavia_member_status{", None,
         {"proxy=": "pool=", "server=": "member="}),
    "haproxy_server_current_sessions ":
        ("octavia_member_current_sessions ", None, None),
    "haproxy_server_current_sessions{":
        ("octavia_member_current_sessions{", None,
         {"proxy=": "pool=", "server=": "member="}),
    "haproxy_server_max_sessions ":
        ("octavia_member_max_sessions ", None, None),
    "haproxy_server_max_sessions{":
        ("octavia_member_max_sessions{", None,
         {"proxy=": "pool=", "server=": "member="}),
    "haproxy_server_limit_sessions ":
        ("octavia_member_limit_sessions ", None, None),
    "haproxy_server_limit_sessions{":
        ("octavia_member_limit_sessions{", None,
         {"proxy=": "pool=", "server=": "member="}),
    "haproxy_server_sessions_total ":
        ("octavia_member_sessions_total ", None, None),
    "haproxy_server_sessions_total{":
        ("octavia_member_sessions_total{", None,
         {"proxy=": "pool=", "server=": "member="}),
    "haproxy_server_max_session_rate ":
        ("octavia_member_max_session_rate ", None, None),
    "haproxy_server_max_session_rate{":
        ("octavia_member_max_session_rate{", None,
         {"proxy=": "pool=", "server=": "member="}),
    "haproxy_server_last_session_seconds ":
        ("octavia_member_last_session_seconds ",
         "# HELP octavia_member_last_session_seconds Number of seconds since "
         "last session assigned to the member.\n", None),
    "haproxy_server_last_session_seconds{":
        ("octavia_member_last_session_seconds{", None,
         {"proxy=": "pool=", "server=": "member="}),
    "haproxy_server_current_queue ":
        ("octavia_member_current_queue ", None, None),
    "haproxy_server_current_queue{":
        ("octavia_member_current_queue{", None,
         {"proxy=": "pool=", "server=": "member="}),
    "haproxy_server_max_queue ":
        ("octavia_member_max_queue ", None, None),
    "haproxy_server_max_queue{":
        ("octavia_member_max_queue{", None,
         {"proxy=": "pool=", "server=": "member="}),
    "haproxy_server_queue_limit ":
        ("octavia_member_queue_limit ",
         "# HELP octavia_member_queue_limit Configured maxqueue for the "
         "member (0 meaning no limit).\n", None),
    "haproxy_server_queue_limit{":
        ("octavia_member_queue_limit{", None,
         {"proxy=": "pool=", "server=": "member="}),
    "haproxy_server_bytes_in_total ":
        ("octavia_member_bytes_in_total ", None, None),
    "haproxy_server_bytes_in_total{":
        ("octavia_member_bytes_in_total{", None,
         {"proxy=": "pool=", "server=": "member="}),
    "haproxy_server_bytes_out_total ":
        ("octavia_member_bytes_out_total ", None, None),
    "haproxy_server_bytes_out_total{":
        ("octavia_member_bytes_out_total{", None,
         {"proxy=": "pool=", "server=": "member="}),
    "haproxy_server_queue_time_average_seconds ":
        ("octavia_member_queue_time_average_seconds ", None, None),
    "haproxy_server_queue_time_average_seconds{":
        ("octavia_member_queue_time_average_seconds{", None,
         {"proxy=": "pool=", "server=": "member="}),
    "haproxy_server_connect_time_average_seconds ":
        ("octavia_member_connect_time_average_seconds ", None, None),
    "haproxy_server_connect_time_average_seconds{":
        ("octavia_member_connect_time_average_seconds{", None,
         {"proxy=": "pool=", "server=": "member="}),
    "haproxy_server_response_time_average_seconds ":
        ("octavia_member_response_time_average_seconds ", None, None),
    "haproxy_server_response_time_average_seconds{":
        ("octavia_member_response_time_average_seconds{", None,
         {"proxy=": "pool=", "server=": "member="}),
    "haproxy_server_total_time_average_seconds ":
        ("octavia_member_total_time_average_seconds ", None, None),
    "haproxy_server_total_time_average_seconds{":
        ("octavia_member_total_time_average_seconds{", None,
         {"proxy=": "pool=", "server=": "member="}),
    "haproxy_server_max_queue_time_seconds ":
        ("octavia_member_max_queue_time_seconds ", None, None),
    "haproxy_server_max_queue_time_seconds{":
        ("octavia_member_max_queue_time_seconds{", None,
         {"proxy=": "pool=", "server=": "member="}),
    "haproxy_server_max_connect_time_seconds ":
        ("octavia_member_max_connect_time_seconds ", None, None),
    "haproxy_server_max_connect_time_seconds{":
        ("octavia_member_max_connect_time_seconds{", None,
         {"proxy=": "pool=", "server=": "member="}),
    "haproxy_server_max_response_time_seconds ":
        ("octavia_member_max_response_time_seconds ",
         "# HELP octavia_member_max_response_time_seconds Maximum observed "
         "time spent waiting for a member response.\n", None),
    "haproxy_server_max_response_time_seconds{":
        ("octavia_member_max_response_time_seconds{", None,
         {"proxy=": "pool=", "server=": "member="}),
    "haproxy_server_max_total_time_seconds ":
        ("octavia_member_max_total_time_seconds ", None, None),
    "haproxy_server_max_total_time_seconds{":
        ("octavia_member_max_total_time_seconds{", None,
         {"proxy=": "pool=", "server=": "member="}),
    "haproxy_server_connection_attempts_total ":
        ("octavia_member_connection_attempts_total ", None, None),
    "haproxy_server_connection_attempts_total{":
        ("octavia_member_connection_attempts_total{", None,
         {"proxy=": "pool=", "server=": "member="}),
    "haproxy_server_connection_reuses_total ":
        ("octavia_member_connection_reuses_total ", None, None),
    "haproxy_server_connection_reuses_total{":
        ("octavia_member_connection_reuses_total{", None,
         {"proxy=": "pool=", "server=": "member="}),
    "haproxy_server_responses_denied_total ":
        ("octavia_member_responses_denied_total ", None, None),
    "haproxy_server_responses_denied_total{":
        ("octavia_member_responses_denied_total{", None,
         {"proxy=": "pool=", "server=": "member="}),
    "haproxy_server_connection_errors_total ":
        ("octavia_member_connection_errors_total ", None, None),
    "haproxy_server_connection_errors_total{":
        ("octavia_member_connection_errors_total{", None,
         {"proxy=": "pool=", "server=": "member="}),
    "haproxy_server_response_errors_total ":
        ("octavia_member_response_errors_total ", None, None),
    "haproxy_server_response_errors_total{":
        ("octavia_member_response_errors_total{", None,
         {"proxy=": "pool=", "server=": "member="}),
    "haproxy_server_retry_warnings_total ":
        ("octavia_member_retry_warnings_total ", None, None),
    "haproxy_server_retry_warnings_total{":
        ("octavia_member_retry_warnings_total{", None,
         {"proxy=": "pool=", "server=": "member="}),
    "haproxy_server_redispatch_warnings_total ":
        ("octavia_member_redispatch_warnings_total ", None, None),
    "haproxy_server_redispatch_warnings_total{":
        ("octavia_member_redispatch_warnings_total{", None,
         {"proxy=": "pool=", "server=": "member="}),
    "haproxy_server_failed_header_rewriting_total ":
        ("octavia_member_failed_header_rewriting_total ", None, None),
    "haproxy_server_failed_header_rewriting_total{":
        ("octavia_member_failed_header_rewriting_total{", None,
         {"proxy=": "pool=", "server=": "member="}),
    "haproxy_server_client_aborts_total ":
        ("octavia_member_client_aborts_total ", None, None),
    "haproxy_server_client_aborts_total{":
        ("octavia_member_client_aborts_total{", None,
         {"proxy=": "pool=", "server=": "member="}),
    "haproxy_server_server_aborts_total ":
        ("octavia_member_server_aborts_total ", None, None),
    "haproxy_server_server_aborts_total{":
        ("octavia_member_server_aborts_total{", None,
         {"proxy=": "pool=", "server=": "member="}),
    "haproxy_server_weight ":
        ("octavia_member_weight ",
         "# HELP octavia_member_weight Member weight.\n", None),
    "haproxy_server_weight{":
        ("octavia_member_weight{", None,
         {"proxy=": "pool=", "server=": "member="}),
    "haproxy_server_check_failures_total ":
        ("octavia_member_check_failures_total ",
         "# HELP octavia_member_check_failures_total Total number of failed "
         "check (Only counts checks failed when the member is up).\n", None),
    "haproxy_server_check_failures_total{":
        ("octavia_member_check_failures_total{", None,
         {"proxy=": "pool=", "server=": "member="}),
    "haproxy_server_check_up_down_total ":
        ("octavia_member_check_up_down_total ", None, None),
    "haproxy_server_check_up_down_total{":
        ("octavia_member_check_up_down_total{", None,
         {"proxy=": "pool=", "server=": "member="}),
    "haproxy_server_downtime_seconds_total ":
        ("octavia_member_downtime_seconds_total ",
         "# HELP octavia_member_downtime_seconds_total Total downtime (in "
         "seconds) for the member.\n", None),
    "haproxy_server_downtime_seconds_total{":
        ("octavia_member_downtime_seconds_total{", None,
         {"proxy=": "pool=", "server=": "member="}),
    "haproxy_server_check_last_change_seconds ":
        ("octavia_member_check_last_change_seconds ", None, None),
    "haproxy_server_check_last_change_seconds{":
        ("octavia_member_check_last_change_seconds{", None,
         {"proxy=": "pool=", "server=": "member="}),
    "haproxy_server_current_throttle ":
        ("octavia_member_current_throttle ",
         "# HELP octavia_member_current_throttle Current throttle percentage "
         "for the member, when slowstart is active, or no value if not in "
         "slowstart.\n", None),
    "haproxy_server_current_throttle{":
        ("octavia_member_current_throttle{", None,
         {"proxy=": "pool=", "server=": "member="}),
    "haproxy_server_loadbalanced_total ":
        ("octavia_member_loadbalanced_total ",
         "# HELP octavia_member_loadbalanced_total Total number of times a "
         "member was selected, either for new sessions, or when "
         "redispatching.\n", None),
    "haproxy_server_loadbalanced_total{":
        ("octavia_member_loadbalanced_total{", None,
         {"proxy=": "pool=", "server=": "member="}),
    "haproxy_server_http_responses_total ":
        ("octavia_member_http_responses_total ", None, None),
    "haproxy_server_http_responses_total{":
        ("octavia_member_http_responses_total{", None,
         {"proxy=": "pool=", "server=": "member="}),
    "haproxy_server_server_idle_connections_current ":
        ("octavia_member_idle_connections_current ", None, None),
    "haproxy_server_server_idle_connections_current{":
        ("octavia_member_idle_connections_current{", None,
         {"proxy=": "pool=", "server=": "member="}),
    "haproxy_server_server_idle_connections_limit ":
        ("octavia_member_idle_connections_limit ", None, None),
    "haproxy_server_server_idle_connections_limit{":
        ("octavia_member_idle_connections_limit{", None,
         {"proxy=": "pool=", "server=": "member="}),
}
METRIC_KEYS = METRIC_MAP.keys()


class PrometheusProxy(SimpleHTTPRequestHandler):

    protocol_version = 'HTTP/1.1'

    # No need to log every request through the proxy
    def log_request(self, *args, **kwargs):
        pass

    def _add_cpu_utilization(self, metrics_buffer):
        cpu_pcnt = (psutil.getloadavg()[0] / os.cpu_count()) * 100
        metrics_buffer += ("# HELP octavia_loadbalancer_cpu Load balancer "
                           "CPU utilization (percentage).\n")
        metrics_buffer += "# TYPE octavia_loadbalancer_cpu gauge\n"
        cpu_metric_string = f"octavia_loadbalancer_cpu {cpu_pcnt:.1f}\n"
        metrics_buffer += cpu_metric_string
        return metrics_buffer

    def _add_memory_utilization(self, metrics_buffer):
        mem_pcnt = psutil.virtual_memory()[2]
        metrics_buffer += ("# HELP octavia_loadbalancer_memory Load balancer "
                           "memory utilization (percentage).\n")
        metrics_buffer += "# TYPE octavia_loadbalancer_memory gauge\n"
        mem_metric_string = f"octavia_loadbalancer_memory {mem_pcnt:.1f}\n"
        metrics_buffer += mem_metric_string
        return metrics_buffer

    def do_GET(self):
        metrics_buffer = ""

        metrics_buffer = self._add_cpu_utilization(metrics_buffer)
        metrics_buffer = self._add_memory_utilization(metrics_buffer)

        try:
            with urllib.request.urlopen(METRICS_URL) as source:  # nosec
                lines = source.readlines()
                for line in lines:
                    line = line.decode("utf-8")
                    # Don't report metrics for the internal prometheus
                    # proxy loop. The user facing listener will still be
                    # reported.
                    if "prometheus-exporter" in line:
                        continue
                    match = next((x for x in METRIC_KEYS if x in line), False)
                    if match:
                        map_tuple = METRIC_MAP[match]
                        if map_tuple[1] and "HELP" in line:
                            metrics_buffer += map_tuple[1]
                        else:
                            if map_tuple[2] and not line.startswith("#"):
                                for key in map_tuple[2].keys():
                                    line = line.replace(key,
                                                        map_tuple[2][key])
                            metrics_buffer += line.replace(match,
                                                           map_tuple[0])
                    elif PRINT_REJECTED:
                        print("REJECTED: %s" % line)
        except Exception as e:
            print(str(e), flush=True)
            traceback.print_tb(e.__traceback__)
            self.send_response(502)
            self.send_header("connection", "close")
            self.end_headers()
            return

        self.send_response(200)
        self.send_header("cache-control", "no-cache")
        self.send_header("content-type", "text/plain; version=0.0.4")
        self.send_header("connection", "close")
        self.end_headers()
        self.wfile.write(metrics_buffer.encode("utf-8"))


class SignalHandler:

    def __init__(self):
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)

    def shutdown(self, *args):
        EXIT_EVENT.set()


def shutdown_thread(http):
    EXIT_EVENT.wait()
    http.shutdown()


# TODO(johnsom) Remove and switch to ThreadingHTTPServer once python3.7 is
# the minimum version supported.
class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    daemon_threads = True


def main():
    global PRINT_REJECTED
    try:
        if sys.argv[1] == "--rejected":
            PRINT_REJECTED = True
    except Exception:
        pass

    SignalHandler()

    while not EXIT_EVENT.is_set():
        # The amphora-haproxy network namespace may not be present, so handle
        # it gracefully.
        try:
            with network_namespace.NetworkNamespace(consts.AMPHORA_NAMESPACE):
                httpd = ThreadedHTTPServer(('127.0.0.1', 9102),
                                           PrometheusProxy)
                shutdownthread = threading.Thread(target=shutdown_thread,
                                                  args=(httpd,))
                shutdownthread.start()

                # TODO(johnsom) Uncomment this when we move to
                #               ThreadingHTTPServer
                # httpd.daemon_threads = True
                print("Now serving on port 9102")
                httpd.serve_forever()
        except Exception:
            time.sleep(1)


if __name__ == "__main__":
    main()
