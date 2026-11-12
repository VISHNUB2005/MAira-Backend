-- MAira migration for an already-imported local database.
-- Run this against mira_db if the original schema is already present.
-- It preserves existing records and password hashes.

BEGIN;

ALTER TABLE sch_con.tb_con_user
    ALTER COLUMN password_hash DROP NOT NULL;

ALTER TABLE sch_con.tb_con_admin
    ALTER COLUMN password_hash DROP NOT NULL;

ALTER TABLE sch_con.tb_con_admin
    ADD COLUMN IF NOT EXISTS name VARCHAR(150);

COMMIT;
