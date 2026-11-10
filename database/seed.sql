BEGIN;

-- Insert 18 approved student accounts
-- Password hashes remain NULL until registration is completed.

INSERT INTO sch_con.tb_con_user
    (email, user_type, password_hash, status)
VALUES
    ('sganushree.v@gmail.com', 'STUDENT', NULL, 'ACTIVE'),
    ('priyabherji22@gmail.com', 'STUDENT', NULL, 'ACTIVE'),
    ('cchendu590@gmail.com', 'STUDENT', NULL, 'ACTIVE'),
    ('sujaydevadiga7055@gmail.com', 'STUDENT', NULL, 'ACTIVE'),
    ('chandanachari.k@gmail.com', 'STUDENT', NULL, 'ACTIVE'),
    ('milanved9@gmail.com', 'STUDENT', NULL, 'ACTIVE'),
    ('hschethan611@gmail.com', 'STUDENT', NULL, 'ACTIVE'),
    ('divyaprabha5544@gmail.com', 'STUDENT', NULL, 'ACTIVE'),
    ('shivanandag25@gmail.com', 'STUDENT', NULL, 'ACTIVE'),
    ('thenameisani889@gmail.com', 'STUDENT', NULL, 'ACTIVE'),
    ('sandranrp112@gmail.com', 'STUDENT', NULL, 'ACTIVE'),
    ('gradhika2218@gmail.com', 'STUDENT', NULL, 'ACTIVE'),
    ('hazrapijush60@gmail.com', 'STUDENT', NULL, 'ACTIVE'),
    ('kavishri2307@gmail.com', 'STUDENT', NULL, 'ACTIVE'),
    ('3251.viking@gmail.com', 'STUDENT', NULL, 'ACTIVE'),
    ('gokulg7289@gmail.com', 'STUDENT', NULL, 'ACTIVE'),
    ('abhilashsiriger01@gmail.com', 'STUDENT', NULL, 'ACTIVE'),
    ('priyalokesh26409@gmail.com', 'STUDENT', NULL, 'ACTIVE')
ON CONFLICT (email) DO NOTHING;

-- Insert initial admin account
INSERT INTO sch_con.tb_con_admin
    (name, email, password_hash, status)
VALUES
    ('Vishnu', '02vishnub05@gmail.com', NULL, 'ACTIVE')
ON CONFLICT (email)
DO UPDATE SET name = EXCLUDED.name;

COMMIT;
