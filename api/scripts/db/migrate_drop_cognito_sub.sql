-- Remove cognito_sub from clients; auth scoping uses client_email_id from the JWT.
ALTER TABLE clients DROP COLUMN IF EXISTS cognito_sub;
