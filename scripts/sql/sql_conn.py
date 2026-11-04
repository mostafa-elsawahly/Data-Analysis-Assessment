import os, pyodbc

def connect():
    return pyodbc.connect(
        "Driver={ODBC Driver 18 for SQL Server};"
        f"Server=tcp:{os.environ['SQL_SERVER']},{os.environ.get('SQL_PORT', '1433')};"
        f"Database={os.environ['SQL_DB']};"
        f"UID={os.environ['SQL_USER']};PWD={os.environ['SQL_PASSWORD']};"
        "Encrypt=yes;TrustServerCertificate=yes;Connection Timeout=30;"
    )