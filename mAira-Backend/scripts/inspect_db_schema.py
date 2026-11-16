import asyncio
import asyncpg

async def main():
    conn = await asyncpg.connect("postgresql://postgres:root@127.0.0.1:5432/mira_db")
    rows = await conn.fetch("""
        SELECT table_name, column_name, data_type, is_nullable, column_default 
        FROM information_schema.columns 
        WHERE table_schema = 'sch_con' 
        ORDER BY table_name, ordinal_position;
    """)
    for r in rows:
        print(f"{r['table_name']}.{r['column_name']}: {r['data_type']} (nullable={r['is_nullable']}, default={r['column_default']})")
    
    print("\n--- Constraints ---")
    constraints = await conn.fetch("""
        SELECT tc.table_name, tc.constraint_name, tc.constraint_type, kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
          AND tc.table_schema = kcu.table_schema
        WHERE tc.table_schema = 'sch_con'
        ORDER BY tc.table_name, tc.constraint_name;
    """)
    for c in constraints:
        print(f"{c['table_name']}: {c['constraint_name']} ({c['constraint_type']}) -> {c['column_name']}")
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
