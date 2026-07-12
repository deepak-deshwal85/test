-- call_schedule = yes/no (campaign queue). status = READY / MEETING_SCHEDULED / MEETING_NOT_SCHEDULED.
-- Usage: uv run python infra/scripts/migrate_database.py --use-tunnel --file migrate_consumer_call_status.sql

ALTER TABLE consumers
    DROP CONSTRAINT IF EXISTS chk_consumers_call_schedule;

ALTER TABLE consumers
    DROP CONSTRAINT IF EXISTS chk_consumers_status;

-- If a prior migration moved lifecycle values onto call_schedule, restore them to status.
UPDATE consumers
SET status = call_schedule
WHERE call_schedule IN ('READY', 'MEETING_SCHEDULED', 'MEETING_NOT_SCHEDULED');

UPDATE consumers
SET call_schedule = 'yes'
WHERE call_schedule = 'READY';

UPDATE consumers
SET call_schedule = 'no'
WHERE call_schedule IN ('MEETING_SCHEDULED', 'MEETING_NOT_SCHEDULED');

ALTER TABLE consumers
    ALTER COLUMN call_schedule TYPE VARCHAR(3);

ALTER TABLE consumers
    ALTER COLUMN call_schedule SET DEFAULT 'no';

UPDATE consumers
SET status = 'READY'
WHERE status IN ('active', 'inactive') OR status IS NULL;

ALTER TABLE consumers
    ALTER COLUMN status SET DEFAULT 'READY';

ALTER TABLE consumers
    ADD CONSTRAINT chk_consumers_call_schedule
    CHECK (call_schedule IN ('yes', 'no'));

ALTER TABLE consumers
    ADD CONSTRAINT chk_consumers_status
    CHECK (status IN ('READY', 'MEETING_SCHEDULED', 'MEETING_NOT_SCHEDULED'));
