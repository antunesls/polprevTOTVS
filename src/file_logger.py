import os
import re
import sys
from datetime import datetime


ANSI_RE = re.compile(r"\033\[[0-9;]*m")


def strip_ansi(text):
    return ANSI_RE.sub("", text)


class TeeStream:
    def __init__(self, console_stream, log_stream, strip_colors=True):
        self.console_stream = console_stream
        self.log_stream = log_stream
        self.strip_colors = strip_colors
        self.encoding = getattr(console_stream, "encoding", "utf-8")

    def write(self, text):
        if not isinstance(text, str):
            text = str(text)
        self.console_stream.write(text)
        self.log_stream.write(strip_ansi(text) if self.strip_colors else text)
        return len(text)

    def flush(self):
        self.console_stream.flush()
        self.log_stream.flush()

    def isatty(self):
        return getattr(self.console_stream, "isatty", lambda: False)()


def start_file_logging(log_dir, prefix="polprev", strip_colors=True):
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_path = os.path.join(log_dir, f"{prefix}-{timestamp}.log")
    log_stream = open(log_path, "w", encoding="utf-8", newline="")

    state = {
        "path": log_path,
        "log_stream": log_stream,
        "stdout": sys.stdout,
        "stderr": sys.stderr,
    }
    sys.stdout = TeeStream(sys.stdout, log_stream, strip_colors=strip_colors)
    sys.stderr = TeeStream(sys.stderr, log_stream, strip_colors=strip_colors)
    return state


def stop_file_logging(state):
    if not state:
        return
    if state.get("closed"):
        return

    current_stdout = sys.stdout
    current_stderr = sys.stderr
    try:
        if current_stdout:
            current_stdout.flush()
        if current_stderr and current_stderr is not current_stdout:
            current_stderr.flush()
    finally:
        sys.stdout = state["stdout"]
        sys.stderr = state["stderr"]
        state["log_stream"].close()
        state["closed"] = True
