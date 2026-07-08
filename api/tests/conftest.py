import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("OAUTH_DISABLED", "true")


@pytest.fixture
def client() -> TestClient:
    from app.main import create_app

    return TestClient(create_app())
