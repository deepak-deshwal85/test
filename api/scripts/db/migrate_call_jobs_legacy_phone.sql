-- Remove legacy call_jobs.client_phone_number (replaced by client_business_phone_number).

UPDATE call_jobs
SET client_business_phone_number = client_phone_number
WHERE (client_business_phone_number IS NULL OR client_business_phone_number = '')
  AND client_phone_number IS NOT NULL;

ALTER TABLE call_jobs
    ALTER COLUMN client_phone_number DROP NOT NULL;

ALTER TABLE call_jobs
    DROP COLUMN IF EXISTS client_phone_number;
