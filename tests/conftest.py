"""Pytest path setup for shared integration helpers."""

from __future__ import annotations

import sys
from pathlib import Path

_INTEGRATION_DIR = Path(__file__).resolve().parent / "integration"
if str(_INTEGRATION_DIR) not in sys.path:
    sys.path.insert(0, str(_INTEGRATION_DIR))
