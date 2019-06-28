#    Copyright (c) 2019 Red Hat, Inc.
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

"""add protocol in listener keys

Revision ID: a5762a99609a
Revises: 392fb85b4419
Create Date: 2019-06-28 14:02:11.415292

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = 'a5762a99609a'
down_revision = '392fb85b4419'


def upgrade():
    op.execute("ALTER TABLE `listener` "
               "DROP INDEX `uq_listener_load_balancer_id_protocol_port`, "
               "ADD UNIQUE KEY "
               "`uq_listener_load_balancer_id_protocol_port` "
               "(`load_balancer_id`, `protocol`, `protocol_port`)")
