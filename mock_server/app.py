"""
Mock AI Recommendation Server
------------------------------
Simulates an OpenAI-compatible endpoint that returns product recommendations.
Used by all test layers so the suite runs without a real LLM API key.
"""

import json
import random
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(
    title="AI Product Recommendation Engine",
    description="Mock OpenAI-compatible recommendation API for QA testing",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# Load the product catalog so the mock only returns real products
# ---------------------------------------------------------------------------
CATALOG_PATH = Path(__file__).parent.parent / "tests" / "hallucination" / "product_catalog.json"

def _load_catalog() -> list[dict]:
    if CATALOG_PATH.exists():
        with open(CATALOG_PATH) as f:
            return json.load(f)["products"]
    return []

PRODUCT_CATALOG = _load_catalog()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class RecommendationRequest(BaseModel):
    user_id: str
    context: str
    max_results: int = 3
    category: str | None = None


class ProductRecommendation(BaseModel):
    product_id: str
    name: str
    category: str
    price: float
    confidence_score: float
    reason: str


class RecommendationResponse(BaseModel):
    request_id: str
    user_id: str
    recommendations: list[ProductRecommendation]
    model: str
    latency_ms: int


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/v1/health")
async def health_check() -> dict[str, Any]:
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0", "catalog_size": len(PRODUCT_CATALOG)}


@app.post("/v1/recommendations", response_model=RecommendationResponse)
async def get_recommendations(request: RecommendationRequest) -> RecommendationResponse:
    """
    Returns AI-generated product recommendations.
    Simulates realistic latency and always returns products from the known catalog.
    """
    start = time.time()

    if not request.user_id:
        raise HTTPException(status_code=422, detail="user_id is required")

    # Filter by category if provided
    pool = PRODUCT_CATALOG
    if request.category:
        pool = [p for p in PRODUCT_CATALOG if p["category"].lower() == request.category.lower()]
        if not pool:
            pool = PRODUCT_CATALOG  # fall back to full catalog

    # Pick up to max_results products
    count = min(request.max_results, len(pool))
    selected = random.sample(pool, count)

    recommendations = [
        ProductRecommendation(
            product_id=p["product_id"],
            name=p["name"],
            category=p["category"],
            price=p["price"],
            confidence_score=round(random.uniform(0.72, 0.98), 2),
            reason=f"Based on your interest in {request.context}, this {p['category']} item is highly rated.",
        )
        for p in selected
    ]

    elapsed_ms = int((time.time() - start) * 1000)

    return RecommendationResponse(
        request_id=f"req_{int(time.time() * 1000)}",
        user_id=request.user_id,
        recommendations=recommendations,
        model="gpt-4o-mini-mock",
        latency_ms=elapsed_ms,
    )


@app.post("/v1/recommendations/hallucinate", response_model=RecommendationResponse)
async def get_hallucinated_recommendations(request: RecommendationRequest) -> RecommendationResponse:
    """
    Intentionally returns hallucinated (fake) product data.
    Used to verify that hallucination detection tests catch bad responses.
    """
    start = time.time()

    fake_recommendations = [
        ProductRecommendation(
            product_id="FAKE-9999",
            name="Quantum Flux Sneakers Pro Max Ultra",
            category="Footwear",
            price=9999.99,
            confidence_score=0.99,
            reason="This product doesn't exist but the model made it up.",
        )
    ]

    elapsed_ms = int((time.time() - start) * 1000)

    return RecommendationResponse(
        request_id=f"req_{int(time.time() * 1000)}",
        user_id=request.user_id,
        recommendations=fake_recommendations,
        model="gpt-4o-mini-mock",
        latency_ms=elapsed_ms,
    )
