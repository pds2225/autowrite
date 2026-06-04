from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

import httpx
from openai import OpenAI

from ..config import Settings
from ..utils import log_line


class OpenAIService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.provider = settings.ai_provider
        self._client = OpenAI(api_key=settings.openai_api_key) if settings.has_openai else None
        self._runtime_disabled_reason = ""

    @property
    def available(self) -> bool:
        return self.provider != "none" and not self._runtime_disabled_reason

    @property
    def status_text(self) -> str:
        if self._runtime_disabled_reason:
            return f"AI 연결 비활성화: {self._runtime_disabled_reason}"
        if self.provider == "openai":
            return "OpenAI 사용 가능"
        if self.provider == "anthropic":
            return "Claude 사용 가능 (이미지는 기본 카드로 대체될 수 있음)"
        return "AI API 키 없음, 기본 동작만 사용"

    def _is_auth_error(self, exc: Exception) -> bool:
        status_code = getattr(exc, "status_code", None)
        if status_code in {401, 403}:
            return True
        response = getattr(exc, "response", None)
        response_code = getattr(response, "status_code", None)
        if response_code in {401, 403}:
            return True
        text = str(exc).lower()
        auth_markers = ("401", "403", "unauthorized", "forbidden", "invalid api key", "authentication")
        return any(marker in text for marker in auth_markers)

    def _disable_runtime(self, reason: str) -> None:
        if self._runtime_disabled_reason:
            return
        self._runtime_disabled_reason = reason
        log_line(f"[WARN] AI runtime disabled: {reason}")

    def _extract_json(self, text: str) -> dict[str, Any] | list[Any] | None:
        if not text:
            return None
        stripped = text.strip()
        if stripped.startswith("```") and "\n" in stripped:
            stripped = stripped.split("\n", 1)[1]
            if stripped.endswith("```"):
                stripped = stripped[:-3]
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            start = stripped.find("{")
            end = stripped.rfind("}")
            if start >= 0 and end > start:
                try:
                    return json.loads(stripped[start : end + 1])
                except json.JSONDecodeError:
                    return None
        return None

    def complete_json(self, system_prompt: str, user_prompt: str, model: str | None = None) -> dict[str, Any] | None:
        if not self.available:
            return None
        output_text = self._complete_text(system_prompt, user_prompt, model=model, temperature=0.2)
        payload = self._extract_json(output_text)
        if isinstance(payload, dict):
            return payload
        return None

    def _complete_text(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float = 0.2,
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
    ) -> str:
        if self.provider == "openai":
            return self._complete_text_openai(system_prompt, user_prompt, model, temperature, tools)
        if self.provider == "anthropic":
            return self._complete_text_anthropic(system_prompt, user_prompt, model, temperature, tools, max_tokens)
        return ""

    def _complete_text_openai(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None,
        temperature: float,
        tools: list[dict[str, Any]] | None = None,
    ) -> str:
        if self._client is None:
            return ""
        try:
            response = self._client.responses.create(
                model=model or self.settings.openai_model,
                instructions=system_prompt,
                input=user_prompt,
                tools=tools or [],
                temperature=temperature,
            )
            return response.output_text.strip()
        except Exception as exc:
            if self._is_auth_error(exc):
                self._disable_runtime("API 키 인증 실패")
            log_line(f"[WARN] OpenAI 호출 실패: {exc}")
            return ""

    def _complete_text_anthropic(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None,
        temperature: float,
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
    ) -> str:
        if not self.settings.has_anthropic:
            return ""
        headers = {
            "x-api-key": self.settings.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": model or self.settings.anthropic_model,
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
            "temperature": temperature,
        }
        if tools:
            payload["tools"] = tools
        try:
            response = httpx.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
                timeout=120.0,
            )
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            if self._is_auth_error(exc):
                self._disable_runtime("API 키 인증 실패")
            log_line(f"[WARN] Anthropic 호출 실패: {exc}")
            return ""
        parts: list[str] = []
        for block in data.get("content", []):
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")).strip())
        return "\n".join(part for part in parts if part).strip()

    def refine_template_profile(self, raw_profile: dict[str, Any], doc_summary: dict[str, Any]) -> dict[str, Any] | None:
        system_prompt = (
            "You improve a DOCX template profile for a grant proposal generator. "
            "Return strict JSON only. Keep the same schema keys. "
            "Prefer anchor_text that exactly appears in the template."
        )
        user_prompt = json.dumps({"profile": raw_profile, "doc_summary": doc_summary}, ensure_ascii=False)
        return self.complete_json(system_prompt, user_prompt)

    def draft_missing_answers(self, questions: list[dict[str, Any]], context: str) -> dict[str, str]:
        if not self.available:
            return {}
        system_prompt = (
            "You fill missing grant proposal form answers from the provided context. "
            "Return a JSON object where each key is question_id and each value is concise Korean text."
        )
        user_prompt = json.dumps({"questions": questions, "context": context}, ensure_ascii=False)
        result = self.complete_json(system_prompt, user_prompt)
        if not isinstance(result, dict):
            return {}
        return {str(key): str(value) for key, value in result.items()}

    def summarize_sources(self, topic: str, snippets: list[dict[str, str]]) -> str:
        if not self.available:
            return snippets[0]["snippet"] if snippets else ""
        system_prompt = (
            "You summarize evidence for a Korean business support proposal. "
            "Return plain Korean text in 3 short sentences."
        )
        user_prompt = json.dumps({"topic": topic, "snippets": snippets}, ensure_ascii=False)
        model = self.settings.openai_search_model if self.provider == "openai" else self.settings.anthropic_search_model
        output = self._complete_text(system_prompt, user_prompt, model=model, temperature=0.2, max_tokens=1200)
        return output or (snippets[0]["snippet"] if snippets else "")

    def web_search_sources(self, topic: str) -> list[dict[str, str]]:
        if not self.available:
            return []
        if self.provider == "anthropic":
            return self._web_search_sources_anthropic(topic)
        return self._web_search_sources_openai(topic)

    def _web_search_sources_openai(self, topic: str) -> list[dict[str, str]]:
        if self._client is None:
            return []
        system_prompt = (
            "Search the web and return JSON only. "
            "Return an array named sources. Each item must have title, url, organization, summary."
        )
        try:
            response = self._client.responses.create(
                model=self.settings.openai_search_model,
                instructions=system_prompt,
                input=f"주제: {topic}",
                tools=[
                    {
                        "type": "web_search_preview",
                        "search_context_size": "medium",
                        "user_location": {"type": "approximate", "country": "KR", "timezone": "Asia/Seoul"},
                    }
                ],
                temperature=0.2,
            )
        except Exception as exc:
            log_line(f"[WARN] OpenAI 웹검색 실패: {exc}")
            return []
        payload = self._extract_json(response.output_text)
        return self._normalize_sources_payload(payload)

    def _web_search_sources_anthropic(self, topic: str) -> list[dict[str, str]]:
        system_prompt = (
            "You search the web for evidence used in Korean business-support proposals. "
            "Return JSON only with an array field named sources. "
            "Each source item must include title, url, organization, and summary."
        )
        output = self._complete_text(
            system_prompt,
            f"주제: {topic}",
            model=self.settings.anthropic_search_model,
            temperature=0.2,
            max_tokens=1800,
            tools=[
                {
                    "type": "web_search_20250305",
                    "name": "web_search",
                    "max_uses": 3,
                }
            ],
        )
        payload = self._extract_json(output)
        return self._normalize_sources_payload(payload)

    def _normalize_sources_payload(self, payload: dict[str, Any] | list[Any] | None) -> list[dict[str, str]]:
        if isinstance(payload, dict):
            sources = payload.get("sources", [])
            if isinstance(sources, list):
                cleaned = []
                for item in sources:
                    if not isinstance(item, dict):
                        continue
                    cleaned.append(
                        {
                            "title": str(item.get("title", "")),
                            "url": str(item.get("url", "")),
                            "organization": str(item.get("organization", "")),
                            "snippet": str(item.get("summary", "")),
                        }
                    )
                return cleaned
        return []

    def propose_image_prompt(self, slot_label: str, context: str) -> str:
        if not self.available:
            return f"{slot_label}를 설명하는 깔끔한 인포그래픽"
        system_prompt = (
            "You create image prompts for formal Korean business-support proposal documents. "
            "Return one Korean sentence only."
        )
        user_prompt = json.dumps({"slot_label": slot_label, "context": context}, ensure_ascii=False)
        output = self._complete_text(system_prompt, user_prompt, temperature=0.4, max_tokens=300)
        return output or f"{slot_label}를 설명하는 깔끔한 인포그래픽"

    def generate_image_file(self, prompt: str, output_path: Path) -> bool:
        if not self.available or self.provider != "openai" or self._client is None:
            return False
        log_line(f"[IMG] OpenAI image generate: {output_path.name}")
        try:
            result = self._client.images.generate(
                model=self.settings.openai_image_model,
                prompt=prompt,
                size="1536x1024",
                quality="medium",
                response_format="b64_json",
            )
            image_b64 = result.data[0].b64_json if result.data else None
            if not image_b64:
                return False
            output_path.write_bytes(base64.b64decode(image_b64))
            return True
        except Exception as exc:
            log_line(f"[WARN] OpenAI 이미지 생성 실패: {exc}")
            return False
