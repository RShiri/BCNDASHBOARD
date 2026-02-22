import sqlite3
import os

db_path = r"EliteAnalytics\data\elite_analytics.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Get matches that start with 1842
cur.execute("SELECT id FROM matches WHERE id LIKE '1842%'")
deleted_ids = cur.fetchall()

if deleted_ids:
    print(f"Deleting the following incorrect matches: {[r[0] for r in deleted_ids]}")
    cur.execute("DELETE FROM matches WHERE id LIKE '1842%'")
    conn.commit()
    print("Database cleaned successfully!")
else:
    print("No bad matches found in DB.")

conn.close()
