from __future__ import annotations

import unittest

from docx import Document
from docx.enum.text import WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from auto_write.services.docx_ops import set_cell_text


class DocxOpsTests(unittest.TestCase):
    def test_set_cell_text_clears_run_highlight_from_placeholder_text(self):
        doc = Document()
        table = doc.add_table(rows=1, cols=1)
        cell = table.cell(0, 0)
        paragraph = cell.paragraphs[0]
        run = paragraph.add_run("※ 작성요령")
        run.font.highlight_color = WD_COLOR_INDEX.YELLOW

        set_cell_text(cell, "완료 문장")

        highlights = cell._tc.findall(".//" + qn("w:highlight"))
        self.assertEqual(len(highlights), 0)
        self.assertIn("완료 문장", cell.text)

    def test_set_cell_text_removes_placeholder_cell_shading(self):
        doc = Document()
        table = doc.add_table(rows=1, cols=1)
        cell = table.cell(0, 0)
        tc = cell._tc
        tc_pr = tc.find(qn("w:tcPr"))
        if tc_pr is None:
            tc_pr = OxmlElement("w:tcPr")
            tc.insert(0, tc_pr)
        shading = OxmlElement("w:shd")
        shading.set(qn("w:fill"), "FFFF00")
        tc_pr.append(shading)

        set_cell_text(cell, "채워진 값")

        tc_pr_after = cell._tc.find(qn("w:tcPr"))
        self.assertIsNotNone(tc_pr_after)
        self.assertIsNone(tc_pr_after.find(qn("w:shd")))
        self.assertIn("채워진 값", cell.text)


if __name__ == "__main__":
    unittest.main()

