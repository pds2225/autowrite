# Loop 4 샘플 생성 검증 보고서

- 일시: 2026-06-02
- 대상: `D:\auto_write` (Loop 2 PSST + Loop 3 results)
- 검증 방식: 자동 테스트 추가 + 템플릿/파일 존재 점검 (에이전트 shell은 bkit 훅으로 pytest 미실행)

## 1. 전체 3줄 요약

1. **Loop 4**용 통합 테스트 `app/tests/test_loop4_sample_generate.py`를 추가했습니다. 샘플 PSST DOCX → 생성 → `results/`·`hwp_paste.txt`·본문 반영을 코드로 검증합니다.
2. **실템플릿 `tpl_a790bad2ed82`**: `template_profile.json`만 있고 **원본 DOCX 파일이 워크스페이스에 없음** → 웹 E2E는 DOCX 재업로드 후 진행 필요.
3. 다음 승인: 로컬 pytest 통과 확인 후 실사용, 또는 **`중지: 로컬만 유지`** / GitHub 반영은 별도 승인.

## 2. 샘플 입력 (테스트·수동 검증 공통)

| 항목 | 샘플 값 |
|------|---------|
| 과제명 | LOOP4 테스트 과제 |
| 기관명 | LOOP4 테스트 기업 |
| 사업 개요 | LOOP4 샘플 사업 개요: AI 안전 제어 스타트업 |
| 추가 메모 | `LOOP4 해결 파트` / (빈 줄) / `LOOP4 성장 파트` / (빈 줄) / `LOOP4 팀 파트` |
| 옵션 | 부분 작성 ON · PSST만 ON · 이미지 OFF |

## 3. 자동 검증 (pytest)

**실행 위치:** `D:\auto_write\app`

```powershell
$env:PYTHONPATH = "D:\auto_write\app"
& "$env:LocalAppData\Programs\Python\Python311\python.exe" -m pytest tests\test_loop4_sample_generate.py tests\test_psst_mapping.py -q --tb=short
```

**성공 기준**

- `test_loop4_sample_generate_writes_results_and_psst_text` PASS
- `output.docx`·`results\{prj}\*.docx`에 **사업 개요** 문구 포함
- `hwp_paste.txt`에 개요 + 해결/성장/팀 3단락 포함
- `image_slot_coverage.all_filled == 0` (이미지 OFF)

## 4. 수동 실사용 검증 (tpl_a790bad2ed82)

**전제:** 아래 DOCX가 폴더에 있어야 합니다.

`D:\auto_write\workspace\templates\tpl_a790bad2ed82\2026년도 초기창업패키지(AI 인재 실증형) 사업계획서 임상진대표작성 20260601.docx`

현재 워크스페이스 스캔: **해당 docx 미발견** (profile JSON만 존재).

**절차**

1. `D:\auto_write\check_env.bat`
2. `D:\auto_write\launch.bat` → http://127.0.0.1:8765
3. 템플릿 없으면 DOCX 재업로드 → 프로젝트 생성
4. 위 샘플 입력 + 생성
5. 확인:
   - `D:\auto_write\results\{프로젝트ID}\` 에 `*_초안.docx`, `hwp_paste.txt`
   - HWP: `hwp_paste.txt` 또는 화면 **전체 복사**
   - DOCX: 「1. 문제 인식」 아래에 **사업 개요**와 동일 문장

## 5. 실사용 체크리스트

| # | 확인 항목 | 기대 |
|---|-----------|------|
| 1 | results 폴더 생성 | `D:\auto_write\results\prj_xxx\` |
| 2 | 날짜 DOCX | `{YYYYMMDD}_{과제명}_초안.docx` |
| 3 | PSST-P = 사업 개요 | 본문 일치 |
| 4 | 메모 3단락 → S/Sc/T | hwp_paste·DOCX 일치 |
| 5 | 이미지 없음 | 새 PNG 삽입 없음 |
| 6 | 오류 메시지 | `generation_summary.txt` 한글 |

## 6. 알려진 제한 (Loop 4 시점)

- 표 `table_index` 불일치 시 일부 칸 미채움 (QA 오류 한글 표시)
- AI 키 없으면 빈 PSST 외 칸은 fallback 문장 가능 (핵심은 **사용자 PSST 우선**)
- 에이전트 환경 pytest 실행: bkit `unified-bash-pre.js` 차단 → **로컬 실행 필요**

## 7. 다음 승인 문구

- `승인: GitHub 반영` — 커밋·PR (사용자 요청 시)
- `중지: 로컬만 유지` — 배포·PR 없이 종료
- pytest 결과 붙여넣기 — 실패 시 `test-fix` 연계
