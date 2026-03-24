"""
prompts/section_2_2.py — 2-2. 재창업 아이템의 실현 및 구체화 방안
"""

from .common import FORMAT_INSTRUCTIONS


def get_section_2_2_prompt(company_info: dict) -> str:
    """
    2-2. 재창업 아이템의 실현 및 구체화 방안 섹션 프롬프트 생성.

    Args:
        company_info: 기업 정보 딕셔너리. 필요 키:
            - business_item: 재창업 아이템
            - tech_stack: 기술 스택
            - dev_phases: 개발 단계별 계획 (리스트)
            - current_dev_status: 현재 개발 현황
            - key_features: 핵심 기능 목록
    """
    business_item = company_info.get("business_item", "[재창업 아이템]")
    tech_stack = company_info.get("tech_stack", "[기술 스택]")
    dev_phases = company_info.get("dev_phases", [])
    current_dev_status = company_info.get("current_dev_status", "[현재 개발 현황]")
    key_features = company_info.get("key_features", [])

    phases_text = ""
    for p in dev_phases:
        phases_text += f"  - Phase {p.get('phase', '')}: {p.get('name', '')} ({p.get('period', '')})\n"
        for detail in p.get('details', []):
            phases_text += f"    - {detail}\n"

    features_text = "\n".join(f"  - {f}" for f in key_features) if key_features else "[핵심 기능]"

    return f"""## 작성 과제: 2-2. 재창업 아이템의 실현 및 구체화 방안

### 기업 정보
- 재창업 아이템: {business_item}
- 기술 스택: {tech_stack}
- 현재 개발 현황: {current_dev_status}

### 핵심 기능
{features_text}

### 개발 단계 계획
{phases_text}

### 작성 요구사항

이 섹션은 기술적 실현 가능성과 개발 로드맵을 증명하는 파트입니다.

**가. 개발 현황 및 계획**을 Phase 기반으로 작성:

- Phase별로 명확한 기간과 목표를 제시
- 각 Phase 형식: "Phase N. 단계명 ('YY.MM 완료/예정)"
- 각 Phase 아래 핵심 개발 내용 1-2줄
- 이미 완료된 Phase는 "구축 완료"로, 예정 Phase는 "예정, 협약 기간 내" 등으로 표기

### Phase 작성 패턴:
1. Phase 1: 핵심 인프라/데이터 기반 구축 (이미 완료 또는 진행중)
2. Phase 2: 핵심 기능 고도화 (협약 기간 내 완료 예정)
3. Phase 3: 확장 기능 및 수익화 (후속 지원사업 활용)

### 참고 예시

```
가. 개발 현황 및 계획
Phase 1. 핵심 데이터 인프라 및 추천 엔진 ('26.01 구축 완료)
- 5종 글로벌 API를 통합한 데이터 파이프라인·ISO3 표준화 엔진 구축

Phase 2. 바이어 매칭 및 필터링 고도화 ('26 05 예정, 협약 기간 내)
- FitScore 정밀 바이어 매칭 시스템(제재·품목 규제·MOQ·인증) 필터링

Phase 3. 수익성 시뮬레이션 및 수출 계약체결 (후속 지원사업 활용)
- 제품단가·물류·관세 등을 반영한 Landed Cost 기반 수익성 시뮬레이션
- 수출계약서 자동 생성(RPA)으로 빠른 계약체결 가능(예: Alibaba.com)
```

{FORMAT_INSTRUCTIONS}"""
