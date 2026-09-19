#!/usr/bin/env python3
"""Thin wrapper kept for backward compatibility.

Delegates to aditsystem_backend.cli.bootstrap_admin, which is now the
authoritative implementation. See docs/bootstrap_admin.md for usage.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from aditsystem_backend.cli.bootstrap_admin import _run

if __name__ == "__main__":
    sys.exit(asyncio.run(_run()))
