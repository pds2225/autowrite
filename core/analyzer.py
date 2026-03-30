"""
bizplan_injector/core/analyzer.py
-----------------------------------
DOCX 양식 구조 자동 분석기

주요 기능:
- 표 수, 행/열, 셀 내용 출력
- 단락 헤딩 목록 추출
- content.json 스켈레톤 자동 생성
- template_schema.json 생성 (v2)
"""

import zipfile
import os
import json
import re
from lxml import etree

WNS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS  = {"w": WNS}


def _w(tag: str) -> str:
    """Word XML 네임스페이스가 포함된 완전한 태그명 반환. 예) 'p' → '{...}p'"""
    return f"{{{WNS}}}{tag}"


def cell_text(cell: etree._Element) -> str:
    """셀(<w:tc>) 내 모든 텍스트를 이어 붙여 반환."""
    return "".join(r.text or "" for r in cell.iter(_w("t")))


def para_text(p: etree._Element) -> str:
    """단락(<w:p>) 내 모든 텍스트를 이어 붙여 반환."""
    return "".join(r.text or "" for r in p.iter(_w("t")))


def analyze_docx(docx_path: str, verbose: bool = True) -> dict:
    """
    DOCX 파일의 표 구조와 단락 헤딩을 분석하여 반환.

    Args:
        docx_path: 분석할 DOCX 파일 경로
        verbose:   True이면 분석 결과를 콘솔에 출력 (기본 True)

    Returns:
        {
          "tables":   [{"index": int, "row_count": int, "rows": [[str, ...], ...]}, ...],
          "headings": [{"index": int, "text": str}, ...]
        }

    Notes:
        - 표 미리보기는 최대 5행까지만 포함합니다.
        - 헤딩은 100자 미만의 단락 텍스트를 기준으로 추출합니다.
    """
    with zipfile.ZipFile(docx_path, "r") as z:
        with z.open("word/document.xml") as f:
            tree = etree.parse(f)

    root = tree.getroot()
    body = root.find(_w("body"), NS)

    tables_info = []
    for t_idx, tbl in enumerate(body.findall(_w("tbl"), NS)):
        rows = tbl.findall(_w("tr"), NS)
        table_data = {"index": t_idx, "row_count": len(rows), "rows": []}
        for r_idx, row in enumerate(rows[:5]):  # 최대 5행 미리보기
            cells = row.findall(_w("tc"), NS)
            row_data = [cell_text(c)[:60].strip() for c in cells]
            table_data["rows"].append(row_data)
        tables_info.append(table_data)

    headings = []
    all_body = list(body)
    for i, elem in enumerate(all_body):
        if elem.tag == _w("p"):
            txt = para_text(elem).strip()
            if txt and len(txt) < 100:
                headings.append({"index": i, "text": txt})

    result = {"tables": tables_info, "headings": headings}

    if verbose:
        print(f"\n{'='*60}")
        print(f"📄 파일: {os.path.basename(docx_path)}")
        print(f"{'='*60}")
        print(f"\n📊 표 목록 ({len(tables_info)}개):")
        for t in tables_info:
            first_row = t["rows"][0] if t["rows"] else []
            sample = " | ".join(c[:20] for c in first_row[:4] if c)
            print(f"  표{t['index']:02d}: {t['row_count']}행  [{sample}]")

        print(f"\n📝 주요 단락 (헤딩):")
        for h in headings[:30]:
            print(f"  [{h['index']:03d}] {h['text'][:70]}")

    return result


def generate_content_skeleton(docx_path: str, output_path: str = "content_skeleton.json") -> dict:
    """
    DOCX 분석 결과를 바탕으로 content.json 스켈레톤을 자동 생성.

    표의 헤더 행 셀과 섹션 키워드(숫자-숫자 패턴)를 탐지하여
    값만 채우면 되는 초안 JSON 파일을 생성합니다.

    Args:
        docx_path:   분석할 DOCX 파일 경로
        output_path: 생성할 JSON 파일 경로 (기본: "content_skeleton.json")

    Returns:
        생성된 스켈레톤 딕셔너리

    Notes:
        - 표 셀 스켈레톤은 각 표의 첫 3행까지만 포함합니다.
        - 섹션 키워드는 "1-1", "1-2" 등 사전 정의된 목록 기준으로 탐지합니다.
        - 생성된 JSON의 "_hint" 필드는 작성 안내용 주석이므로 주입 시 무시됩니다.
    """
    result = analyze_docx(docx_path, verbose=False)

    skeleton = {
        "_comment": "이 파일에 내용을 채워서 inject.py를 실행하세요",
        "delete_tables": [0, -1],
        "table_cells": [],
        "table_rows": [],
        "sections": [],
    }

    # 표 셀 스켈레톤
    for t in result["tables"]:
        for r_idx, row in enumerate(t["rows"][:3]):
            for c_idx, cell_val in enumerate(row):
                if cell_val:
                    skeleton["table_cells"].append({
                        "_hint": f"표{t['index']} 행{r_idx} 셀{c_idx}: 현재값='{cell_val[:30]}'",
                        "table": t["index"],
                        "row": r_idx,
                        "cell": c_idx,
                        "text": "",
                        "align": "left",
                        "size": 18,
                    })

    # 섹션 스켈레톤
    section_keywords = ["1-1", "1-2", "2-1", "2-2", "3-1", "3-2", "3-3-3", "4-1-1", "4-2"]
    for h in result["headings"]:
        for kw in section_keywords:
            if kw in h["text"]:
                skeleton["sections"].append({
                    "_hint": f"인덱스 {h['index']}: {h['text'][:50]}",
                    "keyword": kw,
                    "lines": ["내용을 여기에 작성하세요."],
                    "size": 18,
                })

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(skeleton, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 스켈레톤 생성: {output_path}")
    return skeleton


# ── v2: template_schema 생성 ─────────────────────────────────────

# 섹션 헤딩 패턴 (예: "1-1", "2-3", "3-3-3")
_HEADING_RE = re.compile(r"^\s*(\d+\s*[-–]\s*\d+(?:\s*[-–]\s*\d+)?)")
# 파란색 텍스트 여부 판별용 테마 색 (Word 기본 accent/theme colors)
_BLUE_HEX = {"4472C4", "5B9BD5", "2E75B6", "1F497D", "17375E", "0070C0", "00B0F0"}


def _is_blue_run(rpr: etree._Element) -> bool:
    """<w:rPr>에서 파란 계열 색 여부를 확인한다."""
    if rpr is None:
        return False
    color = rpr.find(_w("color"), NS)
    if color is not None:
        val = (color.get(f"{{{WNS}}}val") or "").upper()
        if val in _BLUE_HEX:
            return True
    theme_color = rpr.find(_w("color"), NS)
    if theme_color is not None:
        tc = (theme_color.get(f"{{{WNS}}}themeColor") or "").lower()
        if "accent" in tc:
            return True
    return False


def _para_is_blue(p: etree._Element) -> bool:
    """단락 내 첫 번째 run이 파란 색인지 확인한다."""
    for r in p.findall(_w("r"), NS):
        rpr = r.find(_w("rPr"), NS)
        if _is_blue_run(rpr):
            return True
    return False


def _estimate_char_limit(placeholder_text: str, section_lines: list[str]) -> int:
    """
    placeholder 텍스트와 기존 섹션 내용으로 글자 수 한도를 추정한다.
    기본: 500자. 줄수*150 기준 보정.
    """
    if section_lines:
        total = sum(len(l) for l in section_lines)
        # 평균 줄 수 기반 추정 (줄당 ~150자 여유)
        lines = len(section_lines)
        return max(300, min(total * 3, lines * 150, 2000))
    # placeholder 힌트에서 줄 수 추정
    m = re.search(r"(\d+)\s*줄|(\d+)\s*line", placeholder_text, re.IGNORECASE)
    if m:
        lines = int(m.group(1) or m.group(2))
        return lines * 150
    return 500


def generate_template_schema(
    docx_path: str,
    output_path: str = "template_schema.json",
) -> dict:
    """
    DOCX 양식을 분석하여 template_schema.json을 생성한다.

    content.json 작성과 검증에 사용되는 메타정보:
    - 섹션별 keyword, char_limit_estimate, placeholder 후보
    - 표 목록과 위험도(표 삭제 위험)
    - 헤딩 매핑 결과

    Args:
        docx_path:   분석할 DOCX 파일 경로
        output_path: 생성할 JSON 파일 경로

    Returns:
        template_schema dict:
        {
          "sections": [{"keyword", "heading_text", "char_limit_estimate", "placeholder_candidates"}],
          "tables":   [{"index", "row_count", "risk_level", "header_row"}],
          "headings": [{"index", "text", "category"}],
          "stats":    {"total_sections", "total_tables", "has_blue_placeholders"}
        }
    """
    with zipfile.ZipFile(docx_path, "r") as z:
        with z.open("word/document.xml") as f:
            tree = etree.parse(f)

    root = tree.getroot()
    body = root.find(_w("body"), NS)
    body_list = list(body)

    # ── 섹션 블록 추출 ────────────────────────────────────────
    sections = []
    seen_keywords: set[str] = set()

    # 현재 섹션 추적
    current_kw: str | None = None
    current_heading: str = ""
    current_lines: list[str] = []
    current_placeholders: list[str] = []

    def _flush_section():
        nonlocal current_kw, current_heading, current_lines, current_placeholders
        if current_kw:
            limit = _estimate_char_limit(" ".join(current_placeholders), current_lines)
            sections.append({
                "keyword":             current_kw,
                "heading_text":        current_heading,
                "char_limit_estimate": limit,
                "placeholder_candidates": current_placeholders[:5],  # 최대 5개
            })
        current_kw = None
        current_heading = ""
        current_lines = []
        current_placeholders = []

    has_blue = False
    for elem in body_list:
        if elem.tag != _w("p"):
            continue
        txt = para_text(elem).strip()
        if not txt:
            continue

        # 헤딩 판별
        m = _HEADING_RE.match(txt)
        if m and len(txt) < 80:
            kw_raw = m.group(1)
            kw = re.sub(r"\s*[-–]\s*", "-", kw_raw).strip()
            if kw not in seen_keywords:
                _flush_section()
                current_kw = kw
                current_heading = txt
                seen_keywords.add(kw)
            continue

        # 본문 / placeholder 수집
        if current_kw:
            current_lines.append(txt)
            if _para_is_blue(elem) or txt.startswith("(") or "작성" in txt or "입력" in txt:
                has_blue = True
                current_placeholders.append(txt[:100])

    _flush_section()

    # ── 표 분석 ───────────────────────────────────────────────
    tables_schema = []
    for t_idx, tbl in enumerate(body.findall(_w("tbl"), NS)):
        rows = tbl.findall(_w("tr"), NS)
        row_count = len(rows)
        # 첫 행 헤더
        header_row: list[str] = []
        if rows:
            header_row = [cell_text(c)[:40].strip() for c in rows[0].findall(_w("tc"), NS)]

        # 위험도: 단일 행 + 단일 열 → 서술형 표 → LOW
        #         헤더 없음 + 많은 행 → MEDIUM
        #         복합 구조 → HIGH
        col_count = len(rows[0].findall(_w("tc"), NS)) if rows else 0
        if col_count <= 1:
            risk = "LOW"
        elif row_count <= 3:
            risk = "LOW"
        elif all(not h for h in header_row):
            risk = "HIGH"
        else:
            risk = "MEDIUM"

        tables_schema.append({
            "index":      t_idx,
            "row_count":  row_count,
            "col_count":  col_count,
            "risk_level": risk,
            "header_row": [h for h in header_row if h][:6],
        })

    # ── 헤딩 매핑 (criteria_mapper 사용) ──────────────────────
    headings_raw = []
    for elem in body_list:
        if elem.tag != _w("p"):
            continue
        txt = para_text(elem).strip()
        if txt and len(txt) < 100:
            headings_raw.append(txt)

    try:
        from .criteria_mapper import map_heading
        headings_mapped = [
            {"text": h, "category": map_heading(h).category}
            for h in headings_raw[:50]
        ]
    except ImportError:
        headings_mapped = [{"text": h, "category": "UNKNOWN"} for h in headings_raw[:50]]

    schema = {
        "sections": sections,
        "tables":   tables_schema,
        "headings": headings_mapped,
        "stats": {
            "total_sections":      len(sections),
            "total_tables":        len(tables_schema),
            "has_blue_placeholders": has_blue,
        },
    }

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, ensure_ascii=False, indent=2)

    print(f"✅ 템플릿 스키마 생성: {output_path}")
    print(f"   섹션: {len(sections)}개 / 표: {len(tables_schema)}개")
    return schema
