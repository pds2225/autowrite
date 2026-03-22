# 📄 BizPlan Injector

> **사업계획서 DOCX 자동 주입 도구**  
> 원본 양식 서식을 그대로 유지하면서, JSON 파일 하나로 모든 내용을 자동 채워넣습니다.

---

## 🚀 빠른 시작

### 1. 설치

```bash
git clone https://github.com/YOUR_USERNAME/bizplan_injector.git
cd bizplan_injector
pip install -r requirements.txt
```

### 2. 사용법

#### ① 원본 양식 구조 분석
```bash
python inject.py --analyze templates/양식.docx
```

#### ② content.json 스켈레톤 자동 생성
```bash
python inject.py --skeleton templates/양식.docx --output content_skeleton.json
```

#### ③ 사업계획서 자동 생성
```bash
python inject.py --template templates/양식.docx --content examples/content_marketgate.json --output output/사업계획서_완성.docx
```

#### ④ Windows에서 더블클릭 실행
```
run.bat  (윈도우)
run.sh   (맥/리눅스)
```

---

## 📁 폴더 구조

```
bizplan_injector/
├── inject.py                    # 메인 CLI
├── requirements.txt
├── run.bat                      # Windows 실행 스크립트
├── run.sh                       # Mac/Linux 실행 스크립트
├── core/
│   ├── __init__.py
│   ├── injector.py              # 핵심 주입 엔진
│   └── analyzer.py              # DOCX 구조 분석기
├── templates/
│   └── 양식.docx                 # 원본 사업계획서 양식 (여기에 넣으세요)
├── examples/
│   └── content_marketgate.json  # MarketGate 예시 content
└── output/                      # 생성된 파일 저장 위치
```

---

## 📝 content.json 구조 설명

```json
{
  "delete_tables": [0, 13],        // 삭제할 표 인덱스 (목차, 비목 참고 등)

  "table_cells": [                 // 특정 셀에 값 주입
    {
      "table": 1,                  // 표 인덱스 (0부터 시작)
      "row": 0,                    // 행 인덱스
      "cell": 1,                   // 열 인덱스
      "text": "마켓게이트",         // 주입할 텍스트
      "bold": false,               // 굵게 여부
      "size": 18,                  // 폰트 크기 (hPt 단위, 18 = 9pt)
      "align": "left"              // 정렬: left / center / right
    }
  ],

  "table_rows": [                  // 표 데이터 행 전체 교체
    {
      "table": 4,                  // 표 인덱스
      "header_rows": 1,            // 헤더 행 수 (삭제하지 않을 행)
      "size": 18,
      "rows": [
        {
          "cells": ["값1", "값2", "값3"],
          "aligns": ["center", "left", "center"]
        }
      ]
    }
  ],

  "sections": [                    // 단락 섹션 내용 주입
    {
      "keyword": "1 -1",           // 헤딩에 포함된 키워드
      "lines": [                   // 주입할 줄 목록
        "◦ 외부적 배경...",
        "- 세부 내용..."
      ],
      "size": 18
    }
  ]
}
```

---

## ✨ 주요 기능

| 기능 | 설명 |
|------|------|
| 🔵 파란 안내문구 자동 제거 | 양식의 파란색 안내 텍스트를 모두 제거 |
| 📊 표 셀 개별 주입 | 특정 행/열에 값 직접 주입 |
| 📋 표 데이터 행 전체 교체 | 사업비 표, 로드맵 표 등 데이터 행 일괄 교체 |
| 📝 단락 섹션 주입 | 헤딩 키워드로 위치 찾아 내용 삽입 |
| 🔍 양식 구조 분석 | 표 목록, 헤딩 목록 자동 출력 |
| 📄 스켈레톤 생성 | content.json 초안 자동 생성 |

---

## 🔧 Python API로 사용하기

```python
from core import BizPlanInjector

inj = BizPlanInjector("templates/양식.docx")
inj.load_content("examples/content_marketgate.json")
stats = inj.run()
inj.save("output/사업계획서_완성.docx")

print(f"파란 안내문구 제거: {stats['blue_removed']}개")
```

---

## 📌 참고사항

- **양식이 달라지면** `python inject.py --skeleton 새양식.docx` 로 새 스켈레톤 생성 후 내용만 채우세요
- **표 인덱스**는 `--analyze` 명령으로 확인하세요
- **폰트 크기**: Word의 pt 단위 × 2 = size 값 (예: 9pt → size=18)

---

## 📦 의존성

```
lxml>=4.9.0
python-docx>=0.8.11
```

---

## 📜 License

MIT License
