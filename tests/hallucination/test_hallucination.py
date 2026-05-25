"""
Hallucination Detection Tests
-------------------------------
Verifies that the AI recommendation engine only returns products that exist
in the known product catalog. Any product_id, name, or price that doesn't
match the catalog is flagged as a hallucination.

Two test scenarios:
  1. Normal endpoint — should return only real catalog products (pass)
  2. Hallucinate endpoint — intentionally returns fake products (should be caught)
"""

import json
import os
from pathlib import Path

import pytest
import requests

BASE_URL = os.getenv("MOCK_SERVER_URL", "http://localhost:8000")

CATALOG_PATH = Path(__file__).parent / "product_catalog.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_catalog() -> dict:
    """Load the known product catalog from disk."""
    with open(CATALOG_PATH) as f:
        return json.load(f)


def get_catalog_index(catalog: dict) -> tuple[set, dict]:
    """
    Returns:
        known_ids: set of valid product_id strings
        price_map: dict mapping product_id -> price
    """
    products = catalog["products"]
    known_ids = {p["product_id"] for p in products}
    price_map = {p["product_id"]: p["price"] for p in products}
    return known_ids, price_map


def is_hallucinated(recommendation: dict, known_ids: set, price_map: dict) -> list[str]:
    """
    Check a single recommendation for hallucination signals.
    Returns a list of violation strings (empty = no hallucination).
    """
    violations = []
    pid = recommendation.get("product_id", "")

    if pid not in known_ids:
        violations.append(f"Unknown product_id: '{pid}' not in catalog")
        return violations  # can't check price if ID is unknown

    catalog_price = price_map[pid]
    response_price = recommendation.get("price", 0)
    # Allow a small tolerance for currency rounding
    if abs(response_price - catalog_price) > 0.01:
        violations.append(
            f"Price mismatch for {pid}: catalog={catalog_price}, response={response_price}"
        )

    return violations


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def catalog() -> dict:
    return load_catalog()


@pytest.fixture(scope="module")
def catalog_index(catalog: dict) -> tuple[set, dict]:
    return get_catalog_index(catalog)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.hallucination
def test_catalog_loads_successfully(catalog: dict) -> None:
    """Sanity check: the product catalog file must be valid and non-empty."""
    assert "products" in catalog
    assert len(catalog["products"]) > 0


@pytest.mark.hallucination
def test_normal_recommendations_contain_only_catalog_products(
    catalog_index: tuple[set, dict],
) -> None:
    """
    The /v1/recommendations endpoint must only return products from the
    known catalog. Any unknown product_id is a hallucination.
    """
    known_ids, price_map = catalog_index

    resp = requests.post(
        f"{BASE_URL}/v1/recommendations",
        json={"user_id": "user-hal-001", "context": "fitness equipment"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()

    all_violations: list[str] = []
    for rec in data.get("recommendations", []):
        violations = is_hallucinated(rec, known_ids, price_map)
        all_violations.extend(violations)

    assert not all_violations, (
        f"Hallucination detected in recommendations:\n"
        + "\n".join(f"  - {v}" for v in all_violations)
    )


@pytest.mark.hallucination
def test_hallucination_endpoint_is_caught(catalog_index: tuple[set, dict]) -> None:
    """
    The /v1/recommendations/hallucinate endpoint intentionally returns fake
    products. This test verifies our detection logic catches them.
    """
    known_ids, price_map = catalog_index

    resp = requests.post(
        f"{BASE_URL}/v1/recommendations/hallucinate",
        json={"user_id": "user-hal-002", "context": "test hallucination"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()

    all_violations: list[str] = []
    for rec in data.get("recommendations", []):
        violations = is_hallucinated(rec, known_ids, price_map)
        all_violations.extend(violations)

    # We EXPECT violations here — the test passes only if hallucinations are detected
    assert all_violations, (
        "Expected hallucination detection to find violations, but none were found. "
        "The hallucination scorer may not be working correctly."
    )


@pytest.mark.hallucination
def test_category_filter_returns_only_matching_category(
    catalog_index: tuple[set, dict],
) -> None:
    """When a category filter is applied, all returned products must match that category."""
    known_ids, price_map = catalog_index

    resp = requests.post(
        f"{BASE_URL}/v1/recommendations",
        json={
            "user_id": "user-hal-003",
            "context": "wireless audio",
            "category": "Electronics",
        },
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()

    for rec in data.get("recommendations", []):
        assert rec["category"] == "Electronics", (
            f"Category filter violated: expected 'Electronics', got '{rec['category']}' "
            f"for product '{rec['product_id']}'"
        )


@pytest.mark.hallucination
def test_all_catalog_product_ids_are_unique(catalog: dict) -> None:
    """The catalog itself must not have duplicate product IDs."""
    ids = [p["product_id"] for p in catalog["products"]]
    assert len(ids) == len(set(ids)), "Duplicate product_id found in product_catalog.json"


@pytest.mark.hallucination
def test_all_catalog_prices_are_positive(catalog: dict) -> None:
    """Every product in the catalog must have a positive price."""
    for product in catalog["products"]:
        assert product["price"] > 0, (
            f"Product '{product['product_id']}' has non-positive price: {product['price']}"
        )
