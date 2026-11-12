import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from pathlib import Path

def setup_test_db():
    print("Checking / creating isolated test database: mira_test_db...")
    # Connect to postgres system database to create mira_test_db if not exists
    conn = psycopg2.connect("postgresql://postgres:root@127.0.0.1:5432/postgres")
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = 'mira_test_db'")
    if not cur.fetchone():
        cur.execute("CREATE DATABASE mira_test_db")
        print("[OK] Created database mira_test_db")
    else:
        print("[INFO] Database mira_test_db already exists")
    cur.close()
    conn.close()

    # Apply schema to mira_test_db
    schema_file = Path("c:/Dev/mAira/database/mira_db_schema.sql")
    if not schema_file.exists():
        print(f"[ERROR] Schema file not found at {schema_file}")
        sys.exit(1)

    test_conn = psycopg2.connect("postgresql://postgres:root@127.0.0.1:5432/mira_test_db")
    test_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    test_cur = test_conn.cursor()
    
    # Check if schema sch_con already exists
    test_cur.execute("SELECT 1 FROM information_schema.schemata WHERE schema_name = 'sch_con'")
    if not test_cur.fetchone():
        print("[INFO] Applying mira_db_schema.sql to mira_test_db...")
        sql_content = schema_file.read_text(encoding="utf-8")
        # Remove psql-specific slash commands like \restrict or \unrestrict
        cleaned_sql_lines = []
        for line in sql_content.splitlines():
            if line.strip().startswith("\\restrict") or line.strip().startswith("\\unrestrict"):
                continue
            cleaned_sql_lines.append(line)
        cleaned_sql = "\n".join(cleaned_sql_lines)
        test_cur.execute(cleaned_sql)
        print("[OK] Applied authoritative schema to mira_test_db")
    else:
        print("[INFO] Schema sch_con already exists in mira_test_db")

    test_cur.close()
    test_conn.close()
    print("[SUCCESS] Isolated test database mira_test_db is ready.")

if __name__ == "__main__":
    setup_test_db()
