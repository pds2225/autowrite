# Ralph 오케스트레이터 실행 가이드 (auto_write)

이 문서는 `/oh-my-claudecode:ralph` 류의 **PC 로컬 OMC / Team Ralph 하네스**로
auto_write 기능개선 워크플로우를 **실제로 실행**하기 위한 안내다.
지금 만든 런처는 새 파일 2개뿐이며, **기존 파일은 수정하지 않았다.**

## 준비된 파일 (신규)
- `.claude/commands/autowrite-ralph.md` — 정식 런처(슬래시 커맨드 = Ralph 프롬프트 본문)
- `docs/RALPH_AUTOWRITE_GUIDE.md` — 본 가이드

## PC에서 실행하는 방법 (D:\auto_write)

이 브랜치를 PC로 받는다:
```bash
git fetch origin claude/remote-control-9Z7Zx
git checkout claude/remote-control-9Z7Zx
```

### 방법 A — 프로젝트 슬래시 커맨드 (권장)
D:\auto_write 를 Claude Code로 열면 프로젝트 커맨드가 자동 인식된다.
```
/autowrite-ralph
```
선택 인자로 대상 템플릿/문서 경로를 넘길 수 있다:
```
/autowrite-ralph templates\새양식.docx
```

### 방법 B — Team Ralph 루프 하네스 사용
`.claude/commands/autowrite-ralph.md` **본문 전체**를 복사해
`/oh-my-claudecode:ralph` 의 루프 프롬프트로 붙여넣는다.
(런처가 PHASE 0에서 `D:\.claude` 의 실제 Agent/Skill/Workflow를 탐색·재사용하도록 설계됨.)

## 왜 원격(현재 세션)에서 바로 실행하지 않았나
- `/oh-my-claudecode:ralph`, `Team Ralph`, `D:\.claude`(OMC) 자산은 **사용자 PC(Windows)** 에 있다.
- 현재 세션은 `pds2225/autowrite` 를 클론한 **격리된 리눅스 컨테이너**라 그 자산에 접근할 수 없다.
- 따라서 "기존 하네스를 최대 활용"하라는 요구를 만족하려면, 그 하네스가 있는 **PC에서 실행**되어야 한다. 이 런처가 그 진입점이다.

## 런처에 미리 박아둔 실제 리포 사실 (grounding)
런처가 헛도는 것을 막기 위해, 다음 사실을 프롬프트에 명시해 두었다:
- 점수 산정은 **이미 존재**: `python app/main.py --input <in.json> --output <out.json>` →
  결과 JSON의 `score_breakdown.total_score (/100)` + `validation_issues`. → **새로 만들지 말고 재사용/확장.**
- 양식 인젝션 CLI: `python inject.py --analyze | --skeleton | --template/--content` (참고: `docs/새양식_적용_가이드.md`).
- 테스트 baseline:
  - `python -m pytest tests/ -q` → **22 passed**
  - `cd app && python -m pytest -q` → **57 passed / 1 failed**
  - 알려진 실패(우선 수정 후보): `app/tests/test_project_service_safety.py::ProjectServiceSafetyTests::test_generate_inserts_section_when_anchor_has_no_blank_paragraph`
- 후처리/정리 로직 진입점 후보: `core/content_normalizer.py`, `core/injector.py`, `app/auto_write/`.
- 이 리포의 기존 하네스 자산: `.claude/settings.json`(SessionStart hook) + `.claude/hooks/session-start.sh`.

## 안전장치 (런처에 포함)
- 백업 우선 → 수정 → 테스트 → 커밋 순서 강제, 백업 없이 덮어쓰기 금지
- 품질 게이트 85점 미만 시 수정·재검사 최대 10회, 테스트 실패 시 수정·재시도 최대 10회
- `.env`/Secret 출력·유료 API 호출·`results`/`templates` 원본 삭제·테스트 없는 커밋 금지
- 새 Agent/Skill/Workflow/Command 생성 금지(기존 자산 재사용), 불가피 시 사유를 `PROJECT_REPORT.md` 기록
