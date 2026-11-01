import os, pyodbc

conn = pyodbc.connect(
    "Driver={ODBC Driver 18 for SQL Server};"
    f"Server=tcp:{os.environ['SQL_SERVER']},1433;Database={os.environ['SQL_DB']};"
    f"Uid={os.environ['SQL_USER']};Pwd={os.environ['SQL_PASSWORD']};"
    "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=90;")
cur = conn.cursor()

for t in ["accessions", "separations"]:
    print(f"\n=== opm.{t} ===")
    print("year | files | rows | sum(count)")
    for r in cur.execute(f"""
        SELECT data_year, COUNT(DISTINCT data_month), COUNT(*), SUM(CAST([count] AS BIGINT))
        FROM opm.{t} GROUP BY data_year ORDER BY data_year"""):
        print(r[0], "|", r[1], "|", r[2], "|", r[3])

    bad = cur.execute(f"""
        SELECT l.source_file, l.row_count, COUNT(x.source_file)
        FROM opm.load_log l LEFT JOIN opm.{t} x ON x.source_file = l.source_file
        WHERE l.dataset = '{t}'
        GROUP BY l.source_file, l.row_count
        HAVING l.row_count <> COUNT(x.source_file)""").fetchall()
    print("ملفات عدد صفوفها في الداتا بيس مختلف عن الملف:", len(bad))
    for r in bad:
        print("  ", tuple(r))
