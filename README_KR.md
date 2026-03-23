# 사업계획서용 이미지 자동수집기

사업계획서 섹션별 요약을 입력하면, 우선순위(통계/현장/제품/공정) 기반으로 이미지를 검색하고 다운로드한 뒤 `manifest`를 생성하는 Streamlit 도구입니다.

## 1) 제공 기능
- 사업명 + 섹션별 요약 입력
- 섹션별 후보 이미지 자동 검색 (SerpAPI 또는 Bing Image Search API)
- 섹션별 기본 3개 이미지 다운로드
- 최소 해상도(너비/높이) 필터
- 동일/유사 이미지 중복 제거 (SHA256 + pHash)
- 출처 URL/캡션 포함 `images_manifest.json`, `images_manifest.csv` 생성
- 오류 로그 저장 (`logs/error.log`)
- 생성형 이미지 보관용 `separate_generated_images/` 폴더 분리

## 2) 프로젝트 구조

```text
.
├─ app.py
├─ image_search.py
├─ downloader.py
├─ dedupe.py
├─ manifest_writer.py
├─ requirements.txt
├─ README_KR.md
├─ images/
├─ separate_generated_images/
├─ logs/
├─ queries.csv
├─ images_manifest.json
└─ images_manifest.csv
```

## 3) 설치 (Windows)

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## 4) API 키 설정

### SerpAPI (권장)
```powershell
setx SERPAPI_API_KEY "YOUR_KEY"
```

### Bing Image Search API (선택)
```powershell
setx BING_SEARCH_API_KEY "YOUR_KEY"
setx BING_IMAGE_SEARCH_ENDPOINT "https://api.bing.microsoft.com/v7.0/images/search"
```

> 참고: Bing 관련 정책/가용성은 시점에 따라 달라질 수 있으므로, 신규 구성은 SerpAPI 우선 권장입니다.

## 5) 실행

```powershell
streamlit run app.py
```

브라우저에서 다음을 입력합니다.
1. 사업명
2. 섹션명 + 요약(예: `problem`, `solution`, `scaleup`, `team`)
3. 섹션별 다운로드 개수(기본 3), 최소 해상도

## 6) 출력 결과
- `images/`: 다운로드된 이미지
- `images_manifest.json`, `images_manifest.csv`: 파일명, 섹션, 출처 URL, 캡션, 해상도, 해시 등
- `queries.csv`: 실제 검색/수집 대상 URL 추적
- `logs/error.log`: 오류 로그

## 7) 파일명 규칙
`section_index_title.ext`

예시: `problem_01_market_size_chart.jpg`

## 8) 캡션 생성 방식
`[section] title — summary 앞부분` 형식으로 자동 생성합니다.

## 9) 주의사항
- 검색 API 응답 품질에 따라 이미지 품질/저작권 상태가 다를 수 있습니다.
- 실제 배포/상업 이용 시 이미지 라이선스 검토가 필요합니다.
