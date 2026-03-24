"""
prompts/section_1_2.py — 1-2. 재창업 아이템 목표시장(고객) 현황 및 필요성
"""

from .common import FORMAT_INSTRUCTIONS


def get_section_1_2_prompt(company_info: dict) -> str:
    """
    1-2. 재창업 아이템 목표시장(고객) 현황 및 필요성 섹션 프롬프트 생성.

    Args:
        company_info: 기업 정보 딕셔너리. 필요 키:
            - business_item: 재창업 아이템
            - target_market: 목표 시장 설명
            - market_problem: 시장의 핵심 문제점
            - solution_steps: 솔루션 단계별 설명 (리스트)
            - tam/sam/som: 시장 규모 수치
            - competitors: 경쟁사 분석 정보
    """
    business_item = company_info.get("business_item", "[재창업 아이템]")
    target_market = company_info.get("target_market", "[목표 시장]")
    market_problem = company_info.get("market_problem", "[시장 문제점]")
    solution_steps = company_info.get("solution_steps", [])
    tam = company_info.get("tam", "[TAM]")
    sam = company_info.get("sam", "[SAM]")
    som = company_info.get("som", "[SOM]")
    competitors = company_info.get("competitors", "[경쟁사 정보]")
    industry = company_info.get("industry", "[산업 분야]")

    steps_text = ""
    for i, step in enumerate(solution_steps, 1):
        steps_text += f"  {i}단계: {step}\n"

    return f"""## 작성 과제: 1-2. 재창업 아이템 목표시장(고객) 현황 및 필요성

### 기업 정보
- 재창업 아이템: {business_item}
- 목표 시장: {target_market}
- 시장 핵심 문제: {market_problem}
- 산업 분야: {industry}
- TAM: {tam}
- SAM: {sam}
- SOM: {som}
- 경쟁사 정보: {competitors}

### 솔루션 단계
{steps_text}

### 작성 요구사항

이 섹션은 4개 파트로 구성됩니다:

**가. 사업 필요성**: 목표 시장의 핵심 진입장벽과 문제점
- 3가지 핵심 문제를 1)/2)/3) 번호로 제시
- 각 문제에 "→ 해결 필요" 형태의 방향성 제시
- 각 문제 아래 - 불렛으로 구체적 통계, 수치 포함 (출처 필수)
- 예시: "1) 대규모 수출 데이터 파편화 →수출 데이터 통합시스템 필요"

**나. 사업 아이템 소개**: 실제 문제를 해결하는 솔루션 단계별 설명
- 전체 솔루션 흐름을 한 줄로 요약 (>로 연결)
- 각 단계를 "N단계. 기능명" 형식으로 설명
- 각 단계 아래 - 불렛으로 구체적 기술/방법론 설명
- 화살표(→) 활용하여 입력→처리→결과 흐름 표현

**다. 목표시장 현황**: TAM/SAM/SOM 시장 규모 분석
- SOM 목표를 먼저 명시 (SAM 대비 점유율 %)
- TAM → SAM → SOM 순서로 구체적 산출 근거 포함
- 수치는 원 단위까지 표기 (예: 5,370억원)
- 산출 기준 명시 (기업 수 × 단가 × 기간)

**라. 차별성 및 경쟁사 분석**: 공공/민간 경쟁사 대비 차별점
- 공공 서비스의 한계점 1-2줄
- 민간 서비스의 한계점 1-2줄
- 당사 서비스의 차별점 2-3줄 (핵심 USP)

### 참고 예시

```
가. 사업 필요성: 중소기업 수출의 높은 진입장벽
중소기업의 수출 단계별 진입 장벽과 해결방안 필요

1) 대규모 수출 데이터 파편화 →수출 데이터 통합시스템 필요
- 대량의 수출 데이터가 UNComtrade, KITA 등에 광범위하게 퍼져있어, 담당 인력이 부족한 중소기업은 데이터 수집조차 힘듦

2) 데이터 해석, 활용방안 부재 →AI·데이터 기반 서비스 필요
- 다양한 수출 데이터가 있어도 실제 수출 의사결정에 활용하기 어려움
- 데이터 해석과 활용을 자동화하는 AI 기반 수출 전략 프로세스 필요

다. 목표시장 현황
- SOM: 3개년 이내 매출 38억 원 목표(SAM 대비 점유율 2.3%)
- TAM (전체 시장): 5,370 억원 *중소기업 9.8만개 / 월 구독료 29만원 기준
- SAM (유효 시장): 1,644 억원 *예상 수요기업 30,000개 기준
- SOM (수익 목표): 38 억원 *Y3 구독 고객 700개사 기준
```

{FORMAT_INSTRUCTIONS}"""
