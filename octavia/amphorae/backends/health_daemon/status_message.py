#    Copyright 2014 Hewlett-Packard Development Company, L.P.
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

import hashlib
import hmac
import json


def encode(msg, key):
    result = {}
    src = json.dumps(msg)
    hmc = hmac.new(key.encode('ascii'), src.encode('ascii'), hashlib.sha1)
    result['msg'] = msg
    result['hmac'] = hmc.hexdigest()
    return json.dumps(result)


def checkhmac(envelope_str, key):
    envelope = json.loads(envelope_str)
    src = json.dumps(envelope['msg'])
    hmc = hmac.new(key.encode('ascii'), src.encode('ascii'), hashlib.sha1)
    return hmc.hexdigest() == envelope['hmac']
