"""
Pact Consumer Contract Test
-----------------------------
Defines the contract from the consumer's perspective (e.g., the frontend or
a downstream microservice). Specifies exactly what requests it will send and
what response shape it expects from the AI recommendation provider.

The generated pact file is saved to /pacts/ and used by the provider
verification test to confirm the API honours the contract.

Run with:
    pytest tests/contract/consumer_test.py -v
"""

import json
import os
from pathlib import Path

import pytest
import requests
from pact import Consumer, Provider  # type: ignore[import]

PACT_DIR = Path(__file__).parent.parent.parent / "pacts"
PACT_DIR.mkdir(exist_ok=True)

MOCK_PORT = 1234
MOCK_HOST = "localhost"


# ---------------------------------------------------------------------------
# Pact setup
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def pact():
    """Create and start the Pact mock provider."""
    consumer = Consumer("RecommendationConsumer")
    provider = Provider("RecommendationProvider")
    p = consumer.has_pact_with(
        provider,
        host_name=MOCK_HOST,
        port=MOCK_PORT,
        pact_dir=str(PACT_DIR),
        log_dir=str(PACT_DIR),
    )
    p.start_service()
    yield p
    p.stop_service()


# ---------------------------------------------------------------------------
# Contract definitions
# ---------------------------------------------------------------------------

@pytest.mark.contract
def test_get_recommendations_contract(pact) -> None:
    """
    Consumer contract: POST /v1/recommendations
    The consumer expects a response with a list of product recommendations,
    each containing the required fields.
    """
    expected_body = {
        "request_id": "req_123456",
        "user_id": "user-contract-001",
        "recommendations": [
            {
                "product_id": "SHOE-001",
                "name": "AeroStride Running Shoes",
                "category": "Footwear",
                "price": 129.99,
                "confidence_score": 0.92,
                "reason": "Based on your interest in running, this Footwear item is highly rated.",
            }
        ],
        "model": "gpt-4o-mini-mock",
        "latency_ms": 45,
    }

    (
        pact
        .given("a user with running shoe interest exists")
        .upon_receiving("a request for product recommendations")
        .with_request(
            method="POST",
            path="/v1/recommendations",
            headers={"Content-Type": "application/json"},
            body={
                "user_id": "user-contract-001",
                "context": "running shoes for marathon training",
                "max_results": 3,
            },
        )
        .will_respond_with(
            status=200,
            headers={"Content-Type": "application/json"},
            body=expected_body,
        )
    )

    with pact:
        resp = requests.post(
            f"http://{MOCK_HOST}:{MOCK_PORT}/v1/recommendations",
            json={
                "user_id": "user-contract-001",
                "context": "running shoes for marathon training",
                "max_results": 3,
            },
            headers={"Content-Type": "application/json"},
            timeout=10,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == "user-contract-001"
    assert len(data["recommendations"]) >= 1
    assert "product_id" in data["recommendations"][0]


@pytest.mark.contract
def test_health_check_contract(pact) -> None:
    """
    Consumer contract: GET /v1/health
    The consumer expects a healthy status response.
    """
    (
        pact
        .given("the recommendation service is running")
        .upon_receiving("a health check request")
        .with_request(method="GET", path="/v1/health")
        .will_respond_with(
            status=200,
            headers={"Content-Type": "application/json"},
            body={"status": "healthy"},
        )
    )

    with pact:
        resp = requests.get(
            f"http://{MOCK_HOST}:{MOCK_PORT}/v1/health",
            timeout=10,
        )

    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.contract
def test_pact_file_was_generated() -> None:
    """Verify the pact file was written to disk after the contract tests run."""
    pact_files = list(PACT_DIR.glob("*.json"))
    assert pact_files, (
        f"No pact files found in {PACT_DIR}. "
        "Run the consumer contract tests first to generate them."
    )
    # Validate the pact file is valid JSON
    for pact_file in pact_files:
        with open(pact_file) as f:
            data = json.load(f)
        assert "consumer" in data
        assert "provider" in data
        assert "interactions" in data
