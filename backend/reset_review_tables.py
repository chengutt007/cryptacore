"""
Reset review-related tables so SQLAlchemy can recreate them with the correct schema.
Safe to run while backend is stopped.
"""
import sqlite3

conn = sqlite3.connect('crypta_v2.db')
cur = conn.cursor()

# Drop in safe order (review_alerts and review_analysis only — keep reviews data)
cur.execute('DROP TABLE IF EXISTS review_alerts')
cur.execute('DROP TABLE IF EXISTS review_analysis')
conn.commit()
conn.close()
print('Dropped review_alerts and review_analysis — SQLAlchemy will recreate them on next startup.')
