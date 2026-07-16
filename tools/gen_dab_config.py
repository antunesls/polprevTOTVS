import json
import pyodbc

conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=localhost;DATABASE=TOTVS_2510;"
    "UID=TOTVS12;PWD=TOTVS12"
)

TABLES = [
    "AO2990",
    "SYS_USR", "SYS_USR_MODULE", "SYS_USR_ACCESS", "SYS_USR_GROUPS",
    "SYS_GRP_GROUP", "SYS_RULES", "SYS_RULES_FEATURES", "SYS_RULES_BUTTONS",
    "SYS_RULES_GRP_RULES", "SYS_RULES_USR_RULES",
    "MPMENU_MENU", "MPMENU_ITEM", "MPMENU_FUNCTION", "MPMENU_I18N",
]

entities = {}
for table in TABLES:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_NAME=? ORDER BY ORDINAL_POSITION", (table,))
    cols = [r[0] for r in cursor.fetchall()]
    fields = []
    for col in cols:
        is_pk = (col == "R_E_C_N_O_")
        fields.append({"name": col, "primary-key": is_pk})
    entities[table] = {
        "source": {"object": table, "type": "table"},
        "fields": fields,
        "rest": {"enabled": False},
        "permissions": [
            {"role": "anonymous", "actions": [{"action": "read"}]}
        ],
    }
    print(f"  {table}: {len(fields)} fields (PK={len([f for f in fields if f['primary-key']])})")

conn.close()

config = {
    "$schema": "https://github.com/Azure/data-api-builder/releases/download/v2.0.9/dab.draft.schema.json",
    "data-source": {
        "database-type": "mssql",
        "connection-string": "@env('MSSQL_CONNECTION_STRING')",
        "options": {"set-session-context": False},
    },
    "runtime": {
        "rest": {"enabled": False, "path": "/api", "request-body-strict": False},
        "graphql": {"enabled": False, "path": "/graphql", "allow-introspection": True},
        "mcp": {"enabled": True, "path": "/mcp"},
        "host": {
            "cors": {"origins": [], "allow-credentials": False},
            "authentication": {"provider": "Unauthenticated"},
            "mode": "development",
        },
        "telemetry": {
            "open-telemetry": {
                "enabled": True,
                "endpoint": "@env('OTEL_EXPORTER_OTLP_ENDPOINT')",
                "headers": "@env('OTEL_EXPORTER_OTLP_HEADERS')",
                "service-name": "@env('OTEL_SERVICE_NAME')",
            }
        },
    },
    "entities": entities,
}

output_path = r"C:\Users\antunesls\dab-config.json"
with open(output_path, "w") as f:
    json.dump(config, f, indent=2)

total_fields = sum(len(ent["fields"]) for ent in entities.values())
print(f"\nGenerated: {len(entities)} entities, {total_fields} total fields")
print(f"Saved to: {output_path}")
