# Copyright 2026 OpenStack Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License.

"""Seed the active/active standby amphora role.

The historical active/active migration used by an earlier lab image seeded
``IN_CLUSTER`` but omitted ``IN_CLUSTER_STANDBY``.  Keep this repair
idempotent so it is safe both for an existing database and for a fresh
database where the corrected base migration already inserted the row.
"""

from alembic import op
import sqlalchemy as sa


revision = 'e8c1f2a3b4d5'
down_revision = 'd5cf3da30ed8'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(sa.text(
        "INSERT INTO amphora_roles (name, description) "
        "SELECT 'IN_CLUSTER_STANDBY', "
        "'Standby member of an amphora cluster' "
        "WHERE NOT EXISTS (SELECT 1 FROM amphora_roles "
        "WHERE name = 'IN_CLUSTER_STANDBY')"))


def downgrade():
    op.execute(sa.text(
        "DELETE FROM amphora_roles WHERE name = 'IN_CLUSTER_STANDBY'"))
