import os
from sqlalchemy import create_engine, inspect
from dotenv import load_dotenv

load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"))
insp = inspect(engine)

for table in insp.get_table_names():
    print(f"Table: {table}")
    for col in insp.get_columns(table):
        print(f"  {col['name']}: {col['type']}")
