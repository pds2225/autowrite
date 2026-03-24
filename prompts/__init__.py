"""
prompts/ — 사업계획서 섹션별 프롬프트 템플릿 패키지

각 섹션별 프롬프트 함수:
  get_section_N_prompt(company_info: dict) -> str

지원 섹션:
  1-1: 폐업 원인 분석 및 개선 방안
  1-2: 재창업 아이템 목표시장 및 필요성
  2-1: 재창업 아이템 준비 현황
  2-2: 재창업 아이템 실현 및 구체화 방안
  3-1: 재창업 아이템 비즈니스 모델
  3-2: 재창업 아이템 사업화 추진 전략
  3-3: 사업 추진 일정 및 자금 운용 계획
  4-1: 조직 구성 및 보유 역량
  4-2: 조직 구성 계획
"""

from .section_1_1 import get_section_1_1_prompt
from .section_1_2 import get_section_1_2_prompt
from .section_2_1 import get_section_2_1_prompt
from .section_2_2 import get_section_2_2_prompt
from .section_3_1 import get_section_3_1_prompt
from .section_3_2 import get_section_3_2_prompt
from .section_3_3 import get_section_3_3_prompt
from .section_4_1 import get_section_4_1_prompt
from .section_4_2 import get_section_4_2_prompt
from .common import SYSTEM_PROMPT, FORMAT_INSTRUCTIONS

SECTION_PROMPTS = {
    "1-1": get_section_1_1_prompt,
    "1-2": get_section_1_2_prompt,
    "2-1": get_section_2_1_prompt,
    "2-2": get_section_2_2_prompt,
    "3-1": get_section_3_1_prompt,
    "3-2": get_section_3_2_prompt,
    "3-3": get_section_3_3_prompt,
    "4-1": get_section_4_1_prompt,
    "4-2": get_section_4_2_prompt,
}

__all__ = [
    "SECTION_PROMPTS",
    "SYSTEM_PROMPT",
    "FORMAT_INSTRUCTIONS",
    "get_section_1_1_prompt",
    "get_section_1_2_prompt",
    "get_section_2_1_prompt",
    "get_section_2_2_prompt",
    "get_section_3_1_prompt",
    "get_section_3_2_prompt",
    "get_section_3_3_prompt",
    "get_section_4_1_prompt",
    "get_section_4_2_prompt",
]
