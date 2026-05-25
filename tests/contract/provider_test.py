"""
Pact Provider Verification Test
---------------------------------
Verifies that the actual recommendation provider (mock server) honours the
contracts defined by the consumer. Reads the pact files from /pacts/ and
replays each interaction against the running server.

The provider must be running before this test executes:
    uvicorn mock_server.app:app --port 8000

Run with:
    pytest tests/contract/provider_test.py -v
"""

import os
from pathlib import Path

import pytest
from pact import Verifier  # type: ignore[import]

PACT_DIR = Path(__file__).parent.parent.parent / "pacts"
PROVIDER_URL = os.getenv("MOCK_SERVER_URL", "http://localhost:8000")


@pytest.mark.contract
def test_provider_honours_consumer_contract() -> None:
    """
    Verify the recommendation provider satisfies all consumer contracts.
    Reads pact files from the /pacts/ directory and verifies each interaction.
    """
    pact_files = list(PACT_DIR.glob("*.json"))

    if not pact_files:
        pytest.skip(
            f"No pact files found in {PACT_DIR}. "
            "Run consumer_test.py first to generate the pact files."
        )

    verifier = Verifier(
        provider="RecommendationProvider",
        provider_base_url=PROVIDER_URL,
    )

    output, _ = verifier.verify_pacts(
        sources=[str(p) for p in pact_files],
        verbose=True,
    )

    assert output == 0, (
        f"Provider verification failed. The provider does not honour one or more "
        f"consumer contracts. Check the output above for details."
    )
