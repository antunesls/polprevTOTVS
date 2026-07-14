import time
import requests
import urllib3
from src.config import API_CONFIG

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ProtheusAPI:
    def __init__(self, config=None):
        cfg = config or API_CONFIG
        self.base_url = cfg["base_url"].rstrip("/")
        self.token = cfg.get("bearer_token", "")
        self.username = cfg.get("api_username", "")
        self.password = cfg.get("api_password", "")
        self.tenant_id = cfg.get("tenant_id", "")
        self.erp_database = cfg.get("erp_database", "") or time.strftime("%Y%m%d")
        self.erp_module = cfg.get("erp_module", "CFG")
        self.verify_ssl = cfg.get("verify_ssl", False)
        self.timeout = cfg.get("timeout", 30)
        self._expires_at = 0
        self._refresh_token = ""

    def authenticate(self):
        if not self.username or not self.password:
            return False, "Usuario e senha nao configurados."

        url = f"{self.base_url}/api/oauth2/v1/token"
        params = {
            "grant_type": "password",
            "username": self.username,
            "password": self.password,
        }

        try:
            r = requests.post(url, params=params,
                              verify=self.verify_ssl, timeout=self.timeout)
            if r.status_code in (200, 201):
                data = r.json()
                self.token = data.get("access_token", "")
                self._refresh_token = data.get("refresh_token", "")
                expires_in = data.get("expires_in", 3600)
                self._expires_at = time.time() + expires_in - 60

                token_preview = self.token[:30] + "..." if len(self.token) > 30 else self.token
                return True, f"Autenticado ({expires_in}s). Token: {token_preview}"

            if r.status_code == 401:
                return False, "Credenciais invalidas. Verifique usuario e senha."
            return False, f"Erro HTTP {r.status_code}: {r.text[:120]}"

        except requests.exceptions.ConnectionError:
            return False, f"Conexao recusada em {url}. Appserver REST rodando?"
        except Exception as e:
            return False, str(e)

    def _ensure_token(self):
        if self.token and self._expires_at > 0 and time.time() > self._expires_at:
            self.token = ""
            self._expires_at = 0

        if not self.token and self.username and self.password:
            ok, msg = self.authenticate()
            if not ok:
                return False, msg

        if not self.token:
            return False, "Nenhum token disponivel. Configure usuario/senha ou bearer_token."

        return True, ""

    def _headers(self):
        h = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "pt-BR",
            "Connection": "keep-alive",
            "User-Agent": "polprevTOTVS/1.0",
        }
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        if self.tenant_id:
            h["tenantid"] = self.tenant_id
        if self.erp_database:
            h["x-erp-database"] = self.erp_database
        if self.erp_module:
            h["x-erp-module"] = self.erp_module
        return h

    def _get(self, path, params=None):
        token_ok, token_msg = self._ensure_token()
        if not token_ok:
            return {"_error": True, "_status": 0, "_body": token_msg, "_no_token": True}

        url = f"{self.base_url}{path}"
        try:
            r = requests.get(url, headers=self._headers(), params=params or {},
                             verify=self.verify_ssl, timeout=self.timeout)
            if r.status_code in (200, 201):
                try:
                    return r.json()
                except ValueError:
                    return {"_raw": r.text}
            if r.status_code == 401:
                return {"_error": True, "_status": 401, "_body": "Token JWT expirado ou invalido. Reconfigure as credenciais.", "_token_expired": True}
            return {"_error": True, "_status": r.status_code, "_body": r.text}

        except requests.exceptions.ConnectionError as e:
            return {"_error": True, "_status": 0, "_body": str(e), "_conn_refused": True}
        except Exception as e:
            return {"_error": True, "_status": -1, "_body": str(e)}

    def test_connection(self):
        token_ok, token_msg = self._ensure_token()
        if not token_ok:
            return False, token_msg

        result = self._get("/api/framework/v1/FwRestTranslate/privileges", {"language": "pt-br"})
        if result.get("_conn_refused"):
            return False, "Conexao recusada. Verifique se o appserver esta rodando."
        if result.get("_no_token"):
            return False, result.get("_body", "Falha ao obter token.")
        if result.get("_error"):
            if result.get("_status") == 401:
                return False, "Token JWT invalido. Verifique credenciais."
            return False, f"Erro HTTP {result.get('_status')}: {result.get('_body', '')[:120]}"
        return True, f"OK — token valido"

    def test_full_login(self):
        if not self.username or not self.password:
            return False, "Configure usuario e senha primeiro (opcoes B e C)."

        ok, msg = self.authenticate()
        if not ok:
            return False, msg

        ok2, msg2 = self.test_connection()
        return ok2, f"Login: {msg} | API: {msg2}"

    def get_users(self):
        return self._get("/api/framework/getusers",
                         {"keyReturn": "items", "id_field": "USR_ID", "usr_msblql": "0"})

    def get_privilege_translations(self):
        return self._get("/api/framework/v1/FwRestTranslate/privileges",
                         {"language": "pt-br"})

    def get_list_privileges(self):
        return self._get("/api/framework/v1/FwRestTranslate/listprivileges",
                         {"language": "pt-br"})

    def generic_query(self, fields, tables, where=None, pagesize=999):
        params = {"fields": fields, "tables": tables, "pagesize": str(pagesize)}
        if where:
            params["where"] = where
        return self._get("/api/framework/v1/genericQuery", params)

    def get_menu_def(self, rotina):
        return self._get("/api/framework/v1/basicProtheusServices/menudef",
                         {"Rotina": rotina})

    def get_function_users(self, function, user=None, page=1, pageSize=10):
        params = {
            "function": function,
            "page": str(page),
            "pageSize": str(pageSize),
            "usr_msblql": "0",
        }
        if user:
            params["user"] = user
        return self._get("/api/framework/privileges/functions/users", params)

    def get_function_user_privileges(self, user):
        return self._get("/api/framework/privileges/functions/userPrivileges",
                         {"user": user})

    def get_function_user_detail(self, user):
        return self._get("/api/framework/privileges/functions/userDetail",
                         {"user": user})

    def get_function_groups(self):
        return self._get("/api/framework/privileges/functions/groups")

    def get_function_privilege(self, privilege_id):
        return self._get("/api/framework/privileges/functions/privilege",
                         {"privilege": privilege_id})

    def get_function_privilege_linked(self, privilege_id):
        return self._get("/api/framework/privileges/functions/privilegeLinked",
                         {"privilege": privilege_id})

    def get_function_privilege_menu_def(self, privilege_id):
        return self._get("/api/framework/privileges/functions/privilegeMenuDef",
                         {"privilege": privilege_id})

    def get_function_group_menu_def(self, group_id):
        return self._get("/api/framework/privileges/functions/groupMenuDef",
                         {"group": group_id})

    def get_function_group_menu_def_detail(self, group_id):
        return self._get("/api/framework/privileges/functions/groupMenuDefDetail",
                         {"group": group_id})

    def get_function_user_menu_def(self, user):
        return self._get("/api/framework/privileges/functions/userMenuDef",
                         {"user": user})

    def get_function_user_menu_def_detail(self, user):
        return self._get("/api/framework/privileges/functions/userMenuDefDetail",
                         {"user": user})

    def get_dashboard_menu_detail(self, menu, function=None, pagesize=999999):
        params = {"pagesize": str(pagesize), "menu": menu}
        if function:
            params["function"] = function
        return self._get("/api/framework/dashboard/detail/"
                         "totvs.framework.adapter.privileges.menu/mp_menu", params)

    def get_sanitation_totals(self):
        return self._get("/api/framework/privileges/sanitation/totals")

    def get_sanitation_menus_with_privileges(self):
        return self._get("/api/framework/privileges/sanitation/menusWithPrivileges")

    def get_sanitation_users_without_privileges(self):
        return self._get("/api/framework/privileges/sanitation/usersWithoutPrivileges")

    def get_sanitation_users_with_privileges_exclusive(self):
        return self._get("/api/framework/privileges/sanitation/usersWithPrivilegesExclusive")

    def get_sanitation_users_with_privileges_on_profile(self):
        return self._get("/api/framework/privileges/sanitation/usersWithPrivilegesOnProfile")

    def collect_all_sanitation_data(self):
        results = {}
        endpoints = {
            "totals": self.get_sanitation_totals,
            "menusWithPrivileges": self.get_sanitation_menus_with_privileges,
            "usersWithoutPrivileges": self.get_sanitation_users_without_privileges,
            "usersWithPrivilegesExclusive": self.get_sanitation_users_with_privileges_exclusive,
            "usersWithPrivilegesOnProfile": self.get_sanitation_users_with_privileges_on_profile,
        }
        for key, func in endpoints.items():
            results[key] = func()
        return results


def create_api():
    return ProtheusAPI()
