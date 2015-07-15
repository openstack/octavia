# Copyright 2014 Hewlett-Packard Development Company, L.P.
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

import binascii
import hashlib
import hmac
import json
import zlib

from oslo_log import log as logging

from octavia.common import exceptions
from octavia.i18n import _LW

LOG = logging.getLogger(__name__)

hash_algo = hashlib.sha256
hash_len = 32


def to_hex(byte_array):
    return binascii.hexlify(byte_array).decode()


def encode_obj(obj):
    json_bytes = json.dumps(obj).encode('utf-8')
    binary_array = zlib.compress(json_bytes, 9)
    return binary_array


def decode_obj(binary_array):
    json_str = zlib.decompress(binary_array).decode('utf-8')
    obj = json.loads(json_str)
    return obj


def wrap_envelope(obj, key):
    payload = encode_obj(obj)
    hmc = get_hmac(payload, key)
    envelope = payload + hmc
    return envelope


def unwrap_envelope(envelope, key):
    payload = envelope[:-hash_len]
    expected_hmc = envelope[-hash_len:]
    calculated_hmc = get_hmac(payload, key)
    if expected_hmc != calculated_hmc:
        LOG.warn(_LW('calculated hmac: %(s1)s not equal to msg hmac: '
                     '%(s2)s dropping packet'), {'s1': to_hex(calculated_hmc),
                                                 's2': to_hex(expected_hmc)})
        fmt = 'calculated hmac: {0} not equal to msg hmac: {1} dropping packet'
        raise exceptions.InvalidHMACException(fmt.format(
            to_hex(calculated_hmc), to_hex(expected_hmc)))
    obj = decode_obj(payload)
    return obj


def get_hmac(payload, key):
    hmc = hmac.new(key.encode("utf-8"), payload, hashlib.sha256)
    return hmc.digest()
