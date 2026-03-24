"""
prompts/section_3_1.py — 3-1. 재창업 아이템 비즈니스 모델
"""

from .common import FORMAT_INSTRUCTIONS


def get_section_3_1_prompt(company_info: dict) -> str:
    """
    3-1. 재창업 아이템 비즈니스 모델 섹션 프롬프트 생성.

    Args:
        company_info: 기업 정보 딕셔너리. 필요 키:
            - business_item: 재창업 아이템
            - revenue_model: 수익 모델 설명
            - subscription_plans: 구독 플랜 정보 (리스트)
            - partnership_revenue: 협력사 연계 매출 정보
            - pricing: 가격 정책
    """
    business_item = company_info.get("business_item", "[재창업 아이템]")
    revenue_model = company_info.get("revenue_model", "[수익 모델]")
    subscription_plans = company_info.get("subscription_plans", [])
    partnership_revenue = company_info.get("partnership_revenue", "[협력사 연계매출]")
    pricing = company_info.get("pricing", "[가격 정책]")

    plans_text = ""
    for p in subscription_plans:
        plans_text += f"  - {p.get('name', '')}: {p.get('price', '')} — {p.get('features', '')}\n"

    return f"""## 작성 과제: 3-1. 재창업 아이템 비즈니스 모델

### 기업 정보
- 재창업 아이템: {business_item}
- 수익 모델: {revenue_model}
- 가격 정책: {pricing}
- 협력사 연계매출: {partnership_revenue}

### 구독 플랜
{plans_text}

### 작성 요구사항

비즈니스 모델의 수익 구조와 협력 매출을 구체적으로 설명하세요.

**핵심 메시지**: 구독료 수입은 기본, 서비스 단계별 협력사 연계 매출 확대가 핵심

**수출 단계별 필요 서비스 협력사 연계 매출** 패턴:
- 번호별로 "서비스 단계 → 연계 서비스, 수익 항목 (건당 금액)" 형식
- 단계별 구체적 수익 금액 범위 포함 (건당 30~50만 원, 거래액의 2~5% 등)

### 참고 예시

```
- 구독료 수입은 부차적, 수출기업에 필요한 서비스 협력사 연계매출을 확대 예정

수출 단계별 필요 서비스 협력사 연계 매출:
01 국가확정 후 → 관세 전문가 연계, FTA 원산지 확인, 관세 (건당 30~50만 원)
02 바이어확정 후 → 유통/에이전트 매칭, 현지 파트너 중개수수료 (거래액의 2~5%)
03 계약진행 시 → 회계/노무 법인 연계, 외환, 세무, 해외 주재원 관리 (건당 50~100만 원)
04 물류/현지 진출 → 포워더 & 지사화, 풀필먼트, 해외 법인 설립 (건당 100~300만 원)
```

{FORMAT_INSTRUCTIONS}"""
