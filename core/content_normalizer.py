"""
core/content_normalizer.py
---------------------------
v2 모듈 1: 입력 데이터 표준화

두 가지 입력 포맷을 공통 스키마로 정규화한다:
  1. content.json  — 기존 주입용 포맷 (table_cells / sections 등)
  2. company_info  — 기업정보 JSON (AI 생성용 프로필)

출력: normalized_content.json / normalized_profile.json
"""

from __future__ import annotations

import json
import os
from typing import Any

# ── 공통 스키마 정의 ──────────────────────────────────────────────
PROFILE_SCHEMA: dict[str, dict] = {
    "company": {
        "required": ["name"],
        "optional": ["representative", "establishment_date", "business_number",
                     "location", "industry", "business_type"],
        "defaults": {"industry": "", "business_type": ""},
    },
    "ceo": {
        "required": ["name"],
        "optional": ["education", "career", "certifications", "background"],
        "defaults": {"education": [], "career": [], "certifications": []},
    },
    "service": {
        "required": ["name"],
        "optional": ["description", "features", "tech_stack",
                     "development_status", "differentiators"],
        "defaults": {"features": [], "differentiators": []},
    },
    "market": {
        "required": [],
        "optional": ["tam", "sam", "som", "competitors", "target_customer"],
        "defaults": {"tam": "", "sam": "", "som": "", "competitors": []},
    },
    "bm": {
        "required": [],
        "optional": ["revenue_streams", "pricing", "target_customer"],
        "defaults": {"revenue_streams": []},
    },
    "budget": {
        "required": [],
        "optional": ["total", "government", "self_funding", "items"],
        "defaults": {"items": []},
    },
    "team": {
        "required": [],
        "optional": ["current_members", "planned_members"],
        "defaults": {"current_members": [], "planned_members": []},
    },
}

# ── 필드 별칭 맵 (기존 키 → 표준 키) ─────────────────────────────
_COMPANY_ALIASES = {
    "company_name": "name",
    "representative": "representative",
    "ceo_name": "representative",
}
_SERVICE_ALIASES = {
    "business_item": "name",
    "item_name": "name",
    "solution_overview": "description",
}
_MARKET_ALIASES = {
    "target_market": "target_customer",
    "market_problem": "problem",
}


def _merge_aliases(raw: dict, aliases: dict) -> dict:
    """별칭 키를 표준 키로 변환하고 원본과 병합한다."""
    result = dict(raw)
    for alias, standard in aliases.items():
        if alias in raw and standard not in result:
            result[standard] = raw[alias]
    return result


def normalize_profile(raw: dict) -> dict:
    """
    기업정보 JSON(company_info)을 표준 profile 스키마로 정규화한다.

    Args:
        raw: company_info_sample.json 형식 또는 company_profile.yaml 형식 dict

    Returns:
        정규화된 profile dict:
        {
          "company": {...}, "ceo": {...}, "service": {...},
          "market": {...}, "bm": {...}, "budget": {...}, "team": {...},
          "_warnings": [...],
          "_source_keys": [...]
        }
    """
    warnings: list[str] = []
    source_keys = list(raw.keys())

    # ── company 블록 ──
    company = _merge_aliases(raw, _COMPANY_ALIASES)
    normalized_company = {}
    for field, default in {**{"name": "", "representative": ""},
                           **dict.fromkeys(PROFILE_SCHEMA["company"]["optional"], "")}.items():
        normalized_company[field] = company.get(field, default)
    # 최상위 company_name 지원
    if not normalized_company["name"] and "company_name" in raw:
        normalized_company["name"] = raw["company_name"]

    # ── ceo 블록 ──
    ceo_raw = raw.get("ceo", {})
    if not ceo_raw and "representative" in raw:
        ceo_raw = {"name": raw["representative"]}
    normalized_ceo = {
        "name": ceo_raw.get("name", raw.get("representative", "")),
        "education": _ensure_list(ceo_raw.get("education", raw.get("ceo_education", []))),
        "career": _ensure_list(ceo_raw.get("career", raw.get("ceo_career", []))),
        "certifications": _ensure_list(ceo_raw.get("certifications", [])),
        "background": ceo_raw.get("background", raw.get("ceo_background", "")),
    }

    # ── service 블록 ──
    svc_raw = _merge_aliases(raw.get("service", raw), _SERVICE_ALIASES)
    normalized_service = {
        "name": svc_raw.get("name", raw.get("business_item", raw.get("item_name", ""))),
        "description": svc_raw.get("description", raw.get("solution_overview", "")),
        "features": _ensure_list(svc_raw.get("features", raw.get("solution_steps", []))),
        "tech_stack": svc_raw.get("tech_stack", raw.get("tech_stack", "")),
        "development_status": svc_raw.get("development_status", raw.get("development_status", "")),
        "differentiators": _ensure_list(svc_raw.get("differentiators", [])),
    }

    # ── market 블록 ──
    mkt_raw = raw.get("market", {})
    normalized_market = {
        "tam": _extract_market_value(mkt_raw.get("tam", raw.get("tam", ""))),
        "sam": _extract_market_value(mkt_raw.get("sam", raw.get("sam", ""))),
        "som": _extract_market_value(mkt_raw.get("som", raw.get("som", ""))),
        "target_customer": mkt_raw.get(
            "target_customer", raw.get("target_market", raw.get("target_customer", ""))
        ),
        "competitors": _parse_competitors(
            mkt_raw.get("competitors", raw.get("competitors", ""))
        ),
        "problem": raw.get("market_problem", mkt_raw.get("problem", "")),
    }

    # ── bm 블록 ──
    bm_raw = raw.get("business_model", raw.get("bm", {}))
    normalized_bm = {
        "revenue_streams": _ensure_list(
            bm_raw.get("revenue_streams", raw.get("revenue_streams", []))
        ),
        "pricing": bm_raw.get("pricing", raw.get("pricing", "")),
        "target_customer": bm_raw.get(
            "target_customer", normalized_market["target_customer"]
        ),
    }

    # ── budget 블록 ──
    budget_raw = raw.get("budget", {})
    normalized_budget = {
        "total": _to_number(budget_raw.get("total", raw.get("budget_total", 0))),
        "government": _to_number(
            budget_raw.get("government", raw.get("government_funding", 0))
        ),
        "self_funding": _to_number(
            budget_raw.get("self", budget_raw.get("self_funding", raw.get("self_funding", 0)))
        ),
        "items": _ensure_list(budget_raw.get("items", [])),
    }

    # ── team 블록 ──
    team_raw = raw.get("team", {})
    normalized_team = {
        "current_members": _ensure_list(
            team_raw.get("current", team_raw.get("current_members", []))
        ),
        "planned_members": _ensure_list(
            team_raw.get("planned", team_raw.get("planned_members", []))
        ),
    }

    # ── 누락 필드 경고 ──
    if not normalized_company["name"]:
        warnings.append("company.name 누락 — 기업명이 없습니다.")
    if not normalized_service["name"]:
        warnings.append("service.name 누락 — 사업 아이템명이 없습니다.")
    if not normalized_market["tam"] and not normalized_market["sam"]:
        warnings.append("market.tam/sam 누락 — 시장 규모 데이터가 없습니다.")
    if not normalized_team["current_members"]:
        warnings.append("team.current_members 누락 — 현재 팀원 정보가 없습니다.")

    return {
        "company":  normalized_company,
        "ceo":      normalized_ceo,
        "service":  normalized_service,
        "market":   normalized_market,
        "bm":       normalized_bm,
        "budget":   normalized_budget,
        "team":     normalized_team,
        "_warnings":     warnings,
        "_source_keys":  source_keys,
    }


def normalize_content(raw: dict) -> dict:
    """
    기존 content.json을 검증·정규화한다.

    Args:
        raw: content.json 형식 dict

    Returns:
        정규화된 content dict (경고 포함)
    """
    warnings: list[str] = []

    # 필수 최상위 키
    result = {
        "delete_tables": _ensure_list(raw.get("delete_tables", [])),
        "table_cells":   _ensure_list(raw.get("table_cells", [])),
        "table_rows":    _ensure_list(raw.get("table_rows", [])),
        "sections":      _ensure_list(raw.get("sections", [])),
        "images":        _ensure_list(raw.get("images", [])),
        "_comment":      raw.get("_comment", ""),
    }

    # table_cells 검증
    for i, cell in enumerate(result["table_cells"]):
        if not isinstance(cell, dict):
            warnings.append(f"table_cells[{i}]: dict 타입 아님")
            continue
        for req in ("table", "row", "cell", "text"):
            if req not in cell:
                warnings.append(f"table_cells[{i}]: '{req}' 필드 없음")

    # sections 검증
    for i, sec in enumerate(result["sections"]):
        if not isinstance(sec, dict):
            warnings.append(f"sections[{i}]: dict 타입 아님")
            continue
        if "keyword" not in sec:
            warnings.append(f"sections[{i}]: 'keyword' 없음")
        if "lines" not in sec or not sec["lines"]:
            warnings.append(f"sections[{i}] keyword={sec.get('keyword')!r}: 'lines' 비어 있음")

    if warnings:
        result["_warnings"] = warnings

    return result


def load_and_normalize(path: str) -> dict:
    """
    JSON/YAML 파일을 로드하고 포맷을 자동 감지하여 정규화한다.

    content.json 형식(table_cells 포함)이면 normalize_content(),
    company_info 형식이면 normalize_profile()을 적용한다.
    """
    _, ext = os.path.splitext(path.lower())
    with open(path, encoding="utf-8") as f:
        if ext in (".yaml", ".yml"):
            try:
                import yaml
                raw = yaml.safe_load(f)
            except ImportError:
                raise RuntimeError("pyyaml 패키지가 필요합니다: pip install pyyaml")
        else:
            raw = json.load(f)

    # 포맷 자동 감지: table_cells / sections 최상위 키 → content.json
    if "table_cells" in raw or "sections" in raw:
        return normalize_content(raw)
    return normalize_profile(raw)


def save_normalized(data: dict, output_path: str) -> None:
    """정규화된 dict를 JSON으로 저장한다."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── 내부 헬퍼 ────────────────────────────────────────────────────
def _ensure_list(v: Any) -> list:
    if isinstance(v, list):
        return v
    if v is None or v == "":
        return []
    return [v]


def _to_number(v: Any) -> float:
    """한국어 금액 문자열을 float으로 변환. 원 단위 정수 그대로 반환."""
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        import re
        v = v.replace(",", "")
        m = re.search(r"[\d.]+", v)
        return float(m.group()) if m else 0.0
    return 0.0


def _extract_market_value(v: Any) -> str:
    """TAM/SAM/SOM 값에서 금액 문자열을 추출한다."""
    if isinstance(v, dict):
        return str(v.get("value", v.get("amount", "")))
    return str(v) if v else ""


def _parse_competitors(v: Any) -> list:
    """경쟁사 정보를 list[dict] 형식으로 변환한다."""
    if isinstance(v, list):
        return v
    if isinstance(v, str) and v:
        # "공공: KOTRA, 무역협회 등. 민간: ..." 형식 → 단일 항목
        return [{"name": "경쟁사", "description": v}]
    return []
