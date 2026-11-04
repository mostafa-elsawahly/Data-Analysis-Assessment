import os
from sql_conn import connect

SCHEMA = os.environ.get("SQL_SCHEMA", "opm")
cur = connect().cursor()

tables = [r[0] for r in cur.execute(
    "SELECT name FROM sys.tables WHERE schema_id = SCHEMA_ID(?) AND name <> 'load_log'",
    SCHEMA)]
print("Tables in", SCHEMA, ":", tables)

for t in tables:
    print(f"\n=== {SCHEMA}.{t} ===")
    print("year | months | rows | sum(count)")
    for r in cur.execute(f"""SELECT data_year, COUNT(DISTINCT data_month), COUNT(*),
                                    SUM(CAST([count] AS BIGINT))
                             FROM {SCHEMA}.{t} GROUP BY data_year ORDER BY data_year"""):
        print(r[0], "|", r[1], "|", r[2], "|", r[3])

    bad = cur.execute(f"""SELECT l.source_file, l.row_count, COUNT(x.source_file)
        FROM {SCHEMA}.load_log l
        LEFT JOIN {SCHEMA}.{t} x ON x.source_file = l.source_file
        WHERE l.dataset = ?
        GROUP BY l.source_file, l.row_count
        HAVING l.row_count <> COUNT(x.source_file)""", t).fetchall()
    print("Files whose row count in the DB differs from the file:", len(bad))
    for r in bad:
        print("  ", tuple(r))