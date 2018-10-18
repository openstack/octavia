# Copyright 2018 Huawei
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
#

"""Extend the l7rule type for support client certificate cases

Revision ID: 1afc932f1ca2
Revises: ffad172e98c1
Create Date: 2018-10-03 20:47:52.405865

"""


from alembic import op
import sqlalchemy as sa
from sqlalchemy import sql

# revision identifiers, used by Alembic.
revision = '1afc932f1ca2'
down_revision = 'ffad172e98c1'

new_fields = ['SSL_CONN_HAS_CERT', 'SSL_VERIFY_RESULT', 'SSL_DN_FIELD']


def upgrade():

    insert_table = sql.table(
        u'l7rule_type',
        sql.column(u'name', sa.String),
        sql.column(u'description', sa.String)
    )
    cows = [{'name': field} for field in new_fields]
    op.bulk_insert(insert_table, cows)
