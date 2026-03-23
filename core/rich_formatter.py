#!/usr/bin/env python3
"""
rich_formatter.py — 리치 텍스트 서식 지원 모듈
------------------------------------------------
Phase 2: 인라인 볼드(**text**), 들여쓰기 레벨, dict 형식 라인 처리

지원하는 라인 형식:
  1. str  — 기존 방식 (하위 호환)
  2. dict — 리치 서식 지정
     {
       "text":   "내용 (**강조** 포함 가능)",   # 필수
       "bold":   false,                          # 선택 (전체 볼드)
       "indent": 1,                              # 선택 (들여쓰기 레벨 0-3)
       "size":   18,                             # 선택 (섹션 기본값 override)
       "color":  "FF0000"                        # 선택 (hex 색상)
     }

인라인 볼드: **텍스트** 패턴을 파싱하여 run 단위로 분리합니다.
들여쓰기: 레벨 1 = 360 twips, 레벨 2 = 720 twips, 레벨 3 = 1080 twips
"""

import re
from lxml import etree


# ── XML 네임스페이스 ──────────────────────────────────────────────
WNS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
INDENT_PER_LEVEL = 360  # 1레벨당 twips (약 6.35mm)


def _w(tag: str) -> str:
    return f"{{{WNS}}}{tag}"


def parse_inline_bold(text: str) -> list:
    """
    **text** 패턴을 파싱하여 (텍스트, is_bold) 튜플 목록으로 반환한다.

    Args:
        text: **bold** 마크업이 포함된 문자열

    Returns:
        [(텍스트, is_bold), ...] 튜플 목록

    Examples:
        "일반 **강조** 텍스트"
        → [("일반 ", False), ("강조", True), (" 텍스트", False)]

        "**전체 볼드**"
        → [("전체 볼드", True)]

        "마크업 없음"
        → [("마크업 없음", False)]
    """
    parts = []
    pattern = re.compile(r"\*\*(.+?)\*\*")
    last_end = 0

    for m in pattern.finditer(text):
        before = text[last_end:m.start()]
        if before:
            parts.append((before, False))
        parts.append((m.group(1), True))
        last_end = m.end()

    remaining = text[last_end:]
    if remaining:
        parts.append((remaining, False))

    return parts if parts else [(text, False)]


def make_rich_run(
    text: str,
    bold: bool = False,
    size: int = 18,
    color: str = None,
    font: str = "맑은 고딕",
) -> etree._Element:
    """
    서식이 적용된 <w:r> run 요소를 생성한다.

    Args:
        text:  표시할 텍스트
        bold:  굵게 여부
        size:  폰트 크기 (hPt 단위, Word pt × 2. 예: 9pt → 18)
        color: 16진수 색상 코드 (예: "FF0000"). None이면 기본색
        font:  폰트명

    Returns:
        <w:r> 요소
    """
    rPr = etree.Element(_w("rPr"))

    if bold:
        etree.SubElement(rPr, _w("b"))
        etree.SubElement(rPr, _w("bCs"))

    rFonts = etree.SubElement(rPr, _w("rFonts"))
    for attr in ("ascii", "hAnsi", "eastAsia"):
        rFonts.set(_w(attr), font)

    for tag in ("sz", "szCs"):
        el = etree.SubElement(rPr, _w(tag))
        el.set(_w("val"), str(size))

    if color:
        col = etree.SubElement(rPr, _w("color"))
        col.set(_w("val"), color)

    r = etree.Element(_w("r"))
    r.append(rPr)
    t = etree.SubElement(r, _w("t"))
    t.text = text
    if text and (text[0] == " " or text[-1] == " "):
        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    return r


def make_rich_para(
    text: str,
    bold: bool = False,
    size: int = 18,
    color: str = None,
    indent: int = 0,
    align: str = "left",
    font: str = "맑은 고딕",
    before: int = 0,
    after: int = 0,
) -> etree._Element:
    """
    **bold** 인라인 마크업을 파싱하여 mixed-format <w:p> 요소를 생성한다.

    Args:
        text:   텍스트 (**bold** 패턴 포함 가능)
        bold:   전체 강제 볼드 (True이면 인라인 파싱 없이 전체 bold)
        size:   폰트 크기 (hPt 단위)
        color:  16진수 색상 코드
        indent: 들여쓰기 레벨 (0=없음, 1=360twips, 2=720twips, 3=1080twips)
        align:  정렬 ('left' | 'center' | 'right' | 'both')
        font:   폰트명
        before: 단락 앞 간격 (twip)
        after:  단락 뒤 간격 (twip)

    Returns:
        <w:p> 요소
    """
    p = etree.Element(_w("p"))
    pPr = etree.SubElement(p, _w("pPr"))

    # 정렬
    jc = etree.SubElement(pPr, _w("jc"))
    jc.set(_w("val"), align)

    # 간격
    sp = etree.SubElement(pPr, _w("spacing"))
    sp.set(_w("before"), str(before))
    sp.set(_w("after"), str(after))

    # 들여쓰기
    if indent > 0:
        ind_el = etree.SubElement(pPr, _w("ind"))
        ind_el.set(_w("left"), str(indent * INDENT_PER_LEVEL))

    # 텍스트가 없으면 빈 단락
    if not text.strip():
        return p

    if bold:
        # 전체 볼드: 인라인 파싱 없이 단일 run
        p.append(make_rich_run(text, bold=True, size=size, color=color, font=font))
    else:
        # 인라인 **bold** 파싱: 여러 run 생성
        parts = parse_inline_bold(text)
        if len(parts) == 1 and not parts[0][1]:
            # 마크업 없음 — 단일 run (성능 최적화)
            p.append(make_rich_run(text, bold=False, size=size, color=color, font=font))
        else:
            for part_text, part_bold in parts:
                p.append(make_rich_run(
                    part_text,
                    bold=part_bold,
                    size=size,
                    color=color,
                    font=font,
                ))

    return p


def line_to_para(
    line,
    default_size: int = 18,
    default_align: str = "left",
    font: str = "맑은 고딕",
) -> etree._Element:
    """
    라인 명세(str 또는 dict)를 <w:p> 요소로 변환한다.

    두 가지 입력 형식을 지원한다:

    1. str — 기존 방식 (하위 호환):
       "◦ 소제목"  →  make_rich_para("◦ 소제목", ...)

    2. dict — 리치 서식:
       {
         "text":   "내용 (**강조** 포함 가능)",
         "bold":   false,
         "indent": 1,
         "size":   18,
         "color":  "FF0000"
       }

    Args:
        line:          str 또는 dict 형식의 라인 명세
        default_size:  섹션 기본 폰트 크기 (hPt 단위)
        default_align: 기본 정렬
        font:          폰트명

    Returns:
        <w:p> 요소
    """
    if isinstance(line, str):
        return make_rich_para(
            text=line,
            size=default_size,
            align=default_align,
            font=font,
        )

    if isinstance(line, dict):
        return make_rich_para(
            text=line.get("text", ""),
            bold=line.get("bold", False),
            size=line.get("size", default_size),
            color=line.get("color"),
            indent=line.get("indent", 0),
            align=line.get("align", default_align),
            font=font,
        )

    # 예상치 못한 타입 — 문자열 변환 fallback
    return make_rich_para(str(line), size=default_size, align=default_align, font=font)
