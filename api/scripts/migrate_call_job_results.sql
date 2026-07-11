-- Legacy one-off migration — included in scripts/db/schema.sql.
-- Kept for reference only; new environments should run init_db.py instead.

ALTER TABLE IF EXISTS call_jobs
    ADD COLUMN IF NOT EXISTS results_json TEXT;
