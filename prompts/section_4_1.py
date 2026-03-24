"""
prompts/section_4_1.py — 4-1. 조직 구성 및 보유 역량
"""

from .common import FORMAT_INSTRUCTIONS


def get_section_4_1_prompt(company_info: dict) -> str:
    """
    4-1. 조직 구성 및 보유 역량 섹션 프롬프트 생성.

    Args:
        company_info: 기업 정보 딕셔너리. 필요 키:
            - business_item: 재창업 아이템
            - ceo_info: 대표자 정보 (dict: name, education, career, certifications, strengths)
            - team_members: 팀원 정보 (리스트)
    """
    business_item = company_info.get("business_item", "[재창업 아이템]")
    ceo = company_info.get("ceo_info", {})
    team_members = company_info.get("team_members", [])

    ceo_name = ceo.get("name", "[대표자명]")
    ceo_education = ceo.get("education", "[학력]")
    ceo_career = ceo.get("career", "[경력]")
    ceo_certs = ceo.get("certifications", "[자격]")
    ceo_strengths = ceo.get("strengths", "[강점]")

    team_text = ""
    for i, m in enumerate(team_members, 1):
        team_text += f"  {i}) {m.get('role', '')} ({m.get('status', '채용 예정')})\n"
        team_text += f"     - {m.get('description', '')}\n"

    return f"""## 작성 과제: 4-1. 조직 구성 및 보유 역량

### 기업 정보
- 재창업 아이템: {business_item}

### 대표자 정보
- 이름: {ceo_name}
- 학력: {ceo_education}
- 경력: {ceo_career}
- 자격사항: {ceo_certs}
- 핵심 강점: {ceo_strengths}

### 팀원 정보
{team_text}

### 작성 요구사항

이 섹션은 대표자와 팀의 역량을 입증하는 파트입니다.

**가. 대표자 역량**
- 핵심 역량을 한 줄로 요약 (예: "융합 역량: 필드 지식 × 개발 역량 동시에 보유")
- 해당 사업과 관련된 실무 경험 기반 강점 2-3가지
- 학력, 주요경력을 시간순으로 정리
- 자격사항 목록

경력 표기 형식:
"- YY.MM-YY.MM 기관명 직책(업무)"

자격사항 표기 형식:
"- 자격명 (발급기관, 취득일)"

**나. 팀 역량**
- 각 팀원을 번호로 정리
- 직급/역할, 채용 상태 (재직중/채용예정)
- 경력 요약 1줄
- 해당 사업에서의 역할과 기대 기여 1줄

### 참고 예시

```
가. 대표자 역량
- 융합 역량: 필드 지식 × 개발 역량 동시에 보유
- 수출 컨설턴트 활동으로 수출 중소기업의 애로사항 및 사업 필요성 확인
- AI 서비스 기획 및 바이브 코딩 역량 보유 (PM 업무 가능)
- 개발자와 공동 작업 FastAPI 기반 백엔드 및 데이터 파이프라인 구축

학력: 석사 경영컨설팅 (25.08 졸업)
주요경력:
- 22.11-25.11 **파트너스 경영컨설팅 대표(총괄)
- 22.02-22.11 **브릿지 경영컨설팅 선임컨설턴트(컨설팅)
자격사항:
- 경영지도사 (중소벤처기업부, 20.01.01)
- 스타트업 AC 심사역 (씨엔티테크, 23.02.07)

나. 팀 역량
1) 백엔드 개발자 (팀장급, 채용 예정)
- 백엔드 개발 경력 7년 이상, AI 서비스 개발 경력 2년을 보유한 AI 개발자

2) 프론트엔드 개발자 (팀원급, 채용 예정)
- SaaS 기반 AI 서비스를 단독 기획·설계·개발·운영 경험 보유 풀스택 개발자
```

{FORMAT_INSTRUCTIONS}"""
