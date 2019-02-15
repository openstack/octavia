# Copyright 2017 Rackspace, US Inc.
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

"""Fix_IPv6_VIP

Revision ID: 11e4bb2bb8ef
Revises: 211982b05afc
Create Date: 2019-01-28 08:35:35.333616

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '11e4bb2bb8ef'
down_revision = '211982b05afc'


def upgrade():
    op.alter_column(u'vip', u'ip_address', type_=sa.String(64))
