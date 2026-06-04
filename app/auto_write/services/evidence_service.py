from __future__ import annotations

import base64
from urllib.parse import parse_qs, quote, unquote, urlparse

import httpx
from lxml import html

from ..models import EvidenceRequest, EvidenceSource
from .openai_client import OpenAIService


class EvidenceService:
    PREFERRED_DOMAINS = ("go.kr", "or.kr", "ac.kr", "re.kr")

    def __init__(self, openai_service: OpenAIService):
        self.openai_service = openai_service

    def search(self, requests: list[EvidenceRequest]) -> list[EvidenceSource]:
        sources: list[EvidenceSource] = []
        for request in requests:
            query = request.topic.strip()
            if not query:
                continue
            snippets = self.openai_service.web_search_sources(query) if self.openai_service.available else []
            if not snippets:
                snippets = self._duckduckgo_snippets(query)
            if not snippets:
                continue
            summary = self.openai_service.summarize_sources(query, snippets)
            for snippet in snippets[:3]:
                sources.append(
                    EvidenceSource(
                        topic=query,
                        title=snippet["title"],
                        url=snippet["url"],
                        summary=summary or snippet["snippet"],
                        used_for=[request.purpose] if request.purpose else [],
                    )
                )
        return sources

    def _duckduckgo_snippets(self, query: str) -> list[dict[str, str]]:
        preferred_query = f"{query} (site:go.kr OR site:or.kr OR site:ac.kr)"
        results = self._bing_search(preferred_query)
        if results:
            return results
        return self._bing_search(query)

    def _bing_search(self, query: str) -> list[dict[str, str]]:
        url = f"https://www.bing.com/search?mkt=ko-KR&q={quote(query)}"
        try:
            response = httpx.get(
                url,
                timeout=20.0,
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            response.raise_for_status()
        except Exception:
            return []
        document = html.fromstring(response.text)
        results: list[dict[str, str]] = []
        for item in document.xpath('//li[contains(@class, "b_algo")]'):
            title = "".join(item.xpath(".//h2//text()")).strip()
            links = item.xpath(".//h2/a/@href")
            snippet = " ".join(part.strip() for part in item.xpath(".//p//text()") if part.strip())
            link = self._normalize_bing_link(links[0]) if links else ""
            if not title or not link:
                continue
            results.append({"title": title, "url": link, "snippet": snippet})
        preferred = [item for item in results if self._is_preferred_domain(item["url"])]
        remainder = [item for item in results if item not in preferred]
        return (preferred + remainder)[:5]

    def _normalize_bing_link(self, url: str) -> str:
        if not url:
            return ""
        parsed = urlparse(url)
        if "bing.com" not in parsed.netloc:
            return url
        encoded = parse_qs(parsed.query).get("u", [""])[0]
        if encoded.startswith("a1"):
            encoded = encoded[2:]
        decoded = self._decode_base64_url(encoded)
        return decoded or unquote(encoded) or url

    def _decode_base64_url(self, value: str) -> str:
        candidate = value.strip()
        if not candidate:
            return ""
        padding = "=" * (-len(candidate) % 4)
        try:
            decoded = base64.urlsafe_b64decode(candidate + padding).decode("utf-8")
        except Exception:
            return ""
        return decoded if decoded.startswith("http") else ""

    def _is_preferred_domain(self, url: str) -> bool:
        host = urlparse(url).netloc.lower()
        return any(host.endswith(domain) for domain in self.PREFERRED_DOMAINS)
