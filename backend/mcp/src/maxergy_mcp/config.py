"""Environment access for MAXergy settings.

Settings use the `MAXERGY_` prefix. The pre-rename prefix `MAXNERGY_` is still read as a
fallback so existing Railway deployments keep working during the migration; a one-time
warning is printed when it is used. The fallback will be removed once all deployments use
the MAXERGY_ names.
"""

from __future__ import annotations

import os
import sys

_LEGACY_PREFIX = "MAXNERGY_"
_warned: set[str] = set()


def env(name: str, default: str = "") -> str:
    """Return MAXERGY_<name> (stripped), falling back to the deprecated MAXNERGY_<name>."""
    value = os.environ.get(f"MAXERGY_{name}")
    if value is None:
        value = os.environ.get(f"{_LEGACY_PREFIX}{name}")
        if value is not None and name not in _warned:
            _warned.add(name)
            print(
                f"[maxergy] {_LEGACY_PREFIX}{name} is deprecated — rename it to MAXERGY_{name}.",
                file=sys.stderr,
            )
    return (value if value is not None else default).strip()
