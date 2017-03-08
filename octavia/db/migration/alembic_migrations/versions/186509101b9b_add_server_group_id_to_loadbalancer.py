# Copyright 2016 Hewlett-Packard Development Company, L.P.
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
#

"""add_server_group_id_to_loadbalancer

Revision ID: 186509101b9b
Revises: 29ff921a6eb
Create Date: 2016-01-25 15:12:52.489652

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '186509101b9b'
down_revision = '458c9ee2a011'


def upgrade():
    op.add_column(u'load_balancer', sa.Column(u'server_group_id',
                                              sa.String(36), nullable=True))
