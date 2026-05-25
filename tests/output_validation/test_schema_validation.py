"""
Output Validation Tests — Pydantic + pytest
--------------------------------------------
Validates that the AI recommendation API returns responses that conform to
the expected JSON schema. Tests cover:
  - Happy path: valid response parses without errors
  - Missing required fields
  - Wrong field types
  - Out-of-range values (price, confidence_score)
  - Duplicate product IDs in a single response
  - Invalid product_id format

These tests run against the mock server. Set MOCK_SERVER_URL in .env or
the environment to point at a real server.
"""

import os

import pytest
import requests
from pydantic import ValidationError

from tests.output_validation.models import RecommendationResponse

BASE_URL = os.getenv("MOCK_SERVER_URL", "http://localhost:8000")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def valid_response() -> dict:
    """Fetch a real response from the mock server."""
    resp = requests.post(
        f"{BASE_URL}/v1/recommendations",
        json={"user_id": "user-123", "context": "running shoes for marathon training"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

@pytest.mark.schema
def test_valid_response_parses_successfully(valid_response: dict) -> None:
    """A well-formed API response should parse without any ValidationError."""
    model = RecommendationResponse.model_validate(valid_response)
    assert model.request_id
    assert model.user_id == "user-123"
    assert len(model.recommendations) >= 1


@pytest.mark.schema
def test_all_recommendations_have_required_fields(valid_response: dict) -> None:
    """Every recommendation in the list must have all required fields populated."""
    model = RecommendationResponse.model_validate(valid_response)
    for rec in model.recommendations:
        assert rec.product_id
        assert rec.name
        assert rec.category
        assert rec.price > 0
        assert 0.0 <= rec.confidence_score <= 1.0
        assert len(rec.reason) >= 10


@pytest.mark.schema
def test_latency_ms_is_non_negative(valid_response: dict) -> None:
    """Latency must be a non-negative integer."""
    model = RecommendationResponse.model_validate(valid_response)
    assert model.latency_ms >= 0


@pytest.mark.schema
def test_model_field_is_present(valid_response: dict) -> None:
    """The model identifier must be present in the response."""
    model = RecommendationResponse.model_validate(valid_response)
    assert model.model


# ---------------------------------------------------------------------------
# Schema violation tests (unit-level, no server needed)
# ---------------------------------------------------------------------------

@pytest.mark.schema
def test_missing_request_id_raises_validation_error() -> None:
    """Responses without request_id must fail validation."""
    bad_payload = {
        "user_id": "user-123",
        "recommendations": [
            {
                "product_id": "SHOE-001",
                "name": "AeroStride Running Shoes",
                "category": "Footwear",
                "price": 129.99,
                "confidence_score": 0.92,
                "reason": "Great for marathon training based on your history.",
            }
        ],
        "model": "gpt-4o-mini",
        "latency_ms": 450,
    }
    with pytest.raises(ValidationError) as exc_info:
        RecommendationResponse.model_validate(bad_payload)
    assert "request_id" in str(exc_info.value)


@pytest.mark.schema
def test_negative_price_raises_validation_error() -> None:
    """A negative price must be rejected by the schema."""
    bad_payload = {
        "request_id": "req_001",
        "user_id": "user-123",
        "recommendations": [
            {
                "product_id": "SHOE-001",
                "name": "AeroStride Running Shoes",
                "category": "Footwear",
                "price": -10.00,  # invalid
                "confidence_score": 0.92,
                "reason": "Great for marathon training based on your history.",
            }
        ],
        "model": "gpt-4o-mini",
        "latency_ms": 450,
    }
    with pytest.raises(ValidationError) as exc_info:
        RecommendationResponse.model_validate(bad_payload)
    assert "price" in str(exc_info.value)


@pytest.mark.schema
def test_confidence_score_above_1_raises_validation_error() -> None:
    """Confidence scores must be between 0 and 1."""
    bad_payload = {
        "request_id": "req_001",
        "user_id": "user-123",
        "recommendations": [
            {
                "product_id": "SHOE-001",
                "name": "AeroStride Running Shoes",
                "category": "Footwear",
                "price": 129.99,
                "confidence_score": 1.5,  # invalid — above 1.0
                "reason": "Great for marathon training based on your history.",
            }
        ],
        "model": "gpt-4o-mini",
        "latency_ms": 450,
    }
    with pytest.raises(ValidationError) as exc_info:
        RecommendationResponse.model_validate(bad_payload)
    assert "confidence_score" in str(exc_info.value)


@pytest.mark.schema
def test_duplicate_product_ids_raise_validation_error() -> None:
    """The same product must not appear twice in one response."""
    bad_payload = {
        "request_id": "req_001",
        "user_id": "user-123",
        "recommendations": [
            {
                "product_id": "SHOE-001",
                "name": "AeroStride Running Shoes",
                "category": "Footwear",
                "price": 129.99,
                "confidence_score": 0.92,
                "reason": "Great for marathon training based on your history.",
            },
            {
                "product_id": "SHOE-001",  # duplicate
                "name": "AeroStride Running Shoes",
                "category": "Footwear",
                "price": 129.99,
                "confidence_score": 0.88,
                "reason": "Also great for marathon training.",
            },
        ],
        "model": "gpt-4o-mini",
        "latency_ms": 450,
    }
    with pytest.raises(ValidationError) as exc_info:
        RecommendationResponse.model_validate(bad_payload)
    assert "Duplicate" in str(exc_info.value)


@pytest.mark.schema
def test_invalid_product_id_format_raises_validation_error() -> None:
    """Product IDs that don't match CATEGORY-NNN format must be rejected."""
    bad_payload = {
        "request_id": "req_001",
        "user_id": "user-123",
        "recommendations": [
            {
                "product_id": "FAKE-9999-EXTRA",  # invalid format
                "name": "Some Product",
                "category": "Footwear",
                "price": 99.99,
                "confidence_score": 0.85,
                "reason": "This product ID format is not valid per our catalog spec.",
            }
        ],
        "model": "gpt-4o-mini",
        "latency_ms": 450,
    }
    with pytest.raises(ValidationError) as exc_info:
        RecommendationResponse.model_validate(bad_payload)
    assert "product_id" in str(exc_info.value)


@pytest.mark.schema
def test_absurd_price_raises_validation_error() -> None:
    """Prices above $100,000 are treated as hallucinations and must fail."""
    bad_payload = {
        "request_id": "req_001",
        "user_id": "user-123",
        "recommendations": [
            {
                "product_id": "SHOE-001",
                "name": "Diamond-Encrusted Sneakers",
                "category": "Footwear",
                "price": 999_999.99,  # hallucinated price
                "confidence_score": 0.99,
                "reason": "Luxury item for high-net-worth customers.",
            }
        ],
        "model": "gpt-4o-mini",
        "latency_ms": 450,
    }
    with pytest.raises(ValidationError) as exc_info:
        RecommendationResponse.model_validate(bad_payload)
    assert "price" in str(exc_info.value)


@pytest.mark.schema
def test_max_results_parameter_respected() -> None:
    """The API should respect the max_results parameter."""
    resp = requests.post(
        f"{BASE_URL}/v1/recommendations",
        json={
            "user_id": "user-456",
            "context": "home office setup",
            "max_results": 2,
        },
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    model = RecommendationResponse.model_validate(data)
    assert len(model.recommendations) <= 2
