import os, sys, functools, tiktoken, subprocess, re

from pathlib import Path

@functools.lru_cache(maxsize=1)

def _detect_refresh_rate() -> float:
    try:
        if sys.platform.startswith("win"):
            import ctypes
            user32, gdi32 = ctypes.windll.user32, ctypes.windll.gdi32
            hdc = user32.GetDC(0)
            hz = gdi32.GetDeviceCaps(hdc, 116)
            user32.ReleaseDC(0, hdc)
            return float(hz)
        if sys.platform.startswith("darwin"):
            out = subprocess.check_output(["system_profiler", "SPDisplaysDataType"]).decode()
            m = re.search(r"Refresh Rate:\s*(\d+)", out)
            return float(m.group(1)) if m else 0.0
        out = subprocess.check_output(["xrandr", "--current"]).decode()
        m = re.search(r"\s(\d+(?:\.\d+)?)\s*Hz", out)
        return float(m.group(1)) if m else 0.0
    except:
        return 0.0

def _env_rate() -> float:
    try:
        v = float(os.getenv("CM_REFRESH_HZ", "0"))
        return v if v >= 60 else 0.0
    except:
        return 0.0

@functools.lru_cache(maxsize=1)

def get_refresh_rate() -> float:
    return _env_rate() or _detect_refresh_rate() or 144.0

def get_cli_refresh_interval() -> float:
    return 1.0 / max(240.0, get_refresh_rate())

STATE_FILE = os.path.join(

    (os.getenv("APPDATA") or Path.home()) if sys.platform.startswith("win") else (os.getenv("XDG_STATE_HOME") or Path.home() / ".codemap"),
    "CodeMap",
    "__tree_state__",

)

SNAPSHOT_DIR = os.path.join(

    (os.getenv("APPDATA") or Path.home()) if sys.platform.startswith("win") else (os.getenv("XDG_DATA_HOME") or Path.home() / ".local/share"),
    "CodeMap",
    "snapshots",

)

os.makedirs(SNAPSHOT_DIR, exist_ok=True)

SUCCESS_MESSAGE_DURATION = 1.0

CLI_REFRESH_INTERVAL = get_cli_refresh_interval()

IGNORED_PATTERNS = [

    "__pycache__", "node_modules", "dist", "build", "venv", ".git", ".svn", ".hg",
    ".idea", ".vscode", ".env", ".DS_Store", "Thumbs.db", ".bak", ".tmp",
    "desktop.ini", ".log", ".db", ".key", ".pyc", ".exe", ".dll", ".so",
    ".dylib", "__tree_state__",

]

ALLOWED_EXTENSIONS = [

    ".py", ".pyi", ".pyc", ".pyo", ".pyd", ".txt", ".md", ".rst", ".docx", ".pdf",
    ".odt", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".sh", ".bash", ".zsh",
    ".csh", ".ksh", ".bat", ".cmd", ".ps1", ".vbs", ".js", ".ts", ".tsx", ".jsx",
    ".mjs", ".cjs", ".c", ".cpp", ".h", ".hpp", ".cs", ".go", ".rs", ".swift",
    ".vb", ".fs", ".sql", ".html", ".htm", ".css", ".scss", ".sass", ".less",
    ".xml",

]

COPY_FORMAT_PRESETS = {

    "blocks": "{path}:\n\"\"\"\n{content}\n\"\"\"\n",
    "lines": "{path}: {content}\n",
    "raw": "{content}\n",
    "optimized": "{path}\n```{language}\n{content}\n```\n",
    "compact": "```{language} {path}\n{content}\n```",
    "dash": "{path}\n---\n{language}\n{content}\n---\n",

}

SCROLL_SPEED = {"normal": 1, "accelerated": 5}

MAX_TREE_DEPTH = 10

INPUT_TIMEOUT = CLI_REFRESH_INTERVAL

CLEANUP_PATTERNS = ["__pycache__", "*.pyc", "*.pyo", "*.pyd", ".coverage", ".pytest_cache", ".hypothesis", "*.so", "*.c", "*.o"]

CLEANUP_OPTIONS = {"enabled": True, "recursive": True, "follow_symlinks": False, "delete_empty_dirs": False}

ENCODING = tiktoken.encoding_for_model("gpt-4o")

def count_tokens(content: str) -> int:
    return len(ENCODING.encode(content))

__all__ = [

    "STATE_FILE", "SNAPSHOT_DIR", "SUCCESS_MESSAGE_DURATION", "CLI_REFRESH_INTERVAL",
    "IGNORED_PATTERNS", "ALLOWED_EXTENSIONS", "COPY_FORMAT_PRESETS", "SCROLL_SPEED",
    "MAX_TREE_DEPTH", "INPUT_TIMEOUT", "count_tokens", "CLEANUP_PATTERNS",
    "CLEANUP_OPTIONS", "get_refresh_rate", "get_cli_refresh_interval",

]
