from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
if not PYTHON.exists():
    raise SystemExit("Missing .venv. Run the dependency install step first.")

cmd = [
    str(PYTHON),
    "-m",
    "uvicorn",
    "vmf_api.fastapi_app:app",
    "--app-dir",
    "apps/local-api",
    "--host",
    "127.0.0.1",
    "--port",
    "17860",
]
raise SystemExit(subprocess.call(cmd, cwd=str(ROOT)))
