"""
prompts/section_3_2.py — 3-2. 재창업 아이템 사업화 추진 전략
"""

from .common import FORMAT_INSTRUCTIONS


def get_section_3_2_prompt(company_info: dict) -> str:
    """
    3-2. 재창업 아이템 사업화 추진 전략 섹션 프롬프트 생성.

    Args:
        company_info: 기업 정보 딕셔너리. 필요 키:
            - business_item: 재창업 아이템
            - marketing_plan: 마케팅 계획
            - sales_channels: 영업 채널
            - go_to_market: GTM 전략
            - target_customers: 타겟 고객
    """
    business_item = company_info.get("business_item", "[재창업 아이템]")
    marketing_plan = company_info.get("marketing_plan", "[마케팅 계획]")
    sales_channels = company_info.get("sales_channels", "[영업 채널]")
    go_to_market = company_info.get("go_to_market", "[GTM 전략]")
    target_customers = company_info.get("target_customers", "[타겟 고객]")

    return f"""## 작성 과제: 3-2. 재창업 아이템 사업화 추진 전략

### 기업 정보
- 재창업 아이템: {business_item}
- 마케팅 계획: {marketing_plan}
- 영업 채널: {sales_channels}
- GTM 전략: {go_to_market}
- 타겟 고객: {target_customers}

### 작성 요구사항

마케팅·영업 계획을 채널별로 구체적으로 작성하세요.

**가. 마케팅·영업 계획**을 채널별 1)/2)/3)으로 구성:

각 채널 패턴:
"N) 채널유형: 구체적 전략 → 기대효과"
- 세부 전략 또는 수익 모델 설명

채널 구분:
1) 공공 채널: 정부 수출지원사업(수출바우처 등) 수행기관 등록 전략
2) 민간 협력: 수출 관련 기업·기관 제휴를 통한 사용자 확장
3) 직접 채널: 온라인 마케팅·콘텐츠를 통한 직접 고객 확보

각 채널별로:
- 구체적 실행 방안 (예: "수출바우처 수행기관 등록")
- 수익화 방식 (예: "월 구독 모델", "성공보수", "키워드 SEO")
- 기대 효과 1줄

### 참고 예시

```
가. 마케팅·영업 계획
1) 공공: 수출바우처 수행기관 등록 → 정부 예산으로 서비스 구매 → 초기 비용 장벽 해소
- 수출 단계별 기능을 제공하는 월 구독 모델

2) 민간 협력: 수출 관련 기업·기관 제휴 → 사용자 규모 확장
- 바이어 매칭(성공보수) / 계약 대행료(검토비) / 물류/관세/법무(파트너십 수수료)

3) 직접 채널: 수출 입문 기업 대상 온라인 마케팅 → 반복 매출
- HS Code/국가추천 키워드 SEO·콘텐츠 마케팅 진행
```

{FORMAT_INSTRUCTIONS}"""
