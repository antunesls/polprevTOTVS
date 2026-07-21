import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import run
from src import config


class ConfigTest(unittest.TestCase):
    def test_save_and_load_preserve_ignore_single_user_departments_flag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config_user.json"
            original_flag = config.IGNORE_SINGLE_USER_DEPARTMENTS

            with patch("src.config.CONFIG_USER_PATH", str(config_path)):
                config.IGNORE_SINGLE_USER_DEPARTMENTS = False
                config.save_user_config()

                saved = json.loads(config_path.read_text(encoding="utf-8"))
                self.assertFalse(saved["ignore_single_user_departments"])

                config.IGNORE_SINGLE_USER_DEPARTMENTS = True
                config.load_user_config()

                self.assertFalse(config.IGNORE_SINGLE_USER_DEPARTMENTS)

            config.IGNORE_SINGLE_USER_DEPARTMENTS = original_flag

    def test_save_and_load_preserve_extended_parameters(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config_user.json"
            original_values = {
                "cluster_similarity_threshold": config.CLUSTER_SIMILARITY_THRESHOLD,
                "min_cluster_size": config.MIN_CLUSTER_SIZE,
                "file_logging_enabled": config.FILE_LOGGING_ENABLED,
                "log_dir": config.LOG_DIR,
                "api": dict(config.API_CONFIG),
            }

            with patch("src.config.CONFIG_USER_PATH", str(config_path)):
                config.CLUSTER_SIMILARITY_THRESHOLD = 0.65
                config.MIN_CLUSTER_SIZE = 3
                config.FILE_LOGGING_ENABLED = False
                config.LOG_DIR = "output/meus_logs"
                config.API_CONFIG.update({
                    "enabled": True,
                    "bearer_token": "token123",
                    "erp_database": "99",
                    "erp_module": "FAT",
                    "verify_ssl": True,
                    "timeout": 45,
                })
                config.save_user_config()

                saved = json.loads(config_path.read_text(encoding="utf-8"))
                self.assertEqual(saved["cluster_similarity_threshold"], 0.65)
                self.assertEqual(saved["min_cluster_size"], 3)
                self.assertFalse(saved["file_logging_enabled"])
                self.assertEqual(saved["log_dir"], "output/meus_logs")
                self.assertTrue(saved["api"]["enabled"])
                self.assertEqual(saved["api"]["bearer_token"], "token123")
                self.assertEqual(saved["api"]["erp_database"], "99")
                self.assertEqual(saved["api"]["erp_module"], "FAT")
                self.assertTrue(saved["api"]["verify_ssl"])
                self.assertEqual(saved["api"]["timeout"], 45)

                config.CLUSTER_SIMILARITY_THRESHOLD = 0.4
                config.MIN_CLUSTER_SIZE = 2
                config.FILE_LOGGING_ENABLED = True
                config.LOG_DIR = "output/logs"
                config.API_CONFIG.update({
                    "enabled": False,
                    "bearer_token": "",
                    "erp_database": "",
                    "erp_module": "CFG",
                    "verify_ssl": False,
                    "timeout": 30,
                })

                config.load_user_config()

                self.assertEqual(config.CLUSTER_SIMILARITY_THRESHOLD, 0.65)
                self.assertEqual(config.MIN_CLUSTER_SIZE, 3)
                self.assertFalse(config.FILE_LOGGING_ENABLED)
                self.assertEqual(config.LOG_DIR, "output/meus_logs")
                self.assertTrue(config.API_CONFIG["enabled"])
                self.assertEqual(config.API_CONFIG["bearer_token"], "token123")
                self.assertEqual(config.API_CONFIG["erp_database"], "99")
                self.assertEqual(config.API_CONFIG["erp_module"], "FAT")
                self.assertTrue(config.API_CONFIG["verify_ssl"])
                self.assertEqual(config.API_CONFIG["timeout"], 45)

            config.CLUSTER_SIMILARITY_THRESHOLD = original_values["cluster_similarity_threshold"]
            config.MIN_CLUSTER_SIZE = original_values["min_cluster_size"]
            config.FILE_LOGGING_ENABLED = original_values["file_logging_enabled"]
            config.LOG_DIR = original_values["log_dir"]
            config.API_CONFIG.clear()
            config.API_CONFIG.update(original_values["api"])

    def test_parametrization_menu_shows_extended_parameters(self):
        original_mode = config.PRIVILEGE_MODE
        output = StringIO()

        with patch("run.cfg.PRIVILEGE_MODE", "organizational_layer"), \
             patch("run.input", return_value="0"), \
             patch("run.cls"), \
             redirect_stdout(output):
            run.menu_parametrizacao()

        text = output.getvalue()

        for expected in (
            "Min. depto",
            "Threshold Jaccard",
            "Tam. conjunto",
            "Ignorar grupos",
            "API ativa",
            "Bearer Token",
            "ERP Database",
            "ERP Modulo",
            "Verify SSL",
            "Timeout API",
            "Log arquivo",
            "Diretorio logs",
        ):
            self.assertIn(expected, text)

        config.PRIVILEGE_MODE = original_mode

    def test_save_and_load_ignored_user_group_ids(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config_user.json"
            original_ids = list(config.IGNORED_USER_GROUP_IDS)

            with patch("src.config.CONFIG_USER_PATH", str(config_path)):
                config.IGNORED_USER_GROUP_IDS = ["000000", "000123"]
                config.save_user_config()

                saved = json.loads(config_path.read_text(encoding="utf-8"))
                self.assertEqual(saved["ignored_user_group_ids"], ["000000", "000123"])

                config.IGNORED_USER_GROUP_IDS = ["000000"]
                config.load_user_config()

                self.assertEqual(config.IGNORED_USER_GROUP_IDS, ["000000", "000123"])

            config.IGNORED_USER_GROUP_IDS = original_ids

    def test_ignored_user_group_ids_default_is_admin(self):
        self.assertEqual(config.IGNORED_USER_GROUP_IDS, ["000000"])

    def test_save_ignored_user_group_ids_strips_and_filters_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config_user.json"
            original_ids = list(config.IGNORED_USER_GROUP_IDS)

            with patch("src.config.CONFIG_USER_PATH", str(config_path)):
                config.IGNORED_USER_GROUP_IDS = [" 000000 ", "", "000999", " "]
                config.save_user_config()

                saved = json.loads(config_path.read_text(encoding="utf-8"))
                self.assertEqual(saved["ignored_user_group_ids"], ["000000", "000999"])

            config.IGNORED_USER_GROUP_IDS = original_ids


if __name__ == "__main__":
    unittest.main()
