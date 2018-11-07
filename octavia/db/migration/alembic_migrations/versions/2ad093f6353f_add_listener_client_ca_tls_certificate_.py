# Copyright 2018 Huawei
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

"""Add listener client_ca_tls_certificate_id column

Revision ID: 2ad093f6353f
Revises: 11e4bb2bb8ef
Create Date: 2019-02-13 08:32:43.009997

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2ad093f6353f'
down_revision = '11e4bb2bb8ef'


def upgrade():
    op.add_column(
        u'listener',
        sa.Column(u'client_ca_tls_certificate_id', sa.String(255),
                  nullable=True)
    )
