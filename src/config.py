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

LLM_API_KEY = ""
LLM_BASE_URL = "https://openrouter.ai/api/v1"
LLM_MODEL = "openai/gpt-4o-mini"

API_CONFIG = {
    "enabled": False,
    "base_url": "https://localhost:1234/app-root",
    "api_username": "",
    "api_password": "",
    "bearer_token": "",
    "tenant_id": "",
    "erp_database": "",
    "erp_module": "CFG",
    "verify_ssl": False,
    "timeout": 30,
}

DATA_MODE = "live"

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
    "SYS_RULES_TRANSACT",
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
        globals()["LLM_API_KEY"] = user_cfg.get("llm_api_key", "")
        globals()["LLM_BASE_URL"] = user_cfg.get("llm_base_url", "https://openrouter.ai/api/v1")
        globals()["LLM_MODEL"] = user_cfg.get("llm_model", "openai/gpt-4o-mini")
        api_cfg = user_cfg.get("api", {})
        if api_cfg:
            API_CONFIG.update(api_cfg)
    except Exception:
        pass


def save_user_config():
    data = {
        "db": {k: DB_CONFIG[k] for k in ("server", "database", "username", "password", "driver")},
        "privilege_mode": PRIVILEGE_MODE,
        "empresa_name": EMPRESA_NAME,
        "llm_api_key": LLM_API_KEY,
        "llm_base_url": LLM_BASE_URL,
        "llm_model": LLM_MODEL,
        "api": {
            "enabled": API_CONFIG["enabled"],
            "base_url": API_CONFIG["base_url"],
            "api_username": API_CONFIG["api_username"],
            "api_password": API_CONFIG["api_password"],
            "bearer_token": API_CONFIG["bearer_token"],
            "tenant_id": API_CONFIG["tenant_id"],
            "erp_database": API_CONFIG["erp_database"],
            "erp_module": API_CONFIG["erp_module"],
            "verify_ssl": API_CONFIG["verify_ssl"],
            "timeout": API_CONFIG["timeout"],
        },
    }
    with open(CONFIG_USER_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
