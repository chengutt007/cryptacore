import sqlite3
conn = sqlite3.connect('crypta_v2.db')
cur = conn.cursor()

for table in ['review_analysis', 'review_alerts']:
    cur.execute(f'PRAGMA table_info({table})')
    cols = [r[1] for r in cur.fetchall()]
    print(f'{table} columns: {cols}')
    if 'created_at' not in cols:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN created_at DATETIME")
        print(f'  -> Added created_at to {table}')
    if table == 'review_alerts':
        for col in ['reason', 'detail']:
            if col not in cols:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} TEXT")
                print(f'  -> Added {col} to {table}')

conn.commit()
conn.close()
print('Migration complete.')
