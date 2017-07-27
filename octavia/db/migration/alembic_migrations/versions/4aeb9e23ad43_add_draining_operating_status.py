# Copyright 2017 GoDaddy
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
"""Add DRAINING operating status

Revision ID: 4aeb9e23ad43
Revises: e6672bda93bf
Create Date: 2017-07-27 00:54:07.128617

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '4aeb9e23ad43'
down_revision = 'e6672bda93bf'


def upgrade():
    bind = op.get_bind()
    md = sa.MetaData()
    sa.Table('operating_status', md, autoload=True, autoload_with=bind)
    op.bulk_insert(md.tables['operating_status'], [{'name': 'DRAINING'}])
