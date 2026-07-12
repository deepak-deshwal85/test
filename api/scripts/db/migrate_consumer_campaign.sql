-- Add campaign scheduling columns to existing consumers tables.
-- Safe to re-run (IF NOT EXISTS / IF EXISTS).

ALTER TABLE consumers
    ADD COLUMN IF NOT EXISTS call_schedule VARCHAR(3);

ALTER TABLE consumers
    ADD COLUMN IF NOT EXISTS status VARCHAR(32);

UPDATE consumers
SET call_schedule = 'no'
WHERE call_schedule IS NULL;

UPDATE consumers
SET status = 'active'
WHERE status IS NULL;

ALTER TABLE consumers
    ALTER COLUMN call_schedule SET DEFAULT 'no';

ALTER TABLE consumers
    ALTER COLUMN call_schedule SET NOT NULL;

ALTER TABLE consumers
    ALTER COLUMN status SET DEFAULT 'active';

ALTER TABLE consumers
    ALTER COLUMN status SET NOT NULL;

ALTER TABLE consumers
    DROP CONSTRAINT IF EXISTS chk_consumers_call_schedule;

ALTER TABLE consumers
    ADD CONSTRAINT chk_consumers_call_schedule
    CHECK (call_schedule IN ('yes', 'no'));

ALTER TABLE consumers
    DROP CONSTRAINT IF EXISTS chk_consumers_status;

ALTER TABLE consumers
    ADD CONSTRAINT chk_consumers_status
    CHECK (status IN ('active', 'inactive'));

CREATE INDEX IF NOT EXISTS idx_consumers_call_schedule
    ON consumers (client_email_id, call_schedule);
