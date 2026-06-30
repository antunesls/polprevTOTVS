import json
import os

DB_CONFIG = {
    "server": "localhost",
    "database": "TOTVS_2510",
    "username": "TOTVS12",
    "password": "TOTVS12",
    "driver": "ODBC Driver 17 for SQL Server",
}

PRIVILEGE_MODE = "per_user"

EMPRESA_NAME = ""

OUTPUT_DIR = "output"

CONFIG_USER_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config_user.json")

SCHEMA_TABLES = [
    "SYS_USR",
    "SYS_USR_MODULE",
    "SYS_USR_GROUPS",
    "SYS_USR_ACCESS",
    "SYS_GRP_GROUP",
    "SYS_RULES",
    "SYS_RULES_FEATURES",
    "SYS_RULES_BUTTONS",
    "SYS_RULES_GRP_RULES",
    "SYS_RULES_USR_RULES",
    "MPMENU_MENU",
    "MPMENU_ITEM",
    "MPMENU_FUNCTION",
    "MPMENU_I18N",
]


def load_user_config():
    if not os.path.exists(CONFIG_USER_PATH):
        return
    try:
        with open(CONFIG_USER_PATH, "r", encoding="utf-8") as f:
            user_cfg = json.load(f)
        DB_CONFIG.update(user_cfg.get("db", {}))
        globals()["PRIVILEGE_MODE"] = user_cfg.get("privilege_mode", "per_user")
        globals()["EMPRESA_NAME"] = user_cfg.get("empresa_name", "")
    except Exception:
        pass


def save_user_config():
    data = {
        "db": {k: DB_CONFIG[k] for k in ("server", "database", "username", "password", "driver")},
        "privilege_mode": PRIVILEGE_MODE,
        "empresa_name": EMPRESA_NAME,
    }
    with open(CONFIG_USER_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
