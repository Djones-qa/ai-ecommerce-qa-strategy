"""
Shared pytest fixtures and configuration.
"""

import os
import time

import pytest
import requests


MOCK_SERVER_URL = os.getenv("MOCK_SERVER_URL", "http://localhost:8000")


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "schema: Output schema validation tests")
    config.addinivalue_line("markers", "hallucination: Hallucination detection tests")
    config.addinivalue_line("markers", "toxicity: Toxicity and safety tests")
    config.addinivalue_line("markers", "contract: Pact contract tests")
    config.addinivalue_line("markers", "slow: Tests that take longer to run")


@pytest.fixture(scope="session", autouse=True)
def verify_mock_server_is_running():
    """
    Session-scoped fixture that checks the mock server is reachable before
    any tests that require it run. Skips server-dependent tests gracefully
    if the server is not available.
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = requests.get(f"{MOCK_SERVER_URL}/v1/health", timeout=5)
            if resp.status_code == 200:
                print(f"\n✓ Mock server is running at {MOCK_SERVER_URL}")
                return
        except requests.exceptions.ConnectionError:
            if attempt < max_retries - 1:
                time.sleep(2)

    pytest.skip(
        f"Mock server not reachable at {MOCK_SERVER_URL}. "
        "Start it with: uvicorn mock_server.app:app --port 8000"
    )
