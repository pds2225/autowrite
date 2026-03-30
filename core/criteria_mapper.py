"""
core/criteria_mapper.py
------------------------
v2 모듈 3: 평가항목 매핑

DOCX 헤딩 또는 공고 항목명을 내부 표준 평가항목으로 매핑한다.
규칙 기반 우선, 불확실한 경우만 "UNKNOWN" 처리.

내부 표준 항목:
  PROBLEM   — 문제인식 / 배경 / 시장 현황
  SOLUTION  — 솔루션 / 기술 / 서비스 / 아이템
  MARKET    — 시장분석 / TAM/SAM/SOM / 경쟁사
  BM        — 비즈니스모델 / 수익구조 / 가격전략
  SCALEUP   — 성장전략 / 사업화계획 / 로드맵 / 자금
  TEAM      — 팀구성 / 대표자 역량 / 조직계획
  META      — 사업개요 / 일반현황 (표 헤더류)
  UNKNOWN   — 매핑 불가
"""

from __future__ import annotations

import re
from typing import NamedTuple


# ── 표준 카테고리 상수 ─────────────────────────────────────────────
PROBLEM  = "PROBLEM"
SOLUTION = "SOLUTION"
MARKET   = "MARKET"
BM       = "BM"
SCALEUP  = "SCALEUP"
TEAM     = "TEAM"
META     = "META"
UNKNOWN  = "UNKNOWN"

ALL_CATEGORIES = [PROBLEM, SOLUTION, MARKET, BM, SCALEUP, TEAM]
REQUIRED_CATEGORIES = [PROBLEM, SOLUTION, MARKET, BM, SCALEUP, TEAM]


class MappingResult(NamedTuple):
    category: str       # 표준 카테고리
    confidence: float   # 0.0 ~ 1.0
    matched_rule: str   # 매칭된 규칙 설명


# ── 규칙 정의 (순서 중요: 특수 규칙 먼저) ─────────────────────────
# (패턴, 카테고리, 설명, 신뢰도)
_RULES: list[tuple[str, str, str, float]] = [
    # META — 일반현황·사업개요
    (r"일반\s*현황|사업\s*개요|신청\s*정보|과제\s*개요",          META,    "일반현황/사업개요",   1.0),
    (r"폐업\s*이력|재도전|창업\s*이력",                           META,    "폐업이력",            1.0),

    # PROBLEM — 문제인식
    (r"문제\s*인식|배경|현황\s*및\s*필요성|시장\s*실패|pain",     PROBLEM, "문제인식/배경",       1.0),
    (r"1\s*[-–]\s*1|1\.1",                                        PROBLEM, "섹션번호 1-1",        0.9),

    # MARKET — 시장분석
    (r"시장\s*분석|목표\s*시장|tam|sam|som|시장\s*규모|경쟁",     MARKET,  "시장분석/TAM-SAM-SOM",1.0),
    (r"1\s*[-–]\s*2|1\.2",                                        MARKET,  "섹션번호 1-2",        0.9),

    # SOLUTION — 솔루션/아이템
    (r"솔루션|기술|서비스|아이템|제품|준비\s*현황|개발\s*현황",   SOLUTION,"솔루션/아이템",       1.0),
    (r"2\s*[-–]\s*[12]|2\.[12]",                                  SOLUTION,"섹션번호 2-1/2-2",    0.9),
    (r"구체화|실현|차별",                                          SOLUTION,"구체화/차별화",       0.85),

    # BM — 비즈니스모델
    (r"비즈니스\s*모델|수익\s*구조|수익\s*모델|bm|가격|pricing",  BM,      "BM/수익구조",         1.0),
    (r"3\s*[-–]\s*1|3\.1",                                        BM,      "섹션번호 3-1",        0.9),

    # SCALEUP — 성장전략/자금
    (r"성장\s*전략|사업화|스케일\s*업|scale|추진\s*일정|로드맵",  SCALEUP, "성장전략/로드맵",     1.0),
    (r"자금|예산|사업비|정부\s*지원|집행",                         SCALEUP, "자금/예산",           0.95),
    (r"3\s*[-–]\s*[23]|3\s*[-–]\s*3|3\.[23]",                    SCALEUP, "섹션번호 3-2/3-3",    0.9),

    # TEAM — 팀구성
    (r"팀|조직|대표|구성원|인력|역량|경력|학력",                   TEAM,    "팀/조직구성",         1.0),
    (r"4\s*[-–]\s*[12]|4\.[12]",                                  TEAM,    "섹션번호 4-1/4-2",    0.9),
]

# 컴파일된 규칙 캐시
_COMPILED_RULES: list[tuple[re.Pattern, str, str, float]] | None = None


def _get_compiled_rules():
    global _COMPILED_RULES
    if _COMPILED_RULES is None:
        _COMPILED_RULES = [
            (re.compile(pattern, re.IGNORECASE), cat, desc, conf)
            for pattern, cat, desc, conf in _RULES
        ]
    return _COMPILED_RULES


def map_heading(heading_text: str) -> MappingResult:
    """
    단일 헤딩 텍스트를 내부 표준 카테고리로 매핑한다.

    Args:
        heading_text: DOCX 헤딩 또는 공고 항목명 문자열

    Returns:
        MappingResult(category, confidence, matched_rule)

    Examples:
        map_heading("1-1. 문제인식 및 배경")
        → MappingResult(category='PROBLEM', confidence=1.0, ...)

        map_heading("3-3-3. 자금 집행 계획")
        → MappingResult(category='SCALEUP', confidence=0.95, ...)
    """
    txt = heading_text.strip()
    if not txt:
        return MappingResult(UNKNOWN, 0.0, "빈 텍스트")

    best: MappingResult | None = None
    for pattern, cat, desc, conf in _get_compiled_rules():
        if pattern.search(txt):
            result = MappingResult(cat, conf, desc)
            if best is None or result.confidence > best.confidence:
                best = result

    return best if best else MappingResult(UNKNOWN, 0.0, "매칭 규칙 없음")


def map_all_headings(headings: list[str]) -> dict[str, list[str]]:
    """
    헤딩 목록 전체를 매핑하고 카테고리별로 그룹화한다.

    Args:
        headings: 헤딩 텍스트 목록

    Returns:
        {카테고리: [헤딩 텍스트, ...]} 형식 dict
        예: {"PROBLEM": ["1-1 문제인식"], "MARKET": ["1-2 시장분석"], ...}
    """
    result: dict[str, list[str]] = {cat: [] for cat in [*ALL_CATEGORIES, META, UNKNOWN]}
    for h in headings:
        mapped = map_heading(h)
        result[mapped.category].append(h)
    return result


def get_missing_categories(mapped: dict[str, list[str]]) -> list[str]:
    """
    필수 카테고리 중 매핑된 헤딩이 없는 항목 목록을 반환한다.

    Args:
        mapped: map_all_headings() 출력

    Returns:
        누락된 카테고리 이름 목록 (예: ["MARKET", "SCALEUP"])
    """
    return [cat for cat in REQUIRED_CATEGORIES if not mapped.get(cat)]


def build_mapping_result(
    headings: list[str],
    section_codes: list[str] | None = None,
) -> dict:
    """
    헤딩 목록 전체에 대한 매핑 보고서를 생성한다.

    Args:
        headings:      DOCX에서 추출한 헤딩 텍스트 목록
        section_codes: content.json sections의 keyword 목록 (선택)

    Returns:
        mapping_result.json 형식 dict:
        {
          "mapped": {카테고리: [헤딩, ...]},
          "missing_categories": [...],
          "detail": [{heading, category, confidence, rule}, ...],
          "section_mapping": {keyword: category},  (section_codes 제공 시)
          "coverage": 0.0~1.0
        }
    """
    detail = []
    for h in headings:
        r = map_heading(h)
        detail.append({
            "heading":    h,
            "category":  r.category,
            "confidence": round(r.confidence, 2),
            "rule":       r.matched_rule,
        })

    mapped = map_all_headings(headings)
    missing = get_missing_categories(mapped)
    found = len(REQUIRED_CATEGORIES) - len(missing)
    coverage = round(found / len(REQUIRED_CATEGORIES), 2)

    result: dict = {
        "mapped":             {k: v for k, v in mapped.items() if v},
        "missing_categories": missing,
        "detail":             detail,
        "coverage":           coverage,
    }

    if section_codes:
        sec_map = {}
        for kw in section_codes:
            r = map_heading(kw)
            sec_map[kw] = r.category
        result["section_mapping"] = sec_map

    return result
