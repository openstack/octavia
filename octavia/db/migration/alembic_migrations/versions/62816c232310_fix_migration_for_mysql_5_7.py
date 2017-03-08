# Copyright 2016 IBM
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Fix migration for MySQL 5.7

Revision ID: 62816c232310
Revises: 36b94648fef8
Create Date: 2016-06-07 12:59:21.059619

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '62816c232310'
down_revision = '36b94648fef8'


def upgrade():
    op.alter_column(u'sni', u'tls_container_id', type_=sa.String(128),
                    existing_type=sa.String(36), nullable=False)
