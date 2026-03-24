"""
prompts/section_2_1.py — 2-1. 재창업 아이템 준비 현황
"""

from .common import FORMAT_INSTRUCTIONS


def get_section_2_1_prompt(company_info: dict) -> str:
    """
    2-1. 재창업 아이템 준비 현황 섹션 프롬프트 생성.

    Args:
        company_info: 기업 정보 딕셔너리. 필요 키:
            - business_item: 재창업 아이템
            - ip_status: 지식재산권 현황 (특허, 상표 등)
            - partnerships: 제휴/협력 현황 (리스트)
            - pilot_status: 파일럿 테스트 현황
            - prototype_status: 프로토타입/MVP 개발 현황
    """
    business_item = company_info.get("business_item", "[재창업 아이템]")
    ip_status = company_info.get("ip_status", "[지식재산권 현황]")
    partnerships = company_info.get("partnerships", [])
    pilot_status = company_info.get("pilot_status", "[파일럿 현황]")
    prototype_status = company_info.get("prototype_status", "[프로토타입 현황]")

    partner_text = ""
    for i, p in enumerate(partnerships, 1):
        partner_text += f"  {i}. {p.get('name', '')} - {p.get('type', '')} - {p.get('cooperation', '')}\n"

    return f"""## 작성 과제: 2-1. 재창업 아이템 준비 현황

### 기업 정보
- 재창업 아이템: {business_item}
- 지식재산권 현황: {ip_status}
- 파일럿 현황: {pilot_status}
- 프로토타입/MVP 현황: {prototype_status}

### 파트너/협력 현황
{partner_text}

### 작성 요구사항

이 섹션은 사업 준비의 구체적 진행 상황을 입증하는 파트입니다.

**1) 기술 진입 장벽 구축: 지식재산권 확보**
- 특허/상표/디자인 출원 현황을 구체적으로 기재
- 출원번호, 출원일자 포함
- 특허 명칭을 정확히 기재

**2) 제휴/협력 채널 구축: 다수의 네트워크 확보**
- 파일럿 테스트 대상 기업 수와 확보 현황
- 파트너 현황을 번호 리스트로 정리:
  각 파트너: 기관명 - 유형/역할 - 협력 내용 (관계 단계)
  예시: "1. 루살카 외 11개사 - 수출 경험 유/무 기업 - 파일럿 테스트 진행 (타겟)"

**3) MVP/프로토타입 개발 현황** (해당 시)
- 개발 완료된 기능, 기술 스택 언급
- GitHub 등 증빙 가능한 근거 포함

### 참고 예시

```
1) 기술 진입 장벽 구축: 지식재산권 확보
- 본 사업 관련 특허 1건 출원 (10-2026-0026207, 2026.02.10.)
- HS 코드 및 공공 데이터를 활용한 지능형 수출 유망 국가 추천 및 바이어 매칭 시스템과 그 방법

2) 제휴/협력 채널 구축: 다수의 네트워크 확보
- 10개사 이상의 파일럿 테스트 진행예정 중소기업 확보

파트너 현황:
1. 루살카 외 11개사 - 수출 경험 유/무 기업 - 파일럿 테스트 진행 (타겟)
2. 연세대 창업지원단 외 7개사 - 기업 보육 기관 - 서비스 실증 및 확산 (협력관계)
3. 어나더브레인 외1개사 - 투자사(VC, AC) - 투자유치 가능성 검토
4. DIG(DOAN INTERNATIONAL GROUP) - 베트남 현지 컨설팅사 - 해외 실증 지원
5. 한국경영기술지도사회 외 1개사 - 수출 지원사업 운영기관 - 테스트 기업 모집 지원
```

{FORMAT_INSTRUCTIONS}"""
