"""
bizplan_injector/core/analyzer.py
-----------------------------------
DOCX 양식 구조 자동 분석기

주요 기능:
- 표 수, 행/열, 셀 내용 출력
- 단락 헤딩 목록 추출
- content.json 스켈레톤 자동 생성
"""

import zipfile
import os
import json
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
