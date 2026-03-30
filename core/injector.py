"""
bizplan_injector/core/injector.py
----------------------------------
사업계획서 DOCX 자동 주입 엔진

주요 기능:
- 원본 양식 DOCX를 그대로 유지하면서 JSON 내용을 주입
- 파란색 안내문구 자동 제거
- 표 데이터 주입 (단일셀, 다중셀, 복합표)
- 단락 섹션 키워드 기반 내용 교체

수정 이력:
- [버그1] delete_tables 음수 인덱스 방어 처리 추가 (0 <= i < len 조건)
- [버그2] inject_after_keyword 섹션 경계 인식 개선 (다음 섹션 헤딩 p태그도 종료 기준으로 처리)
"""

import re
import zipfile
import shutil
import os
import copy
import json
from lxml import etree

from .rich_formatter import line_to_para


# ── XML 네임스페이스 ──────────────────────────────────────────────
WNS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS  = {"w": WNS}
BLUE_COLORS = {
    "4472c4","1f3864","2e74b5","4f81bd","17375e","244185",
    "1f497d","0070c0","4f6228","538135","0000ff","blue",
    "2f5496","215868","1f5c8b",
}

# 섹션 헤딩 판별용 패턴
# ① 줄 시작이 숫자-숫자: "1-1 문제인식", "3-3-3 자금계획"
_HEADING_START = re.compile(r"^\s*\d+\s*[-–]\s*\d+")
# ② 짧은 줄(≤20자) 속 숫자-숫자: "가. 1-2", "① 2-1 현황"
_HEADING_INNER = re.compile(r"\d+\s*[-–]\s*\d+")
# ③ 숫자범위 표현: "1-2개", "30-40%", "2-3억", "1-2년" 등 (본문에서 흔함)
_RANGE_EXPR = re.compile(r"\d+\s*[-–]\s*\d+[개건명년월일억만조백%]")


def _is_section_boundary(txt: str) -> bool:
    """
    단락 텍스트가 다음 섹션의 헤딩인지 판별한다.

    판별 기준:
    1. 단락이 '숫자-숫자' 패턴으로 시작 → 헤딩 (접두 공백 허용)
    2. 짧은 단락(≤20자) + '숫자-숫자' 포함 + 단위 없음 → 헤딩 가능성
       "수출국가 1-2개" → _RANGE_EXPR 제외 → 헤딩 X
       "가. 1-2" / "① 2-1 현황" → 짧고 단위 없음 → 헤딩 O
    """
    if not txt:
        return False
    if _HEADING_START.search(txt):
        return True
    if _RANGE_EXPR.search(txt):   # 단위 붙은 숫자 범위 → 본문
        return False
    return len(txt) <= 20 and bool(_HEADING_INNER.search(txt))


def _normalize_kw(s: str) -> str:
    """키워드 정규화: 대시 전후 공백 제거, 소문자화."""
    return re.sub(r"\s*[-–]\s*", "-", s).strip().lower()


# ── 저수준 XML 헬퍼 ──────────────────────────────────────────────
def _w(tag: str) -> str:
    """Word XML 네임스페이스가 포함된 완전한 태그명 반환. 예) 'p' → '{...}p'"""
    return f"{{{WNS}}}{tag}"


def make_run(text: str, bold: bool = False, color: str = None,
             size: int = 18, font: str = "맑은 고딕") -> etree._Element:
    """
    Word XML <w:r> (run) 요소 생성.

    Args:
        text:  표시할 텍스트
        bold:  굵게 여부
        color: 16진수 색상 코드 (예: "FF0000"). None이면 기본색
        size:  폰트 크기 (hPt 단위, Word pt × 2. 예: 9pt → 18)
        font:  폰트명 (기본: 맑은 고딕)

    Returns:
        <w:r> 요소
    """
    rPr = etree.Element(_w("rPr"))
    if bold:
        etree.SubElement(rPr, _w("b"))
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


def make_para(text: str = "", bold: bool = False, color: str = None,
              size: int = 18, align: str = "left",
              before: int = 0, after: int = 0,
              font: str = "맑은 고딕") -> etree._Element:
    """
    Word XML <w:p> (단락) 요소 생성.

    Args:
        text:   단락 텍스트 (빈 문자열이면 빈 단락)
        bold:   굵게 여부
        color:  16진수 색상 코드
        size:   폰트 크기 (hPt 단위)
        align:  정렬 ('left' | 'center' | 'right' | 'both')
        before: 단락 앞 간격 (twip 단위)
        after:  단락 뒤 간격 (twip 단위)
        font:   폰트명

    Returns:
        <w:p> 요소
    """
    p = etree.Element(_w("p"))
    pPr = etree.SubElement(p, _w("pPr"))
    jc = etree.SubElement(pPr, _w("jc"))
    jc.set(_w("val"), align)
    sp = etree.SubElement(pPr, _w("spacing"))
    sp.set(_w("before"), str(before))
    sp.set(_w("after"), str(after))
    if text.strip():
        p.append(make_run(text, bold=bold, color=color, size=size, font=font))
    return p


def cell_text(cell: etree._Element) -> str:
    """셀(<w:tc>) 내 모든 텍스트를 이어 붙여 반환."""
    return "".join(r.text or "" for r in cell.iter(_w("t")))


def para_text(p: etree._Element) -> str:
    """단락(<w:p>) 내 모든 텍스트를 이어 붙여 반환."""
    return "".join(r.text or "" for r in p.iter(_w("t")))


def get_rows(tbl: etree._Element) -> list:
    """표(<w:tbl>)에서 행(<w:tr>) 목록 반환."""
    return tbl.findall(_w("tr"), NS)


def get_cells(row: etree._Element) -> list:
    """행(<w:tr>)에서 셀(<w:tc>) 목록 반환."""
    return row.findall(_w("tc"), NS)


def set_cell_text(cell: etree._Element, text: str,
                  bold: bool = False, size: int = 18,
                  align: str = "left", color: str = None):
    """
    셀의 모든 단락을 제거하고 단일 텍스트 단락으로 교체.

    Args:
        cell:  대상 <w:tc> 요소
        text:  주입할 텍스트
        bold:  굵게 여부
        size:  폰트 크기 (hPt 단위)
        align: 정렬
        color: 16진수 색상 코드
    """
    for p in cell.findall(_w("p"), NS):
        cell.remove(p)
    cell.append(make_para(text, bold=bold, color=color, size=size, align=align))


def set_cell_multiline(cell: etree._Element, lines: list,
                       size: int = 18, align: str = "left",
                       bold_first: bool = False):
    """
    셀에 여러 줄 텍스트를 단락 단위로 주입.

    Args:
        cell:       대상 <w:tc> 요소
        lines:      주입할 텍스트 목록 (각 항목이 별도 단락)
        size:       폰트 크기 (hPt 단위)
        align:      정렬
        bold_first: 첫 번째 줄만 굵게 처리
    """
    for p in cell.findall(_w("p"), NS):
        cell.remove(p)
    for i, line in enumerate(lines):
        cell.append(make_para(line, bold=(bold_first and i == 0), size=size, align=align))


# ── 파란색 안내문구 제거 ─────────────────────────────────────────
def is_blue_run(run: etree._Element) -> bool:
    """
    run(<w:r>)이 파란색 안내문구인지 판별.

    BLUE_COLORS 집합에 정의된 색상 코드 중 하나와 일치하면 True 반환.
    """
    rPr = run.find(_w("rPr"), NS)
    if rPr is None:
        return False
    color = rPr.find(_w("color"), NS)
    if color is None:
        return False
    return color.get(_w("val"), "").lower() in BLUE_COLORS


def remove_blue_runs(para: etree._Element) -> int:
    """
    단락 내 파란색 run을 모두 제거하고 제거 개수 반환.

    Args:
        para: 대상 <w:p> 요소

    Returns:
        제거된 run 수
    """
    removed = 0
    for r in para.findall(_w("r"), NS):
        if is_blue_run(r):
            para.remove(r)
            removed += 1
    return removed


def remove_all_blue(body: etree._Element) -> int:
    """
    body 전체에서 파란색 run을 모두 제거하고 총 제거 개수 반환.

    Args:
        body: <w:body> 요소

    Returns:
        제거된 총 run 수
    """
    total = 0
    for p in body.iter(_w("p")):
        total += remove_blue_runs(p)
    return total


def remove_consecutive_empty_paras(body: etree._Element, max_consecutive: int = 2) -> int:
    """
    연속 빈 단락을 max_consecutive 개 이하로 압축.

    Args:
        body:            <w:body> 요소
        max_consecutive: 허용할 최대 연속 빈 단락 수 (기본 2)

    Returns:
        제거된 빈 단락 수
    """
    removed = 0
    body_list = list(body)
    i = 0
    while i < len(body_list) - max_consecutive:
        window = body_list[i:i + max_consecutive + 1]
        if all(
            e.tag == _w("p") and not para_text(e).strip()
            for e in window
        ):
            body.remove(window[1])
            body_list = list(body)
            removed += 1
            continue
        i += 1
    return removed


# ── 핵심 주입 클래스 ─────────────────────────────────────────────
class BizPlanInjector:
    """
    사업계획서 DOCX 자동 주입 엔진.

    원본 양식 DOCX 파일을 언패킹하고, content.json의 지시에 따라
    표 셀 주입 / 표 행 교체 / 단락 섹션 주입 / 파란 안내문구 제거를
    순서대로 수행한 뒤 새 DOCX로 저장합니다.

    사용법::

        inj = BizPlanInjector("templates/양식.docx")
        inj.load_content("examples/content_marketgate.json")
        stats = inj.run()
        inj.save("output/사업계획서_완성.docx")
        print(stats)  # {"blue_removed": N, "empty_paras_removed": N}
    """

    def __init__(self, template_path: str):
        """
        Args:
            template_path: 원본 양식 DOCX 파일 경로
        """
        self.template_path = template_path
        self.work_dir = "/tmp/bizplan_work"
        self.content = {}
        self.tree = None
        self.root = None
        self.body = None
        self.tables = []

    # ── 초기화 ──────────────────────────────────────────────────
    def _unpack(self):
        """
        DOCX(ZIP)를 work_dir에 압축 해제하고 document.xml을 파싱.

        self.tree, self.root, self.body, self.tables를 초기화합니다.
        이미 work_dir가 존재하면 먼저 삭제 후 재생성합니다.
        """
        if os.path.exists(self.work_dir):
            shutil.rmtree(self.work_dir)
        os.makedirs(self.work_dir)
        with zipfile.ZipFile(self.template_path, "r") as z:
            z.extractall(self.work_dir)
        xml_path = os.path.join(self.work_dir, "word/document.xml")
        self.tree = etree.parse(xml_path)
        self.root = self.tree.getroot()
        self.body = self.root.find(_w("body"), NS)
        self.tables = [c for c in self.body if c.tag == _w("tbl")]
        self.xml_path = xml_path

    def load_content(self, content_path: str):
        """
        JSON 파일에서 주입 내용을 로드.

        Args:
            content_path: content.json 파일 경로 (UTF-8 인코딩)
        """
        with open(content_path, "r", encoding="utf-8") as f:
            self.content = json.load(f)

    def set_content(self, content: dict):
        """
        딕셔너리를 직접 주입 내용으로 설정 (Python API용).

        Args:
            content: content.json과 동일한 구조의 딕셔너리
        """
        self.content = content

    # ── 표 유틸 ─────────────────────────────────────────────────
    def get_table(self, idx: int):
        """
        인덱스로 표 요소 반환. 범위 초과 시 None 반환.

        Args:
            idx: 표 인덱스 (0부터 시작, 음수 불가)

        Returns:
            <w:tbl> 요소 또는 None
        """
        if 0 <= idx < len(self.tables):
            return self.tables[idx]
        return None

    def inject_table_cell(self, table_idx: int, row_idx: int, cell_idx: int,
                           text, multiline: bool = False, size: int = 18,
                           align: str = "left", bold: bool = False):
        """
        지정한 표·행·열 위치의 단일 셀에 텍스트 주입.

        범위를 벗어난 인덱스는 조용히 무시합니다(silent skip).

        Args:
            table_idx: 표 인덱스
            row_idx:   행 인덱스
            cell_idx:  열 인덱스
            text:      주입할 텍스트 (multiline=True이면 list)
            multiline: True이면 text를 줄 목록으로 처리
            size:      폰트 크기 (hPt 단위)
            align:     정렬
            bold:      굵게 여부
        """
        t = self.get_table(table_idx)
        if t is None:
            return
        rows = get_rows(t)
        if row_idx >= len(rows):
            return
        cells = get_cells(rows[row_idx])
        if cell_idx >= len(cells):
            return
        cell = cells[cell_idx]
        if multiline and isinstance(text, list):
            set_cell_multiline(cell, text, size=size, align=align, bold_first=bold)
        else:
            set_cell_text(cell, str(text), bold=bold, size=size, align=align)

    def rebuild_table_rows(self, table_idx: int, data_rows: list,
                            header_rows: int = 1, size: int = 18):
        """
        표의 데이터 행(헤더 제외)을 통째로 교체.

        헤더 행은 보존하고, 나머지 기존 행을 모두 제거한 뒤
        data_rows의 내용으로 새 행을 추가합니다.
        새 행의 서식은 헤더 바로 다음 행을 deepcopy하여 기반으로 사용합니다.

        Args:
            table_idx:   표 인덱스
            data_rows:   행 데이터 목록.
                         각 항목: {"cells": ["값1", ...], "aligns": ["center", ...]}
            header_rows: 보존할 헤더 행 수 (기본 1)
            size:        폰트 크기 (hPt 단위, 기본 18)
        """
        t = self.get_table(table_idx)
        if t is None:
            return
        rows = get_rows(t)
        # 기존 데이터 행 제거 (헤더 제외)
        for row in rows[header_rows:]:
            t.remove(row)
        # 기준 행 복사하여 새 행 생성
        ref_row = rows[min(header_rows, len(rows) - 1)]
        for row_data in data_rows:
            new_row = copy.deepcopy(ref_row)
            cells = get_cells(new_row)
            row_cells = row_data.get("cells", [])
            aligns = row_data.get("aligns", [])
            for j, val in enumerate(row_cells):
                if j < len(cells):
                    align = aligns[j] if j < len(aligns) else "left"
                    if isinstance(val, list):
                        set_cell_multiline(cells[j], val, size=size, align=align)
                    else:
                        set_cell_text(cells[j], str(val), size=size, align=align)
            t.append(new_row)

    # ── 단락 주입 ────────────────────────────────────────────────
    def inject_after_keyword(self, keyword: str, lines: list, size: int = 18) -> bool:
        """
        keyword를 포함한 헤딩 단락 바로 뒤의 기존 내용을 제거하고 새 내용 삽입.

        종료 기준 (다음 중 먼저 만나는 요소까지 기존 내용 제거):
          1. <w:tbl> 표 태그
          2. 섹션 헤딩 패턴(숫자-숫자)을 포함한 <w:p> 단락  ← [버그2 수정]

        Args:
            keyword: 헤딩 단락에서 찾을 키워드 문자열
            lines:   주입할 줄 목록. 각 항목은 str 또는 dict:
                     - str: 기존 방식 (하위 호환)
                     - dict: {"text": "...", "bold": false, "indent": 1, "size": 18, "color": "..."}
                       "text"에 **bold** 인라인 마크업 사용 가능
            size:    섹션 기본 폰트 크기 (hPt 단위). 각 라인 dict의 "size"로 override 가능

        Returns:
            True  — 키워드를 찾아 주입 성공
            False — 키워드를 찾지 못해 주입 건너뜀
        """
        body_list = list(self.body)
        heading_elem = None
        heading_idx = -1
        kw_norm = _normalize_kw(keyword)
        for i, elem in enumerate(body_list):
            if elem.tag == _w("p") and kw_norm in _normalize_kw(para_text(elem)):
                heading_elem = elem
                heading_idx = i
                break
        if heading_elem is None:
            return False

        # 다음 섹션 헤딩 또는 표까지 기존 단락 제거
        end_idx = len(body_list)
        for j in range(heading_idx + 1, len(body_list)):
            elem = body_list[j]
            # 종료 조건 1: 표 태그
            if elem.tag == _w("tbl"):
                end_idx = j
                break
            # 종료 조건 2: 다음 섹션 헤딩 단락 (숫자-숫자 패턴)
            if elem.tag == _w("p"):
                txt = para_text(elem).strip()
                if _is_section_boundary(txt):
                    end_idx = j
                    break

        for elem in body_list[heading_idx + 1: end_idx]:
            if elem in list(self.body):
                self.body.remove(elem)

        # 새 내용 삽입: str/dict 모두 line_to_para로 처리 (Phase 2 리치 서식)
        curr = list(self.body)
        pos = curr.index(heading_elem) + 1
        for line in reversed(lines):
            para = line_to_para(line, default_size=size)
            self.body.insert(pos, para)
        return True

    def delete_tables(self, indices: list):
        """
        지정 인덱스의 표를 body에서 삭제.

        목차·비목참고 등 불필요한 표를 제거할 때 사용합니다.
        삭제 후 self.tables를 재로드합니다.

        Args:
            indices: 삭제할 표 인덱스 목록.
                     음수 인덱스는 무시합니다(버그1 수정: 0 <= i < len 조건).
        """
        # [버그1 수정] 음수 인덱스 방어: 0 <= i < len(self.tables) 조건으로 제한
        to_del = [self.tables[i] for i in indices if 0 <= i < len(self.tables)]
        for t in to_del:
            if t in list(self.body):
                self.body.remove(t)
        # tables 재로드
        self.tables = [c for c in self.body if c.tag == _w("tbl")]

    # ── 후처리 ──────────────────────────────────────────────────
    def clean(self) -> dict:
        """
        파란 안내문구 제거 및 연속 빈 단락 압축 후처리 실행.

        Returns:
            {"blue_removed": int, "empty_paras_removed": int}
        """
        blue = remove_all_blue(self.body)
        empty = remove_consecutive_empty_paras(self.body)
        return {"blue_removed": blue, "empty_paras_removed": empty}

    # ── 저장 ────────────────────────────────────────────────────
    def save(self, output_path: str) -> str:
        """
        수정된 document.xml을 work_dir에 기록하고 DOCX(ZIP)로 재패킹.

        Args:
            output_path: 출력 DOCX 파일 경로

        Returns:
            output_path (체이닝 편의)
        """
        xml_str = etree.tostring(
            self.tree, xml_declaration=True, encoding="UTF-8", standalone=True
        )
        with open(self.xml_path, "wb") as f:
            f.write(xml_str)
        with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for root_dir, _, files in os.walk(self.work_dir):
                for fname in files:
                    fpath = os.path.join(root_dir, fname)
                    arcname = os.path.relpath(fpath, self.work_dir)
                    zout.write(fpath, arcname)
        return output_path

    # ── 이미지 삽입 ─────────────────────────────────────────────
    def inject_image(self, keyword: str, image_path: str,
                     width_cm: float = 10.0, height_cm: float = 7.0,
                     align: str = "center") -> bool:
        """
        keyword를 포함한 헤딩 단락 바로 뒤에 이미지를 삽입.

        이미지를 word/media/에 복사하고, document.xml.rels에 관계를 등록한 뒤
        <w:drawing> 요소를 body에 삽입합니다.

        Args:
            keyword:    헤딩 단락에서 찾을 키워드
            image_path: 삽입할 이미지 파일 경로 (.png / .jpg / .jpeg)
            width_cm:   이미지 너비 (cm 단위, 기본 10.0)
            height_cm:  이미지 높이 (cm 단위, 기본 7.0)
            align:      단락 정렬 ('center' | 'left' | 'right')

        Returns:
            True — 키워드를 찾아 이미지 삽입 성공
            False — 키워드를 찾지 못해 건너뜀 / 이미지 파일 없음
        """
        if not os.path.exists(image_path):
            return False

        # ── 이미지 파일을 word/media/에 복사 ──
        ext = os.path.splitext(image_path)[1].lower()  # .png / .jpg
        media_dir = os.path.join(self.work_dir, "word", "media")
        os.makedirs(media_dir, exist_ok=True)

        # 기존 이미지 파일 수 세어 고유 이름 결정
        existing = [f for f in os.listdir(media_dir) if f.startswith("image")]
        img_num = len(existing) + 1
        media_name = f"image{img_num}{ext}"
        media_dest = os.path.join(media_dir, media_name)
        shutil.copy2(image_path, media_dest)

        # ── .rels 파일에 관계 추가 ──
        rels_path = os.path.join(self.work_dir, "word", "_rels", "document.xml.rels")
        RELS_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
        IMG_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"

        rels_tree = etree.parse(rels_path)
        rels_root = rels_tree.getroot()

        # 기존 rId 중 최대값을 구해 새 rId 할당
        existing_ids = [
            int(el.get("Id", "rId0").replace("rId", "") or 0)
            for el in rels_root
        ]
        new_rid_num = max(existing_ids, default=0) + 1
        new_rid = f"rId{new_rid_num}"

        rel_el = etree.SubElement(rels_root, f"{{{RELS_NS}}}Relationship")
        rel_el.set("Id", new_rid)
        rel_el.set("Type", IMG_TYPE)
        rel_el.set("Target", f"media/{media_name}")

        with open(rels_path, "wb") as f:
            f.write(etree.tostring(rels_tree, xml_declaration=True,
                                   encoding="UTF-8", standalone=True))

        # ── <w:drawing> 요소 생성 ──
        # 1 cm = 914400 EMU
        cx = int(width_cm * 914400)
        cy = int(height_cm * 914400)

        # 고유 drawing id
        existing_drawings = self.root.findall(".//{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}docPr")
        draw_id = len(existing_drawings) + 1

        WP  = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
        A   = "http://schemas.openxmlformats.org/drawingml/2006/main"
        PIC = "http://schemas.openxmlformats.org/drawingml/2006/picture"
        R   = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

        inline = etree.Element(f"{{{WP}}}inline")
        for attr, val in [("distT","0"),("distB","0"),("distL","0"),("distR","0")]:
            inline.set(attr, val)

        extent = etree.SubElement(inline, f"{{{WP}}}extent")
        extent.set("cx", str(cx))
        extent.set("cy", str(cy))

        doc_pr = etree.SubElement(inline, f"{{{WP}}}docPr")
        doc_pr.set("id", str(draw_id))
        doc_pr.set("name", f"Image {draw_id}")

        graphic = etree.SubElement(inline, f"{{{A}}}graphic")
        graphic_data = etree.SubElement(graphic, f"{{{A}}}graphicData")
        graphic_data.set("uri", PIC)

        pic_el = etree.SubElement(graphic_data, f"{{{PIC}}}pic")

        nvPicPr = etree.SubElement(pic_el, f"{{{PIC}}}nvPicPr")
        cNvPr = etree.SubElement(nvPicPr, f"{{{PIC}}}cNvPr")
        cNvPr.set("id", str(draw_id))
        cNvPr.set("name", f"Image {draw_id}")
        etree.SubElement(nvPicPr, f"{{{PIC}}}cNvPicPr")

        blipFill = etree.SubElement(pic_el, f"{{{PIC}}}blipFill")
        blip = etree.SubElement(blipFill, f"{{{A}}}blip")
        blip.set(f"{{{R}}}embed", new_rid)
        stretch = etree.SubElement(blipFill, f"{{{A}}}stretch")
        etree.SubElement(stretch, f"{{{A}}}fillRect")

        spPr = etree.SubElement(pic_el, f"{{{PIC}}}spPr")
        xfrm = etree.SubElement(spPr, f"{{{A}}}xfrm")
        off = etree.SubElement(xfrm, f"{{{A}}}off")
        off.set("x", "0"); off.set("y", "0")
        ext_el = etree.SubElement(xfrm, f"{{{A}}}ext")
        ext_el.set("cx", str(cx)); ext_el.set("cy", str(cy))
        prstGeom = etree.SubElement(spPr, f"{{{A}}}prstGeom")
        prstGeom.set("prst", "rect")
        etree.SubElement(prstGeom, f"{{{A}}}avLst")

        # drawing을 감싸는 <w:p> 생성
        img_para = etree.Element(_w("p"))
        pPr = etree.SubElement(img_para, _w("pPr"))
        jc = etree.SubElement(pPr, _w("jc"))
        jc.set(_w("val"), align)
        run = etree.SubElement(img_para, _w("r"))
        drawing = etree.SubElement(run, _w("drawing"))
        drawing.append(inline)

        # ── 헤딩 단락 위치 찾아 삽입 ──
        body_list = list(self.body)
        heading_idx = -1
        kw_norm = _normalize_kw(keyword)
        for i, elem in enumerate(body_list):
            if elem.tag == _w("p") and kw_norm in _normalize_kw(para_text(elem)):
                heading_idx = i
                break
        if heading_idx == -1:
            return False

        curr = list(self.body)
        insert_pos = curr.index(body_list[heading_idx]) + 1
        self.body.insert(insert_pos, img_para)
        return True

    # ── 메인 실행 ────────────────────────────────────────────────
    def run(self) -> dict:
        """
        content.json 기반으로 전체 주입 파이프라인 실행.

        실행 순서:
          1. DOCX 언패킹 및 XML 파싱
          2. delete_tables — 불필요 표 삭제
          3. table_cells   — 개별 셀 텍스트 주입
          4. table_rows    — 표 데이터 행 전체 교체
          5. sections      — 섹션 키워드 기반 단락 내용 교체
          6. clean         — 파란 안내문구 제거 + 빈 단락 압축

        Returns:
            {"blue_removed": int, "empty_paras_removed": int}
        """
        self._unpack()

        # 1. 삭제 대상 표 처리
        delete_tables = self.content.get("delete_tables", [])
        if delete_tables:
            self.delete_tables(delete_tables)

        # 2. 표 셀 주입
        for item in self.content.get("table_cells", []):
            self.inject_table_cell(
                table_idx=item["table"],
                row_idx=item["row"],
                cell_idx=item["cell"],
                text=item["text"],
                multiline=item.get("multiline", False),
                size=item.get("size", 18),
                align=item.get("align", "left"),
                bold=item.get("bold", False),
            )

        # 3. 표 행 전체 교체
        for item in self.content.get("table_rows", []):
            self.rebuild_table_rows(
                table_idx=item["table"],
                data_rows=item["rows"],
                header_rows=item.get("header_rows", 1),
                size=item.get("size", 18),
            )

        # 4. 단락 섹션 주입
        ok_count, fail_count = 0, 0
        for item in self.content.get("sections", []):
            ok = self.inject_after_keyword(
                keyword=item["keyword"],
                lines=item["lines"],
                size=item.get("size", 18),
            )
            if ok:
                ok_count += 1
            else:
                fail_count += 1
                print(f"  ⚠️  섹션 키워드 미발견: {item['keyword']!r} — DOCX 헤딩과 불일치 가능성")
        if fail_count:
            print(f"  ℹ️  섹션 주입 결과: 성공 {ok_count}개 / 실패 {fail_count}개")
            print("      --analyze 플래그로 DOCX 헤딩 텍스트를 확인하세요.")

        # 5. 이미지 삽입
        for item in self.content.get("images", []):
            self.inject_image(
                keyword=item["keyword"],
                image_path=item["image_path"],
                width_cm=item.get("width_cm", 10.0),
                height_cm=item.get("height_cm", 7.0),
                align=item.get("align", "center"),
            )

        # 6. 후처리
        stats = self.clean()
        return stats
