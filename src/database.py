import pyodbc
from contextlib import contextmanager
from src.config import DB_CONFIG


def build_connection_string():
    return (
        f"DRIVER={{{DB_CONFIG['driver']}}};"
        f"SERVER={DB_CONFIG['server']};"
        f"DATABASE={DB_CONFIG['database']};"
        f"UID={DB_CONFIG['username']};"
        f"PWD={DB_CONFIG['password']};"
    )


@contextmanager
def get_connection():
    conn_str = build_connection_string()
    conn = pyodbc.connect(conn_str)
    try:
        yield conn
    finally:
        conn.close()


def fetch_all(conn, query, params=None):
    cursor = conn.cursor()
    if params:
        cursor.execute(query, params)
    else:
        cursor.execute(query)
    columns = [col[0] for col in cursor.description] if cursor.description else []
    rows = cursor.fetchall()
    return columns, rows


def fetch_dicts(conn, query, params=None):
    columns, rows = fetch_all(conn, query, params)
    return [dict(zip(columns, row)) for row in rows]
