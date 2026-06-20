# Auto Write

`D:\auto_write\launch.bat`를 실행하면 로컬 웹 화면이 열립니다.

## 주요 기능

- DOCX 템플릿 업로드 후 자동 구조 분석
- 문단, 표 빈 칸, 이미지 위치를 JSON으로 수정 가능
- 참고자료 업로드와 입력 폼 기반 문안 생성
- 통계 검색 결과를 `sources.json`으로 저장
- 설명 이미지를 자동 생성하거나 기본 이미지로 대체
- 결과 DOCX, QA 리포트, 출처 목록, 벤치마크 비교 리포트 저장
- 참고사업계획서(PDF/DOCX)에서 활용 가능한 문장 패턴을 추출해 초안 작성에 반영

## 실행 방법

### Windows 사용

```bat
D:\auto_write\launch.bat
```

`launch.bat`는 `app` 폴더로 이동한 뒤 `python -m uvicorn auto_write.main:app --host 127.0.0.1 --port 8765`를 실행하고 브라우저를 엽니다.
`AUTO_WRITE_HOST`와 `AUTO_WRITE_PORT`를 지정하면 호스트와 포트를 바꿀 수 있습니다.

### 개발 환경 사용

```bash
cd app
python -m pip install -r requirements.txt
python -m uvicorn auto_write.main:app --host 127.0.0.1 --port 8765
```

상태 확인:

```bash
curl http://127.0.0.1:8765/health
```

`/health`는 `status`, `ai_available`, `ai_provider`, `status_text`를 반환합니다.

## OpenAI API 키

더 정확한 문안 생성에는 `OPENAI_API_KEY` 또는 `ANTHROPIC_API_KEY` 환경 변수가 필요합니다.
OpenAI 키가 있으면 문안 생성, 검색, 이미지 생성까지 모두 사용할 수 있습니다.
Anthropic 키가 있으면 문안 생성과 요약에 사용할 수 있고, 이미지는 기본 카드로 대체될 수 있습니다.
키가 없어도 템플릿 분석, 입력 저장, 기본 이미지 생성, DOCX 출력은 동작합니다.

### 키 설정 방법(비개발자용)

1. `D:\auto_write\app\.env.example` 파일을 복사해서 `D:\auto_write\app\.env` 파일을 만듭니다.
2. `.env` 파일의 `OPENAI_API_KEY=` 또는 `ANTHROPIC_API_KEY=` 뒤에 발급받은 키를 붙여 넣습니다.
3. `D:\auto_write\launch.bat`를 다시 실행합니다.
4. 두 키가 모두 비어 있으면 실행 창에 기본 동작 안내가 표시됩니다.

### 참고사례 폴더(잘 쓴 부분 재활용)

- 기본값: `2025년\20250406 희망리턴패키지 서류평가\경영개선 4조 서류평가` 폴더를 자동 탐색합니다.
- 경로를 바꾸려면 `.env`에 아래 값을 넣으면 됩니다.
  - `AUTO_WRITE_REFERENCE_LIBRARY_DIR=폴더전체경로`
- 지원 형식: `PDF`, `DOCX`, `TXT`, `MD`

## PSST 초안 생성 워크플로우

최근 사업계획서 양식은 PSST 구조를 기준으로 처리합니다. 기본 프로젝트 설정은 `부분 작성 양식 개선`, `PSST만 생성`, `이미지 생성 안 함`이 켜진 상태로 저장됩니다.

1. 홈 화면에서 DOCX/HWPX/HWP 템플릿을 업로드합니다.
2. 템플릿 상세 화면에서 분석된 문단, 표, 이미지 슬롯 JSON을 확인하고 필요하면 수정 후 저장합니다.
3. 프로젝트를 생성한 뒤 핵심 입력값을 작성합니다.
4. `계획서 생성 실행`을 누르면 입력 저장, 부족한 항목 보정, DOCX 렌더링, QA 리포트, results 패키지 발행이 한 번에 수행됩니다.

### 입력 매핑 규칙

| 입력 | 반영 위치 |
|---|---|
| `사업 개요` | PSST `1. 문제 인식 (Problem)` 문단 |
| `추가 메모` 한 덩어리 | PSST `2. 실현 가능성 (Solution)` 문단 |
| `추가 메모`를 빈 줄로 나눈 2~3개 블록 | 순서대로 `Solution`, `Scale-up`, `Team` 문단 |
| 자동 입력용 파일 | 과제명, 기관명, 사업 개요, 추가 메모, 근거 주제 자동 보완 및 참고자료로 저장 |
| 참고자료 여러 개 | 생성 컨텍스트와 출처 기반 보정에 사용 |

PSST 문단은 템플릿의 문단 라벨 또는 앵커 텍스트가 아래 형태와 맞을 때 인식됩니다.

- `1. 문제 인식 ... Problem`
- `2. 실현 가능성 ... Solution`
- `3. 성장전략 ... Scale`
- `4. 팀 구성 ... Team`

`PSST만 생성`이 켜져 있으면 위 4개 문단과 핵심 표만 자동 보정합니다. `○ 산업 동향` 같은 불릿 본문, 제출 확인문, 증빙/개인정보/담당자 항목은 자동 보정 대상에서 제외됩니다.

### 생성 결과 위치

실사용 파일은 프로젝트별 `results` 폴더에 발행됩니다.

| 파일 | 용도 |
|---|---|
| `YYYYMMDD_과제명_초안.docx` | 제출용으로 확인할 날짜 표기 초안 |
| `output.docx` | 최신 생성 DOCX 사본 |
| `hwp_paste.txt` | 한글(HWP)에 제목별로 붙여넣을 전체 텍스트 |
| `copy_blocks.json` | 화면의 섹션별 `복사` 버튼에 쓰이는 블록 데이터 |
| `fill_map.json` | PSST 매핑, 사용자 입력 반영 여부, 렌더링 요약 |
| `generation_summary.txt` | 생성 통과/경고 요약과 사용 안내 |
| `qa_report.json` | 렌더링·문서 품질 점검 결과 |

작업 폴더의 `workspace/projects/<project_id>/output`에는 `sources.json`, `benchmark_compare.json`, `transfer_report.json`, `preview_manifest.json`도 저장됩니다. 화면의 다운로드 링크는 먼저 `results` 파일을 찾고, 없으면 작업 폴더의 `output` 파일을 반환합니다.

## 운영 및 문제 해결

- 템플릿 분석 결과가 어긋나면 템플릿 상세 화면의 JSON에서 문단 앵커와 표 셀 라벨을 먼저 확인합니다.
- AI 키가 없으면 문안 품질은 제한되지만 템플릿 분석, 입력 저장, DOCX 렌더링, `results` 발행은 계속 동작합니다.
- HWP 작업은 `hwp_paste.txt`의 `=== 제목 ===` 아래 본문과 탭 구분 표 줄을 원본 양식 위치에 붙여넣는 방식이 가장 안전합니다.
- DOCX 미리보기 렌더러가 없으면 `preview_manifest.json`은 `skipped` 또는 경고 상태가 될 수 있습니다. 이 경우에도 DOCX와 QA 파일은 생성됩니다.
- 참고자료를 업로드한 경우 원문 보존 모드로 처리되어 근거가 없는 항목은 임의로 채우지 않을 수 있습니다. 빈 항목은 `fill_map.json`과 QA 경고를 확인합니다.
