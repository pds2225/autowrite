# 통합 고도화 마스터 플랜

## 1) 목표
- 여러 플랫폼(Skywork, Auto Write 등)에서 만든 기능을 `D:\auto_write\app` 한 코드베이스로 통합한다.
- 각 플랫폼의 장점만 남기고, 중복/충돌 코드는 제거한다.
- 비개발자도 안정적으로 실행 가능한 수준(실행 배치 + 웹 UI + 자동 테스트 통과)까지 고도화한다.

## 2) 핵심 원칙
- 단일 기준 코드베이스: `auto_write`를 기준으로 통합한다.
- 기능 단위 흡수: 파일 전체 복붙이 아니라 기능(버그 수정/알고리즘/규칙) 단위로 가져온다.
- 회귀 테스트 우선: 기존 기능이 망가지지 않았는지 자동검사 후 반영한다.
  - 회귀 테스트: 기존에 되던 기능이 수정 후에도 계속 되는지 확인하는 테스트.
- 롤백 가능 유지: 각 단계에서 되돌릴 수 있도록 백업 지점을 남긴다.
  - 롤백: 문제 발생 시 이전 안정 상태로 복원하는 절차.

## 3) 비교 대상 최소 파일
- 상세 비교 번들: `D:\auto_write\compare_bundle_autowrite`
- 권장 최소 비교 파일:
  - `auto_write/analysis/docx_template.py`
  - `auto_write/services/project_service.py`
  - `auto_write/services/render_service.py`
  - `auto_write/services/docx_ops.py`
  - `auto_write/services/image_service.py`
  - `auto_write/services/qa_service.py`
  - `workspace_examples/template_profile_example.json`
  - `workspace_examples/project_input_example.json`

## 4) 기능 매핑 (구 플랫폼 -> 현재 플랫폼)
- 템플릿 파싱/맵: `template_parser.py` -> `analysis/docx_template.py`
- 본문/표/이미지 렌더: `render_agent.py`, `docx_writer.py`, `formatter.py` -> `services/render_service.py`, `services/docx_ops.py`
- 이미지 추천/삽입: `image_advisor.py`, `asset_agent.py` -> `services/image_service.py`
- 품질검사: `qa_agent.py` -> `services/qa_service.py`
- 문안/표 자동작성: `writer_agent.py`, `table_agent.py` -> `services/project_service.py`

## 5) 4단계 실행 순서

### Phase A. 안정화 기준선 고정
- 작업:
  - 실행 경로/키 로딩 점검 (`launch.bat`, `.env`)
  - `/health`가 항상 응답하도록 고정
  - 기본 테스트 전부 통과 상태 확보
- 완료 기준:
  - `python -m unittest discover -s tests -p "test_*.py"` 통과
  - 웹 접속 및 생성 플로우 동작

### Phase B. Skywork 장점 흡수
- 작업:
  - 이미지 중복 삽입 방지 로직 강화
  - 텍스트 색/서식 보존 로직 강화
  - 계획서 작성 품질 규칙(핵심 항목 자동작성) 정교화
- 완료 기준:
  - 이미지 슬롯당 drawing 1개 유지
  - 스타일 깨짐(색상/폰트) 재발 없음
  - QA 오류 감소 추세 확인

### Phase C. 범용 템플릿 엔진 강화
- 작업:
  - 동의서/행정 페이지 자동 제외 규칙 확장
  - 템플릿별 필수/선택 질문 자동 분리
  - 결과 문서 기반 QA 판정 강화
- 완료 기준:
  - 불필요 입력 필드 감소
  - 템플릿 2종 이상에서 작성 성공

### Phase D. 운영 고도화
- 작업:
  - 비교 리포트 자동 생성(벤치마크 대비 갭)
  - 실패 원인 사용자 문구 개선
  - 백업/복원 절차 문서화
- 완료 기준:
  - 비개발자 기준으로 원인 파악 가능
  - 재실행/복원 절차 5분 내 수행 가능

## 6) 이번 주 우선 백로그
- [ ] 템플릿 분석 결과를 “사업계획 본문 우선”으로 재정렬
- [ ] 자동작성 입력 최소화(핵심 입력 + 참고자료 중심)
- [ ] 이미지 삽입 위치 신뢰도 점수 도입(낮으면 삽입 보류)
- [ ] QA 메시지 표준화(무엇이 비었고 어떻게 채울지 안내)
- [ ] 생성 실패 케이스 5개 재현 테스트 추가

## 7) 리스크와 대응
- 리스크: 플랫폼별 데이터 구조 불일치로 필드 누락/오삽입
  - 대응: 매핑 테이블 고정 + 파싱 결과 검증 단계 추가
- 리스크: 이미지/서식 삽입 시 문서 스타일 훼손
  - 대응: 빈 슬롯 우선 삽입 + 강제 포맷 리셋 금지
- 리스크: AI 제공자 변경(OpenAI/Anthropic) 시 출력 편차
  - 대응: 제공자 어댑터 통일 + 공통 fallback 문구 유지

## 8) 롤백 포인트
- 코드 롤백: Phase 시작 전 파일 스냅샷 저장
- 데이터 롤백: `workspace/templates`, `workspace/projects` 백업본 유지
- 운영 롤백: `launch.bat` 이전 버전 보관

