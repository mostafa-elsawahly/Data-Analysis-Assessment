import os, glob, urllib.parse
import pandas as pd
from sqlalchemy import create_engine

conn = urllib.parse.quote_plus(
    "DRIVER={ODBC Driver 18 for SQL Server};"
    f"SERVER={os.environ['DB_SERVER']},1433;"
    f"DATABASE={os.environ['DB_NAME']};"
    f"UID={os.environ['DB_USER']};PWD={os.environ['DB_PASSWORD']};"
    "TrustServerCertificate=yes;Encrypt=yes"
)
engine = create_engine(f"mssql+pyodbc:///?odbc_connect={conn}", fast_executemany=True)

for path in glob.glob("datasets/*/*/*.csv"):
    year, category = path.split("/")[1:3]   # مثلاً 2022 / Accessions
    for chunk in pd.read_csv(path, chunksize=50_000, low_memory=False):
        chunk["source_year"] = year
        chunk.to_sql(category.lower(), engine, if_exists="append", index=False)
