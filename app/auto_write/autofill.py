from __future__ import annotations

import json
import re
from typing import Mapping

AUTOFILL_KEYS = ("project_title", "organization_name", "user_brief", "user_notes", "evidence_topics")

_FIELD_PATTERNS: dict[str, tuple[str, ...]] = {
    "project_title": (r"과제명", r"사업명", r"프로젝트명", r"지원사업명"),
    "organization_name": (r"기관명", r"회사명", r"기업명", r"상호", r"업체명"),
    "user_brief": (r"사업\s*개요", r"아이템\s*개요", r"사업내용", r"핵심\s*내용", r"문제\s*및\s*해결"),
    "user_notes": (r"추가\s*메모", r"강점", r"차별점", r"보유역량", r"추진계획", r"팀\s*구성"),
}

_EVIDENCE_PATTERNS = (r"근거\s*주제", r"통계\s*주제", r"검색\s*주제", r"필요\s*자료", r"출처\s*주제")
_LABEL_LINE_RE = re.compile(r"^\s*(?P<label>[^:\n：]{1,30})\s*[:：]\s*(?P<value>.+?)\s*$")
_WHITESPACE_RE = re.compile(r"[ \t]+")


def normalize_text(value: object) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [_WHITESPACE_RE.sub(" ", line).strip() for line in text.split("\n")]
    return "\n".join(line for line in lines if line)


def _label_matches(label: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, label, re.IGNORECASE) for pattern in patterns)


def _compact(value: str, limit: int = 2500) -> str:
    text = normalize_text(value)
    if len(text) > limit:
        return text[:limit].rstrip() + "..."
    return text


def _from_json_text(text: str) -> dict[str, str]:
    try:
        data = json.loads(text)
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    aliases = {
        "project_title": ("project_title", "과제명", "사업명", "프로젝트명"),
        "organization_name": ("organization_name", "기관명", "회사명", "기업명", "상호"),
        "user_brief": ("user_brief", "사업 개요", "사업개요", "아이템 개요", "사업내용"),
        "user_notes": ("user_notes", "추가 메모", "추가메모", "강점", "차별점"),
        "evidence_topics": ("evidence_topics", "근거 주제", "통계 주제", "검색 주제"),
    }
    result: dict[str, str] = {}
    for target, names in aliases.items():
        for name in names:
            if name in data and str(data[name]).strip():
                value = data[name]
                if isinstance(value, list):
                    result[target] = "\n".join(str(item).strip() for item in value if str(item).strip())
                else:
                    result[target] = str(value).strip()
                break
    return result


def build_autofill_values(text: str) -> dict[str, str]:
    """Extract project form values from a single uploaded briefing/reference file.

    Supports labeled Korean lines such as "과제명: ...", "회사명: ...",
    "사업 개요: ...", and simple JSON files with equivalent keys. If no
    labeled business overview exists, a short summary-like excerpt is used as
    user_brief so the generation flow can start from one attached file.
    """
    normalized = normalize_text(text)
    if not normalized:
        return {}

    result = _from_json_text(normalized)
    evidence_lines: list[str] = []
    unlabeled_lines: list[str] = []

    for line in normalized.split("\n"):
        match = _LABEL_LINE_RE.match(line)
        if not match:
            unlabeled_lines.append(line)
            continue
        label = match.group("label").strip()
        value = match.group("value").strip()
        if not value:
            continue
        handled = False
        for key, patterns in _FIELD_PATTERNS.items():
            if key not in result and _label_matches(label, patterns):
                result[key] = value
                handled = True
                break
        if handled:
            continue
        if _label_matches(label, _EVIDENCE_PATTERNS):
            evidence_lines.append(value)

    if evidence_lines and not result.get("evidence_topics"):
        result["evidence_topics"] = "\n".join(evidence_lines)

    if not result.get("user_brief"):
        candidate = "\n".join(unlabeled_lines[:12]) or normalized
        result["user_brief"] = _compact(candidate)

    return {key: _compact(value) for key, value in result.items() if key in AUTOFILL_KEYS and str(value).strip()}


def merge_form_with_autofill(form_values: Mapping[str, object], autofill_values: Mapping[str, object]) -> dict[str, str]:
    """Merge manual form values and extracted file values.

    Manual user input wins. File-extracted values only fill blank fields.
    """
    merged: dict[str, str] = {}
    for key in AUTOFILL_KEYS:
        manual = str(form_values.get(key, "") or "").strip()
        extracted = str(autofill_values.get(key, "") or "").strip()
        merged[key] = manual or extracted
    return merged
