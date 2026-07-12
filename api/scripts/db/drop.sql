-- Drop all RelayDesk application tables (destructive).
-- Order respects foreign keys: consumers -> clients.

DROP TABLE IF EXISTS call_jobs CASCADE;
DROP TABLE IF EXISTS consumers CASCADE;
DROP TABLE IF EXISTS clients CASCADE;
