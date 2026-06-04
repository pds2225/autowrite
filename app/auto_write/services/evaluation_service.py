"""evaluation_service.py

지원사업 공고의 평가기준·배점을 파싱하고,
생성된 사업계획서를 기준별로 AI 채점한 뒤
취약 항목을 재보완하는 Evaluation Loop 서비스.

케이스 A 원칙 유지:
- 원문(기존 사업계획서)에 없는 내용을 새로 생성하지 않음
- 재보완 시에도 원문 기반 재배치/표현 조정만 허용
- 숫자·고유명사·금액은 절대 변형 금지
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..utils import log_line
from .openai_client import OpenAIService


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class EvalCriterion:
    """단일 평가 기준 항목."""
    name: str          # 기준명 (예: "창업 아이템 차별성")
    max_score: int     # 배점 (예: 20)
    description: str   # 세부 설명
    keywords: list[str] = field(default_factory=list)  # 관련 키워드


@dataclass
class CriterionScore:
    """기준별 채점 결과."""
    name: str
    max_score: int
    score: int           # 실제 점수
    ratio: float         # score / max_score
    strengths: str       # 잘 된 점
    weaknesses: str      # 미흡한 점
    suggestion: str      # 보완 방향 (원문 기반)
    related_sections: list[str] = field(default_factory=list)  # 관련 섹션 ID


@dataclass
class EvalResult:
    """평가 루프 1회 결과."""
    iteration: int
    total_score: int
    max_total: int
    pass_ratio: float           # total / max_total
    criteria_scores: list[CriterionScore]
    weak_sections: list[str]    # 보완 필요 섹션 question_id 목록
    summary: str


@dataclass
class EvalLoopReport:
    """전체 평가 루프 리포트."""
    project_id: str
    iterations: list[EvalResult]
    final_score: int
    final_max: int
    final_pass_ratio: float
    converged: bool
    announcement_criteria: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# EvaluationService
# ---------------------------------------------------------------------------

class EvaluationService:
    """공고 파싱 + 채점 + 보완 루프."""

    # 공고에서 배점 패턴을 찾는 정규식 (예: "차별성 및 경쟁력 20점", "(20)")
    SCORE_PATTERN_RE = re.compile(
        r"(?P<name>[가-힣\w\s·\-()]{2,30}?)\s*"
        r"[\(（]?\s*(?P<score>\d{1,3})\s*점?\s*[\)）]"
    )
    SECTION_SPLIT_RE = re.compile(r"\n{2,}|\r\n{2,}")
    MIN_REWRITE_SCORE_RATIO = 0.6   # 60% 미만이면 재보완 대상

    def __init__(self, openai_service: OpenAIService):
        self.openai_service = openai_service

    # ------------------------------------------------------------------
    # 1. 공고 파싱
    # ------------------------------------------------------------------

    def parse_announcement(self, text: str) -> list[EvalCriterion]:
        """공고 텍스트에서 평가기준과 배점을 추출한다."""
        if not self.openai_service.available:
            return self._parse_announcement_rule_based(text)

        system_prompt = (
            "당신은 정부지원사업 공고문에서 평가기준과 배점을 추출하는 전문가입니다.\n"
            "아래 공고 텍스트에서 평가 항목명, 배점(점수), 세부 설명을 추출하여 JSON 배열로 반환하세요.\n\n"
            "반환 형식 (JSON array):\n"
            '[{"name": "항목명", "max_score": 20, "description": "세부 설명", "keywords": ["키워드1", "키워드2"]}]\n\n'
            "규칙:\n"
            "- 평가항목이 아닌 지원자격, 제출서류 등은 제외\n"
            "- 배점이 명시된 항목만 포함\n"
            "- description은 해당 항목의 평가 기준 원문을 요약\n"
            "- keywords는 사업계획서에서 이 항목과 관련된 핵심 단어 3~5개"
        )
        user_prompt = f"공고 텍스트:\n{text[:8000]}"

        result = self.openai_service.complete_json(system_prompt, user_prompt)
        if isinstance(result, list):
            criteria = []
            for item in result:
                if not isinstance(item, dict):
                    continue
                try:
                    criteria.append(EvalCriterion(
                        name=str(item.get("name", "")).strip(),
                        max_score=int(item.get("max_score", 0)),
                        description=str(item.get("description", "")).strip(),
                        keywords=list(item.get("keywords", [])),
                    ))
                except (ValueError, TypeError):
                    continue
            if criteria:
                log_line(f"[EvalService] 평가기준 {len(criteria)}개 파싱 완료 (AI)")
                return criteria
        # fallback
        return self._parse_announcement_rule_based(text)

    def _parse_announcement_rule_based(self, text: str) -> list[EvalCriterion]:
        """AI 없을 때 정규식으로 배점 항목을 추출."""
        criteria: list[EvalCriterion] = []
        for match in self.SCORE_PATTERN_RE.finditer(text):
            name = match.group("name").strip()
            score = int(match.group("score"))
            if score < 5 or score > 100:
                continue
            if len(name) < 3:
                continue
            criteria.append(EvalCriterion(
                name=name,
                max_score=score,
                description="",
                keywords=[],
            ))
        log_line(f"[EvalService] 평가기준 {len(criteria)}개 파싱 완료 (규칙기반)")
        return criteria

    # ------------------------------------------------------------------
    # 2. 채점
    # ------------------------------------------------------------------

    def score_document(
        self,
        doc_text: str,
        criteria: list[EvalCriterion],
        profile_questions: list[dict[str, Any]],
    ) -> list[CriterionScore]:
        """사업계획서 텍스트를 각 평가기준으로 채점한다."""
        if not self.openai_service.available:
            # AI 없으면 기본점수 반환
            return [
                CriterionScore(
                    name=c.name, max_score=c.max_score,
                    score=int(c.max_score * 0.5),
                    ratio=0.5,
                    strengths="AI 미연결 - 자동 채점 불가",
                    weaknesses="직접 확인 필요",
                    suggestion="API 키 설정 후 재시도",
                )
                for c in criteria
            ]

        criteria_json = [
            {"name": c.name, "max_score": c.max_score, "description": c.description, "keywords": c.keywords}
            for c in criteria
        ]
        system_prompt = (
            "당신은 정부지원사업 심사위원입니다. 제공된 사업계획서를 평가기준에 따라 채점하세요.\n\n"
            "[채점 원칙]\n"
            "1. 각 기준의 max_score 범위 내에서 정수 점수를 부여\n"
            "2. 근거 없는 내용·허수 텍스트가 있으면 감점\n"
            "3. 수치·근거·구체성이 있으면 가점\n"
            "4. 기존에 없는 내용 생성 여부도 감점 요인\n\n"
            "반환 형식 (JSON array):\n"
            '[{"name": "기준명", "score": 15, "strengths": "잘된점", '
            '"weaknesses": "미흡한점", "suggestion": "보완방향(원문기반)", '
            '"related_sections": ["section_id_1"]}]'
        )
        user_prompt = json.dumps({
            "criteria": criteria_json,
            "document_text": doc_text[:6000],
            "section_ids": [q.get("question_id", "") for q in profile_questions[:30]],
        }, ensure_ascii=False)

        result = self.openai_service.complete_json(system_prompt, user_prompt)
        scores: list[CriterionScore] = []
        if isinstance(result, list):
            crit_by_name = {c.name: c for c in criteria}
            for item in result:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name", "")).strip()
                crit = crit_by_name.get(name)
                if crit is None:
                    # 이름이 조금 다를 수 있으므로 부분 매칭
                    for cn, cv in crit_by_name.items():
                        if name in cn or cn in name:
                            crit = cv
                            break
                if crit is None:
                    continue
                raw_score = int(item.get("score", 0))
                clamped = max(0, min(raw_score, crit.max_score))
                scores.append(CriterionScore(
                    name=name,
                    max_score=crit.max_score,
                    score=clamped,
                    ratio=clamped / crit.max_score if crit.max_score else 0.0,
                    strengths=str(item.get("strengths", "")),
                    weaknesses=str(item.get("weaknesses", "")),
                    suggestion=str(item.get("suggestion", "")),
                    related_sections=list(item.get("related_sections", [])),
                ))

        # 파싱 실패한 기준은 50% 기본점수
        scored_names = {s.name for s in scores}
        for c in criteria:
            if c.name not in scored_names:
                scores.append(CriterionScore(
                    name=c.name, max_score=c.max_score,
                    score=int(c.max_score * 0.5), ratio=0.5,
                    strengths="", weaknesses="채점 파싱 실패",
                    suggestion="직접 확인 필요",
                ))
        return scores

    def build_eval_result(
        self,
        iteration: int,
        scores: list[CriterionScore],
        profile_questions: list[dict[str, Any]],
    ) -> EvalResult:
        """채점 결과를 EvalResult로 집계한다."""
        total = sum(s.score for s in scores)
        max_total = sum(s.max_score for s in scores)
        pass_ratio = total / max_total if max_total else 0.0

        # 취약 섹션: 60% 미만 기준의 related_sections 수집
        weak_sections: list[str] = []
        for s in scores:
            if s.ratio < self.MIN_REWRITE_SCORE_RATIO:
                weak_sections.extend(s.related_sections)
        # related_sections이 비어있는 경우 키워드로 섹션 매핑
        if not weak_sections:
            for s in scores:
                if s.ratio < self.MIN_REWRITE_SCORE_RATIO:
                    weak_sections.extend(
                        self._match_sections_by_keywords(s, profile_questions)
                    )
        weak_sections = list(dict.fromkeys(weak_sections))  # 중복 제거, 순서 유지

        summary_lines = [f"총점: {total}/{max_total} ({pass_ratio*100:.1f}%)"]
        for s in scores:
            bar = "▓" * int(s.ratio * 10) + "░" * (10 - int(s.ratio * 10))
            summary_lines.append(f"  [{bar}] {s.name}: {s.score}/{s.max_score}")
        if weak_sections:
            summary_lines.append(f"보완 필요 섹션: {', '.join(weak_sections)}")

        return EvalResult(
            iteration=iteration,
            total_score=total,
            max_total=max_total,
            pass_ratio=pass_ratio,
            criteria_scores=scores,
            weak_sections=weak_sections,
            summary="\n".join(summary_lines),
        )

    def _match_sections_by_keywords(
        self,
        score: CriterionScore,
        profile_questions: list[dict[str, Any]],
    ) -> list[str]:
        """키워드 기반으로 관련 섹션 ID를 찾는다."""
        keywords = set(score.name.replace(" ", "") + score.weaknesses.replace(" ", ""))
        matched = []
        for q in profile_questions:
            label = str(q.get("label", ""))
            qid = str(q.get("question_id", ""))
            if not qid or str(q.get("target", {}).get("kind", "")) != "section":
                continue
            if any(kw in label for kw in score.name.split()):
                matched.append(qid)
        return matched[:3]

    # ------------------------------------------------------------------
    # 3. 재보완 프롬프트 생성
    # ------------------------------------------------------------------

    def build_refinement_context(
        self,
        weak_sections: list[str],
        scores: list[CriterionScore],
        profile_questions: list[dict[str, Any]],
        source_context: str,
    ) -> str:
        """취약 섹션 재보완을 위한 컨텍스트를 구성한다."""
        score_by_section: dict[str, CriterionScore] = {}
        for s in scores:
            for sec_id in s.related_sections:
                score_by_section[sec_id] = s

        lines = [source_context.strip(), "", "=== 평가 결과 기반 보완 지시 ==="]
        qid_to_label = {
            str(q.get("question_id", "")): str(q.get("label", ""))
            for q in profile_questions
        }
        for sec_id in weak_sections:
            label = qid_to_label.get(sec_id, sec_id)
            cs = score_by_section.get(sec_id)
            if cs:
                lines.append(
                    f"[보완필요] 항목: {label} | 현재점수: {cs.score}/{cs.max_score} | "
                    f"미흡: {cs.weaknesses} | 보완방향: {cs.suggestion}"
                )
            else:
                lines.append(f"[보완필요] 항목: {label}")
        lines.append("")
        lines.append("[원칙] 원문에 있는 내용만 사용. 없는 내용 생성 금지. 수치·고유명사 변형 금지.")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 4. 결과 직렬화
    # ------------------------------------------------------------------

    def to_report_dict(self, report: EvalLoopReport) -> dict[str, Any]:
        """EvalLoopReport를 JSON 직렬화 가능한 dict로 변환."""
        return {
            "project_id": report.project_id,
            "final_score": report.final_score,
            "final_max": report.final_max,
            "final_pass_ratio": round(report.final_pass_ratio, 4),
            "converged": report.converged,
            "announcement_criteria": report.announcement_criteria,
            "iterations": [
                {
                    "iteration": r.iteration,
                    "total_score": r.total_score,
                    "max_total": r.max_total,
                    "pass_ratio": round(r.pass_ratio, 4),
                    "summary": r.summary,
                    "weak_sections": r.weak_sections,
                    "criteria_scores": [
                        {
                            "name": s.name,
                            "max_score": s.max_score,
                            "score": s.score,
                            "ratio": round(s.ratio, 4),
                            "strengths": s.strengths,
                            "weaknesses": s.weaknesses,
                            "suggestion": s.suggestion,
                            "related_sections": s.related_sections,
                        }
                        for s in r.criteria_scores
                    ],
                }
                for r in report.iterations
            ],
        }
