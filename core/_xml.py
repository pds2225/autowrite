"""
core/_xml.py
------------
Word XML 공통 상수·헬퍼. injector.py · analyzer.py 양쪽에서 공유합니다.
"""
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
