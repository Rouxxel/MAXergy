"""Environment access for MAXergy settings (all variables use the `MAXERGY_` prefix)."""

from __future__ import annotations

import os


def env(name: str, default: str = "") -> str:
    """Return MAXERGY_<name>, stripped (default when unset)."""
    return os.environ.get(f"MAXERGY_{name}", default).strip()
