-- MAira safe local seed example.
-- Replace these .invalid addresses with approved development addresses before use.
-- Do NOT commit a real database/seed.sql containing team email addresses.
-- Password hashes intentionally remain NULL until OTP registration is completed.

BEGIN;

INSERT INTO sch_con.tb_con_user
    (email, user_type, password_hash, status)
VALUES
    ('student1@example.invalid', 'STUDENT', NULL, 'ACTIVE'),
    ('student2@example.invalid', 'STUDENT', NULL, 'ACTIVE')
ON CONFLICT (email) DO NOTHING;

INSERT INTO sch_con.tb_con_admin
    (name, email, password_hash, status)
VALUES
    ('Local Admin', 'admin@example.invalid', NULL, 'ACTIVE')
ON CONFLICT (email)
DO UPDATE SET name = EXCLUDED.name;

COMMIT;
