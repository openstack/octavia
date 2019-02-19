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
import zlib

from oslo_log import log as logging
from oslo_serialization import jsonutils
from oslo_utils import secretutils

from octavia.common import exceptions

LOG = logging.getLogger(__name__)

hash_algo = hashlib.sha256
hash_len = 32
hex_hash_len = 64


def to_hex(byte_array):
    return binascii.hexlify(byte_array).decode()


def encode_obj(obj):
    json_bytes = jsonutils.dumps(obj).encode('utf-8')
    binary_array = zlib.compress(json_bytes, 9)
    return binary_array


def decode_obj(binary_array):
    json_str = zlib.decompress(binary_array).decode('utf-8')
    obj = jsonutils.loads(json_str)
    return obj


def wrap_envelope(obj, key, hex=True):
    payload = encode_obj(obj)
    hmc = get_hmac(payload, key, hex=hex)
    envelope = payload + hmc
    return envelope


def unwrap_envelope(envelope, key):
    """A backward-compatible way to get data.

    We may still receive package from amphorae that are using digest() instead
    of hexdigest()
    """
    try:
        return get_payload(envelope, key, hex=True)
    except Exception:
        return get_payload(envelope, key, hex=False)


def get_payload(envelope, key, hex=True):
    len = hex_hash_len if hex else hash_len
    payload = envelope[:-len]
    expected_hmc = envelope[-len:]
    calculated_hmc = get_hmac(payload, key, hex=hex)
    if not secretutils.constant_time_compare(expected_hmc, calculated_hmc):
        LOG.warning(
            'calculated hmac(hex=%(hex)s): %(s1)s not equal to msg hmac: '
            '%(s2)s dropping packet',
            {
                'hex': hex,
                's1': to_hex(calculated_hmc),
                's2': to_hex(expected_hmc)
            }
        )
        fmt = 'calculated hmac: {0} not equal to msg hmac: {1} dropping packet'
        raise exceptions.InvalidHMACException(fmt.format(
            to_hex(calculated_hmc), to_hex(expected_hmc)))
    obj = decode_obj(payload)
    return obj


def get_hmac(payload, key, hex=True):
    """Get digest for the payload.

    The hex param is for backward compatibility, so the package data sent from
    the existing amphorae can still be checked in the previous approach.
    """
    hmc = hmac.new(key.encode("utf-8"), payload, hashlib.sha256)
    return hmc.hexdigest().encode("utf-8") if hex else hmc.digest()
