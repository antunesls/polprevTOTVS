import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run
from src import config as cfg


class FileLoggerTest(unittest.TestCase):
    def test_tee_stream_writes_console_and_file_without_ansi_in_log(self):
        from src.file_logger import TeeStream

        console = io.StringIO()
        logfile = io.StringIO()
        tee = TeeStream(console, logfile, strip_colors=True)

        tee.write("\033[92mOK\033[0m teste\n")
        tee.flush()

        self.assertEqual(console.getvalue(), "\033[92mOK\033[0m teste\n")
        self.assertEqual(logfile.getvalue(), "OK teste\n")

    def test_start_file_logging_creates_session_log_file(self):
        from src.file_logger import start_file_logging, stop_file_logging

        original_stdout = os.sys.stdout
        original_stderr = os.sys.stderr
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                state = start_file_logging(tmpdir, prefix="polprev-test")
                try:
                    print("linha de teste")
                finally:
                    stop_file_logging(state)

                log_files = list(Path(tmpdir).glob("polprev-test-*.log"))
                self.assertEqual(len(log_files), 1)
                content = log_files[0].read_text(encoding="utf-8")
                self.assertIn("linha de teste", content)
        finally:
            os.sys.stdout = original_stdout
            os.sys.stderr = original_stderr


class RunIntegrationTest(unittest.TestCase):
    def test_initialize_runtime_logging_starts_file_logging_when_enabled(self):
        original_enabled = cfg.FILE_LOGGING_ENABLED if hasattr(cfg, "FILE_LOGGING_ENABLED") else True
        original_log_dir = cfg.LOG_DIR if hasattr(cfg, "LOG_DIR") else ""
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                cfg.FILE_LOGGING_ENABLED = True
                cfg.LOG_DIR = tmpdir

                state = run.initialize_runtime_logging()
                try:
                    self.assertIsNotNone(state)
                    self.assertTrue(Path(state["path"]).exists())
                finally:
                    run.shutdown_runtime_logging(state)
        finally:
            cfg.FILE_LOGGING_ENABLED = original_enabled
            cfg.LOG_DIR = original_log_dir

    def test_initialize_runtime_logging_skips_when_disabled(self):
        original_enabled = cfg.FILE_LOGGING_ENABLED if hasattr(cfg, "FILE_LOGGING_ENABLED") else True
        try:
            cfg.FILE_LOGGING_ENABLED = False
            state = run.initialize_runtime_logging()
            self.assertIsNone(state)
        finally:
            cfg.FILE_LOGGING_ENABLED = original_enabled


if __name__ == "__main__":
    unittest.main()
