#!/usr/bin/python
#
# Copyright 2016 IBM. All rights reserved
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
#
# Converts a PKCS7 certificate bundle in DER or PEM format into
# a sequence of PEM-encoded certificates.

import base64
import sys

from cryptography.hazmat import backends
from cryptography.hazmat.primitives import serialization
from cryptography import x509
from pyasn1.codec.der import decoder as der_decoder
from pyasn1.codec.der import encoder as der_encoder
from pyasn1_modules import rfc2315
import six


PKCS7_BEG = """-----BEGIN PKCS7-----"""
PKCS7_END = """-----END PKCS7-----"""


# Based on pyasn1-modules.pem.readPemBlocksFromFile, but eliminates the need
# to operate on a file handle.
def _read_pem_blocks(data, *markers):
    stSpam, stHam, stDump = 0, 1, 2

    startMarkers = dict(map(lambda x: (x[1], x[0]),
                            enumerate(map(lambda x: x[0], markers))))
    stopMarkers = dict(map(lambda x: (x[1], x[0]),
                           enumerate(map(lambda x: x[1], markers))))
    idx = -1
    state = stSpam
    if six.PY3:
        data = str(data, encoding="UTF-8")
    for certLine in data.replace('\r', '').split('\n'):
        if not certLine:
            break
        certLine = certLine.strip()
        if state == stSpam:
            if certLine in startMarkers:
                certLines = []
                idx = startMarkers[certLine]
                state = stHam
                continue
        if state == stHam:
            if certLine in stopMarkers and stopMarkers[certLine] == idx:
                state = stDump
            else:
                certLines.append(certLine)
        if state == stDump:
            if six.PY2:
                yield ''.join([
                    base64.b64decode(x) for x in certLines])
            elif six.PY3:
                yield ''.encode().join([
                    base64.b64decode(x) for x in certLines])
            state = stSpam


def _process_pkcs7_substrate(substrate):
    contentInfo, _ = der_decoder.decode(substrate,
                                        asn1Spec=rfc2315.ContentInfo())

    contentType = contentInfo.getComponentByName('contentType')

    if contentType != rfc2315.signedData:
        raise Exception

    content, _ = der_decoder.decode(
        contentInfo.getComponentByName('content'),
        asn1Spec=rfc2315.SignedData())

    for blob in content.getComponentByName('certificates'):
        cert = x509.load_der_x509_certificate(der_encoder.encode(blob),
                                              backends.default_backend())
        six.print_(cert.public_bytes(
            encoding=serialization.Encoding.PEM).decode(
            'unicode_escape'), end='')


# Main program code
if len(sys.argv) != 1:
    six.print_('Usage: cat <pkcs7_bundle.p7b> | %s' % sys.argv[0])
    sys.exit(-1)

# Need to read in binary bytes in case DER encoding of PKCS7 bundle
if six.PY2:
    data = sys.stdin.read()
elif six.PY3:
    data = sys.stdin.buffer.read()

# Look for PEM encoding
if PKCS7_BEG in str(data):
    for substrate in _read_pem_blocks(data, (PKCS7_BEG, PKCS7_END)):
        _process_pkcs7_substrate(substrate)

# If no PEM encoding, assume this is DER encoded and try to decode
else:
    _process_pkcs7_substrate(data)
