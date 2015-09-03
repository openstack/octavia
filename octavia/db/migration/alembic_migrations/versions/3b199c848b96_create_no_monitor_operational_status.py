# Copyright 2015 Hewlett-Packard Development Company, L.P.
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
"""Create NO_MONITOR operational_status

Revision ID: 3b199c848b96
Revises: 543f5d8e4e56
Create Date: 2015-09-03 17:11:03.724070

"""

# revision identifiers, used by Alembic.
revision = '3b199c848b96'
down_revision = '543f5d8e4e56'

from alembic import op
import sqlalchemy as sa


def upgrade():
    bind = op.get_bind()
    md = sa.MetaData()
    sa.Table('operating_status', md, autoload=True, autoload_with=bind)
    op.bulk_insert(md.tables['operating_status'], [{'name': 'NO_MONITOR'}])
