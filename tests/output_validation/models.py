"""
Pydantic models for AI recommendation API response validation.

These models define the expected schema for every response from the
/v1/recommendations endpoint. Any deviation — missing fields, wrong types,
out-of-range values — will raise a ValidationError caught by pytest.
"""

from pydantic import BaseModel, Field, field_validator


class ProductRecommendation(BaseModel):
    """A single product recommendation returned by the AI engine."""

    product_id: str = Field(..., min_length=1, description="Unique product identifier")
    name: str = Field(..., min_length=1, description="Human-readable product name")
    category: str = Field(..., min_length=1, description="Product category")
    price: float = Field(..., gt=0, description="Product price in USD, must be positive")
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Model confidence score between 0 and 1"
    )
    reason: str = Field(..., min_length=10, description="Explanation for the recommendation")

    @field_validator("price")
    @classmethod
    def price_must_be_reasonable(cls, v: float) -> float:
        """Guard against absurd hallucinated prices."""
        if v > 100_000:
            raise ValueError(f"Price {v} exceeds maximum reasonable value of $100,000")
        return v

    @field_validator("product_id")
    @classmethod
    def product_id_format(cls, v: str) -> str:
        """Product IDs must follow the CATEGORY-NNN pattern."""
        parts = v.split("-")
        if len(parts) != 2 or not parts[1].isdigit():
            raise ValueError(
                f"product_id '{v}' does not match expected format 'CATEGORY-NNN'"
            )
        return v


class RecommendationResponse(BaseModel):
    """Top-level response envelope from the recommendation API."""

    request_id: str = Field(..., min_length=1, description="Unique request identifier")
    user_id: str = Field(..., min_length=1, description="The requesting user's ID")
    recommendations: list[ProductRecommendation] = Field(
        ..., min_length=1, max_length=10, description="List of recommended products"
    )
    model: str = Field(..., min_length=1, description="Model identifier used for inference")
    latency_ms: int = Field(..., ge=0, description="Server-side inference latency in milliseconds")

    @field_validator("recommendations")
    @classmethod
    def no_duplicate_products(cls, v: list[ProductRecommendation]) -> list[ProductRecommendation]:
        """Ensure the same product is not recommended twice in one response."""
        ids = [r.product_id for r in v]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate product_id found in recommendations list")
        return v
