# Copyright 2020 Red Hat, Inc. All rights reserved.
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

"""add listener alpn protocols column

Revision ID: 2ab994dd3ec2
Revises: 32e5c35b26a8
Create Date: 2020-08-02 21:51:21.261087

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2ab994dd3ec2'
down_revision = '32e5c35b26a8'


def upgrade():
    op.add_column(
        'listener',
        sa.Column('alpn_protocols', sa.String(512), nullable=True)
    )
