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

"""update vip

Revision ID: 14892634e228
Revises: 3a1e1cdb7b27
Create Date: 2015-01-10 00:53:57.798213

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '14892634e228'
down_revision = '3a1e1cdb7b27'


def upgrade():
    with op.batch_alter_table(u'vip') as batch_op:
        batch_op.alter_column(u'subnet_id', new_column_name=u'network_id',
                              existing_type=sa.String(36))
        batch_op.alter_column(u'net_port_id', new_column_name=u'port_id',
                              existing_type=sa.String(36))
        batch_op.drop_column(u'floating_ip_id')
        batch_op.drop_column(u'floating_ip_network_id')
