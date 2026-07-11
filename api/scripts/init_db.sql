-- Deprecated: use `uv run python scripts/init_db.py` instead.
-- Schema lives in scripts/db/schema.sql; seed data in scripts/db/seed.sql.
--
-- Terraform/RDS creates the empty `relaydesk` database. Run init_db.py once
-- after deploy (or locally through the SSM tunnel) to create tables and seed.

\echo 'Run: cd api && uv run python scripts/init_db.py'
