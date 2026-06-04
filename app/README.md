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
