#    Copyright 2016 VMware
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

"""Insert headers

Revision ID: 4d9cf7d32f2
Revises: 9bf4d21caaea
Create Date: 2016-02-21 17:16:22.316744

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '4d9cf7d32f2'
down_revision = '9bf4d21caaea'


def upgrade():
    op.add_column('listener', sa.Column('insert_headers', sa.PickleType()))
