"""
core/rich_formatter.py
-----------------------
AI 생성 콘텐츠를 Word XML 단락으로 변환하는 리치 포맷터.

Phase 2 기능:
- 인라인 볼드 (**텍스트**)
- 들여쓰기 레벨 (indent: 0/1/2)
- 딕셔너리 형식 입력: {"text": "...", "indent": 0, "bold": false}
- 일반 문자열 입력도 지원 (하위 호환)
"""

from .injector import make_para, make_run, _w


# 들여쓰기 레벨별 왼쪽 인덴트 (twip 단위, 1cm ≈ 567 twip)
INDENT_MAP = {
    0: 0,
    1: 400,   # ~0.7cm
    2: 800,   # ~1.4cm
    3: 1200,  # ~2.1cm
}


def parse_inline_bold(text: str, size: int = 18, font: str = "맑은 고딕") -> list:
    """
    **볼드** 마크다운 구문을 파싱하여 Word XML run 요소 목록으로 변환.

    Args:
        text: 인라인 볼드 마크업이 포함된 텍스트
        size: 폰트 크기 (hPt)
        font: 폰트명

    Returns:
        list of <w:r> 요소
    """
    import re
    runs = []
    parts = re.split(r'(\*\*[^*]+\*\*)', text)
    for part in parts:
        if not part:
            continue
        if part.startswith('**') and part.endswith('**'):
            runs.append(make_run(part[2:-2], bold=True, size=size, font=font))
        else:
            runs.append(make_run(part, bold=False, size=size, font=font))
    return runs


def rich_line_to_para(line, size: int = 18, font: str = "맑은 고딕"):
    """
    단일 라인(딕셔너리 또는 문자열)을 Word XML <w:p> 요소로 변환.

    Args:
        line: 다음 중 하나:
              - str: 일반 텍스트 (인라인 볼드 지원)
              - dict: {"text": str, "indent": int, "bold": bool}
        size: 폰트 크기 (hPt)
        font: 폰트명

    Returns:
        <w:p> 요소
    """
    from lxml import etree

    if isinstance(line, str):
        text = line
        indent = 0
        bold = False
    elif isinstance(line, dict):
        text = line.get("text", "")
        indent = line.get("indent", 0)
        bold = line.get("bold", False)
    else:
        text = str(line)
        indent = 0
        bold = False

    # 빈 줄 처리
    if not text.strip():
        return make_para("", size=size)

    # <w:p> 생성
    p = etree.Element(_w("p"))
    pPr = etree.SubElement(p, _w("pPr"))

    # 들여쓰기 설정
    if indent > 0:
        ind = etree.SubElement(pPr, _w("ind"))
        twip = INDENT_MAP.get(indent, indent * 400)
        ind.set(_w("left"), str(twip))

    # 줄간격 설정
    sp = etree.SubElement(pPr, _w("spacing"))
    sp.set(_w("after"), "40")
    sp.set(_w("line"), "276")
    sp.set(_w("lineRule"), "auto")

    # 전체 볼드인 경우
    if bold:
        runs = [make_run(text, bold=True, size=size, font=font)]
    elif '**' in text:
        runs = parse_inline_bold(text, size=size, font=font)
    else:
        runs = [make_run(text, bold=False, size=size, font=font)]

    for r in runs:
        p.append(r)

    return p


def format_rich_lines(lines: list, size: int = 18, font: str = "맑은 고딕") -> list:
    """
    AI 생성 콘텐츠 라인 목록을 Word XML <w:p> 요소 목록으로 변환.

    Args:
        lines: 라인 목록. 각 항목은 str 또는 dict 형식.
        size: 기본 폰트 크기
        font: 기본 폰트명

    Returns:
        list of <w:p> 요소
    """
    return [rich_line_to_para(line, size=size, font=font) for line in lines]
