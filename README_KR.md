# DOCX 주입 안정화 엔진 (KR)

이 프로젝트는 사업계획서 템플릿(DOCX)이 매번 달라져도 **깨짐을 줄이는 반자동 주입 엔진**을 목표로 합니다.

## 핵심 기능
- 표 구조 진단(`parsed_template.json`): gridSpan/vMerge 감지, 위험도(safe/caution/manual), 표 유형 후보(team/budget/schedule/org/unknown)
- spanMap 기반 표 주입: visual column 기준 처리, 병합셀 위험 시 강제 주입 대신 warning
- 섹션 텍스트 최소변경 주입: 기존 paragraph/run 구조 유지 우선
- 후처리 자동화: 안내문구 정리, 목차 블록 제거, 말미 참고 블록 제거
- 이미지 주입 안정화: 앵커 우선 + 섹션 fallback + warning
- 렌더 검수: LibreOffice headless로 PDF 변환 + 페이지 수 + 썸네일(가능 시)
- 위험영역 로그: `warnings.json`

## 폴더/파일
- `app.py`: 실행 진입점
- `parser.py`: 템플릿 구조 진단
- `injector.py`: 텍스트/표/이미지 주입
- `postprocess.py`: 앵커 기반 후처리
- `render_check.py`: PDF 렌더 검수
- `models.py`: dataclass 모델
- `utils.py`: 공용 유틸
- `tests/test_engine.py`: 테스트

## 실행
```bash
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py \
  --template input/template.docx \
  --content input/content_master.json \
  --tables input/tables.json \
  --images input/images_manifest.json \
  --output-docx output/result.docx \
  --output-dir output
```

## 출력물
- `output/parsed_template.json`
- `output/warnings.json`
- `output/render_check.json`
- `output/result.docx`
- `output/result.pdf` (LibreOffice 설치 시)

## 주의사항
- vMerge가 있는 복잡 표는 자동주입을 건너뛰고 경고를 남깁니다.
- 이미지 위치를 찾지 못하면 섹션 끝 또는 문서 끝 fallback 삽입합니다.
- 이 엔진은 “완전 자동”이 아닌 “수동검수 시간을 줄이는 자동화”를 목표로 합니다.
