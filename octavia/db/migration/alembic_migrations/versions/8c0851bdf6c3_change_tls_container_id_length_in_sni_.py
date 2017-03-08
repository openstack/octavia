# Copyright 2016 Hewlett-Packard Development Company, L.P.
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

"""change_tls_container_id_length_in_sni_table

Revision ID: 8c0851bdf6c3
Revises: 186509101b9b
Create Date: 2016-03-23 19:08:53.148812

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '8c0851bdf6c3'
down_revision = '186509101b9b'


def upgrade():
    op.alter_column(u'sni', u'tls_container_id', type_=sa.String(128),
                    existing_type=sa.String(36), nullable=False)
