-- Drop all RelayDesk application tables (destructive).
-- Order respects foreign keys: customers -> clients.

DROP TABLE IF EXISTS call_jobs CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS clients CASCADE;
