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

"""add primary key to spares_pool

Revision ID: 392fb85b4419
Revises: 46d914b2a5e5
Create Date: 2019-04-30 09:58:54.159823

"""

from alembic import op
from sqlalchemy.engine import reflection

from oslo_log import log as logging


# revision identifiers, used by Alembic.
revision = '392fb85b4419'
down_revision = '46d914b2a5e5'

LOG = logging.getLogger(__name__)


def upgrade():
    bind = op.get_bind()
    inspector = reflection.Inspector.from_engine(bind.engine)
    pk = inspector.get_pk_constraint('spares_pool')
    if not pk['constrained_columns']:
        op.create_primary_key(
            u'pk_spares_pool', u'spares_pool', [u'updated_at'])
    else:
        # Revision '46d914b2a5e5' has been updated to create the
        # missing PK. Depending whether the env is already deployed or
        # not we may or not have to add the primary key.
        LOG.info("The primary key in spares_pool already exists, continuing.")
