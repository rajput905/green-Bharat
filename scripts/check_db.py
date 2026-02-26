
import sqlite3
import os

db_path = 'greenflow/data/greenflow_dev.db'
if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
else:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    try:
        cur.execute('SELECT COUNT(*) FROM analytics_records')
        count = cur.fetchone()[0]
        print(f"Analytics records count: {count}")
        
        cur.execute('SELECT * FROM analytics_records ORDER BY id DESC LIMIT 1')
        row = cur.fetchone()
        print(f"Latest record: {row}")
    except Exception as e:
        print(f"Error: {e}")
    conn.close()
