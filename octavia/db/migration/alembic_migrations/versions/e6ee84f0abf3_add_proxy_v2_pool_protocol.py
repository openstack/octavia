# Copyright 2020 Red Hat, Inc. All rights reserved.
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
"""Add PROXY v2 pool protocol

Revision ID: e6ee84f0abf3
Revises: 2ab994dd3ec2
Create Date: 2020-08-24 11:12:46.745185

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import sql


# revision identifiers, used by Alembic.
revision = 'e6ee84f0abf3'
down_revision = '2ab994dd3ec2'


def upgrade():
    insert_table = sql.table(
        u'protocol',
        sql.column(u'name', sa.String),
        sql.column(u'description', sa.String)
    )

    op.bulk_insert(
        insert_table,
        [
            {'name': 'PROXYV2'}
        ]
    )
