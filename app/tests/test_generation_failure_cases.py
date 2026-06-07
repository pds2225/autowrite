"""생성 실패 케이스 재현 테스트.

마스터 플랜(INTEGRATION_MASTER_PLAN.md) 백로그의
"생성 실패 케이스 5개 재현 테스트 추가" 항목을 구현한 것이다.

각 테스트는 자동작성 결과물에서 실제로 발생했던 대표적인 실패 유형을
QAService.build_report가 정확히 잡아내고, 사용자에게 "무엇이 비었고
어떻게 채울지"를 안내하는 표준 메시지를 내보내는지 검증한다.
QAService는 외부 API 키 없이 단독으로 동작하므로 결정적으로 재현된다.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from docx import Document

from auto_write.models import (
    GeneratedImage,
    ImageSlotProfile,
    ProjectInput,
    QuestionProfile,
    SectionProfile,
    TemplateProfile,
)
from auto_write.services.qa_service import QAService


class GenerationFailureCaseTests(unittest.TestCase):
    """결과 문서/입력에서 발생하는 대표 실패 5종을 재현한다."""

    def setUp(self) -> None:
        self.qa = QAService()
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp_dir.name)

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def _write_docx(self, name: str, paragraphs: list[str]) -> Path:
        path = self.root / name
        doc = Document()
        for text in paragraphs:
            doc.add_paragraph(text)
        doc.save(path)
        return path

    def _render_result(self, output_path: Path) -> dict:
        return {
            "output_path": str(output_path),
            "sections_written": 0,
            "cells_written": 0,
            "images_written": 0,
            "errors": [],
            "warnings": [],
        }

    def _build(
        self,
        profile: TemplateProfile,
        project_input: ProjectInput,
        output_path: Path,
        images: list[GeneratedImage] | None = None,
    ) -> dict:
        return self.qa.build_report(
            profile=profile,
            project_input=project_input,
            render_result=self._render_result(output_path),
            images=images or [],
            evidence=[],
        )

    # 케이스 1: 필수 과제 메타값(과제명)이 비어 있는 경우 -------------------
    def test_missing_required_project_meta_is_reported_with_fill_guidance(self):
        profile = TemplateProfile(
            template_id="tpl_meta",
            template_name="meta.docx",
            source_docx="meta.docx",
            questions=[
                QuestionProfile(
                    question_id="project_title",
                    label="과제명",
                    required=True,
                    target={"kind": "project_meta", "key": "project_title"},
                )
            ],
        )
        project_input = ProjectInput(template_id="tpl_meta", project_meta={})
        output_path = self._write_docx("meta.docx", ["1. 사업 개요"])

        report = self._build(profile, project_input, output_path)

        self.assertFalse(report["passed"])
        self.assertEqual(report["error_count"], 1)
        message = report["errors"][0]
        self.assertIn("[필수입력]", message)
        self.assertIn("'과제명'", message)
        # 어디를 어떻게 채워야 하는지 경로까지 안내해야 한다.
        self.assertIn("meta.project_title", message)

    # 케이스 2: 필수 본문 섹션이 결과 문서에서 비어 있는 경우 ---------------
    def test_required_section_blank_in_output_is_reported(self):
        profile = TemplateProfile(
            template_id="tpl_section",
            template_name="section.docx",
            source_docx="section.docx",
            sections=[
                SectionProfile(
                    field_id="section_overview",
                    label="사업 개요",
                    anchor_text="1. 사업 개요",
                    required=True,
                )
            ],
            questions=[
                QuestionProfile(
                    question_id="section_overview",
                    label="사업 개요",
                    required=True,
                    target={"kind": "section", "field_id": "section_overview"},
                )
            ],
        )
        project_input = ProjectInput(template_id="tpl_section", answers={})
        # 앵커 문단만 있고 그 아래 본문이 채워지지 않은 결과 문서.
        output_path = self._write_docx("section.docx", ["1. 사업 개요"])

        report = self._build(profile, project_input, output_path)

        self.assertFalse(report["passed"])
        self.assertEqual(report["error_count"], 1)
        message = report["errors"][0]
        self.assertIn("[필수입력]", message)
        self.assertIn("결과 문서에서 비어있습니다", message)
        self.assertIn("answers.section_overview", message)

    # 케이스 3: 필수 이미지가 생성되지 않은 경우 ---------------------------
    def test_required_image_slot_not_generated_is_reported(self):
        profile = TemplateProfile(
            template_id="tpl_image",
            template_name="image.docx",
            source_docx="image.docx",
            image_slots=[
                ImageSlotProfile(slot_id="img_main", label="대표 이미지", required=True)
            ],
        )
        project_input = ProjectInput(template_id="tpl_image")
        output_path = self._write_docx("image.docx", ["1. 사업 개요"])

        report = self._build(profile, project_input, output_path, images=[])

        self.assertFalse(report["passed"])
        self.assertEqual(report["error_count"], 1)
        message = report["errors"][0]
        self.assertIn("[필수이미지]", message)
        self.assertIn("'대표 이미지'", message)

    # 케이스 4: 결과 문서를 생성하지 못한 경우 ---------------------------
    def test_missing_output_docx_is_reported(self):
        profile = TemplateProfile(
            template_id="tpl_none",
            template_name="none.docx",
            source_docx="none.docx",
        )
        project_input = ProjectInput(template_id="tpl_none")
        # 존재하지 않는 경로 -> 최종 산출물 누락.
        output_path = self.root / "never_created.docx"

        report = self._build(profile, project_input, output_path)

        self.assertFalse(report["passed"])
        messages = report["errors"]
        self.assertTrue(any("[산출물]" in item for item in messages))
        self.assertTrue(any("최종 DOCX 파일이 생성되지 않았습니다" in item for item in messages))

    # 케이스 5: 결과 문서에 가이드 문구/빈 칸이 남아 있는 경우 -----------
    def test_leftover_guide_text_and_placeholder_are_reported(self):
        profile = TemplateProfile(
            template_id="tpl_guide",
            template_name="guide.docx",
            source_docx="guide.docx",
        )
        project_input = ProjectInput(template_id="tpl_guide")
        output_path = self._write_docx(
            "guide.docx",
            [
                "1. 사업 개요",
                "※ 작성요령에 따라 내용을 작성하세요.",  # 가이드 문구 잔존
                "대표자: ○○○",  # 빈 칸(플레이스홀더) 잔존
            ],
        )

        report = self._build(profile, project_input, output_path)

        self.assertFalse(report["passed"])
        self.assertTrue(any("[가이드문구]" in item for item in report["errors"]))
        # ○○○ 빈 칸은 경고로 안내되며 페이지 위치를 알려준다.
        self.assertTrue(any("[빈칸]" in item for item in report["warnings"]))
        self.assertTrue(any("페이지" in item for item in report["warnings"]))


if __name__ == "__main__":
    unittest.main()
