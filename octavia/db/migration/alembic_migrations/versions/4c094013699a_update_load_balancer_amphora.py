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

'''update load balancer amphora relationship

Revision ID: 4c094013699a
Revises: 35dee79d5865
Create Date: 2014-09-15 14:42:44.875448

'''

# revision identifiers, used by Alembic.
revision = '4c094013699a'
down_revision = '35dee79d5865'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column(
        u'amphora',
        sa.Column(u'load_balancer_id', sa.String(36),
                  sa.ForeignKey(u'load_balancer.id',
                                name=u'fk_amphora_load_balancer_id'),
                  nullable=True)
    )
    op.drop_table(u'load_balancer_amphora')
    op.drop_constraint(
        u'fk_container_provisioning_status_name', u'amphora',
        type_=u'foreignkey'
    )
    op.create_foreign_key(
        u'fk_amphora_provisioning_status_name', u'amphora',
        u'provisioning_status', [u'status'], [u'name']
    )


def downgrade():
    op.drop_constraint(
        u'fk_amphora_load_balancer_id', u'amphora', type_=u'foreignkey'
    )
    op.drop_column(
        u'amphora', u'load_balancer_id'
    )
    op.create_table(
        u'load_balancer_amphora',
        sa.Column(u'amphora_id', sa.String(36), nullable=False),
        sa.Column(u'load_balancer_id', sa.String(36), nullable=False),
        sa.ForeignKeyConstraint(
            [u'load_balancer_id'], [u'load_balancer.id'],
            name=u'fk_load_balancer_amphora_load_balancer_id'),
        sa.ForeignKeyConstraint([u'amphora_id'],
                                [u'amphora.id'],
                                name=u'fk_load_balancer_amphora_id'),
        sa.PrimaryKeyConstraint(u'amphora_id', u'load_balancer_id')
    )
    op.drop_constraint(
        u'fk_amphora_provisioning_status_name', u'amphora',
        type_=u'foreignkey'
    )
    op.create_foreign_key(
        u'fk_container_provisioning_status_name', u'amphora',
        u'provisioning_status', [u'status'], [u'name']
    )
