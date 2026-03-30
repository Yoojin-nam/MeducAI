# MeducAI 문서 · README · 버전 관리 정책 (Canonical)

**Status:** Canonical  
**Applies to:** MeducAI 전체 문서 (Protocol / QA / README)  
**Effective date:** 2025-12-15

---

## 1. 목적

본 문서는 MeducAI 프로젝트에서 발생하는 **문서 버전 누적 문제**를 체계적으로 관리하기 위한
**단일·고정된 버전 관리 원칙**을 정의한다.

목표는 다음과 같다.

- 항상 **현재 유효한 문서(Canonical)** 가 무엇인지 명확히 한다.
- 과거 버전을 삭제하지 않으면서도 혼동을 방지한다.
- 논문, IRB, 감사, 협업 환경에서 **재현성과 신뢰성**을 유지한다.

---

## 2. 핵심 원칙 (Non-negotiable Rules)

### Rule 1. Canonical 문서는 항상 1개만 존재한다

- 각 주제(Framework, Plan, Rationale 등)마다 **Canonical 문서는 단 하나**만 허용된다.
- 협업·인용·논의 시 **항상 Canonical만 참조**한다.

---

### Rule 2. Canonical 파일명에는 버전 번호를 붙이지 않는다

**금지 예시**
```
Model_Selection_Rationale.md
```

**권장 예시**
```
Model_Selection_Rationale.md   ← 항상 최신
```

- 버전 정보는 **파일명이 아니라 문서 헤더**에서 관리한다.

---

### Rule 3. 모든 문서는 상단에 상태(Header)를 명시한다

#### Canonical 문서 헤더 템플릿

```markdown
Status: Canonical
Version: 2.0
Applies to: QA Framework v2.0
Supersedes: v1.1
Frozen: Yes (as of YYYY-MM-DD)
```

#### Archived 문서 헤더 템플릿

```markdown
Status: Archived
Version: 1.0
Superseded by: <Canonical file name>
Do not use for new analyses
```

---

## 3. Archived 문서 처리 규칙

- Canonical에서 내려간 문서는 **삭제하지 않는다**.
- 즉시 `archived/` 폴더로 이동한다.

### 권장 구조

```
05_Model_Selection/
├─ Model_Selection_Rationale.md        ← Canonical
└─ archived/
   ├─ Model_Selection_Rationale_v1.0.md
   └─ Model_Selection_Rationale_v1.1.md
```

---

## 4. 버전 업데이트 기준

### 4.1 Minor Update (v2.0 → v2.1)

다음에 해당하면 **같은 파일 유지**:

- 문장 정리, 가독성 개선
- 설명 보강
- Reviewer 대응 문구 추가
- 오탈자 수정

조치:
- `Version` 필드만 증가
- archived 이동 ❌

---

### 4.2 Major Update (v2.x → v3.0)

다음에 해당하면 **새 Canonical 생성**:

- 연구 설계 변경
- QA 구조 변경
- Arm 구성 변경
- 연구 질문 변경

조치:
- 기존 Canonical → `archived/` 이동
- 새로운 Canonical 파일 생성

---

## 5. README에 대한 특별 규칙

### README의 역할

- README는 **문서를 설명하는 안내판**이다.
- README 자체가 설계 문서가 되어서는 안 된다.

### README 금지 사항

- 버전 히스토리 나열 ❌
- v1.0 / v2.0 문서 목록 ❌
- 과거 설계 서술 ❌

### README 권장 내용

```markdown
Canonical documents:
- QA_Framework.md
- Model_Selection_Rationale.md
```

---

## 6. 실무 판단 기준 (Quick Decision Table)

| 상황 | 조치 |
|----|----|
| 최신 문서인가? | 파일명에 v 없음 + Status=Canonical |
| 더 이상 쓰지 않는가? | archived/ 이동 |
| 설계가 바뀌었는가? | Major update |
| 설명만 보강했는가? | Minor update |

---

## 7. 핵심 문장 (운영 원칙)

> **버전은 쌓인다. 그러나 살아있는 문서는 하나다.**

> **파일명은 단순하게, 상태는 명확하게.**

---

## 8. 적용 범위 선언

본 정책은 다음에 동일하게 적용된다.

- QA Framework
- Model Selection Plan / Rationale
- Protocol 문서
- README (Root / Folder level)

---

**End of Document**