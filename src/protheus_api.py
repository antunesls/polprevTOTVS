import requests
import urllib3
from src.config import API_CONFIG

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ProtheusAPI:
    def __init__(self, config=None):
        cfg = config or API_CONFIG
        self.base_url = cfg["base_url"].rstrip("/")
        self.token = cfg["bearer_token"]
        self.tenant_id = cfg["tenant_id"]
        self.erp_database = cfg["erp_database"]
        self.erp_module = cfg["erp_module"]
        self.verify_ssl = cfg["verify_ssl"]
        self.timeout = cfg["timeout"]

    def _headers(self):
        h = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "pt-BR",
            "Authorization": f"Bearer {self.token}",
            "Connection": "keep-alive",
            "User-Agent": "polprevTOTVS/1.0",
        }
        if self.tenant_id:
            h["tenantid"] = self.tenant_id
        if self.erp_database:
            h["x-erp-database"] = self.erp_database
        if self.erp_module:
            h["x-erp-module"] = self.erp_module
        return h

    def _get(self, path, params=None):
        url = f"{self.base_url}{path}"
        try:
            r = requests.get(url, headers=self._headers(), params=params or {},
                             verify=self.verify_ssl, timeout=self.timeout)
            if r.status_code == 200:
                try:
                    return r.json()
                except ValueError:
                    return {"_raw": r.text}
            return {"_error": True, "_status": r.status_code, "_body": r.text}
        except requests.exceptions.ConnectionError as e:
            return {"_error": True, "_status": 0, "_body": str(e), "_conn_refused": True}
        except Exception as e:
            return {"_error": True, "_status": -1, "_body": str(e)}

    def test_connection(self):
        result = self._get("/api/framework/v1/FwRestTranslate/privileges", {"language": "pt-br"})
        if result.get("_conn_refused"):
            return False, "Conexao recusada. Verifique se o appserver esta rodando."
        if result.get("_error"):
            if result.get("_status") == 401:
                return False, "Token JWT invalido ou expirado. Atualize o bearer_token."
            return False, f"Erro HTTP {result.get('_status')}: {result.get('_body', '')[:120]}"
        return True, "OK"

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
