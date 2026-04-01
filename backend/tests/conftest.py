"""
Pytest configuration and fixtures for DevTrack backend tests.
"""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add project root to path so we can import backend modules
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def pytest_configure(config):
    """Ensure config is loaded before tests that need it."""
    pass


@pytest.fixture(scope="session", autouse=True)
def _block_env_file_load():
    """Prevent load_dotenv from opening .env (which may be a named pipe / FIFO).

    On this machine .env is a FIFO; open() on a FIFO blocks indefinitely.
    Mark the config as already-loaded so _load_env() is a no-op for all tests.
    This fixture applies to the entire test session before any imports.
    """
    import backend.config as _cfg
    _cfg._env_loaded = True
    yield
    # Reset so any test that explicitly needs real env loading can do so.
    _cfg._env_loaded = False
