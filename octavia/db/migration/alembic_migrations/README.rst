The migrations in the alembic/versions contain the migrations.

Before running this migration ensure that the database octavia exists.

To run migrations you must first be in the octavia/db/migration directory.

To migrate to the most current version run:
$ octavia-db-manage upgrade head
