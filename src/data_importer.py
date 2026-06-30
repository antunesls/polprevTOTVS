import json
import sqlite3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


C = {
    "reset": "\033[0m",  "cyan": "\033[96m",
    "green": "\033[92m", "yellow": "\033[93m",
    "red": "\033[91m",   "dim": "\033[2m",
    "bold": "\033[1m",
}
if os.name == "nt":
    os.system("")


def import_to_sqlite(json_path):
    if not os.path.exists(json_path):
        print(f"  {C['red']}Arquivo nao encontrado: {json_path}{C['reset']}")
        return None

    print(f"  {C['cyan']}Carregando {json_path}...{C['reset']}")

    with open(json_path, "r", encoding="utf-8-sig") as f:
        data = json.load(f)

    if not isinstance(data, dict) or not data:
        print(f"  {C['red']}JSON invalido. Esperado: objeto com tabelas.{C['reset']}")
        return None

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    total_rows = 0
    table_count = 0

    for table_name, rows in data.items():
        if not rows or not isinstance(rows, list):
            continue

        first = rows[0]
        if not isinstance(first, dict):
            continue

        columns = list(first.keys())
        if not columns:
            continue

        cols_def = ", ".join(f"[{c}] TEXT" for c in columns)
        create_sql = f"CREATE TABLE {table_name} ({cols_def})"
        conn.execute(create_sql)

        placeholders = ", ".join("?" for _ in columns)
        cols_joined = ", ".join(f"[{c}]" for c in columns)
        insert_sql = f"INSERT INTO {table_name} ({cols_joined}) VALUES ({placeholders})"

        batch = []
        for row in rows:
            vals = []
            for c in columns:
                v = row.get(c)
                if v is None:
                    vals.append("")
                else:
                    s = str(v).strip()
                    vals.append(s if s else str(v))
            batch.append(vals)
        conn.executemany(insert_sql, batch)

        total_rows += len(rows)
        table_count += 1

    conn.commit()

    print(f"  {C['green']}Importado: {table_count} tabelas, {total_rows} registros{C['reset']}")
    return conn


def import_and_set_offline(json_path):
    from src.database import set_offline_connection

    conn = import_to_sqlite(json_path)
    if conn is None:
        return False

    set_offline_connection(conn)
    return True
