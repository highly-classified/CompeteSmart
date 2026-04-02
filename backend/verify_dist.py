from src.database import SessionLocal
from sqlalchemy import text

def verify():
    db = SessionLocal()
    try:
        query = """
        SELECT TO_CHAR(DATE_TRUNC('year', created_at), 'YYYY') AS year, COUNT(*) 
        FROM extracted_content 
        GROUP BY 1 ORDER BY 1;
        """
        results = db.execute(text(query)).fetchall()
        print("Yearly distribution:")
        for year, count in results:
            print(f"{year}: {count}")
    finally:
        db.close()

if __name__ == "__main__":
    verify()
