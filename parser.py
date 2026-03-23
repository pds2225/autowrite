from __future__ import annotations

import re
import zipfile
from pathlib import Path

from lxml import etree

from models import ParsedTemplate, TableDiagnosis
from utils import infer_table_type, normalize_text

WNS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": WNS}


def _w(tag: str) -> str:
    return f"{{{WNS}}}{tag}"


def _cell_text(tc: etree._Element) -> str:
    return "".join(t.text or "" for t in tc.iter(_w("t"))).strip()


def _grid_span(tc: etree._Element) -> int:
    tc_pr = tc.find(_w("tcPr"))
    if tc_pr is None:
        return 1
    gs = tc_pr.find(_w("gridSpan"))
    if gs is None:
        return 1
    try:
        return int(gs.get(_w("val"), "1"))
    except ValueError:
        return 1


def _vmerge_state(tc: etree._Element) -> str | None:
    tc_pr = tc.find(_w("tcPr"))
    if tc_pr is None:
        return None
    vm = tc_pr.find(_w("vMerge"))
    if vm is None:
        return None
    return vm.get(_w("val"), "continue")


def _row_visual_cells(tr: etree._Element) -> list[dict[str, object]]:
    cells = []
    c_idx = 0
    for tc in tr.findall(_w("tc")):
        span = _grid_span(tc)
        vmerge = _vmerge_state(tc)
        cells.append({
            "cell": tc,
            "start_col": c_idx,
            "span": span,
            "vmerge": vmerge,
            "text": _cell_text(tc),
        })
        c_idx += span
    return cells


def diagnose_table(tbl: etree._Element, table_index: int) -> TableDiagnosis:
    rows = tbl.findall(_w("tr"))
    visual_rows = [_row_visual_cells(r) for r in rows]
    estimated_cols = max((sum(int(c["span"]) for c in vr) for vr in visual_rows), default=0)
    has_gridspan = any(int(c["span"]) > 1 for vr in visual_rows for c in vr)
    has_vmerge = any((c["vmerge"] is not None) for vr in visual_rows for c in vr)

    header_texts: list[str] = []
    if visual_rows:
        for cell_meta in visual_rows[0]:
            txt = str(cell_meta["text"]).strip()
            if txt:
                header_texts.append(txt)

    repeated_row_candidate = False
    if len(visual_rows) >= 3:
        widths = [len(vr) for vr in visual_rows[1:4]]
        repeated_row_candidate = len(set(widths)) == 1

    table_type = infer_table_type(header_texts)

    reasons: list[str] = []
    risk = "safe"
    if has_vmerge:
        risk = "manual"
        reasons.append("vertical merged cells detected")
    elif has_gridspan:
        risk = "caution"
        reasons.append("horizontal merged cells detected")

    if table_type == "unknown":
        reasons.append("header alias mapping uncertain")
        if risk == "safe":
            risk = "caution"

    reason = "; ".join(reasons) if reasons else "structure looks regular"

    return TableDiagnosis(
        table_index=table_index,
        row_count=len(rows),
        estimated_col_count=estimated_cols,
        has_gridspan=has_gridspan,
        has_vmerge=has_vmerge,
        header_texts=header_texts,
        repeated_row_candidate=repeated_row_candidate,
        table_risk_level=risk,  # type: ignore[arg-type]
        table_type_candidate=table_type,  # type: ignore[arg-type]
        reason=reason,
    )


def analyze_template(docx_path: str) -> ParsedTemplate:
    docx_path_obj = Path(docx_path)
    with zipfile.ZipFile(docx_path_obj, "r") as zf:
        xml_bytes = zf.read("word/document.xml")
    root = etree.fromstring(xml_bytes)
    body = root.find(_w("body"))
    if body is None:
        return ParsedTemplate(template_path=str(docx_path_obj))

    tables = body.findall(_w("tbl"))
    diagnoses = [diagnose_table(tbl, idx) for idx, tbl in enumerate(tables)]

    anchors: list[str] = []
    heading_re = re.compile(r"^\s*\d+(?:[-\.)]\d+)*")
    for p in body.findall(_w("p")):
        text = normalize_text("".join(t.text or "" for t in p.iter(_w("t"))))
        if text and (heading_re.match(text) or any(k in text for k in ["problem", "solution", "team", "예산", "일정"])):
            anchors.append(text)

    return ParsedTemplate(template_path=str(docx_path_obj), table_diagnostics=diagnoses, section_anchors=anchors)
