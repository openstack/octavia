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
"""add cert expiration infor in amphora table

Revision ID: 5a3ee5472c31
Revises: 3b199c848b96
Create Date: 2015-08-20 10:15:19.561066

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '5a3ee5472c31'
down_revision = '3b199c848b96'


def upgrade():
    op.add_column(u'amphora',
                  sa.Column(u'cert_expiration', sa.DateTime(timezone=True),
                            nullable=True)
                  )

    op.add_column(u'amphora', sa.Column(u'cert_busy', sa.Boolean(),
                                        nullable=False, default=False))
