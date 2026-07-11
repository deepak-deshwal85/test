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
    is_approved
)
SELECT
    c.id,
    c.client_business_phone_number,
    c.client_name,
    c.client_email_id,
    v.consumer_phone_number,
    v.consumer_email_id,
    TRUE
FROM clients AS c
CROSS JOIN (
    VALUES
        ('919900000001', 'alice.consumer@example.com'),
        ('919900000002', 'bob.consumer@example.com'),
        ('919900000003', 'carol.consumer@example.com')
) AS v(consumer_phone_number, consumer_email_id)
WHERE c.client_email_id = 'acme@example.com'
  AND c.client_business_phone_number IS NOT NULL
ON CONFLICT (client_email_id, consumer_phone_number) DO UPDATE SET
    consumer_email_id = EXCLUDED.consumer_email_id,
    client_name = EXCLUDED.client_name,
    client_business_phone_number = EXCLUDED.client_business_phone_number,
    is_approved = EXCLUDED.is_approved,
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
