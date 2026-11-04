import os, sys
from pathlib import Path
import pandas as pd, pyarrow as pa, pyarrow.parquet as pq
from sql_conn import connect

SCHEMA = os.environ.get("SQL_SCHEMA", "opm")
FOLDERS = {"accessions": "Accessions", "separations": "Separations", "employment": "Employment"}
wanted = sys.argv[1:] or ["accessions", "separations"]

def sql_type(t):
    if pa.types.is_integer(t): return "INT"
    if pa.types.is_floating(t): return "FLOAT"
    if pa.types.is_timestamp(t) or pa.types.is_date(t): return "DATE"
    if pa.types.is_boolean(t): return "BIT"
    return "NVARCHAR(500)"

conn = connect()
cur = conn.cursor()
cur.fast_executemany = True

cur.execute(f"IF SCHEMA_ID('{SCHEMA}') IS NULL EXEC('CREATE SCHEMA {SCHEMA}')")
cur.execute(f"""IF OBJECT_ID('{SCHEMA}.load_log') IS NULL
CREATE TABLE {SCHEMA}.load_log (
  dataset NVARCHAR(30) NOT NULL, source_file NVARCHAR(100) NOT NULL,
  row_count INT, loaded_at DATETIME2 DEFAULT SYSUTCDATETIME(),
  PRIMARY KEY (dataset, source_file))""")
conn.commit()

for table in wanted:
    folder = FOLDERS[table]
    full = f"{SCHEMA}.{table}"
    files = sorted(Path("datasets").glob(f"*/{folder}/*.parquet"))
    done = {r[0] for r in cur.execute(
        f"SELECT source_file FROM {SCHEMA}.load_log WHERE dataset=?", table)}
    print(f"{folder}: {len(files)} local files, {len(done)} already loaded")

    for p in files:
        if p.stem in done:
            continue
        if cur.execute("SELECT OBJECT_ID(?)", full).fetchone()[0] is None:
            cols = ",\n".join(f"[{f.name}] {sql_type(f.type)} NULL"
                              for f in pq.read_schema(p))
            cur.execute(f"CREATE TABLE {full} (\n{cols}\n)")
            conn.commit()
            print("  created", full)

        tcols = [r[0] for r in cur.execute(
            "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA=? AND TABLE_NAME=? ORDER BY ORDINAL_POSITION",
            SCHEMA, table)]
        df = pd.read_parquet(p)
        extra, missing = set(df.columns) - set(tcols), set(tcols) - set(df.columns)
        if extra or missing:
            print(f"  WARNING {p.stem}: extra={sorted(extra)} missing={sorted(missing)}")
        df = df.reindex(columns=tcols).astype(object)
        df = df.where(df.notna(), None)
        rows = list(df.itertuples(index=False, name=None))

        sql = (f"INSERT INTO {full} ({','.join('[' + c + ']' for c in tcols)}) "
               f"VALUES ({','.join('?' * len(tcols))})")
        try:
            for i in range(0, len(rows), 5000):
                cur.executemany(sql, rows[i:i + 5000])
            cur.execute(f"INSERT INTO {SCHEMA}.load_log (dataset, source_file, row_count) "
                        "VALUES (?,?,?)", table, p.stem, len(rows))
            conn.commit()
        except Exception:
            conn.rollback()
            print("  FAILED on", p.stem)
            raise
        print("  loaded", p.stem, len(rows))

print("Done.")