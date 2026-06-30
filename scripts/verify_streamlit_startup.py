"""Smoke-check Streamlit entry paths (run via: uv run python scripts/verify_streamlit_startup.py)."""
from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_PATH = REPO_ROOT / "src" / "agent_dungeon" / "app.py"
LEVEL_VOICE = REPO_ROOT / "src" / "agent_dungeon" / "level_pages" / "0_Voice.py"
ROOT_APP = REPO_ROOT / "app.py"
PKG_DIR = APP_PATH.parent


def _check_paths() -> None:
    assert APP_PATH.is_file(), f"missing app entry: {APP_PATH}"
    assert LEVEL_VOICE.is_file(), f"missing Voice page: {LEVEL_VOICE}"
    assert not ROOT_APP.is_file(), f"stale root app.py should not exist: {ROOT_APP}"
    assert not (PKG_DIR / "pages").is_dir(), "remove src/agent_dungeon/pages to avoid Streamlit v1 MPA"

    from streamlit.file_util import get_main_script_directory, normalize_path_join

    main = str(APP_PATH.resolve())
    voice = os.path.realpath(
        normalize_path_join(get_main_script_directory(main), "level_pages/0_Voice.py")
    )
    assert Path(voice).is_file(), f"Voice path resolution failed: {voice}"


def _wait_health(port: int, proc: subprocess.Popen[str]) -> None:
    deadline = time.time() + 30
    health_url = f"http://127.0.0.1:{port}/_stcore/health"
    while time.time() < deadline:
        if proc.poll() is not None:
            output = proc.stdout.read() if proc.stdout else ""
            raise RuntimeError(f"Streamlit exited early (code={proc.returncode}).\n{output}")
        try:
            with urllib.request.urlopen(health_url, timeout=2) as resp:
                if resp.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError):
            time.sleep(0.5)
    output = proc.stdout.read() if proc.stdout else ""
    raise RuntimeError(f"Streamlit health check timed out.\n{output}")


def _run_server(cmd: list[str], *, cwd: Path, port: int) -> None:
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        _wait_health(port, proc)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def _check_server_from_repo_root(port: int = 8515) -> None:
    _run_server(
        ["uv", "run", "streamlit", "run", str(APP_PATH), "--server.headless", "true", "--server.port", str(port)],
        cwd=REPO_ROOT,
        port=port,
    )


def _check_agent_dungeon_cli(port: int = 8516) -> None:
    _run_server(
        ["uv", "run", "agent-dungeon", "--server.headless", "true", "--server.port", str(port)],
        cwd=REPO_ROOT,
        port=port,
    )


def _check_manual_cd_trap(port: int = 8517) -> None:
    """Simulates user running from repo root while passing bare app.py (common mistake)."""
    proc = subprocess.Popen(
        ["uv", "run", "streamlit", "run", "app.py", "--server.headless", "true", "--server.port", str(port)],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        raise AssertionError(
            "streamlit run app.py from repo root should fail fast, but server stayed up"
        ) from None
    output = proc.stdout.read() if proc.stdout else ""
    assert proc.returncode != 0, f"expected failure from repo root app.py, got:\n{output}"
    assert "does not exist" in output.lower() or "no such file" in output.lower(), output


def main() -> int:
    _check_paths()
    _check_manual_cd_trap()
    _check_server_from_repo_root()
    _check_agent_dungeon_cli()
    print("verify_streamlit_startup: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
