from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "local-api"))
from vmf_api.server import run

if __name__ == "__main__":
    run()
