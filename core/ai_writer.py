"""
core/ai_writer.py
------------------
Claude API를 사용하여 사업계획서 섹션별 콘텐츠를 생성하는 AI 작성 모듈.

주요 기능:
- 9개 섹션별 프롬프트 기반 콘텐츠 생성
- 리치 포맷(indent/bold) JSON 출력 파싱
- 일반 텍스트 폴백 지원
- 기업 정보 기반 프롬프트 커스터마이징
"""

import json
import re
import os

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from prompts import SECTION_PROMPTS, SYSTEM_PROMPT


# 기본 모델 설정
DEFAULT_MODEL = "claude-sonnet-4-20250514"
DEFAULT_MAX_TOKENS = 4096
DEFAULT_TEMPERATURE = 0.3  # 일관적이고 전문적인 톤 유지


def _parse_ai_response(response_text: str) -> list:
    """
    AI 응답을 파싱하여 리치 포맷 라인 리스트로 변환.

    JSON 배열 형식을 우선 시도하고, 실패 시 일반 텍스트로 폴백.

    Args:
        response_text: AI 응답 텍스트

    Returns:
        리치 포맷 라인 리스트. 각 항목은 dict 또는 str.
    """
    # JSON 배열 추출 시도
    # 코드 블록 안에 있을 수 있음
    json_match = re.search(r'```(?:json)?\s*(\[[\s\S]*?\])\s*```', response_text)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # 코드 블록 없이 JSON 배열만 있을 수 있음
    json_match = re.search(r'(\[[\s\S]*\])', response_text)
    if json_match:
        try:
            parsed = json.loads(json_match.group(1))
            if isinstance(parsed, list) and len(parsed) > 0:
                # dict 리스트인지 확인
                if isinstance(parsed[0], dict) and "text" in parsed[0]:
                    return parsed
        except json.JSONDecodeError:
            pass

    # JSON 파싱 실패 시 일반 텍스트로 폴백
    lines = response_text.strip().split('\n')
    result = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            result.append({"text": "", "indent": 0, "bold": False})
            continue

        # 들여쓰기 추론
        indent = 0
        if stripped.startswith(('- ', '◦ ', '· ')):
            indent = 1
        elif stripped.startswith(('  - ', '  ◦ ')):
            indent = 2

        # 볼드 추론
        bold = False
        if re.match(r'^[가-힣]\.\s', stripped):  # 가. 나. 다. 패턴
            bold = True
        elif re.match(r'^\d+\)\s', stripped):  # 1) 2) 3) 패턴
            bold = True

        result.append({"text": stripped, "indent": indent, "bold": bold})

    return result


def _rich_lines_to_plain(rich_lines: list) -> list:
    """
    리치 포맷 라인 리스트를 일반 문자열 리스트로 변환.
    injector.py의 sections 방식과 호환.

    Args:
        rich_lines: 리치 포맷 라인 리스트

    Returns:
        문자열 리스트
    """
    result = []
    for line in rich_lines:
        if isinstance(line, dict):
            text = line.get("text", "")
            indent = line.get("indent", 0)
            prefix = "  " * indent
            result.append(f"{prefix}{text}")
        else:
            result.append(str(line))
    return result


class AIWriter:
    """
    Claude API를 사용하여 사업계획서 콘텐츠를 생성하는 클래스.

    사용법::

        writer = AIWriter(api_key="sk-ant-...")
        company_info = {
            "company_name": "마켓게이트",
            "business_item": "AI 기반 수출지원 플랫폼",
            ...
        }
        content = writer.generate_section("1-1", company_info)
        # content는 리치 포맷 라인 리스트
    """

    def __init__(self, api_key: str = None, model: str = None,
                 temperature: float = None, max_tokens: int = None):
        """
        Args:
            api_key:     Anthropic API 키 (None이면 ANTHROPIC_API_KEY 환경변수 사용)
            model:       사용할 모델 ID
            temperature: 생성 온도 (낮을수록 일관적)
            max_tokens:  최대 토큰 수
        """
        if not HAS_ANTHROPIC:
            raise ImportError(
                "anthropic 패키지가 설치되지 않았습니다. "
                "'pip install anthropic' 으로 설치하세요."
            )

        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API 키가 필요합니다. "
                "ANTHROPIC_API_KEY 환경변수를 설정하거나 api_key 인수를 전달하세요."
            )

        self.model = model or DEFAULT_MODEL
        self.temperature = temperature if temperature is not None else DEFAULT_TEMPERATURE
        self.max_tokens = max_tokens or DEFAULT_MAX_TOKENS
        self.client = anthropic.Anthropic(api_key=self.api_key)

    def generate_section(self, section_id: str, company_info: dict,
                         output_format: str = "rich") -> list:
        """
        지정 섹션의 콘텐츠를 AI로 생성.

        Args:
            section_id:    섹션 ID (예: "1-1", "2-2", "3-1")
            company_info:  기업 정보 딕셔너리
            output_format: "rich" (dict 리스트) 또는 "plain" (str 리스트)

        Returns:
            생성된 콘텐츠 라인 리스트

        Raises:
            ValueError: 지원하지 않는 섹션 ID
        """
        if section_id not in SECTION_PROMPTS:
            raise ValueError(
                f"지원하지 않는 섹션: {section_id}. "
                f"사용 가능: {list(SECTION_PROMPTS.keys())}"
            )

        prompt_fn = SECTION_PROMPTS[section_id]
        user_prompt = prompt_fn(company_info)

        message = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": user_prompt}
            ],
        )

        response_text = message.content[0].text
        rich_lines = _parse_ai_response(response_text)

        if output_format == "plain":
            return _rich_lines_to_plain(rich_lines)
        return rich_lines

    def generate_all_sections(self, company_info: dict,
                              sections: list = None,
                              output_format: str = "rich",
                              verbose: bool = True) -> dict:
        """
        여러 섹션의 콘텐츠를 순차적으로 생성.

        Args:
            company_info:  기업 정보 딕셔너리
            sections:      생성할 섹션 ID 리스트 (None이면 전체)
            output_format: "rich" 또는 "plain"
            verbose:       진행상황 출력 여부

        Returns:
            {section_id: [lines, ...], ...}
        """
        if sections is None:
            sections = list(SECTION_PROMPTS.keys())

        results = {}
        for i, sid in enumerate(sections, 1):
            if verbose:
                print(f"  [{i}/{len(sections)}] 섹션 {sid} 생성 중...")
            try:
                results[sid] = self.generate_section(sid, company_info, output_format)
                if verbose:
                    line_count = len(results[sid])
                    print(f"           → {line_count}줄 생성 완료")
            except Exception as e:
                if verbose:
                    print(f"           → 오류: {e}")
                results[sid] = []

        return results

    def generate_content_json(self, company_info: dict,
                              base_content: dict = None,
                              sections_map: dict = None,
                              verbose: bool = True) -> dict:
        """
        content.json 형식의 완성 딕셔너리를 생성.

        기존 base_content의 table_cells, table_rows는 유지하면서
        sections 부분만 AI 생성 콘텐츠로 교체.

        Args:
            company_info:  기업 정보 딕셔너리
            base_content:  기존 content.json (표 데이터 등 유지)
            sections_map:  섹션ID→keyword 매핑 (None이면 기본값)
            verbose:       진행상황 출력 여부

        Returns:
            content.json 형식 딕셔너리
        """
        if base_content is None:
            base_content = {}

        # 기본 섹션-키워드 매핑
        if sections_map is None:
            sections_map = {
                "1-1": "1-1",
                "1-2": "1-2",
                "2-1": "2-1",
                "2-2": "2-2",
                "3-1": "3-1",
                "3-2": "3-2",
                "3-3": "3-3",
                "4-1": "4-1",
                "4-2": "4-2",
            }

        # AI 콘텐츠 생성 (plain 포맷 — injector sections 호환)
        ai_content = self.generate_all_sections(
            company_info,
            sections=list(sections_map.keys()),
            output_format="plain",
            verbose=verbose,
        )

        # content.json 조립
        result = {
            "delete_tables": base_content.get("delete_tables", []),
            "table_cells": base_content.get("table_cells", []),
            "table_rows": base_content.get("table_rows", []),
            "sections": [],
            "images": base_content.get("images", []),
        }

        for sid, keyword in sections_map.items():
            lines = ai_content.get(sid, [])
            if lines:
                result["sections"].append({
                    "_section": f"AI 생성 — 섹션 {sid}",
                    "keyword": keyword,
                    "lines": lines,
                    "size": 18,
                })

        return result


def generate_from_company_info(company_info_path: str,
                               base_content_path: str = None,
                               output_path: str = None,
                               api_key: str = None,
                               verbose: bool = True) -> dict:
    """
    기업 정보 JSON 파일로부터 사업계획서 콘텐츠를 AI 생성.

    편의 함수로, CLI에서 직접 호출 가능.

    Args:
        company_info_path: 기업 정보 JSON 파일 경로
        base_content_path: 기존 content.json 경로 (표 데이터 유지용)
        output_path:       출력 JSON 파일 경로
        api_key:           Anthropic API 키
        verbose:           진행상황 출력

    Returns:
        생성된 content.json 딕셔너리
    """
    with open(company_info_path, "r", encoding="utf-8") as f:
        company_info = json.load(f)

    base_content = None
    if base_content_path:
        with open(base_content_path, "r", encoding="utf-8") as f:
            base_content = json.load(f)

    writer = AIWriter(api_key=api_key)

    if verbose:
        print(f"\n🤖 AI 사업계획서 콘텐츠 생성 시작")
        print(f"  모델: {writer.model}")
        print(f"  온도: {writer.temperature}")

    content = writer.generate_content_json(
        company_info,
        base_content=base_content,
        verbose=verbose,
    )

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(content, f, ensure_ascii=False, indent=2)
        if verbose:
            print(f"\n✅ 콘텐츠 저장: {output_path}")

    return content
