-- Dummy development data for RelayDesk (idempotent).
-- Safe to re-run: uses ON CONFLICT DO NOTHING / DO UPDATE where needed.

INSERT INTO clients (
    client_phone_number,
    client_business_phone_number,
    client_name,
    client_email_id,
    cognito_sub
) VALUES
    (
        '919876543210',
        '911171366880',
        'Acme Support',
        'acme@example.com',
        '00000000-0000-4000-8000-000000000001'
    ),
    (
        '919988776655',
        NULL,
        'Pending Guest Co',
        'pending@example.com',
        '00000000-0000-4000-8000-000000000002'
    )
ON CONFLICT (client_email_id) DO UPDATE SET
    client_name = EXCLUDED.client_name,
    client_phone_number = EXCLUDED.client_phone_number,
    client_business_phone_number = COALESCE(
        clients.client_business_phone_number,
        EXCLUDED.client_business_phone_number
    );

INSERT INTO customers (
    client_id,
    client_business_phone_number,
    client_name,
    client_email_id,
    consumer_phone_number,
    consumer_email_id,
    is_approved,
    call_schedule,
    status
)
SELECT
    c.id,
    c.client_business_phone_number,
    c.client_name,
    c.client_email_id,
    v.consumer_phone_number,
    v.consumer_email_id,
    TRUE,
    v.call_schedule,
    v.status
FROM clients AS c
CROSS JOIN (
    VALUES
        ('919900000001', 'alice.consumer@example.com', 'yes', 'active'),
        ('919900000002', 'bob.consumer@example.com', 'yes', 'active'),
        ('919900000003', 'carol.consumer@example.com', 'no', 'active')
) AS v(consumer_phone_number, consumer_email_id, call_schedule, status)
WHERE c.client_email_id = 'acme@example.com'
  AND c.client_business_phone_number IS NOT NULL
ON CONFLICT (client_email_id, consumer_phone_number) DO UPDATE SET
    consumer_email_id = EXCLUDED.consumer_email_id,
    client_name = EXCLUDED.client_name,
    client_business_phone_number = EXCLUDED.client_business_phone_number,
    is_approved = EXCLUDED.is_approved,
    call_schedule = EXCLUDED.call_schedule,
    status = EXCLUDED.status,
    updated_at = NOW();

INSERT INTO call_jobs (
    id,
    client_business_phone_number,
    client_email_id,
    status,
    total_customers,
    calls_completed,
    error_message,
    started_at,
    completed_at,
    results_json
)
SELECT
    'aaaaaaaa-bbbb-cccc-dddd-000000000001'::uuid,
    c.client_business_phone_number,
    c.client_email_id,
    'completed',
    3,
    3,
    NULL,
    NOW() - INTERVAL '1 day',
    NOW() - INTERVAL '1 day' + INTERVAL '15 minutes',
    '[{"customer_id":1,"consumer_phone_number":"919900000001","success":true,"detail":"answered"},{"customer_id":2,"consumer_phone_number":"919900000002","success":true,"detail":"answered"},{"customer_id":3,"consumer_phone_number":"919900000003","success":false,"detail":"no answer"}]'
FROM clients AS c
WHERE c.client_email_id = 'acme@example.com'
  AND c.client_business_phone_number IS NOT NULL
ON CONFLICT (id) DO NOTHING;

INSERT INTO call_jobs (
    id,
    client_business_phone_number,
    client_email_id,
    status,
    total_customers,
    calls_completed,
    error_message
)
SELECT
    'aaaaaaaa-bbbb-cccc-dddd-000000000002'::uuid,
    c.client_business_phone_number,
    c.client_email_id,
    'pending',
    0,
    0,
    NULL
FROM clients AS c
WHERE c.client_email_id = 'acme@example.com'
  AND c.client_business_phone_number IS NOT NULL
ON CONFLICT (id) DO NOTHING;

INSERT INTO call_summaries (
    customer_id,
    client_email_id,
    call_start_time,
    call_end_time,
    call_summary,
    job_id
)
SELECT
    cust.id,
    cust.client_email_id,
    NOW() - INTERVAL '2 hours',
    NOW() - INTERVAL '1 hour 45 minutes',
    'Agent greeted the caller and answered questions about pricing and onboarding. Caller requested a follow-up email.',
    'aaaaaaaa-bbbb-cccc-dddd-000000000001'::uuid
FROM customers AS cust
WHERE cust.client_email_id = 'acme@example.com'
  AND cust.consumer_phone_number = '919900000001';

INSERT INTO call_summaries (
    customer_id,
    client_email_id,
    call_start_time,
    call_end_time,
    call_summary,
    job_id
)
SELECT
    cust.id,
    cust.client_email_id,
    NOW() - INTERVAL '1 day',
    NOW() - INTERVAL '1 day' + INTERVAL '8 minutes',
    'Brief call: caller asked about support hours. Agent provided business hours and offered to schedule a meeting.',
    'aaaaaaaa-bbbb-cccc-dddd-000000000001'::uuid
FROM customers AS cust
WHERE cust.client_email_id = 'acme@example.com'
  AND cust.consumer_phone_number = '919900000002';
