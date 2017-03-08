#    Copyright 2016 Rackspace
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

"""Update vip address size

Revision ID: 82b9402e71fd
Revises: 62816c232310
Create Date: 2016-07-17 14:36:36.698870

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '82b9402e71fd'
down_revision = '4a6ec0ab7284'


def upgrade():
    op.alter_column(u'vip', u'ip_address',
                    existing_type=sa.String(64))
