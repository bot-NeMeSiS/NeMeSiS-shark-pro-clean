from __future__ import annotations

import importlib
import os
import pathlib
import sys
import tempfile

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def app_module():
    os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest")
    os.environ.setdefault("ADMIN_EMAIL", "admin@example.com")
    os.environ.setdefault("ADMIN_PASSWORD", "admin-password")
    os.environ.setdefault("BACKGROUND_JOBS_ENABLED", "false")
    os.environ.setdefault("AUTO_GENERATE_PICKS", "false")
    os.environ.setdefault("AUTO_SEND_TELEGRAM_PICKS", "false")
    os.environ.setdefault("DB_PATH", str(pathlib.Path(tempfile.gettempdir()) / "nemesis_pytest.db"))
    sys.path.insert(0, str(ROOT))
    module = importlib.import_module("app")
    module.app.config.update(TESTING=True)
    return module


@pytest.fixture()
def client(app_module):
    return app_module.app.test_client()
