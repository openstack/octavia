# Copyright (c) 2013 The Johns Hopkins University/Applied Physics Laboratory
# All Rights Reserved.
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

from oslo_config import cfg
from oslo_utils import importutils

certgen_opts = [
    cfg.StrOpt('cert_generator_class',
               default='octavia.certificates.generator.LocalCertGenerator',
               help='The full class name of the cert generator API class'),
]

CONF = cfg.CONF
CONF.register_opts(certgen_opts, group='certificates')


def API():
    cls = importutils.import_class(CONF.certgen.cert_generator_class)
    return cls()
