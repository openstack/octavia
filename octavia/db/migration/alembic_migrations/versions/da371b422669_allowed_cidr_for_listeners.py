#    Copyright 2018 Red Hat, Inc.
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
"""Add CIDRs for listeners

Revision ID: da371b422669
Revises: a5762a99609a
Create Date: 2018-11-22 12:31:39.864238

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'da371b422669'
down_revision = 'a5762a99609a'


def upgrade():
    op.create_table(
        u'listener_cidr',
        sa.Column(u'listener_id', sa.String(36), nullable=False),
        sa.Column(u'cidr', sa.String(64), nullable=False),

        sa.ForeignKeyConstraint([u'listener_id'],
                                [u'listener.id'],
                                name=u'fk_listener_cidr_listener_id'),
        sa.PrimaryKeyConstraint(u'listener_id', u'cidr')
    )
