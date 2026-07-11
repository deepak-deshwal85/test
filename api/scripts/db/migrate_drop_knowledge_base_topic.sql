-- Remove knowledge_base_topic from client_voice_agent_configs.
-- Service offerings belong in voice_agent_greeting_message; factual answers come from document search.
-- Usage: uv run python infra/scripts/migrate_database.py --use-tunnel --file migrate_drop_knowledge_base_topic.sql

ALTER TABLE client_voice_agent_configs
    DROP COLUMN IF EXISTS knowledge_base_topic;
