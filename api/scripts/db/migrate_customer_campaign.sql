-- Add campaign scheduling columns to existing customers tables.
-- Safe to re-run (IF NOT EXISTS / IF EXISTS).

ALTER TABLE customers
    ADD COLUMN IF NOT EXISTS call_schedule VARCHAR(3);

ALTER TABLE customers
    ADD COLUMN IF NOT EXISTS status VARCHAR(32);

UPDATE customers
SET call_schedule = 'no'
WHERE call_schedule IS NULL;

UPDATE customers
SET status = 'active'
WHERE status IS NULL;

ALTER TABLE customers
    ALTER COLUMN call_schedule SET DEFAULT 'no';

ALTER TABLE customers
    ALTER COLUMN call_schedule SET NOT NULL;

ALTER TABLE customers
    ALTER COLUMN status SET DEFAULT 'active';

ALTER TABLE customers
    ALTER COLUMN status SET NOT NULL;

ALTER TABLE customers
    DROP CONSTRAINT IF EXISTS chk_customers_call_schedule;

ALTER TABLE customers
    ADD CONSTRAINT chk_customers_call_schedule
    CHECK (call_schedule IN ('yes', 'no'));

ALTER TABLE customers
    DROP CONSTRAINT IF EXISTS chk_customers_status;

ALTER TABLE customers
    ADD CONSTRAINT chk_customers_status
    CHECK (status IN ('active', 'inactive'));

CREATE INDEX IF NOT EXISTS idx_customers_call_schedule
    ON customers (client_email_id, call_schedule);
