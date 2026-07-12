-- Full normalization: remove denormalized client columns from consumers/call_jobs/call_summaries
-- and drop call_schedule (use status=READY as the campaign trigger condition).
-- Safe to re-run (IF EXISTS / IF NOT EXISTS guards throughout).

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. consumers: backfill client_id, enforce NOT NULL, drop redundant columns
-- ─────────────────────────────────────────────────────────────────────────────

UPDATE consumers c
SET client_id = cl.id
FROM clients cl
WHERE cl.client_email_id = c.client_email_id
  AND c.client_id IS NULL;

ALTER TABLE consumers
    ALTER COLUMN client_id SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'consumers_client_id_fkey' AND contype = 'f'
    ) THEN
        ALTER TABLE consumers
            ADD CONSTRAINT consumers_client_id_fkey
            FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE RESTRICT;
    END IF;
END $$;

-- Drop old unique index that used client_email_id
DROP INDEX IF EXISTS uq_consumers_client_consumer;

-- Create new unique index using client_id
CREATE UNIQUE INDEX IF NOT EXISTS uq_consumers_client_consumer
    ON consumers (client_id, consumer_phone_number);

-- Drop client-specific columns
ALTER TABLE consumers DROP COLUMN IF EXISTS client_email_id;
ALTER TABLE consumers DROP COLUMN IF EXISTS client_business_phone_number;
ALTER TABLE consumers DROP COLUMN IF EXISTS client_name;

-- Drop call_schedule
ALTER TABLE consumers DROP CONSTRAINT IF EXISTS chk_consumers_call_schedule;
ALTER TABLE consumers DROP COLUMN IF EXISTS call_schedule;

-- Drop old indexes that referenced dropped columns
DROP INDEX IF EXISTS idx_consumers_client_business_phone;
DROP INDEX IF EXISTS idx_consumers_client_email;
DROP INDEX IF EXISTS idx_consumers_call_schedule;

-- New index: look up all consumers for a client
CREATE INDEX IF NOT EXISTS idx_consumers_client_id
    ON consumers (client_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. call_jobs: add client_id FK, backfill, drop redundant columns
-- ─────────────────────────────────────────────────────────────────────────────

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'call_jobs' AND column_name = 'client_id'
    ) THEN
        ALTER TABLE call_jobs ADD COLUMN client_id INTEGER;
    END IF;
END $$;

UPDATE call_jobs cj
SET client_id = cl.id
FROM clients cl
WHERE cl.client_email_id = cj.client_email_id
  AND cj.client_id IS NULL;

ALTER TABLE call_jobs
    ALTER COLUMN client_id SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'call_jobs_client_id_fkey' AND contype = 'f'
    ) THEN
        ALTER TABLE call_jobs
            ADD CONSTRAINT call_jobs_client_id_fkey
            FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE RESTRICT;
    END IF;
END $$;

ALTER TABLE call_jobs DROP COLUMN IF EXISTS client_email_id;
ALTER TABLE call_jobs DROP COLUMN IF EXISTS client_business_phone_number;

DROP INDEX IF EXISTS idx_call_jobs_client_business_phone;
DROP INDEX IF EXISTS idx_call_jobs_client_email;

CREATE INDEX IF NOT EXISTS idx_call_jobs_client_id
    ON call_jobs (client_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. call_summaries: add client_id FK, backfill, drop client_email_id
-- ─────────────────────────────────────────────────────────────────────────────

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'call_summaries' AND column_name = 'client_id'
    ) THEN
        ALTER TABLE call_summaries ADD COLUMN client_id INTEGER;
    END IF;
END $$;

UPDATE call_summaries cs
SET client_id = co.client_id
FROM consumers co
WHERE co.id = cs.consumer_id
  AND cs.client_id IS NULL;

ALTER TABLE call_summaries
    ALTER COLUMN client_id SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'call_summaries_client_id_fkey' AND contype = 'f'
    ) THEN
        ALTER TABLE call_summaries
            ADD CONSTRAINT call_summaries_client_id_fkey
            FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE RESTRICT;
    END IF;
END $$;

ALTER TABLE call_summaries DROP COLUMN IF EXISTS client_email_id;

DROP INDEX IF EXISTS idx_call_summaries_client_email;
DROP INDEX IF EXISTS idx_call_summaries_call_start;

CREATE INDEX IF NOT EXISTS idx_call_summaries_client_id
    ON call_summaries (client_id);

CREATE INDEX IF NOT EXISTS idx_call_summaries_client_start
    ON call_summaries (client_id, call_start_time DESC);
