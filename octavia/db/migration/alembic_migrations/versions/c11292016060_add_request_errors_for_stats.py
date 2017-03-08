# Copyright 2016 IBM
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

"""adding request error number to listener_statistics table

Revision ID: c11292016060
Revises: 9b5473976d6d
Create Date: 2016-08-12 03:37:38.656962

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c11292016060'
down_revision = '9b5473976d6d'


def upgrade():
    op.add_column('listener_statistics',
                  sa.Column('request_errors', sa.BigInteger(),
                            nullable=False, default=0))
