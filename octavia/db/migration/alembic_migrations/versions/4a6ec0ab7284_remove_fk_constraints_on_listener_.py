#    Copyright 2014 Rackspace
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

"""Remove FK constraints on listener_statistics because it will be cross-DB

Revision ID: 4a6ec0ab7284
Revises: 62816c232310
Create Date: 2016-07-05 14:09:16.320931

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '4a6ec0ab7284'
down_revision = '62816c232310'


def upgrade():
    # OpenStack has decided that "down" migrations are not supported.
    # The downgrade() method has been omitted for this reason.
    op.drop_constraint('fk_listener_statistics_listener_id',
                       'listener_statistics',
                       type_='foreignkey')
    op.drop_constraint('fk_listener_statistic_amphora_id',
                       'listener_statistics',
                       type_='foreignkey')
