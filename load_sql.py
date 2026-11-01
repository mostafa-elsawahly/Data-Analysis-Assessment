import os, io, re, pyodbc, pandas as pd, pyarrow as pa, pyarrow.parquet as pq
from azure.storage.blob import BlobServiceClient

SCHEMA = "opm"
DATASETS = {"Accessions": "accessions", "Separations": "separations"}

conn = pyodbc.connect(
    "Driver={ODBC Driver 18 for SQL Server};"
    f"Server=tcp:{os.environ['SQL_SERVER']},1433;Database={os.environ['SQL_DB']};"
    f"Uid={os.environ['SQL_USER']};Pwd={os.environ['SQL_PASSWORD']};"
    "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=90;")
cur = conn.cursor()
cur.fast_executemany = True

container = BlobServiceClient.from_connection_string(
    os.environ["AZURE_STORAGE_CONNECTION_STRING"]).get_container_client("incoming")

def sql_type(t):
    if pa.types.is_integer(t): return "INT"
    if pa.types.is_floating(t): return "FLOAT"
    if pa.types.is_timestamp(t) or pa.types.is_date(t): return "DATE"
    if pa.types.is_boolean(t): return "BIT"
    return "NVARCHAR(500)"

cur.execute(f"IF SCHEMA_ID('{SCHEMA}') IS NULL EXEC('CREATE SCHEMA {SCHEMA}')")
cur.execute(f"""IF OBJECT_ID('{SCHEMA}.load_log') IS NULL
CREATE TABLE {SCHEMA}.load_log (
  dataset NVARCHAR(30), source_file NVARCHAR(100) PRIMARY KEY,
  row_count INT, loaded_at DATETIME2 DEFAULT SYSUTCDATETIME())""")
conn.commit()

all_blobs = [b.name for b in container.list_blobs() if b.name.endswith(".parquet")]

for folder, table in DATASETS.items():
    full = f"{SCHEMA}.{table}"
    names = sorted(n for n in all_blobs if re.match(rf"\d{{4}}/{folder}/", n))
    done = {r[0] for r in cur.execute(
        f"SELECT source_file FROM {SCHEMA}.load_log WHERE dataset=?", table)}
    print(f"{folder}: {len(names)} files in Azure, {len(done)} already loaded")

    for name in names:
        src = os.path.basename(name)[:-len(".parquet")]
        if src in done:
            continue
        data = container.download_blob(name).readall()

        if cur.execute("SELECT OBJECT_ID(?)", full).fetchone()[0] is None:
            schema = pq.read_schema(io.BytesIO(data))
            cols = ",\n".join(f"[{f.name}] {sql_type(f.type)} NULL" for f in schema)
            cur.execute(f"CREATE TABLE {full} (\n{cols}\n)")
            conn.commit()
            print("  created table", full)

        tcols = [r[0] for r in cur.execute(
            "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA=? AND TABLE_NAME=? ORDER BY ORDINAL_POSITION",
            SCHEMA, table)]

        df = pd.read_parquet(io.BytesIO(data))
        extra = set(df.columns) - set(tcols)
        missing = set(tcols) - set(df.columns)
        if extra or missing:
            print(f"  WARNING {src}: extra={sorted(extra)} missing={sorted(missing)}")
        df = df.reindex(columns=tcols)
        df = df.astype(object).where(df.notna(), None)
        rows = list(df.itertuples(index=False, name=None))

        sql = (f"INSERT INTO {full} ({','.join('['+c+']' for c in tcols)}) "
               f"VALUES ({','.join('?'*len(tcols))})")
        try:
            for i in range(0, len(rows), 5000):
                cur.executemany(sql, rows[i:i + 5000])
            cur.execute(f"INSERT INTO {SCHEMA}.load_log (dataset, source_file, row_count) "
                        "VALUES (?,?,?)", table, src, len(rows))
            conn.commit()
        except Exception:
            conn.rollback()
            print("  FAILED on", src)
            raise
        print("  loaded", src, len(rows))

    cur.execute(f"""IF NOT EXISTS (SELECT 1 FROM sys.indexes
        WHERE name='ix_{table}_ym' AND object_id=OBJECT_ID('{full}'))
        CREATE INDEX ix_{table}_ym ON {full} (data_year, data_month)""")
    conn.commit()

print("Done.")
