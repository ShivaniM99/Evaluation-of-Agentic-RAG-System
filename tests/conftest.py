import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("OPENAI_API_KEY", "sk-test")

import pytest


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    from observability import store
    monkeypatch.setattr(store, "DB_PATH", str(tmp_path / "t.db"))
    return store.DB_PATH
