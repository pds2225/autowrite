# Codex 시작 문서 — auto\_write 통합 고도화

> **이 파일을 Codex에 붙여넣고 시작하세요.**  
> 개발 지식 없이 단계별로 지시만 하면 됩니다.

---

## 📁 작업 위치

```
기준 코드: D:\auto_write\app\
비교 번들: D:\auto_write\compare_bundle_autowrite\

```

---

## 🔰 Codex 최초 시작 프롬프트 (딱 한 번만 붙여넣기)

```
너는 D:\auto_write\app 을 기준 코드베이스로 삼아 작업한다.
D:\auto_write\compare_bundle_autowrite 안에 Skywork(구 bizplan_datavoucher) 코드가 있다.

작업 원칙:
1. 파일 전체를 교체하지 않는다. 기능(함수/로직) 단위로만 이식한다.
2. 수정 전 반드시 해당 파일을 백업한다 (파일명_backup.py).
3. 수정 후 기존 테스트가 깨지지 않는지 확인한다.
4. 문제 생기면 백업 파일로 즉시 롤백하고 나에게 보고한다.

먼저 이 명령을 실행해서 현재 상태를 확인해줘:
  python -m unittest discover -s tests -p "test_*.py"

그리고 결과를 나에게 알려줘. 통과 몇 개, 실패 몇 개인지.

```

---

## 📋 Phase A — 안정화 기준선 (먼저 해야 함)

**완료 기준**: 테스트 전부 통과 + 브라우저에서 웹앱 열림

### A-1. 실행 환경 점검

```
D:\auto_write\app 폴더의 .env 파일을 열어서
OPENAI_API_KEY 값이 설정되어 있는지 확인해줘.
없으면 나에게 알려줘. 있으면 다음 단계 진행해.

```

### A-2. 웹앱 실행 확인

```
launch.bat 을 실행해서 브라우저에서 http://127.0.0.1:8765 이 열리는지 확인해줘.
열리면 "A-2 완료"라고 알려줘.
오류 나면 오류 메시지 그대로 복사해서 나한테 보여줘.

```

### A-3. 기본 테스트 통과 확인

```
python -m unittest discover -s tests -p "test_*.py" 실행해줘.
결과를 이렇게 정리해줘:
  - 전체 테스트: X개
  - 통과: X개
  - 실패: X개
  - 실패한 테스트 이름 목록

```

---

## 📋 Phase B — Skywork 장점 2개 흡수

**A 완료 후 진행. 순서대로 하나씩.**

---

### B-1. 이미지 중복 삽입 방지 (버그 수정)

**문제 설명 (비개발자용)**:  
지금 코드는 이미지를 표 칸에 1번, 텍스트 안내로 또 1번 — 총 2번 넣어서  
Word에서 이미지가 깨지거나 안 보이는 문제가 있습니다.

**Codex에게 줄 지시:**

```
D:\auto_write\compare_bundle_autowrite\auto_write\services\image_service.py 파일을 열어줘.
그리고 D:\auto_write\app\services\image_service.py 파일을 열어줘.

현재 app 코드에서 이미지 슬롯에 "실제 이미지"와 "텍스트 안내(placeholder)"가
동시에 삽입되는 경우가 있는지 확인해줘.

만약 있다면, 아래 규칙을 추가해줘:
  - 실제 이미지 파일이 있는 슬롯 ID 목록을 먼저 모은다 (image_slot_ids)
  - placeholder를 삽입할 때 image_slot_ids에 있는 슬롯은 건너뛴다

수정 전 image_service.py 를 image_service_backup.py 로 백업해줘.
수정 후 테스트 실행해서 결과 알려줘.

```

---

### B-2. 흰색 텍스트 색상 보존 (버그 수정)

**문제 설명 (비개발자용)**:  
Word 양식에서 어두운 배경 위에 흰 글씨(예: Ⅰ, Ⅱ, Ⅲ 목차 번호)가 있는데,  
지금 코드가 모든 글씨를 검정으로 바꿔버려서 흰 글씨가 사라지는 문제가 있습니다.

**Codex에게 줄 지시:**

```
D:\auto_write\app\services\docx_ops.py 파일을 열어줘.

색상을 "000000"(검정)으로 바꾸는 코드를 모두 찾아줘.

그 코드들에 아래 조건을 추가해줘:
  흰색 계열 색상(ffffff, fffffe, f2f2f2)은 바꾸지 않고 그대로 둔다.

구체적으로:
  - _PRESERVE_COLORS = {"ffffff", "fffffe", "f2f2f2"} 집합을 파일 상단에 추가
  - 색상을 바꾸기 전에 현재 색상이 _PRESERVE_COLORS에 있으면 건너뛴다

수정 전 docx_ops.py 를 docx_ops_backup.py 로 백업해줘.
수정 후 테스트 실행해서 결과 알려줘.

```

---

## 📋 Phase C — 범용 템플릿 엔진 강화

**B 완료 후 진행.**

---

### C-1. 동의서·행정 페이지 자동 제외

**문제 설명 (비개발자용)**:  
Word 양식 안에 "개인정보 동의서", "서약서" 같은 페이지는  
자동작성 대상이 아닌데 지금은 그 안에도 내용을 넣으려 해서 오류가 납니다.

**Codex에게 줄 지시:**

```
D:\auto_write\app\analysis\docx_template.py 파일을 열어줘.

템플릿을 분석할 때 아래 키워드가 포함된 섹션은
"자동작성 제외 대상"으로 분류하는 로직을 추가해줘:
  제외 키워드: ["동의서", "서약서", "확인서", "개인정보", "청렴", "보안", "서명란"]

제외된 섹션은 분석 결과에 is_excluded: true 로 표시하고,
자동작성 시 이 섹션은 건너뛰도록 해줘.

수정 전 docx_template.py 를 docx_template_backup.py 로 백업해줘.
수정 후 테스트 실행해서 결과 알려줘.

```

---

### C-2. 본문 자동작성 품질 강화

**문제 설명 (비개발자용)**:  
지금은 AI가 쓴 문장을 그대로 넣는데,  
정부지원사업 계획서는 "개조식"(·으로 시작하는 짧은 문장들) 형식이어야 합니다.  
구 코드(Skywork)에 이 변환 규칙이 잘 만들어져 있습니다.

**Codex에게 줄 지시:**

```
D:\auto_write\compare_bundle_autowrite\auto_write\services 폴더 안에
writer_agent 관련 파일이 있는지 확인해줘.

없다면 이 경로를 확인해줘:
  D:\auto_write\compare_bundle_autowrite\bizplan_datavoucher\agents\writer_agent.py

writer_agent.py 안의 to_bullet() 함수와 _convert_ending() 함수를
D:\auto_write\app\services\project_service.py 에 이식해줘.

이식 방법:
  - project_service.py 상단에 두 함수를 그대로 복사해서 추가
  - AI가 생성한 텍스트를 저장하기 직전에 to_bullet()을 적용
  - 단, 표 안의 숫자 데이터(사업비, 일정 등)에는 적용하지 않음

수정 전 project_service.py 를 project_service_backup.py 로 백업해줘.
수정 후 테스트 실행해서 결과 알려줘.

```

---

## 📋 Phase D — 운영 고도화

**C 완료 후 진행.**

---

### D-1. QA 메시지 사람 말로 바꾸기

**Codex에게 줄 지시:**

```
D:\auto_write\app\services\qa_service.py 파일을 열어줘.

현재 오류/경고 메시지가 영어 코드나 기술 용어로 되어 있다면
아래 형식으로 바꿔줘:

  기존: "E01: missing field"
  변경: "❌ '사업명' 항목이 비어있습니다. project_input.json의 meta.project_title을 채워주세요."

  기존: "W05: image count exceeded"
  변경: "⚠️ 이미지가 4장 입력되었습니다. 데이터바우처 규정상 1장만 삽입됩니다."

추가로, ○○○ 텍스트가 완성된 DOCX 안에 남아있으면
  "⚠️ X번째 페이지에 빈 칸(○○○)이 남아있습니다. 실제 값으로 교체해주세요."
라는 경고를 추가해줘.

수정 전 qa_service.py 를 qa_service_backup.py 로 백업해줘.

```

---

### D-2. 5분 복구 체크리스트 문서 만들기

**Codex에게 줄 지시:**

```
D:\auto_write\app\ 폴더에 RECOVERY.md 파일을 새로 만들어줘.

내용:
  # 문제 발생 시 5분 복구 방법

  ## 1. 웹앱이 안 열릴 때
    1) launch.bat 닫기
    2) launch.bat 다시 실행
    3) 그래도 안 되면: .env 파일에 OPENAI_API_KEY 있는지 확인

  ## 2. DOCX 생성이 안 될 때
    1) output 폴더 안의 최근 에러 로그 확인
    2) project_input.json에 ○○○ 공란이 있는지 확인
    3) templates 폴더에 .docx 파일이 있는지 확인

  ## 3. 수정한 코드가 문제를 일으킬 때 (롤백)
    1) 문제 파일 이름 확인 (예: docx_ops.py)
    2) 같은 폴더에 _backup.py 파일이 있으면:
       docx_ops.py 삭제 → docx_ops_backup.py 를 docx_ops.py 로 이름 변경
    3) launch.bat 재시작

  ## 4. 테스트 실행 방법
    터미널에서: python -m unittest discover -s tests -p "test_*.py"

```

---

## ✅ 각 Phase 완료 확인 방법

| Phase | 완료 확인 방법 |
| --- | --- |
| A | 테스트 전부 통과 + 브라우저에서 웹앱 열림 |
| B-1 | 생성된 DOCX에서 이미지 중복 없음 |
| B-2 | 생성된 DOCX에서 목차 로마숫자(Ⅰ~Ⅴ) 흰색으로 표시 |
| C-1 | 동의서 페이지에 자동작성 내용 안 들어감 |
| C-2 | 생성된 텍스트가 · 로 시작하는 짧은 문장 형태 |
| D-1 | QA 경고 메시지가 한국어로 표시됨 |
| D-2 | RECOVERY.md 파일 생성됨 |

---

## ⚠️ 문제 생겼을 때

**Codex에게 이렇게 말하세요:**

```
[오류 메시지 붙여넣기]

이 오류가 나서 멈췄어. 원인이 뭔지 설명해줘 (개발 용어 쓰지 말고).
그리고 _backup.py 파일로 롤백해줘.

```

---

## 📌 지금 당장 시작하는 방법

1.  Codex를 열고
2.  `D:\auto_write\app` 폴더를 작업 공간으로 지정
3.  **"🔰 Codex 최초 시작 프롬프트"** 섹션의 내용을 복사해서 Codex에 붙여넣기
4.  테스트 결과 확인 후 Phase A-1부터 순서대로 진행
