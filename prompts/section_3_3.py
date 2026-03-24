"""
prompts/section_3_3.py — 3-3. 사업 추진 일정 및 자금 운용 계획
"""

from .common import FORMAT_INSTRUCTIONS


def get_section_3_3_prompt(company_info: dict) -> str:
    """
    3-3. 사업 추진 일정 및 자금 운용 계획 섹션 프롬프트 생성.

    Args:
        company_info: 기업 정보 딕셔너리. 필요 키:
            - business_item: 재창업 아이템
            - agreement_period: 협약 기간 (예: '26.4월~10월)
            - monthly_milestones: 월별 마일스톤 (리스트)
            - total_budget: 총사업비
            - gov_support: 정부지원금
            - self_fund_cash: 자기부담(현금)
            - self_fund_inkind: 자기부담(현물)
            - budget_items: 비목별 예산 (리스트)
    """
    business_item = company_info.get("business_item", "[재창업 아이템]")
    agreement_period = company_info.get("agreement_period", "[협약 기간]")
    monthly_milestones = company_info.get("monthly_milestones", [])
    total_budget = company_info.get("total_budget", "[총사업비]")
    gov_support = company_info.get("gov_support", "[정부지원금]")
    self_fund_cash = company_info.get("self_fund_cash", "[자기부담 현금]")
    self_fund_inkind = company_info.get("self_fund_inkind", "[자기부담 현물]")
    budget_items = company_info.get("budget_items", [])

    milestones_text = ""
    for i, m in enumerate(monthly_milestones, 1):
        milestones_text += f"  {i}. {m.get('task', '')} ({m.get('period', '')})\n"

    budget_text = ""
    for b in budget_items:
        budget_text += f"  - {b.get('category', '')}: {b.get('detail', '')} = {b.get('amount', '')}\n"

    return f"""## 작성 과제: 3-3. 사업 추진 일정 및 자금 운용 계획

### 기업 정보
- 재창업 아이템: {business_item}
- 협약 기간: {agreement_period}
- 총사업비: {total_budget}
- 정부지원금: {gov_support}
- 자기부담(현금): {self_fund_cash}
- 자기부담(현물): {self_fund_inkind}

### 월별 마일스톤
{milestones_text}

### 비목별 예산
{budget_text}

### 작성 요구사항

이 섹션은 2개 파트로 구성됩니다:

**가. 협약기간 목표 및 추진 일정**
- 협약 기간을 명시하고 월별 마일스톤을 번호 리스트로 정리
- 각 마일스톤: "N. 활동명 - 구체적 목표 (기간)"
- 7개 내외의 월별 마일스톤 제시
- 구체적 수치 목표 포함 (20~30개사, 10개사 등)

**다. 사업비 구성** (참고: 가→다 순서는 양식 특성)
- 총사업비 = 정부지원 + 자기부담(현금) + 자기부담(현물)
- 비목별 세부 내역: 단가 × 수량 = 금액 형식
- 인건비: 직급별 인원 × 개월 × 월급 = 금액

### 참고 예시

```
가. 협약기간 ('26.4월~10월) 목표 및 추진 일정
1. 초기 고객 검증 설계 - 테스트 기업 모집 및 베타 준비 ('26.04)
2. PMF 검증 - 베타 20~30개사 운영 및 기능 개선 ('26.05)
3. 유료화 구조 설계 - Basic/Pro 플랜 확정 및 결제 시스템 구축 ('26.06)
4. 매출 발생 구조 구축 - 유료 고객 10개사 확보·수출바우처 등록 ('26.07)
5. B2B 리드 확보 - 웨비나 개최 및 리드 DB 구축 ('26.08)
6. 제휴 확장 - 관세법인·물류사 제휴 체결 확장 ('26.09)
7. 성과 고도화·투자 준비 - 전환율 분석 및 투자 준비 ('26.10)

다. 사업비 구성
총사업비: 134,340,000원
- 정부지원(ⓐ): 100,000,000원
- 자기부담(ⓑ): 현금 7,670,000원 + 현물 26,670,000원

비목:
- 외주용역비: 개발비 백엔드, 프론트엔드 - 20,000,000원
- 인건비: 백엔드 1명 x 3개월 x 4,800,000원 = 14,400,000원
```

{FORMAT_INSTRUCTIONS}"""
