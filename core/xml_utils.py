"""
core/xml_utils.py
------------------
Word XML 공통 헬퍼 — analyzer.py / injector.py 중복 코드 통합

이 모듈은 내부 전용 유틸리티입니다. core/__init__.py 공개 export 대상이 아닙니다.
"""

from lxml import etree

# ── 네임스페이스 ──────────────────────────────────────────────────
WNS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS  = {"w": WNS}

# ── 파란 계열 hex 색상 집합 (두 파일의 union) ─────────────────────
BLUE_COLORS = {
    "4472c4", "5b9bd5", "2e74b5", "2e75b6", "4f81bd",
    "1f3864", "17375e", "244185", "1f497d", "1f5c8b",
    "0070c0", "00b0f0", "215868", "2f5496", "0000ff",
    "4f6228", "538135", "blue",
}


def _w(tag: str) -> str:
    """Word XML 네임스페이스가 포함된 완전한 태그명 반환. 예) 'p' → '{...}p'"""
    return f"{{{WNS}}}{tag}"


def para_text(p: etree._Element) -> str:
    """단락(<w:p>) 내 모든 텍스트를 이어 붙여 반환."""
    return "".join(r.text or "" for r in p.iter(_w("t")))


def cell_text(tc: etree._Element) -> str:
    """셀(<w:tc>) 내 모든 텍스트를 이어 붙여 반환."""
    return "".join(r.text or "" for r in tc.iter(_w("t")))


def get_rows(tbl: etree._Element) -> list:
    """표(<w:tbl>)에서 행(<w:tr>) 목록 반환."""
    return tbl.findall(_w("tr"), NS)


def get_cells(row: etree._Element) -> list:
    """행(<w:tr>)에서 셀(<w:tc>) 목록 반환."""
    return row.findall(_w("tc"), NS)


def is_blue_run(run: etree._Element) -> bool:
    """
    run(<w:r>)이 파란 계열 색인지 확인한다.

    hex 색상(BLUE_COLORS)과 themeColor 속성을 모두 검사한다.
    """
    rPr = run.find(_w("rPr"), NS)
    if rPr is None:
        return False
    color = rPr.find(_w("color"), NS)
    if color is None:
        return False
    # hex 색상 검사
    val = color.get(f"{{{WNS}}}val") or ""
    if val.lower() in BLUE_COLORS:
        return True
    # themeColor 속성 검사 (accent 계열 = 파란 계열)
    theme = color.get(f"{{{WNS}}}themeColor") or ""
    if "accent" in theme.lower():
        return True
    return False
