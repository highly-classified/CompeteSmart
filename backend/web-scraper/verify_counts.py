import db
from datetime import datetime

with db.get_conn() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT is_synthetic, COUNT(*) FROM snapshots GROUP BY is_synthetic")
        print("Snapshots:", cur.fetchall())
        cur.execute("SELECT is_synthetic, COUNT(*) FROM extracted_content GROUP BY is_synthetic")
        print("Chunks:", cur.fetchall())
