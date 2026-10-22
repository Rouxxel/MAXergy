"""Shared pytest setup for all backend tests (backend/tests and backend/src/tests).

The config loaders resolve paths relative to the backend directory, so tests run from there
regardless of where pytest is invoked.
"""

import json
import os
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent
FIXTURES_DIR = BACKEND_DIR / "tests" / "fixtures"

os.chdir(BACKEND_DIR)
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture
def assessment_dict() -> dict:
    """The canonical example assessment (documentation/data/model_input1.json)."""
    return json.loads((FIXTURES_DIR / "model_input1.json").read_text())
