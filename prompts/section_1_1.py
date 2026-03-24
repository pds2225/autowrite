"""
prompts/section_1_1.py — 1-1. 폐업 원인 분석 및 개선 방안
"""

from .common import FORMAT_INSTRUCTIONS


def get_section_1_1_prompt(company_info: dict) -> str:
    """
    1-1. 폐업 원인 분석 및 개선 방안 섹션 프롬프트 생성.

    Args:
        company_info: 기업 정보 딕셔너리. 필요 키:
            - company_name: 기업명
            - business_item: 재창업 아이템
            - previous_business: 이전 사업 내용
            - closure_reason: 폐업 원인
            - closure_history: 폐업 이력 (리스트)
            - solution_overview: 해결방안 개요
    """
    company_name = company_info.get("company_name", "[기업명]")
    business_item = company_info.get("business_item", "[재창업 아이템]")
    previous_business = company_info.get("previous_business", "[이전 사업]")
    closure_reason = company_info.get("closure_reason", "[폐업 원인]")
    closure_history = company_info.get("closure_history", [])
    solution_overview = company_info.get("solution_overview", "[해결방안]")

    closure_text = ""
    for h in closure_history:
        closure_text += f"- {h.get('company', '')} / {h.get('period', '')} / {h.get('item', '')} / 폐업원인: {h.get('reason', '')}\n"

    return f"""## 작성 과제: 1-1. 폐업 원인 분석 및 개선 방안

### 기업 정보
- 기업명: {company_name}
- 재창업 아이템: {business_item}
- 이전 사업: {previous_business}
- 폐업 원인: {closure_reason}
- 해결방안 개요: {solution_overview}

### 폐업 이력
{closure_text}

### 작성 요구사항

**가. 폐업 원인 분석** 파트를 먼저 작성하세요:
- 폐업의 근본 원인을 3가지 카테고리로 분석 (사업구조, 시장특성, 수익구조 등)
- 각 원인에 대해 (원인) → (해결방안) 대비 구문 사용
- 예시: "(사업 구조) 노동집약적 서비스 → SaaS 기반 자동화 플랫폼"
- 각 원인-해결 쌍 아래에 - 불렛으로 상세 설명 2줄씩 작성
  - 첫 줄: (문제점 키워드) 구체적 문제 설명
  - 둘째 줄: (해결방안 키워드) 구체적 해결 방안

**나. 개선 방안** 파트를 작성하세요:
- 재창업 아이템이 위 폐업 원인을 어떻게 구조적으로 해결하는지
- 사업 확장성, 수익 구조 개선, 경쟁력 확보 관점에서 설명
- 핵심 가치제안을 2-3줄로 명확하게 제시

### 참고 예시 (이 수준의 품질로 작성하세요)

```
가. 폐업 원인 분석 : 중소기업 컨설팅 서비스
컨설팅 서비스 폐업 원인별 개선 방안

(사업 구조) 노동집약적 서비스→SaaS 기반 자동화 플랫폼
- (노동력 기반 사업) 기존 컨설팅은 인력 충원 없이는 사업 확장 제한적
- (SaaS 기반 자동화) 인력 충원 없이도 원활한 사업 확장 가능

(시장 특성) 저연차 컨설턴트의 경험 부족→AI·데이터 활용으로 보완
- (경쟁력 확보한계) 고연차 컨설턴트의 경험량을 단시간에 따라잡기 힘듦
- (AI·데이터 활용) 컨설팅 경험을 데이터화, AI학습으로 경험량 격차극복

(수익구조) 일회성 수익모델→구독형 수익모델로 반복 매출
- (계약 매출) 목적 달성 후 종료되는 단발성 계약 형태로 재계약 어려움
- (구독료 매출) 구독모델도입으로 반복 구매 및 재계약 쉬움

나. 개선 방안: AI·데이터 기반 중소기업 수출지원 One-Stop 플랫폼
재창업 아이템: 중소기업 수출지원 플랫폼
- 수출국가 추천→바이어매칭→계약까지 수출 계획·실행을 한 곳에서 가능
- SaaS 기반으로 사업 확장성과 구독모델로 반복적 매출구조동시 확보
```

{FORMAT_INSTRUCTIONS}"""
