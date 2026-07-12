-- Add per-client voice agent campaign schedules (idempotent).
CREATE TABLE IF NOT EXISTS client_voice_agent_schedules (
    id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL UNIQUE REFERENCES clients(id) ON DELETE CASCADE,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    run_time VARCHAR(5) NOT NULL DEFAULT '09:00',
    days_of_week VARCHAR(32) NOT NULL DEFAULT '1,2,3,4,5',
    timezone VARCHAR(64) NOT NULL DEFAULT 'Asia/Kolkata',
    next_run_at TIMESTAMPTZ,
    last_run_at TIMESTAMPTZ,
    last_job_id UUID REFERENCES call_jobs(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_client_voice_agent_schedules_next_run
    ON client_voice_agent_schedules (next_run_at)
    WHERE enabled = TRUE;
