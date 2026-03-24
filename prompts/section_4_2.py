"""
prompts/section_4_2.py — 4-2. 조직 구성 계획
"""

from .common import FORMAT_INSTRUCTIONS


def get_section_4_2_prompt(company_info: dict) -> str:
    """
    4-2. 조직 구성 계획 섹션 프롬프트 생성.

    Args:
        company_info: 기업 정보 딕셔너리. 필요 키:
            - business_item: 재창업 아이템
            - current_employees: 현재 재직 인원 수
            - hiring_plan: 추가 고용 계획 (리스트)
            - hiring_timeline: 채용 시기
    """
    business_item = company_info.get("business_item", "[재창업 아이템]")
    current_employees = company_info.get("current_employees", 0)
    hiring_plan = company_info.get("hiring_plan", [])
    hiring_timeline = company_info.get("hiring_timeline", "[채용 시기]")

    hire_text = ""
    for i, h in enumerate(hiring_plan, 1):
        hire_text += f"  {i}. {h.get('title', '')} - {h.get('role', '')} - {h.get('requirements', '')}\n"

    return f"""## 작성 과제: 4-2. 조직 구성 계획

### 기업 정보
- 재창업 아이템: {business_item}
- 현재 재직 인원: {current_employees}명
- 채용 시기: {hiring_timeline}

### 채용 계획
{hire_text}

### 작성 요구사항

인력 고용 현황 및 채용 계획을 구체적으로 작성하세요.

**가. 인력 고용 현황 및 계획**
- 예비창업자/현재 인원 상태 설명 1줄
- 현재 재직 인원 수
- 추가 고용계획 (협약기간 내) 인원 수

채용 계획 리스트:
"N. 직급(채용 상태) - 담당 업무 - 요구 역량/경력"

### 참고 예시

```
가. 인력 고용 현황 및 계획
- 예비창업자이나 대표 자기자금으로 백엔드 개발자와 근로 형태 계약체결
현재 재직 인원: - 명
추가 고용계획(협약기간 내): 3 명
1. 팀장(채용 예정) - 백엔드 개발 - 백엔드 개발경력 7년, AI 서비스 개발경력 2년
2. 팀원(채용 예정) - 프론트엔드 개발 - SaaS AI 백/프론트엔드 개발 및 운영 경력 2년
3. 팀원(채용 예정) - 경영지원·어드민 - 행정업무/정산시스템 활용 경력 1년
```

{FORMAT_INSTRUCTIONS}"""
