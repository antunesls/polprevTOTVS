import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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


if __name__ == "__main__":
    unittest.main()
