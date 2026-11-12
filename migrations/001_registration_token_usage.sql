CREATE TABLE IF NOT EXISTS sch_con.tb_con_registration_token_usage (
    jti TEXT PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    consumed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_registration_token_expiry
ON sch_con.tb_con_registration_token_usage (expires_at);
