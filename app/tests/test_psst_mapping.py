from __future__ import annotations

import unittest

from auto_write.models import ProjectInput, SectionProfile, TableCellProfile, TableProfile, TemplateProfile
from auto_write.services.project_service import ProjectService


def _profile_with_psst() -> TemplateProfile:
    sections = [
        SectionProfile(
            field_id="fld_problem",
            label="1. 문제 인식 (Problem)_창업 아이템의 필요성",
            anchor_text="1. 문제 인식 (Problem)_창업 아이템의 필요성",
        ),
        SectionProfile(
            field_id="fld_solution",
            label="2. 실현 가능성 (Solution)_창업 아이템의 개발 계획",
            anchor_text="2. 실현 가능성 (Solution)_창업 아이템의 개발 계획",
        ),
        SectionProfile(
            field_id="fld_scale",
            label="3. 성장전략 (Scale-up)_사업화 추진 전략",
            anchor_text="3. 성장전략 (Scale-up)_사업화 추진 전략",
        ),
        SectionProfile(
            field_id="fld_team",
            label="4. 팀 구성 (Team)_대표자 및 팀원 구성 계획",
            anchor_text="4. 팀 구성 (Team)_대표자 및 팀원 구성 계획",
        ),
        SectionProfile(
            field_id="fld_bullet",
            label="○ 산업 동향",
            anchor_text="○ 산업 동향",
        ),
    ]
    return TemplateProfile(
        template_id="tpl_test",
        template_name="test.docx",
        source_docx="test.docx",
        sections=sections,
    )


def _profile_with_psst_and_tables() -> TemplateProfile:
    profile = _profile_with_psst()
    profile.tables = [
        TableProfile(
            table_id="tbl_core",
            label="□ 일반현황",
            row_count=2,
            col_count=2,
            cells=[
                TableCellProfile(cell_id="cell_company", label="기업명", row=1, cell=0),
                TableCellProfile(cell_id="cell_empty", label="대표자", row=1, cell=1),
            ],
        ),
        TableProfile(
            table_id="tbl_admin",
            label="제출목록",
            row_count=1,
            col_count=1,
            cells=[
                TableCellProfile(cell_id="cell_admin", label="첨부서류", row=0, cell=0),
            ],
        ),
    ]
    return profile


class PsstMappingTests(unittest.TestCase):
    def test_find_psst_field_ids(self) -> None:
        service = ProjectService.__new__(ProjectService)
        mapping = service._find_psst_field_ids(_profile_with_psst())
        self.assertEqual(mapping["problem"], "fld_problem")
        self.assertEqual(mapping["solution"], "fld_solution")
        self.assertEqual(mapping["scale"], "fld_scale")
        self.assertEqual(mapping["team"], "fld_team")

    def test_apply_psst_maps_brief_and_split_notes(self) -> None:
        service = ProjectService.__new__(ProjectService)
        profile = _profile_with_psst()
        answers = {
            "user_brief": "사용자가 쓴 사업 개요",
            "user_notes": "해결 파트\n\n성장 파트\n\n팀 파트",
            "fld_problem": "기존 시드 문단",
        }
        updated = service._apply_psst_from_user_input(answers, profile)
        self.assertEqual(updated["fld_problem"], "사용자가 쓴 사업 개요")
        self.assertEqual(updated["fld_solution"], "해결 파트")
        self.assertEqual(updated["fld_scale"], "성장 파트")
        self.assertEqual(updated["fld_team"], "팀 파트")

    def test_restrict_autofill_targets_excludes_bullet_section(self) -> None:
        service = ProjectService.__new__(ProjectService)
        profile = _profile_with_psst()
        targets = [
            {
                "question_id": "fld_bullet",
                "label": "○ 산업 동향",
                "target": {"kind": "section", "field_id": "fld_bullet"},
            },
            {
                "question_id": "fld_problem",
                "label": "1. 문제 인식 (Problem)_창업 아이템의 필요성",
                "target": {"kind": "section", "field_id": "fld_problem"},
            },
        ]
        restricted = service._restrict_autofill_targets(profile, targets)
        self.assertEqual(len(restricted), 1)
        self.assertEqual(restricted[0]["question_id"], "fld_problem")


    def test_build_hwp_paste_includes_psst_and_brief(self) -> None:
        service = ProjectService.__new__(ProjectService)

        profile = _profile_with_psst()
        project_input = ProjectInput(
            template_id="tpl_test",
            project_meta={"project_title": "테스트 과제"},
            organization_profile={"name": "테스트 기업"},
            answers={
                "user_brief": "사업 개요 원문",
                "fld_problem": "문제 인식 본문",
                "fld_solution": "해결 본문",
            },
        )
        text = service._build_hwp_paste_text(
            profile,
            project_input,
            {"errors": ["표 셀 위치 오류: 일반현황"]},
            psst_field_ids={"fld_problem", "fld_solution", "fld_scale", "fld_team"},
            core_table_ids=set(),
        )
        self.assertIn("=== 1. 문제 인식 (Problem) ===", text)
        self.assertIn("문제 인식 본문", text)
        self.assertIn("=== 입력: 사업 개요 ===", text)
        self.assertIn("사업 개요 원문", text)
        self.assertIn("표 셀 위치 오류", text)

    def test_results_docx_name_sanitizes_user_title(self) -> None:
        service = ProjectService.__new__(ProjectService)
        project_input = ProjectInput(
            template_id="tpl_test",
            project_meta={"project_title": '../시장:검증*사업?'},
        )

        name = service._results_docx_name(project_input)

        self.assertTrue(name.endswith("_초안.docx"))
        self.assertIn("시장검증사업", name)
        for unsafe in '<>:"/\\|?*':
            self.assertNotIn(unsafe, name)

    def test_build_copy_blocks_filters_to_psst_and_core_tables(self) -> None:
        service = ProjectService.__new__(ProjectService)
        profile = _profile_with_psst_and_tables()
        project_input = ProjectInput(
            template_id="tpl_test",
            project_meta={"project_title": "복사 블록 과제"},
            organization_profile={"name": "복사 블록 기업"},
            answers={
                "fld_problem": "문제 인식 본문",
                "fld_bullet": "복사하면 안 되는 소제목 본문",
                "cell_company": "테스트 기업",
                "cell_empty": "",
                "cell_admin": "제출서류 목록",
            },
        )

        blocks = service._build_copy_blocks(
            profile,
            project_input,
            psst_field_ids={"fld_problem", "fld_solution", "fld_scale", "fld_team"},
            core_table_ids=service._core_table_ids(profile),
        )

        self.assertEqual(
            [block["id"] for block in blocks],
            ["project_title", "organization_name", "fld_problem", "cell_company"],
        )
        self.assertEqual(blocks[-1]["title"], "□ 일반현황 / 기업명")
        self.assertNotIn("cell_admin", {block["id"] for block in blocks})

    def test_build_hwp_paste_includes_only_core_table_values(self) -> None:
        service = ProjectService.__new__(ProjectService)
        profile = _profile_with_psst_and_tables()
        project_input = ProjectInput(
            template_id="tpl_test",
            answers={
                "cell_company": "테스트 기업",
                "cell_empty": "",
                "cell_admin": "제출서류 목록",
            },
        )

        text = service._build_hwp_paste_text(
            profile,
            project_input,
            {"errors": []},
            psst_field_ids=set(),
            core_table_ids=service._core_table_ids(profile),
        )

        self.assertIn("=== 표: □ 일반현황 ===", text)
        self.assertIn("기업명\t테스트 기업", text)
        self.assertNotIn("제출목록", text)
        self.assertNotIn("제출서류 목록", text)


if __name__ == "__main__":
    unittest.main()
