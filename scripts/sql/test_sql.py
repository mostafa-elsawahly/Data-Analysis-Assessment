from sql_conn import connect

cur = connect().cursor()
cur.execute("SELECT DB_NAME(), SUSER_NAME()")
print(tuple(cur.fetchone()))

print("Schemas:", [r[0] for r in cur.execute("SELECT name FROM sys.schemas ORDER BY name")])
print("Tables:")
for r in cur.execute("""SELECT s.name, t.name FROM sys.tables t
                        JOIN sys.schemas s ON s.schema_id = t.schema_id ORDER BY 1, 2"""):
    print("  ", r[0], r[1])

for perm in ("CREATE SCHEMA", "CREATE TABLE"):
    ok = cur.execute("SELECT HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', ?)", perm).fetchone()[0]
    print(f"{perm}:", "YES" if ok else "NO")