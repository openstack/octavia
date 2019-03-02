# Copyright 2019 Rackspace US Inc.  All rights reserved.
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

"""extend pool for backend CA and CRL

Revision ID: 74aae261694c
Revises: a1f689aecc1d
Create Date: 2019-02-27 09:22:24.779576

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '74aae261694c'
down_revision = 'a1f689aecc1d'


def upgrade():
    op.add_column(u'pool', sa.Column(u'ca_tls_certificate_id', sa.String(255),
                                     nullable=True))
    op.add_column(u'pool', sa.Column(u'crl_container_id', sa.String(255),
                                     nullable=True))
