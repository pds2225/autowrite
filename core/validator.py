"""
core/validator.py
------------------
v2 모듈 6: 검증/QA 모듈

content.json 또는 정규화된 profile을 입력받아
누락·분량·수치 일관성을 검사하고 validation_report.json을 생성한다.

경고 레벨:
  ERROR   — 주입 또는 AI 생성이 실패할 수 있는 심각한 문제
  WARNING — 품질 저하 가능성 (빈 섹션, 수치 불일치 등)
  INFO    — 개선 권고사항
"""

from __future__ import annotations

import re
from typing import Any


# ── 레벨 상수 ─────────────────────────────────────────────────────
ERROR   = "ERROR"
WARNING = "WARNING"
INFO    = "INFO"


class Issue:
    __slots__ = ("level", "code", "message", "field")

    def __init__(self, level: str, code: str, message: str, field: str = ""):
        self.level   = level
        self.code    = code
        self.message = message
        self.field   = field

    def to_dict(self) -> dict:
        d = {"level": self.level, "code": self.code, "message": self.message}
        if self.field:
            d["field"] = self.field
        return d


# ── 한국어 금액 파서 ──────────────────────────────────────────────
def _parse_amount(v: Any) -> float:
    """한국어 금액 문자열을 원 단위 float으로 변환한다."""
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace(",", "")
    val = 0.0
    # 조
    m = re.search(r"([\d.]+)\s*조", s)
    if m:
        val += float(m.group(1)) * 1e12
    # 억
    m = re.search(r"([\d.]+)\s*억", s)
    if m:
        val += float(m.group(1)) * 1e8
    # 만
    m = re.search(r"([\d.]+)\s*만", s)
    if m:
        val += float(m.group(1)) * 1e4
    if val > 0:
        return val
    # 순수 숫자
    m = re.search(r"[\d.]+", s)
    return float(m.group()) if m else 0.0


# ── 검증 함수 ─────────────────────────────────────────────────────

def _check_content(content: dict) -> list[Issue]:
    """content.json 구조 검증."""
    issues: list[Issue] = []

    # 필수 최상위 키
    for key in ("table_cells", "sections"):
        if not content.get(key):
            issues.append(Issue(
                WARNING, "MISSING_KEY",
                f"'{key}' 키가 없거나 비어 있습니다.",
                field=key,
            ))

    # 섹션 빈 내용 검사
    sections = content.get("sections", [])
    empty_sections = [
        s.get("keyword", f"[{i}]")
        for i, s in enumerate(sections)
        if not s.get("lines")
    ]
    if empty_sections:
        issues.append(Issue(
            WARNING, "EMPTY_SECTION",
            f"내용이 비어 있는 섹션: {', '.join(empty_sections)}",
            field="sections",
        ))

    # 섹션 분량 추정 (라인 수 기반 ≈ 500자 이상이면 overflow 가능성)
    for sec in sections:
        lines = sec.get("lines", [])
        total_chars = sum(
            len(l.get("text", l) if isinstance(l, dict) else l)
            for l in lines
        )
        if total_chars > 1500:
            issues.append(Issue(
                WARNING, "SECTION_OVERFLOW",
                f"섹션 {sec.get('keyword')!r}: 추정 {total_chars}자 — 분량 초과 가능성",
                field=f"sections.{sec.get('keyword')}",
            ))

    # table_cells 빈 텍스트
    for cell in content.get("table_cells", []):
        if not cell.get("text", "").strip():
            coord = f"표{cell.get('table')}-행{cell.get('row')}-셀{cell.get('cell')}"
            issues.append(Issue(
                WARNING, "EMPTY_CELL",
                f"빈 셀 값: {coord}",
                field="table_cells",
            ))

    return issues


def _check_profile(profile: dict) -> list[Issue]:
    """정규화된 profile 검증 (핵심 필수항목)."""
    issues: list[Issue] = []

    # 기업명
    if not profile.get("company", {}).get("name"):
        issues.append(Issue(ERROR, "MISSING_COMPANY_NAME", "기업명(company.name)이 없습니다.", "company.name"))

    # 대표자명
    if not profile.get("ceo", {}).get("name"):
        issues.append(Issue(WARNING, "MISSING_CEO_NAME", "대표자명(ceo.name)이 없습니다.", "ceo.name"))

    # 서비스명
    if not profile.get("service", {}).get("name"):
        issues.append(Issue(ERROR, "MISSING_SERVICE_NAME", "사업 아이템명(service.name)이 없습니다.", "service.name"))

    # 시장 규모 논리 검사: TAM ≥ SAM ≥ SOM
    market = profile.get("market", {})
    tam = _parse_amount(market.get("tam", 0))
    sam = _parse_amount(market.get("sam", 0))
    som = _parse_amount(market.get("som", 0))

    if tam > 0 and sam > 0 and tam < sam:
        issues.append(Issue(
            ERROR, "MARKET_SIZE_LOGIC",
            f"TAM({market['tam']}) < SAM({market['sam']}) — 시장 규모 역전",
            field="market",
        ))
    if sam > 0 and som > 0 and sam < som:
        issues.append(Issue(
            ERROR, "MARKET_SIZE_LOGIC",
            f"SAM({market['sam']}) < SOM({market['som']}) — 시장 규모 역전",
            field="market",
        ))
    if not market.get("tam") and not market.get("sam"):
        issues.append(Issue(WARNING, "MISSING_MARKET_SIZE", "시장 규모(TAM/SAM/SOM)가 없습니다.", "market"))

    # 예산 합계 검증
    budget = profile.get("budget", {})
    total = _parse_amount(budget.get("total", 0))
    gov   = _parse_amount(budget.get("government", 0))
    self_ = _parse_amount(budget.get("self_funding", budget.get("self", 0)))
    if total > 0 and gov > 0 and self_ > 0:
        calc_total = gov + self_
        if abs(calc_total - total) / total > 0.05:  # 5% 이상 차이
            issues.append(Issue(
                WARNING, "BUDGET_SUM_MISMATCH",
                f"예산 합계 불일치: 정부지원금({gov:,.0f}) + 자기부담금({self_:,.0f}) = {calc_total:,.0f} ≠ 총액({total:,.0f})",
                field="budget",
            ))

    # 팀원 존재 여부
    team = profile.get("team", {})
    if not team.get("current_members") and not team.get("planned_members"):
        issues.append(Issue(WARNING, "MISSING_TEAM", "팀 구성원 정보가 없습니다.", "team"))

    # 대표자 이력
    ceo = profile.get("ceo", {})
    if not ceo.get("career") and not ceo.get("background"):
        issues.append(Issue(
            INFO, "MISSING_CEO_CAREER",
            "대표자 경력 정보(ceo.career/background)가 없습니다. 심사에서 감점 요인이 될 수 있습니다.",
            "ceo",
        ))

    # 매출 성장성 (3개년 연속 성장 여부)
    growth = profile.get("growth_strategy", {})
    stages = growth.get("stages", []) if isinstance(growth, dict) else []
    if stages:
        revenues = []
        for s in stages:
            rev = _parse_amount(s.get("revenue", s.get("매출", 0)))
            if rev > 0:
                revenues.append(rev)
        if len(revenues) >= 2:
            for i in range(len(revenues) - 1):
                if revenues[i] >= revenues[i + 1]:
                    issues.append(Issue(
                        WARNING, "REVENUE_NOT_GROWING",
                        f"매출 성장성 미흡: {stages[i].get('stage', i+1)}단계({revenues[i]:,.0f}) "
                        f"≥ {stages[i+1].get('stage', i+2)}단계({revenues[i+1]:,.0f})",
                        field="growth_strategy",
                    ))
                    break

    return issues


def _check_combined(content: dict, profile: dict) -> list[Issue]:
    """content와 profile을 교차 검증한다."""
    issues: list[Issue] = []

    # 섹션 수 vs 프로필 완성도
    sections = content.get("sections", [])
    empty_count = sum(1 for s in sections if not s.get("lines"))
    if empty_count > len(sections) // 2:
        issues.append(Issue(
            WARNING, "TOO_MANY_EMPTY_SECTIONS",
            f"전체 {len(sections)}개 섹션 중 {empty_count}개가 비어 있습니다.",
            field="sections",
        ))

    return issues


def validate_content(
    content: dict,
    profile: dict | None = None,
    template_schema: dict | None = None,
) -> dict:
    """
    content.json (및 선택적으로 profile)을 종합 검증한다.

    Args:
        content:         normalize_content() 결과 또는 raw content.json dict
        profile:         normalize_profile() 결과 (선택)
        template_schema: generate_template_schema() 결과 (선택, 분량 검사용)

    Returns:
        validation_report.json 형식 dict:
        {
          "summary": {"errors": N, "warnings": N, "infos": N, "passed": bool},
          "issues": [{level, code, message, field?}, ...],
          "checked_at": "ISO datetime"
        }
    """
    import datetime

    issues: list[Issue] = []
    issues.extend(_check_content(content))
    if profile:
        issues.extend(_check_profile(profile))
        issues.extend(_check_combined(content, profile))

    # template_schema 기반 섹션 char_limit 검사
    if template_schema:
        schema_sections = {
            s.get("keyword"): s.get("char_limit_estimate", 0)
            for s in template_schema.get("sections", [])
        }
        for sec in content.get("sections", []):
            kw = sec.get("keyword", "")
            limit = schema_sections.get(kw, 0)
            if limit:
                total_chars = sum(
                    len(l.get("text", l) if isinstance(l, dict) else l)
                    for l in sec.get("lines", [])
                )
                if total_chars > limit * 1.2:
                    issues.append(Issue(
                        WARNING, "CHAR_LIMIT_EXCEEDED",
                        f"섹션 {kw!r}: {total_chars}자 > 권장 {limit}자 (120% 초과)",
                        field=f"sections.{kw}",
                    ))

    errors   = sum(1 for i in issues if i.level == ERROR)
    warnings = sum(1 for i in issues if i.level == WARNING)
    infos    = sum(1 for i in issues if i.level == INFO)

    return {
        "summary": {
            "errors":   errors,
            "warnings": warnings,
            "infos":    infos,
            "passed":   errors == 0,
        },
        "issues":     [i.to_dict() for i in issues],
        "checked_at": datetime.datetime.now().isoformat(timespec="seconds"),
    }


def validate_profile(profile: dict) -> dict:
    """
    profile만 단독으로 검증한다. (content 없이 사용 가능)

    Returns:
        validation_report 형식 dict
    """
    return validate_content({}, profile=profile)
