"""CLI entry: always launch Streamlit with the package app path."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_PKG_DIR = Path(__file__).resolve().parent
_APP = _PKG_DIR / "app.py"


def main() -> None:
    if not _APP.is_file():
        raise SystemExit(f"找不到 Streamlit 入口：{_APP}")
    code = subprocess.call(
        [sys.executable, "-m", "streamlit", "run", str(_APP), *sys.argv[1:]],
        cwd=str(_PKG_DIR),
    )
    raise SystemExit(code)
