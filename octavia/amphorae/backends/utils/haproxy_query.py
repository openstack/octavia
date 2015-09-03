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

import csv
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

        dict_results = dict()
        for r in results.split('\n'):
            vals = r.split(":", 1)
            dict_results[vals[0].strip()] = vals[1].strip()
        return dict_results

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
            'show stat {proxy_iid} {object_type} {server_id}'.format(
                proxy_iid=proxy_iid,
                object_type=object_type,
                server_id=server_id))
        list_results = results[2:].split('\n')
        csv_reader = csv.DictReader(list_results)
        return [row for row in csv_reader]

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
        for line in results:
            # pxname: pool, svname: server_name, status: status

            # All the way up is UP, otherwise call it DOWN
            if (line['status'] != consts.UP and
                    line['status'] != consts.NO_CHECK):
                line['status'] = consts.DOWN

            if line['pxname'] not in final_results:
                final_results[line['pxname']] = dict(members={})

            if line['svname'] == 'BACKEND':
                final_results[line['pxname']]['uuid'] = line['pxname']
                final_results[line['pxname']]['status'] = line['status']
            else:
                final_results[line['pxname']]['members'][line['svname']] = (
                    line['status'])
        return final_results
