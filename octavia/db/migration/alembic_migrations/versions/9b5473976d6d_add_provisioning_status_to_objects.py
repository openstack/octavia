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

"""Add provisioning_status to objects

Revision ID: 9b5473976d6d
Revises: 82b9402e71fd
Create Date: 2016-09-20 21:46:26.843695

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '9b5473976d6d'
down_revision = '82b9402e71fd'


def upgrade():

    op.add_column('health_monitor',
                  sa.Column('provisioning_status',
                            sa.String(16),
                            nullable=True)
                  )
    op.create_foreign_key(
        u'fk_health_monitor_provisioning_status_name', u'health_monitor',
        u'provisioning_status', [u'provisioning_status'], [u'name']
    )

    op.add_column('l7policy',
                  sa.Column('provisioning_status',
                            sa.String(16),
                            nullable=True)
                  )
    op.create_foreign_key(
        u'fk_l7policy_provisioning_status_name', u'l7policy',
        u'provisioning_status', [u'provisioning_status'], [u'name']
    )

    op.add_column('l7rule',
                  sa.Column('provisioning_status',
                            sa.String(16),
                            nullable=True)
                  )
    op.create_foreign_key(
        u'fk_l7rule_provisioning_status_name', u'l7rule',
        u'provisioning_status', [u'provisioning_status'], [u'name']
    )

    op.add_column('member',
                  sa.Column('provisioning_status',
                            sa.String(16),
                            nullable=True)
                  )
    op.create_foreign_key(
        u'fk_member_provisioning_status_name', u'member',
        u'provisioning_status', [u'provisioning_status'], [u'name']
    )

    op.add_column('pool',
                  sa.Column('provisioning_status',
                            sa.String(16),
                            nullable=True)
                  )
    op.create_foreign_key(
        u'fk_pool_provisioning_status_name', u'pool',
        u'provisioning_status', [u'provisioning_status'], [u'name']
    )
