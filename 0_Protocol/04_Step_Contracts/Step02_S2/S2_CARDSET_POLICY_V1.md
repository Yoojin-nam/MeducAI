# S2 카드 생성 규격 삽입 블록 (Copy/Paste)

**Status:** Reference (Prompt Template Block)  
**Purpose:** S2 프롬프트에 삽입할 정책 규격 블록  
**Usage:** `S2_SYSTEM` 또는 `S2_USER_ENTITY` 프롬프트에 삽입  
**Last Updated:** 2025-12-20

**Note:** This document contains a **copy-paste block** for S2 prompts. The canonical policy document is `S2_Cardset_Image_Placement_Policy_Canonical.md` (v1.3).

---

### BEGIN: S2_CARDSET_POLICY_V1

#### 목적

* 각 **Entity마다 정확히 3문항**을 생성한다.
* 3문항은 역할이 고정이며, **이미지 배치(Front/Back/None)에 따라 출제 방식이 달라진다.**
* **CLOZE는 생성하지 않는다.** (시험 정합성 우선)

---

### 전역 하드룰 (HARD)

1. **카드 수 고정**

* **FINAL 모드**: 각 Entity당 **정확히 2개 카드**만 생성: `Q1`, `Q2`
* **S0 모드 (QA 실험)**: 각 Entity당 **정확히 3개 카드**만 생성: `Q1`, `Q2`, `Q3`
* 누락/추가 생성 금지.
* **예외 (S0 모드, 드문 케이스):** 
  * S0 모드에서 E < 4인 경우, allocation artifact에 명시된 `cards_for_entity_exact` 값을 따른다.
  * 이는 set-level payload 12장을 보장하기 위한 균등 분배 결과이며, QA 설계상 드문 케이스이다.

2. **유형/이미지 배치 고정**

* Q1: `BASIC` + `IMAGE_ON_BACK` (FINAL 모드)
* Q2: `MCQ` + `IMAGE_ON_BACK` (FINAL 모드)
* Q3: `MCQ` + `NO_IMAGE` (S0 모드에서만 사용, FINAL 모드에서는 생성되지 않음)

3. **이미지 의존성 규칙**

* Q1(legacy: IMAGE_ON_FRONT): **deprecated** — current policy uses IMAGE_ON_BACK (2-card policy)
* Q2(IMAGE_ON_BACK): **이미지 없이도 질문이 성립하고 풀 수 있어야 함** (이미지는 해설 강화용)
* Q3(NO_IMAGE): **이미지 언급/의존 금지**

4. **언급 금지**

* Q2/Q3의 질문(front)에서 “이 영상에서”, “위 CT에서”, “그림에서 보이는” 등 **이미지 참조 문구 금지**.
* Q1의 질문(front)에서 환자 나이/성별/임상/검사수치 등 **텍스트 힌트 과다 제공 금지**(이미지 스템 유지).

5. **난이도/시험 정합성**

* 전문의 시험에 가까운 “단일 최선답(one best answer)” 중심.
* 지엽적 연구/희귀 디테일 지양.

---

### 출력 텍스트 포맷 규칙 (HARD, 안정성)

#### BASIC 포맷(Q1)

* Front는 **한 줄 질문**으로만 구성(짧게).
* Back은 아래 구조를 엄수:

  * `Answer:` 한 줄 (정답은 **단일 용어/진단명/징후명**)
  * `Why:` 2–3개 핵심 근거 (최대 3줄, 각 줄은 짧게)
  * `Pitfall:` 흔한 함정 1줄 (선택)

권장 길이:

* Q1 Front: 4–12 단어(또는 1문장)
* Q1 Back: 6–12줄 이내

#### MCQ 포맷(Q2/Q3)

* Front는 아래 구조를 엄수:

  * `Question:` 1–3문장 스템
  * `Options:` 정확히 5개 보기 (A–E)

    * 표기 형식 고정:
      `A) ...`
      `B) ...`
      `C) ...`
      `D) ...`
      `E) ...`
* Back은 아래 구조를 엄수:

  * `Correct:` 정답 보기 문자 1개(예: `Correct: C`)
  * `Rationale:` 2–4줄(왜 정답인지)
  * `Why others:` 가장 그럴듯한 오답 1개만 1줄로 반박
  * `Takeaway:` 시험용 핵심 1–2줄

---

## 카드별 상세 규칙

### Q1 — (Deprecated) BASIC + IMAGE_ON_FRONT

**의도:** 이미지를 보고 즉시 떠올리는 “핵심 진단/징후/패턴”을 회상.

* Front 템플릿(택1, 하나만 사용)

  * “Most likely diagnosis?”
  * “Name the key imaging sign.”
  * “What pattern is demonstrated?”
* 금지

  * 진단을 강하게 암시하는 텍스트 단서 과다 제공
  * “~가 의심된다” 수준의 장문 임상 정보
* Back(Why) 근거는 **이미지에서 관찰 가능한 특징** 위주로 작성

**자기 점검(HARD):**
“이 Q1이 이미지 없이도 답이 나오나?” → Yes면 실패. 문구/근거를 줄이고 이미지-의존적으로 재작성.

---

### Q2 — MCQ + IMAGE_ON_BACK (텍스트 기반 시험형 + 이미지로 해설 강화)

**의도:** 질문은 텍스트만으로도 풀리되, 이미지가 해설에서 “전형 소견 확인/기억 강화” 역할.

* Question(스템) 구성 원칙

  * 짧은 임상 맥락 + 핵심 영상 소견을 “텍스트로 요약” (이미지 참조 금지)
  * 질문 유형(택1)

    * 가장 가능성 높은 진단
    * 가장 특정적인 영상 소견/징후
    * 감별을 가르는 핵심 포인트
* Options(보기) 구성 원칙

  * 5지선다, 서로 **그럴듯한 감별군**으로 구성
  * “정답 1개 + 엉뚱한 4개” 금지
* Back에서 이미지(ON_BACK)는 다음을 수행한다고 가정하고 서술

  * “전형 소견을 다시 확인하는 시각적 근거”
  * 단, Back 텍스트는 이미지가 없어도 이해 가능하도록 작성(이미지 의존 설명 과다 금지)

**자기 점검(HARD):**
Q2 Front가 이미지 없이도 완전한 시험 문제인가? → No면 실패. “영상에서 보이는” 문구 제거 및 텍스트 소견으로 재구성.

---

### Q3 — MCQ + NO_IMAGE (함정/감별/관리 포인트)

**의도:** 실제 시험에서 자주 묻는 “함정/감별/다음 스텝”을 이미지 없이 회상.

* Question 유형(우선순위)

  1. Next best step / 추가 검사 / 추적 전략
  2. 흔한 함정(benign vs malignant 기준, 과잉진단/과소진단 포인트)
  3. 감별 진단에서 결정적 구분점
* 금지

  * 이미지/모달리티/특정 컷을 전제로 하는 문구
  * “이 영상에서”류 표현
* Options는 임상적으로 타당한 선택지로 구성

**자기 점검(HARD):**
이미지 없이도 질문-보기-정답이 완결되는가? → No면 실패. 이미지 의존 요소 제거.

---

## 최종 검증 체크리스트 (출력 직전)

* [ ] 각 Entity당 카드가 정확히 3개(Q1/Q2/Q3)인가?
* [ ] Q1은 BASIC이며 이미지-의존적인가?
* [ ] Q2는 MCQ이며 Front에 이미지 참조가 없고 텍스트만으로도 풀리는가?
* [ ] Q3는 MCQ이며 이미지 참조가 전혀 없는가?
* [ ] Q2/Q3 보기 5개(A–E) 형식이 정확한가?
* [ ] 정답은 하나이며, 오답이 그럴듯한 감별군인가?
* [ ] CLOZE가 생성되지 않았는가?

### END: S2_CARDSET_POLICY_V1

---

## 적용 팁(바로 붙이는 위치)

* 이 블록은 **S2_SYSTEM**에 넣어도 되고, 더 강하게 하려면 **S2_USER_ENTITY**(엔티티 입력 바로 아래)에도 중복 삽입해도 됩니다.
* 만약 현재 S2 JSON 스키마가 “front/back 텍스트만” 허용한다면, 위 포맷은 그대로 **front/back 문자열에 인라인**으로 들어가도 안정적으로 동작합니다(특히 `Question/Options`와 `Correct/Rationale` 라벨이 파싱/QA에 유리).

원하시면 다음 단계로, **(1) 지금 쓰는 S2 출력 스키마(키 이름들)**에 맞춰 위 규격을 “정확히 어떤 필드에 무엇을 넣는지”로 매핑한 버전(예: `card_type`, `question`, `choices`, `answer`, `explanation` 등)과, **(2) validator에서 잡을 수 있는 정규식 기반 체크(예: Options A–E 누락, 이미지 참조 문구 탐지)**까지 같이 만들어 드리겠습니다.
