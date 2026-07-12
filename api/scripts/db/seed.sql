-- Dummy development data for RelayDesk (idempotent).
-- Safe to re-run: uses ON CONFLICT DO NOTHING / DO UPDATE where needed.

INSERT INTO clients (
    client_phone_number,
    client_business_phone_number,
    client_name,
    client_email_id
) VALUES
    (
        '919876543210',
        '911171366880',
        'Acme Support',
        'acme@example.com'
    ),
    (
        '919988776655',
        NULL,
        'Pending Guest Co',
        'pending@example.com'
    )
ON CONFLICT (client_email_id) DO UPDATE SET
    client_name = EXCLUDED.client_name,
    client_phone_number = EXCLUDED.client_phone_number,
    client_business_phone_number = COALESCE(
        clients.client_business_phone_number,
        EXCLUDED.client_business_phone_number
    );

INSERT INTO consumers (
    client_id,
    consumer_phone_number,
    consumer_email_id,
    is_approved,
    status
)
SELECT
    c.id,
    v.consumer_phone_number,
    v.consumer_email_id,
    TRUE,
    v.status
FROM clients AS c
CROSS JOIN (
    VALUES
        ('919900000001', 'alice.consumer@example.com', 'READY'),
        ('919900000002', 'bob.consumer@example.com', 'READY'),
        ('919900000003', 'carol.consumer@example.com', 'MEETING_NOT_SCHEDULED')
) AS v(consumer_phone_number, consumer_email_id, status)
WHERE c.client_email_id = 'acme@example.com'
  AND c.client_business_phone_number IS NOT NULL
ON CONFLICT (client_id, consumer_phone_number) DO UPDATE SET
    consumer_email_id = EXCLUDED.consumer_email_id,
    is_approved = EXCLUDED.is_approved,
    status = EXCLUDED.status,
    updated_at = NOW();

INSERT INTO call_jobs (
    id,
    client_id,
    status,
    total_consumers,
    calls_completed,
    error_message,
    started_at,
    completed_at,
    results_json
)
SELECT
    'aaaaaaaa-bbbb-cccc-dddd-000000000001'::uuid,
    c.id,
    'completed',
    3,
    3,
    NULL,
    NOW() - INTERVAL '1 day',
    NOW() - INTERVAL '1 day' + INTERVAL '15 minutes',
    '[{"consumer_id":1,"consumer_phone_number":"919900000001","success":true,"detail":"answered"},{"consumer_id":2,"consumer_phone_number":"919900000002","success":true,"detail":"answered"},{"consumer_id":3,"consumer_phone_number":"919900000003","success":false,"detail":"no answer"}]'
FROM clients AS c
WHERE c.client_email_id = 'acme@example.com'
  AND c.client_business_phone_number IS NOT NULL
ON CONFLICT (id) DO NOTHING;

INSERT INTO call_jobs (
    id,
    client_id,
    status,
    total_consumers,
    calls_completed,
    error_message
)
SELECT
    'aaaaaaaa-bbbb-cccc-dddd-000000000002'::uuid,
    c.id,
    'pending',
    0,
    0,
    NULL
FROM clients AS c
WHERE c.client_email_id = 'acme@example.com'
  AND c.client_business_phone_number IS NOT NULL
ON CONFLICT (id) DO NOTHING;

INSERT INTO call_summaries (
    consumer_id,
    client_id,
    call_start_time,
    call_end_time,
    call_summary,
    job_id
)
SELECT
    co.id,
    co.client_id,
    NOW() - INTERVAL '2 hours',
    NOW() - INTERVAL '1 hour 45 minutes',
    'Agent greeted the caller and answered questions about pricing and onboarding. Caller requested a follow-up email.',
    'aaaaaaaa-bbbb-cccc-dddd-000000000001'::uuid
FROM consumers AS co
JOIN clients AS c ON c.id = co.client_id
WHERE c.client_email_id = 'acme@example.com'
  AND co.consumer_phone_number = '919900000001';

INSERT INTO call_summaries (
    consumer_id,
    client_id,
    call_start_time,
    call_end_time,
    call_summary,
    job_id
)
SELECT
    co.id,
    co.client_id,
    NOW() - INTERVAL '1 day',
    NOW() - INTERVAL '1 day' + INTERVAL '8 minutes',
    'Brief call: caller asked about support hours. Agent provided business hours and offered to schedule a meeting.',
    'aaaaaaaa-bbbb-cccc-dddd-000000000001'::uuid
FROM consumers AS co
JOIN clients AS c ON c.id = co.client_id
WHERE c.client_email_id = 'acme@example.com'
  AND co.consumer_phone_number = '919900000002';

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
WHERE c.client_email_id = 'acme@example.com'
ON CONFLICT (client_id) DO UPDATE SET
    calcom_username = EXCLUDED.calcom_username,
    calcom_event_type_slug = EXCLUDED.calcom_event_type_slug,
    calcom_event_type_id = EXCLUDED.calcom_event_type_id,
    updated_at = NOW();
