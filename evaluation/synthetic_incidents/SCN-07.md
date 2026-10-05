scenario: New engineer's local database is missing the payments table after a fresh clone
real_file: alembic/versions/6f5e3d5e8133_initial_migration.py, alembic/versions/14051421d3f0_add_payments_table.py
real_function: upgrade() in both migration files
real_observable_behavior: >
  The initial migration (revision 6f5e3d5e8133) creates only the products,
  users, cart_items, orders, and order_items tables. The payments table is
  created in a separate, later migration (revision 14051421d3f0), whose
  down_revision field points back to 6f5e3d5e8133, meaning it must be
  applied after the initial one.
hypothetical_situation: >
  A new engineer clones the repository, runs a database setup step that
  only applies the first migration file they find, and then gets a
  "no such table: payments" error when hitting the payments endpoints.
expected_evidence:
  - migrations/6f5e3d5e8133_initial_migration.py
  - migrations/14051421d3f0_add_payments_table.py
expected_answer: >
  This is consistent with the migration history: the payments table does
  not exist until the second migration (14051421d3f0) is applied on top
  of the first. Running only the initial migration, or stopping the
  upgrade before reaching the head revision, would leave the database
  without a payments table. The documented fix is to run migrations to
  head (`alembic upgrade head`) rather than applying a single revision.
label: "SYNTHETIC — grounded in verified repository behavior, not a real historical incident"
