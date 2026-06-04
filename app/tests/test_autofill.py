from __future__ import annotations

import unittest

from auto_write.autofill import build_autofill_values, merge_form_with_autofill


class AutofillTests(unittest.TestCase):
    def test_build_autofill_values_extracts_labeled_korean_fields(self):
        text = """
        과제명: AI 기반 소상공인 재도약 지원 플랫폼
        회사명: 밸류업파트너스
        사업 개요: 폐업 위기 소상공인의 경영진단, 정책자금, 실행계획 수립을 지원하는 서비스입니다.
        추가 메모: 대표 컨설팅 경험, 정부지원사업 수행 경험, 단계별 실행 로드맵을 강점으로 제시합니다.
        근거 주제: 소상공인 폐업률 통계
        통계 주제: 희망리턴패키지 수혜기업 성과
        """

        result = build_autofill_values(text)

        self.assertEqual(result["project_title"], "AI 기반 소상공인 재도약 지원 플랫폼")
        self.assertEqual(result["organization_name"], "밸류업파트너스")
        self.assertIn("폐업 위기 소상공인", result["user_brief"])
        self.assertIn("대표 컨설팅 경험", result["user_notes"])
        self.assertIn("소상공인 폐업률 통계", result["evidence_topics"])
        self.assertIn("희망리턴패키지 수혜기업 성과", result["evidence_topics"])

    def test_merge_form_with_autofill_keeps_manual_values_first(self):
        form_values = {
            "project_title": "직접 입력 과제명",
            "organization_name": "",
            "user_brief": "",
            "user_notes": "직접 입력 메모",
            "evidence_topics": "",
        }
        autofill_values = {
            "project_title": "파일 과제명",
            "organization_name": "파일 회사명",
            "user_brief": "파일 사업 개요",
            "user_notes": "파일 메모",
            "evidence_topics": "파일 근거",
        }

        merged = merge_form_with_autofill(form_values, autofill_values)

        self.assertEqual(merged["project_title"], "직접 입력 과제명")
        self.assertEqual(merged["organization_name"], "파일 회사명")
        self.assertEqual(merged["user_brief"], "파일 사업 개요")
        self.assertEqual(merged["user_notes"], "직접 입력 메모")
        self.assertEqual(merged["evidence_topics"], "파일 근거")


if __name__ == "__main__":
    unittest.main()
