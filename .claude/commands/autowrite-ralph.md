---
description: auto_write 문서 품질개선 워크플로우를 기존 OMC / Team Ralph 자산으로 오케스트레이션 실행 (구현보다 오케스트레이션 우선)
argument-hint: "[대상 템플릿/문서 경로 (선택)]"
---

# /autowrite-ralph — auto_write 기능개선 오케스트레이터

> 이 파일은 **PC(D:\auto_write)에서 실행되는 런처**다.
> 본문 전체를 `/oh-my-claudecode:ralph` 의 루프 프롬프트로 붙여넣어 사용해도 동일하게 동작한다.
> 목표는 **분석 보고서 작성이 아니라**, 실제 코드 수정 → 테스트 → 품질검사 → 결과 보고까지 **완료**하는 것이다.
> Claude는 **구현자보다 오케스트레이터 역할을 우선** 수행한다.

대상(선택): `$ARGUMENTS`

---

## PHASE 0 — 하네스 자산 탐색 (작업 시작 즉시, 가정 금지)

다음을 **실제로 읽어서** 확인하고, 발견한 것만 보고한다. 존재하지 않는 자산을 만들어내지 말 것.

1. `D:\.claude` 전체 탐색 (Windows). 폴더 구조와 파일을 실제 나열한다.
2. 사용 가능한 **Agent** 확인 — `D:\.claude\agents\*`, OMC 플러그인 에이전트
3. 사용 가능한 **Skill** 확인 — `D:\.claude\skills\*`, 플러그인 skill
4. 사용 가능한 **Workflow** 확인 — Team Ralph workflow 정의
5. 사용 가능한 **Command** 확인 — `D:\.claude\commands\*`, `/oh-my-claudecode:*`
6. 사용 가능한 **Hook** 확인 — `D:\.claude\settings.json` 의 hooks

> 참고: 이 리포 자체에도 `.claude/settings.json`(SessionStart hook) + `.claude/hooks/session-start.sh` 가 있다. 이것도 자산으로 보고한다.

**반드시 보고**: 실제 발견한 Agent / Skill / Workflow 목록 (파일 경로 기준, 추상 설명 금지).

---

## PHASE 1 — 기존 하네스 우선 활용 규칙

우선순위(높을수록 먼저):
1. 기존 Agent 사용
2. 기존 Skill 사용
3. 기존 Workflow 사용
4. 기존 Command 사용
5. 기존 Hook 사용
6. 기존 코드 수정

금지: **새 Agent / Skill / Workflow / Command 생성 금지.**
예외: 기존 하네스로 **절대 구현 불가능**한 경우에 한해, 그 이유를 `PROJECT_REPORT.md` 에 기록 후 진행.

오케스트레이션 권장: 발견한 Team Ralph orchestrator / 병렬 에이전트가 있으면 그것으로 아래 분석 단계를 fan-out 한다. 없으면 일반 서브에이전트(Explore/general-purpose 류)로 대체하되, 그 사실을 보고한다.

---

## PHASE 2 — auto_write 분석 (병렬 가능)

아래 파일을 확인한다. **없는 파일은 "없음"으로 기록 후 진행**(중단하지 말 것):
`README.md` · `CLAUDE.md` · `AGENTS.md` · `AI_ROUTING.md` · `RULES.md` · `TASKS.md`
`app/` · `tests/` · `templates/` · `results/` · `scripts/`
`pyproject.toml` · `requirements.txt`

> 이 리포의 알려진 사실(grounding):
> - 진입 CLI: `python app/main.py --input <in.json> --output <out.json>` → 결과 JSON에 `score_breakdown.total_score (/100)` 와 `validation_issues` **이미 존재** → **점수 산정 로직을 새로 만들지 말고 재사용/확장**한다.
> - 양식 인젝션 CLI: `python inject.py --analyze <docx>` / `--skeleton <docx> --output <json>` / `--template <docx> --content <json>` (가이드: `docs/새양식_적용_가이드.md`).
> - 핵심 로직: `core/` (analyzer, injector, criteria_mapper, content_normalizer, chart_generator, company_profile), `app/auto_write/` (autofill, document_ingest, models, storage).
> - 안내문구 제거/문단 정리 관련 후처리는 `core/content_normalizer.py`, `core/injector.py`, `app/auto_write/` 의 render/postprocess 경로를 우선 확인한다.

**병렬 fan-out** (서로 독립 → 동시 실행): ① 코드 분석 ② 템플릿 분석 ③ 테스트 분석 ④ 품질규칙 분석.
**순차 필수**: 백업 → 코드 수정 → 테스트 → 저장 → 커밋.

---

## PHASE 3 — 백업 먼저 (덮어쓰기 전 필수)

수정 전, 영향받는 파일과 `results/` 산출물을 백업한다. **백업 없이 덮어쓰기 금지.**
권장: `results/_backup/<UTC타임스탬프>/` 또는 git stash/branch. 롤백 절차를 `PROJECT_REPORT.md` 에 적는다.
`templates/` 원본·`results/` 전체·기존 사용자 데이터 **삭제 금지.**

---

## PHASE 4 — 기능개선 구현 (최소 수정, 기존 기능 보호)

기존 정상 기능 동작을 새 기능보다 우선한다. 대규모 리팩토링 금지. 가능한 한 기존 함수에 가드/옵션을 더하는 방식으로.

1. 기존 양식 안내문구 제거: 파란색 안내문구 / 작성예시 / 작성요령 / "삭제 후 작성" / 텍스트박스 안내문 / 투명선 네모박스 안내문
2. 글머리표 공백 정리
3. 문단 수준별 글자크기 자동 조정
4. 주요문장 Bold / Underline
5. 표 내부 공백 제거
6. 빈 문단 정리
7. 이미지 삽입 제안 생성
8. 문서 유형 자동 분류
9. 사업계획서 PSST 검사
10. 문서 품질점수 산정 (← 기존 `score_breakdown` 재사용/확장)
11. 품질 게이트: 점수 **85점 미만 → 수정 → 재검사**, **최대 10회** 루프
12. 결과물 백업 및 롤백

### 문서 유형별 품질검사 기준
- 사업계획서: PSST · 시장성 · 사업화 · 팀 역량
- 컨설팅보고서: 기업현황 · 진단결과 · 개선과제 · 실행계획 · 기대효과
- 정책자금 보고서: 자금용도 · 상환재원 · 재무현황 · 리스크
- 인증보고서: 인증요건 · 충족현황 · 보완과제

---

## PHASE 5 — 테스트 (테스트 없이 커밋 금지)

후보를 순서대로 시도하고, 실제 동작한 명령을 보고한다:
- 루트: `python -m pytest tests/ -q`  (현재 baseline: **22 passed**)
- 앱:  `cd app && python -m pytest -q`  (현재 baseline: **57 passed / 1 failed**)
  - 알려진 실패: `app/tests/test_project_service_safety.py::ProjectServiceSafetyTests::test_generate_inserts_section_when_anchor_has_no_blank_paragraph` (앵커 뒤 빈 문단이 없을 때 본문 미삽입). **이 회귀를 우선 수정 대상으로 검토.**
- 대체: `uv run pytest`, 기존 inspect/샘플 생성 명령(`inject.py --analyze`, `app/main.py` 샘플 in/out)
- 의존성 누락 시: 루트 `pip install -r requirements.txt`, 앱 `pip install -r app/requirements.txt` (pydantic/fastapi 등)

실패 시: 원인 분석 → 수정 → 재테스트, **최대 10회**. 유료 API 호출 없이(키 없으면 모킹/스킵) 진행.

---

## PHASE 6 — Git (충돌 없을 때만 커밋)

작업 브랜치: `claude/remote-control-9Z7Zx` (지정 외 브랜치 push 금지).
```
git status
git diff --stat
```
변경파일 요약 + 테스트 결과 확인 후, 충돌 없으면:
```
git add .
git commit -m "fix: improve auto_write document quality workflow"
```

---

## 금지사항
.env / API Key / Secret 출력 금지 · 운영 배포 금지 · DB 삭제 금지 · 유료 API 호출 금지 · 기존 정상 기능 삭제 금지 · `results` 전체 삭제 금지 · `templates` 원본 삭제 금지 · 백업 없이 덮어쓰기 금지 · 테스트 없이 커밋 금지 · **성공하지 않았는데 성공으로 보고 금지** · 분석만 하고 종료 금지.

---

## 성공 기준 (모두 충족해야 성공)
1) 코드 수정 완료 2) 테스트 통과 3) 기능 동작 확인 4) 품질검사 완료 5) 품질점수 계산 가능 6) 백업 구조 동작 7) 결과 보고 완료

---

## 최종 보고 형식 (이 순서로 출력)
- 전체 3줄 요약
- 발견한 하네스 자산 (실제 `D:\.claude` 경로 기준)
- 사용한 Agent / 사용한 Skill / 사용한 Workflow
- 확인한 파일 / 수정한 파일 (실제 경로)
- 구현한 기능
- 실행한 테스트 / 테스트 결과 / 실패 후 수정 내용
- 품질점수 결과
- 백업 위치
- 남은 문제 / 수동 확인 필요사항
- Git 상태 / 커밋 해시

> 추상 설명 금지. 실제 사용한 `D:\.claude` 자산명과 실제 파일 경로를 반드시 기록한다.
