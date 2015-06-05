# Copyright 2015 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import socket

from octavia.common import constants as consts


class HAProxyQuery(object):
    """Class used for querying the HAProxy statistics socket.

    The CSV output is defined in the HAProxy documentation:

    http://cbonte.github.io/haproxy-dconv/configuration-1.4.html#9
    """

    def __init__(self, stats_socket):
        """stats_socket

            Path to the HAProxy statistics socket file.
        """

        self.socket = stats_socket

    def _query(self, query):
        """Send the given query to the haproxy statistics socket.

        :returns the output of a successful query as a string with trailing
        newlines removed, or raise an Exception if the query fails.
        """

        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

        try:
            sock.connect(self.socket)
        except socket.error:
            raise Exception("HAProxy '{0}' query failed.".format(query))

        try:
            sock.send(query + '\n')
            data = ''
            while True:
                x = sock.recv(1024)
                if not x:
                    break
                data += x
            return data.rstrip()
        finally:
            sock.close()

    def show_info(self):
        """Get and parse output from 'show info' command."""
        results = self._query('show info')
        list_results = results.split('\n')
        return list_results

    def show_stat(self, proxy_iid=-1, object_type=-1, server_id=-1):
        """Get and parse output from 'show status' command.

        :param proxy_iid
          Proxy ID (column 27 in CSV output). -1 for all.

        :param object_type
          Select the type of dumpable object. Values can be ORed.
             -1 - everything
              1 - frontends
              2 - backends
              4 - servers

        :param server_id
          Server ID (column 28 in CSV output?), or -1 for everything.

        :return stats (split into an array by \n)
        """

        results = self._query(
            'show stat {proxy_iid} {object_type}'
            + '{server_id}'.format(
                proxy_iid=proxy_iid,
                object_type=object_type,
                server_id=server_id))
        list_results = results.split('\n')
        return list_results

    def get_pool_status(self):
        """Get status for each server and the pool as a whole.

        :returns pool data structure
        {<pool-name>: {
          'uuid': <uuid>,
          'status': 'UP'|'DOWN',
          'members': [
            <name>: 'UP'|'DOWN'
          ]
        """

        results = self.show_stat(object_type=6)  # servers + pool

        final_results = {}
        for line in results[1:]:
            elements = line.split(',')
            # 0-pool  1 - server name, 17 - status

            # All the way up is UP, otherwise call it DOWN
            if elements[17] != consts.AMPHORA_UP:
                elements[17] = consts.AMPHORA_DOWN

            if elements[0] not in final_results:
                final_results[elements[0]] = dict(members=[])

            if elements[1] == 'BACKEND':
                final_results[elements[0]]['uuid'] = elements[0]
                final_results[elements[0]]['status'] = elements[17]
            else:
                final_results[elements[0]]['members'].append(
                    {elements[1]: elements[17]})
        return final_results
