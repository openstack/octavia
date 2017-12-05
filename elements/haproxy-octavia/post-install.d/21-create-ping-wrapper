#!/bin/bash
# Copyright 2017 Rackspace, US Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
#
# See the License for the specific language governing permissions and
# limitations under the License.

set -eu
set -o pipefail

ping_cmd=$(command -v ping)
ping6_cmd=$(command -v ping6)

cat > /var/lib/octavia/ping-wrapper.sh <<EOF
#!/bin/bash
if [[ \$HAPROXY_SERVER_ADDR =~ ":" ]]; then
    $ping6_cmd -q -n -w 1 -c 1 \$HAPROXY_SERVER_ADDR > /dev/null 2>&1
else
    $ping_cmd -q -n -w 1 -c 1 \$HAPROXY_SERVER_ADDR > /dev/null 2>&1
fi
EOF

chmod 755 /var/lib/octavia/ping-wrapper.sh
