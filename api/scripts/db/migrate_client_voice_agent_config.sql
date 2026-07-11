-- Per-client voice agent settings (greeting, Cal.com).
-- Usage: uv run python infra/scripts/migrate_database.py --use-tunnel --file migrate_client_voice_agent_config.sql

CREATE TABLE IF NOT EXISTS client_voice_agent_configs (
    id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL UNIQUE REFERENCES clients(id) ON DELETE CASCADE,
    voice_agent_greeting_message TEXT NOT NULL DEFAULT (
        'Greet the caller briefly. Introduce the business and summarize key service '
        'offerings. Say you can answer questions by searching the uploaded documents. '
        'Ask what they would like to know.'
    ),
    calcom_username VARCHAR(255),
    calcom_event_type_slug VARCHAR(255),
    calcom_event_type_id INTEGER,
    calcom_organization_slug VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_client_voice_agent_configs_client_id
    ON client_voice_agent_configs (client_id);

-- Drop legacy column if an earlier migration created it.
ALTER TABLE client_voice_agent_configs
    DROP COLUMN IF EXISTS knowledge_base_topic;

INSERT INTO client_voice_agent_configs (
    client_id,
    voice_agent_greeting_message,
    calcom_username,
    calcom_event_type_slug,
    calcom_event_type_id
)
SELECT
    c.id,
    'Greet the caller briefly. Introduce the business and summarize key service offerings. Say you can answer questions by searching the uploaded documents. Ask what they would like to know.',
    'deepak-kumar-a7vq7q',
    '30min',
    6073963
FROM clients AS c
WHERE c.client_business_phone_number = '911171366880'
ON CONFLICT (client_id) DO NOTHING;

INSERT INTO client_voice_agent_configs (
    client_id,
    voice_agent_greeting_message
)
SELECT
    c.id,
    'Greet the caller briefly. Introduce the business and summarize key service offerings. Say you can answer questions by searching the uploaded documents. Ask what they would like to know.'
FROM clients AS c
WHERE c.client_business_phone_number IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM client_voice_agent_configs AS cfg
      WHERE cfg.client_id = c.id
  );
