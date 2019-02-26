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

"""Add certificate revoke revocation list field

Revision ID: ffad172e98c1
Revises: f21ae3f21adc
Create Date: 2018-10-01 20:47:52.405865

"""


from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'ffad172e98c1'
down_revision = 'f21ae3f21adc'


def upgrade():
    op.add_column(u'listener',
                  sa.Column(u'client_crl_container_id', sa.String(255),
                            nullable=True))
