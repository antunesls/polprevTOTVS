from src.database import get_connection, fetch_dicts


def discover_columns_for_tables(tables, conn=None):
    close_after = False
    if conn is None:
        conn_ctx = get_connection()
        conn = conn_ctx.__enter__()
        close_after = True

    try:
        schema = {}
        for table in tables:
            try:
                rows = fetch_dicts(conn, """
                    SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_NAME = ?
                    ORDER BY ORDINAL_POSITION
                """, (table,))
                if rows:
                    schema[table] = rows
                else:
                    schema[table] = None
            except Exception:
                schema[table] = None
        return schema
    finally:
        if close_after:
            conn_ctx.__exit__(None, None, None)


def get_columns_list(schema, table):
    if table not in schema or schema[table] is None:
        return []
    return [col["COLUMN_NAME"] for col in schema[table]]


def column_exists(schema, table, candidate_names):
    cols = get_columns_list(schema, table)
    for name in candidate_names:
        if name in cols:
            return name
    return None


def print_schema_summary(schema):
    G = "\033[92m"; Y = "\033[93m"; D = "\033[2m"; R = "\033[0m"
    print(f"\n  {G}Tabelas encontradas no banco:{R}")
    for table, cols in schema.items():
        if cols is None:
            print(f"    {Y}[AUSENTE]{R} {table}")
        else:
            col_names = [c["COLUMN_NAME"] for c in cols]
            print(f"    {D}{table}{R} ({len(cols)} cols): {', '.join(col_names[:8])}{'...' if len(cols) > 8 else ''}")
    print()
