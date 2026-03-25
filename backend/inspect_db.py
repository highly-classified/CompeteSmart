import os
from sqlalchemy import create_engine, inspect
from dotenv import load_dotenv

load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"))
insp = inspect(engine)

for table in ["competitors", "snapshots", "extracted_content"]:
    print(f"Table: {table}")
    try:
        for col in insp.get_columns(table):
            print(f"  {col['name']}: {col['type']}")
    except Exception as e:
        print(f"  Error reading table: {e}")
