"""
WHO ICD-11 API client.
Uses the official WHO ICD-11 API for authoritative diagnosis coding.
Free to use — no API key required for read-only access.
"""

import httpx
import structlog

logger = structlog.get_logger(__name__)

ICD11_API_BASE = "https://id.who.int/icd/entity/search"
ICD11_RELEASE = "2024-01"


class ICD11Client:
    """
    Thin wrapper around the WHO ICD-11 linearization search API.
    Docs: https://icd.who.int/icdapi
    """

    def __init__(self):
        self._client = httpx.AsyncClient(timeout=10.0)

    async def search(self, term: str, max_results: int = 3) -> list[dict]:
        """
        Search ICD-11 for a clinical term.

        Returns list of matches with code and title.
        """
        try:
            response = await self._client.get(
                "https://id.who.int/icd/release/11/2024-01/mms/search",
                params={
                    "q": term,
                    "flatResults": "true",
                    "highlightingEnabled": "false",
                    "medicalCodingMode": "true",
                },
                headers={
                    "Accept": "application/json",
                    "Accept-Language": "en",
                    "API-Version": "v2",
                },
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("destinationEntities", [])[:max_results]:
                code = item.get("theCode", "")
                title = item.get("title", "")
                if code and title:
                    results.append({"code": code, "description": title})

            logger.debug("ICD-11 search", term=term, results=len(results))
            return results

        except Exception as e:
            logger.warning("ICD-11 API failed", term=term, error=str(e))
            return []

    async def get_best_match(self, term: str) -> tuple[str | None, str | None]:
        """Return (code, description) for the best ICD-11 match, or (None, None)."""
        results = await self.search(term, max_results=1)
        if results:
            return results[0]["code"], results[0]["description"]
        return None, None

    async def close(self):
        await self._client.aclose()


# Singleton
icd11_client = ICD11Client()