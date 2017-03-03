
..
      Copyright 2017 Intel Corporation
      All Rights Reserved.

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

=========================
Running Octavia in Apache
=========================

To run Octavia in apache2, copy the ``httpd/octavia-api.conf`` sample
configuration file to the appropriate location for the Apache server.

On Debian/Ubuntu systems it is::

    /etc/apache2/sites-available/octavia-api.conf

Restart Apache to have it start serving Octavia.
