-- Rename customers entity to consumers for existing RelayDesk databases.
-- Run after prior migrate_*.sql files. Safe to re-run (guarded with IF EXISTS).

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'customers'
    ) AND NOT EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'consumers'
    ) THEN
        ALTER TABLE customers RENAME TO consumers;
    END IF;
END $$;

ALTER INDEX IF EXISTS uq_customers_client_consumer RENAME TO uq_consumers_client_consumer;
ALTER INDEX IF EXISTS idx_customers_client_business_phone RENAME TO idx_consumers_client_business_phone;
ALTER INDEX IF EXISTS idx_customers_client_email RENAME TO idx_consumers_client_email;
ALTER INDEX IF EXISTS idx_customers_call_schedule RENAME TO idx_consumers_call_schedule;
ALTER INDEX IF EXISTS idx_call_summaries_customer RENAME TO idx_call_summaries_consumer;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_customers_call_schedule'
    ) THEN
        ALTER TABLE consumers
            RENAME CONSTRAINT chk_customers_call_schedule TO chk_consumers_call_schedule;
    END IF;
    IF EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_customers_status'
    ) THEN
        ALTER TABLE consumers
            RENAME CONSTRAINT chk_customers_status TO chk_consumers_status;
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'call_summaries'
          AND column_name = 'customer_id'
    ) THEN
        ALTER TABLE call_summaries RENAME COLUMN customer_id TO consumer_id;
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'call_jobs'
          AND column_name = 'total_customers'
    ) THEN
        ALTER TABLE call_jobs RENAME COLUMN total_customers TO total_consumers;
    END IF;
END $$;

UPDATE call_jobs
SET results_json = REPLACE(results_json, '"customer_id"', '"consumer_id"')
WHERE results_json IS NOT NULL
  AND results_json LIKE '%"customer_id"%';
