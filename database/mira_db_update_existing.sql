-- MAira migration for an already-imported older local database.
-- Run this only when the old schema is already present.
-- It preserves existing records and password hashes.

BEGIN;

ALTER TABLE sch_con.tb_con_user
    ALTER COLUMN password_hash DROP NOT NULL;

ALTER TABLE sch_con.tb_con_admin
    ALTER COLUMN password_hash DROP NOT NULL;

ALTER TABLE sch_con.tb_con_admin
    ADD COLUMN IF NOT EXISTS name VARCHAR(150);

COMMIT;
