"""
tests/test_v2.py
-----------------
v2 모듈 통합 테스트 (최소 10개, 90% 이상 통과 목표)
"""

import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ─────────────────────────────────────────────────────────────────
# 1. content_normalizer: profile 정규화
# ─────────────────────────────────────────────────────────────────
def test_normalize_profile_basic():
    from core.content_normalizer import normalize_profile

    raw = {
        "company_name": "테스트기업",
        "business_item": "AI 솔루션",
        "tam": "1,000억원",
        "sam": "300억원",
        "som": "30억원",
    }
    result = normalize_profile(raw)
    assert result["company"]["name"] == "테스트기업"
    assert result["service"]["name"] == "AI 솔루션"
    assert result["market"]["tam"] == "1,000억원"
    assert isinstance(result["_warnings"], list)


def test_normalize_profile_missing_name_warning():
    from core.content_normalizer import normalize_profile

    raw = {"business_item": "서비스명"}
    result = normalize_profile(raw)
    # company.name 누락 → _warnings에 기록
    assert any("company.name" in w for w in result["_warnings"])


# ─────────────────────────────────────────────────────────────────
# 2. content_normalizer: content.json 정규화
# ─────────────────────────────────────────────────────────────────
def test_normalize_content_basic():
    from core.content_normalizer import normalize_content

    raw = {
        "table_cells": [{"table": 0, "row": 0, "cell": 0, "text": "테스트"}],
        "sections": [{"keyword": "1-1", "lines": ["본문 내용"]}],
    }
    result = normalize_content(raw)
    assert len(result["table_cells"]) == 1
    assert len(result["sections"]) == 1
    assert result["sections"][0]["keyword"] == "1-1"


def test_normalize_content_missing_field_warning():
    from core.content_normalizer import normalize_content

    raw = {
        "table_cells": [{"table": 0, "row": 0}],  # text, cell 누락
        "sections": [],
    }
    result = normalize_content(raw)
    assert "_warnings" in result
    assert any("text" in w or "cell" in w for w in result["_warnings"])


# ─────────────────────────────────────────────────────────────────
# 3. criteria_mapper: 헤딩 매핑
# ─────────────────────────────────────────────────────────────────
def test_map_heading_problem():
    from core.criteria_mapper import map_heading, PROBLEM

    r = map_heading("1-1. 문제인식 및 배경")
    assert r.category == PROBLEM
    assert r.confidence >= 0.9


def test_map_heading_market():
    from core.criteria_mapper import map_heading, MARKET

    r = map_heading("1-2. 목표시장 분석 및 TAM/SAM/SOM")
    assert r.category == MARKET


def test_map_heading_unknown():
    from core.criteria_mapper import map_heading, UNKNOWN

    r = map_heading("기타 항목 xyz")
    assert r.category == UNKNOWN
    assert r.confidence == 0.0


def test_build_mapping_result_coverage():
    from core.criteria_mapper import build_mapping_result, REQUIRED_CATEGORIES

    headings = [
        "1-1. 문제인식",
        "1-2. 시장 분석",
        "2-1. 솔루션",
        "3-1. 비즈니스모델",
        "3-2. 성장전략",
        "4-1. 팀구성",
    ]
    result = build_mapping_result(headings)
    assert result["coverage"] == 1.0
    assert result["missing_categories"] == []
    assert len(result["detail"]) == len(headings)


# ─────────────────────────────────────────────────────────────────
# 4. validator: 검증 리포트
# ─────────────────────────────────────────────────────────────────
def test_validate_content_empty():
    from core.validator import validate_content

    report = validate_content({})
    assert "summary" in report
    assert "issues" in report
    assert "checked_at" in report
    # 빈 content → WARNING 발생 (table_cells, sections 누락)
    assert report["summary"]["warnings"] >= 2


def test_validate_profile_market_logic_error():
    from core.validator import validate_profile

    profile = {
        "company": {"name": "테스트"},
        "service": {"name": "서비스"},
        "market": {"tam": "100억", "sam": "200억", "som": "10억"},  # TAM < SAM → ERROR
    }
    report = validate_profile(profile)
    codes = [i["code"] for i in report["issues"]]
    assert "MARKET_SIZE_LOGIC" in codes
    assert report["summary"]["errors"] >= 1
    assert not report["summary"]["passed"]


def test_validate_profile_passes():
    from core.validator import validate_profile

    profile = {
        "company": {"name": "정상기업"},
        "service": {"name": "AI플랫폼"},
        "market": {"tam": "5000억", "sam": "1000억", "som": "50억"},
        "ceo": {"name": "홍길동"},
        "team": {"current_members": [{"name": "홍길동"}]},
    }
    report = validate_profile(profile)
    # ERROR 없어야 통과
    assert report["summary"]["errors"] == 0
    assert report["summary"]["passed"] is True


# ─────────────────────────────────────────────────────────────────
# 5. validator: template_schema 기반 char_limit 검사
# ─────────────────────────────────────────────────────────────────
def test_validate_content_char_limit():
    from core.validator import validate_content

    long_text = "가" * 600  # 600자
    content = {
        "sections": [{"keyword": "1-1", "lines": [long_text]}],
        "table_cells": [],
    }
    template_schema = {
        "sections": [{"keyword": "1-1", "char_limit_estimate": 400}]
    }
    report = validate_content(content, template_schema=template_schema)
    codes = [i["code"] for i in report["issues"]]
    assert "CHAR_LIMIT_EXCEEDED" in codes


# ─────────────────────────────────────────────────────────────────
# 6. analyzer: generate_template_schema (DOCX 없이 구조 테스트)
# ─────────────────────────────────────────────────────────────────
def test_generate_template_schema_output_path():
    """DOCX가 없어도 함수 임포트 및 시그니처 확인."""
    from core.analyzer import generate_template_schema
    import inspect

    sig = inspect.signature(generate_template_schema)
    params = list(sig.parameters.keys())
    assert "docx_path" in params
    assert "output_path" in params


# ─────────────────────────────────────────────────────────────────
# 7. load_and_normalize: 포맷 자동 감지
# ─────────────────────────────────────────────────────────────────
def test_load_and_normalize_content_format():
    from core.content_normalizer import load_and_normalize

    data = {
        "table_cells": [],
        "sections": [{"keyword": "1-1", "lines": ["내용"]}],
    }
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump(data, f)
        path = f.name

    try:
        result = load_and_normalize(path)
        assert "sections" in result
        assert "table_cells" in result
    finally:
        os.unlink(path)


def test_load_and_normalize_profile_format():
    from core.content_normalizer import load_and_normalize

    data = {"company_name": "프로파일기업", "business_item": "서비스"}
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump(data, f)
        path = f.name

    try:
        result = load_and_normalize(path)
        assert "company" in result
        assert result["company"]["name"] == "프로파일기업"
    finally:
        os.unlink(path)


# ─────────────────────────────────────────────────────────────────
# 8. map_all_headings + get_missing_categories
# ─────────────────────────────────────────────────────────────────
def test_get_missing_categories():
    from core.criteria_mapper import map_all_headings, get_missing_categories, TEAM

    headings = ["1-1. 문제인식", "1-2. 시장", "2-1. 솔루션", "3-1. BM", "3-2. 성장"]
    # TEAM 누락
    mapped = map_all_headings(headings)
    missing = get_missing_categories(mapped)
    assert TEAM in missing


# ─────────────────────────────────────────────────────────────────
# 9. validate_content: budget 합계 불일치
# ─────────────────────────────────────────────────────────────────
def test_validate_budget_mismatch():
    from core.validator import validate_profile

    profile = {
        "company": {"name": "예산테스트"},
        "service": {"name": "서비스"},
        "budget": {
            "total": "1억",
            "government": "8000만",
            "self_funding": "1000만",   # 8000 + 1000 = 9000만 ≠ 1억
        },
    }
    report = validate_profile(profile)
    codes = [i["code"] for i in report["issues"]]
    assert "BUDGET_SUM_MISMATCH" in codes


# ─────────────────────────────────────────────────────────────────
# 10. section_mapping in build_mapping_result
# ─────────────────────────────────────────────────────────────────
def test_build_mapping_section_codes():
    from core.criteria_mapper import build_mapping_result, PROBLEM

    result = build_mapping_result(
        headings=["1-1. 문제인식"],
        section_codes=["1-1", "2-1"],
    )
    assert "section_mapping" in result
    assert result["section_mapping"]["1-1"] == PROBLEM
