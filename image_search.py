from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests

LOGGER = logging.getLogger(__name__)

PRIORITY_HINTS = [
    "statistics",
    "field photo",
    "product photo",
    "process photo",
]


@dataclass
class ImageCandidate:
    section: str
    query: str
    title: str
    source_url: str
    image_url: str
    thumbnail_url: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    provider: str = "unknown"


class ImageSearchClient:
    """Search images using SerpAPI or Bing Image Search API."""

    def __init__(
        self,
        serpapi_key: Optional[str] = None,
        bing_key: Optional[str] = None,
        bing_endpoint: Optional[str] = None,
        timeout: int = 15,
    ) -> None:
        self.serpapi_key = serpapi_key
        self.bing_key = bing_key
        self.bing_endpoint = bing_endpoint
        self.timeout = timeout

    def build_queries(self, business_name: str, section: str, summary: str) -> List[str]:
        base = f"{business_name} {section}"
        summary_core = " ".join(summary.split()[:14])
        return [
            f"{base} {summary_core} {' '.join(PRIORITY_HINTS)}",
            f"{section} statistics market chart",
            f"{section} on-site photo real world",
            f"{section} product process industrial",
        ]

    def search_section(
        self,
        business_name: str,
        section: str,
        summary: str,
        per_section: int = 12,
    ) -> List[ImageCandidate]:
        queries = self.build_queries(business_name, section, summary)
        candidates: List[ImageCandidate] = []

        for query in queries:
            if self.serpapi_key:
                candidates.extend(self._search_serpapi(section, query, per_section))
            elif self.bing_key and self.bing_endpoint:
                candidates.extend(self._search_bing(section, query, per_section))
            else:
                raise RuntimeError("No search API key configured. Set SERPAPI_API_KEY or BING_* env vars.")

            if len(candidates) >= per_section:
                break

        return candidates[:per_section]

    def _search_serpapi(self, section: str, query: str, limit: int) -> List[ImageCandidate]:
        params = {
            "engine": "google_images",
            "q": query,
            "api_key": self.serpapi_key,
            "num": min(100, limit),
            "safe": "active",
        }
        response = requests.get("https://serpapi.com/search.json", params=params, timeout=self.timeout)
        response.raise_for_status()
        payload = response.json()

        output: List[ImageCandidate] = []
        for item in payload.get("images_results", []):
            image_url = item.get("original") or item.get("image")
            source_url = item.get("link") or item.get("source")
            if not image_url or not source_url:
                continue
            output.append(
                ImageCandidate(
                    section=section,
                    query=query,
                    title=item.get("title") or section,
                    source_url=source_url,
                    image_url=image_url,
                    thumbnail_url=item.get("thumbnail"),
                    width=item.get("original_width"),
                    height=item.get("original_height"),
                    provider="serpapi",
                )
            )
            if len(output) >= limit:
                break
        LOGGER.info("SerpAPI query='%s' returned %d candidates", query, len(output))
        return output

    def _search_bing(self, section: str, query: str, limit: int) -> List[ImageCandidate]:
        headers = {"Ocp-Apim-Subscription-Key": self.bing_key}
        params = {
            "q": query,
            "count": min(150, limit),
            "safeSearch": "Moderate",
            "imageType": "Photo",
        }
        response = requests.get(self.bing_endpoint, headers=headers, params=params, timeout=self.timeout)
        response.raise_for_status()
        payload: Dict[str, Any] = response.json()

        output: List[ImageCandidate] = []
        for item in payload.get("value", []):
            image_url = item.get("contentUrl")
            source_url = item.get("hostPageUrl")
            if not image_url or not source_url:
                continue
            output.append(
                ImageCandidate(
                    section=section,
                    query=query,
                    title=item.get("name") or section,
                    source_url=source_url,
                    image_url=image_url,
                    thumbnail_url=item.get("thumbnailUrl"),
                    width=item.get("width"),
                    height=item.get("height"),
                    provider="bing",
                )
            )
            if len(output) >= limit:
                break
        LOGGER.info("Bing query='%s' returned %d candidates", query, len(output))
        return output
