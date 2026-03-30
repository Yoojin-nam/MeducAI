# S5R1 변경 요구사항 정리 (from S5R0 분석/리포트, Arm G)

- **목적**: S5R0에서 빈발한 S1/S2/이미지 관련 `issue_code`와 `patch_hint`를 **S5R1 프롬프트 변경 요구사항**으로 변환해, `S1_SYSTEM / S2_SYSTEM / S4_EXAM_SYSTEM / S4_EXAM_USER` 신규 버전 작성에 바로 사용한다.
- **근거 소스**
  - `0_Protocol/05_Pipeline_and_Execution/archived/2025-12/S5R0_Phase1_Analysis__DEV_armG_mm_before_rerun_preFix.md` (rep1+rep2 합산, issue taxonomy + patch backlog 포함)
  - `2_Data/metadata/generated/DEV_armG_mm_S5R0_before_rerun_preFix_20251229_195130__rep1/reports/s5_report__armG.md` (rep1 S5 validation report)
  - `2_Data/metadata/generated/DEV_armG_mm_S5R0_before_rerun_preFix_20251229_203653__rep2/reports/s5_report__armG.md` (rep2 S5 validation report)

---

## 1) 우선순위 요약 (S5R1에서 “반드시” 줄여야 하는 것)

- **P0 — 이미지 텍스트 과다(최빈)**: `IMAGE_TEXT_*` 계열이 S2 issue_code 상위권을 지배.
  - 요구사항: **라벨 0개 우선**, 불가피할 때만 **최대 1개**, 라벨은 **3단어 이하**, 긴 문장/설명/캡션 금지.
- **P0 — View 불일치(최빈)**: `*_VIEW_MISMATCH`가 빈발.
  - 요구사항: `image_hint.view_or_sequence` ↔ `image_hint_v2.anatomy.orientation(view_plane/projection)`이 **상호일관**하도록 강제. 불일치 시 **보수적 보정 규칙**(예: view_plane 우선/혹은 view_or_sequence 우선)을 프롬프트에 명시.
- **P1 — S2 답변-질문 의도 불일치**: “진단 vs 소견/descriptor”, “vague answer”, “circular answer” 류가 반복 출현.
  - 요구사항: 질문이 **진단**을 요구하면 Answer는 **진단명(질환명)** 으로만. 질문이 소견/검사/징후면 그에 맞는 형태로만. 질문을 재진술하는 **circular answer 금지**.
- **P1 — S2 entity_type ↔ exam_focus 불일치**: `S2_EXAM_FOCUS_ENTITY_TYPE_MISMATCH`가 반복 등장.
  - 요구사항: entity_type별 `exam_focus` 허용값을 “FAIL 조건” 수준으로 강제(예: disease → diagnosis).
- **P2 — S1 용어/기준 최신성·정밀도**: `OUTDATED_*`, `TERM_PRECISION`가 반복.
  - 요구사항: 현행 표준 용어/기준을 우선하고, 숫자 cutoff는 **모호표현 금지**(반드시 명시).

---

## 2) 근거 기반 Top issue_code + patch_hint → S5R1 요구사항 매핑

### 2.1 이미지/도식(S4_EXAM_*) — Top issue_code (rep1+rep2 합산)

아래 항목들은 `S5R0_Phase1_Analysis__...md`의 **S2 top issue codes**와 **Patch backlog (S3_PROMPT/S3_IMAGE)**에서 추출했다.

#### (추가) 컬러 정책 — “흑백 강제” 대신 “제한적 컬러 허용” (S5R1 결정)

- **배경**: 현재 `S4_EXAM_*__S5R0__v8` 프롬프트는 “flat grayscale tone blocks”를 강제하고 있으나, **일러스트(도식) 형태**에서는 적당한 컬러가 가독성에 도움이 될 수 있다.
- **S5R1 변경 요구사항 (S4_EXAM_SYSTEM + S4_EXAM_USER)**  
  - **기본은 중립 톤**(그레이스케일/저채도)으로 유지하되, **필요 시 제한적 포인트 컬러를 허용**한다.
  - **허용 범위(권장)**: 최대 1–2개 accent color(예: 병변/관심구조 강조용). **고채도/무지개 팔레트/그라데이션/발광 효과 금지**.
  - **목적 제한**: 컬러는 “구조 구분/관심부 강조” 용도에 한정(장식/아트화 금지). 컬러 사용이 view/해부학 오해를 유발하면 **컬러를 쓰지 않는다**.

#### A. 이미지 텍스트/라벨 과다 (P0)

- **Top issue_code (count, rep1+rep2 합산)**  
  - `IMAGE_TEXT_EXCESSIVE` (14)  
  - `IMAGE_TEXT_COUNT_EXCEEDED` (8)  
  - `IMAGE_TEXT_BUDGET_EXCEEDED` (5)  
  - `IMAGE_TEXT_LENGTH` (2), `IMAGE_TEXT_TYPO` (2)  
  - 파생: `IMAGE_EXCESSIVE_TEXT`, `IMAGE_STYLE_EXCESSIVE_TEXT`, `PROMPT_COMPLIANCE_TEXT_BUDGET` 등
- **대표 patch_hint(요지, S3_PROMPT 타겟)**  
  - “라벨 개수 제한을 더 엄격히 강제”  
  - “text_budget을 hard constraint로 취급”  
  - “‘minimal_labels_only’ 정책을 더 강하게”
- **S5R1 변경 요구사항 (S4_EXAM_SYSTEM + S4_EXAM_USER)**  
  - **라벨 정책**: “가능하면 0개(최우선) / 불가피할 때 최대 1개”를 **절대 규칙**으로 명시.
  - **라벨 길이**: 라벨은 **3단어 이하**, 괄호/설명문/문장 금지.
  - **텍스트 금지 범주**: 제목/주석/설명/캡션/긴 화살표 텍스트/다중 라벨링 모두 금지.
  - **실패 시 처리**: 규칙 위반 시 “FAIL/재생성”을 유도하는 문구(validator 친화적).

#### B. View 불일치/단면 규칙 위반 (P0)

- **Top issue_code (count, rep1+rep2 합산)**  
  - `PROMPT_COMPLIANCE_VIEW_MISMATCH` (8)  
  - `IMAGE_VIEW_MISMATCH` (7)
- **대표 patch_hint(요지)**  
  - view_plane vs view_or_sequence 불일치 시 **둘 중 하나를 바꿔 정합**  
  - axial 요구 시 “단일 axial slice처럼” 구조를 제한(동시에 여러 레벨 구조가 보이지 않게)
  - didactic diagram이면 view_or_sequence를 “schematic / four-chamber view diagram”처럼 명시
- **S5R1 변경 요구사항 (S4_EXAM_SYSTEM + S4_EXAM_USER, 그리고 S2_SYSTEM의 상호일관 규칙 추가)**  
  - **상호일관 규칙**(필수):  
    - `image_hint.view_or_sequence`가 특정 view(예: axial/coronal/sagittal, AP/PA/lateral, four-chamber 등)를 지정하면, `image_hint_v2.anatomy.orientation`도 **동일한 의미**가 되도록 맞춘다.
    - 둘이 충돌하면 **보수적으로 수정**: (프롬프트에) “우선순위 규칙 + 수정 예시 + 금지 예시”를 포함.
  - **단면 강제**: axial/coronal/sagittal이면 **단일 단면** 느낌(멀티레벨/복수 단면/3D 혼합 금지).
  - **비정형 view**(four-chamber 등)면 해당 view의 구도 토큰을 따르도록 강제.

#### C. 콜라주/멀티패널 위반 (P0/P1)

- **관련 issue_code**: `PROMPT_COMPLIANCE_MULTI_PANEL`, `PROMPT_VIOLATION_COLLAGE` (각 2 수준으로 관찰)
- **S5R1 변경 요구사항 (S4_EXAM_SYSTEM + S4_EXAM_USER)**  
  - “단일 패널”을 절대 규칙으로 재강조(멀티패널/콜라주/분할화면/인셋 금지).
  - 위반 시 재생성 유도 문구 추가.

#### D. Laterality/해부학적 오류 (P1)

- **관찰된 issue_code 예시**: `ANATOMICAL_LATERALITY_MISMATCH`, `ANATOMY_LATERALITY_SWAP`, `ANATOMICAL_ERROR_PATHOLOGY_MISREPRESENTATION` 등(빈도는 낮지만 치명도 높음)
- **대표 patch_hint(요지)**  
  - “laterality inversion / topology constraint를 프롬프트에서 self-check로 강제”
- **S5R1 변경 요구사항 (S4_EXAM_SYSTEM)**  
  - 출력에 드러내지 않는 **내부 self-check**를 추가(좌우/상하/전후 + 주요 구조 상대 위치).
  - 라벨이 있는 경우 **라벨 위치/대상 매칭** self-check 포함.

---

### 2.2 S2_SYSTEM — Top issue_code 및 요구사항

S5R0 Phase1 분석에서는 image 계열이 압도적이지만, S5 report(rep1/rep2)에서 S2 카드 텍스트 품질 이슈가 반복적으로 관찰된다.

#### A. entity_type ↔ exam_focus 불일치 (P1)

- **issue_code**: `S2_EXAM_FOCUS_ENTITY_TYPE_MISMATCH` (Phase1 합산 기준 2; rep2에서도 1)
- **patch_hint(리포트)**: “disease entity면 exam_focus는 diagnosis”
- **S5R1 변경 요구사항 (S2_SYSTEM)**  
  - entity_type별 exam_focus 허용값을 **명시 + 위반 시 FAIL** 수준으로 재강조.
  - 애매하면 disease로 몰지 말고 entity_context로 보수적으로 확정(플랜 방향과 정합).

#### B. 진단 vs 소견/descriptor 혼동 + vague answer (P1)

- **issue_code(리포트)**: `CLARITY_DX_VS_DESCRIPTOR`, `VAGUE_ANSWER` 등
- **대표 patch_hint(리포트)**  
  - “진단을 묻는 경우 imaging descriptor가 아니라 diagnosis로 답하라”
  - “카테고리명이 아니라 구체 질환명으로 답하라”
- **S5R1 변경 요구사항 (S2_SYSTEM)**  
  - 질문 intent 분기 규칙을 더 강하게:  
    - “most likely diagnosis” → Answer는 **질환명 단일**  
    - “finding/descriptor” → Answer는 **소견/용어**  
  - Answer에 “설명/서술” 섞는 패턴을 금지(필요하면 Explanation로만).

#### C. Circular answer (P1)

- **issue_code(리포트)**: `CIRCULAR_ANSWER`
- **patch_hint(리포트)**: “‘purpose/why’를 직접 답하고 what을 반복하지 말라”
- **S5R1 변경 요구사항 (S2_SYSTEM)**  
  - “질문을 재진술하는 답”을 금지하고, 요구된 정보(why/목적/핵심 1문장)를 강제.

#### D. 한국어 용어/오타 (P1)

- **issue_code(리포트)**: `KOR_TERM_TYPO`, `TYPO_KOREAN`, `Linguistic_Error` 등
- **대표 patch_hint(리포트)**  
  - 분만/분산 같은 **유사음 오용** 방지
  - 반복 글자/오타 검수
  - 의학 접두사 번역(Chondro-/Osteo-) 엄격히 구분
- **S5R1 변경 요구사항 (S2_SYSTEM)**  
  - 제출 전 내부 체크리스트: (1) 한글 유사음 (2) 해부학 용어 철자 (3) 의학 접두사/번역 일관성.

#### E. MCQ 구조(운영 권고, P2)

- **리포트 권고**: MCQ 포맷 체크(옵션 5개, correct_index 0–4, rationale 일관성)
- **S5R1 변경 요구사항 (S2_SYSTEM)**  
  - `card_type=MCQ`인 경우 스키마 제약을 “절대 위반 금지”로 재강조(옵션/정답 인덱스/중복 금지).

---

### 2.3 S1_SYSTEM — Top issue_code 및 요구사항

Phase1 분석에서 S1은 빈도는 낮지만, **용어/기준 최신성 + 정의 정밀도**가 반복된다.

#### A. 용어/기준 최신성 (P2)

- **Top issue_code (rep1+rep2 합산)**: `OUTDATED_TERMINOLOGY`, `OUTDATED_CRITERIA`, `OUTDATED_EPONYM`, `TERMINOLOGY_DRIFT`, `TERM_MODERNIZATION` 등
- **S5R1 변경 요구사항 (S1_SYSTEM)**  
  - “현행 표준 용어 우선 + 필요 시 (formerly …)” 규칙을 시스템 프롬프트에 명시.
  - eponym/outdated term은 **현행 용어로 치환**하고 시험 회상 목적이면 괄호로만 보조.

#### B. 정의/수치 cutoff 정밀도 (P2)

- **Top issue_code**: `TERM_PRECISION` (+ `PHYSICS_TERM_PRECISION` 등)
- **대표 patch_hint(분석)**  
  - BI-RADS calcification 기원/threshold를 정확히(예: punctate <0.5mm 등)
- **S5R1 변경 요구사항 (S1_SYSTEM)**  
  - 숫자/기준이 등장하면 “대충/보통/대략” 같은 표현 금지 → **명시적 수치**로 작성.
  - 표 내부 self-check: 용어·숫자·기준이 “출처 표준”과 일치하는지 내부 검증(출력에는 노출하지 않음).

---

## 3) S5R1 구현 체크리스트 (프롬프트 작성 시 바로 사용)

- **S4_EXAM_SYSTEM / S4_EXAM_USER**
  - 라벨 0개 우선, 최대 1개
  - 라벨 3단어 이하, 캡션/설명/문장 금지
  - (S5R1) **제한적 컬러 허용**: 기본 중립 톤 + 포인트 컬러 1–2개 이내(고채도/그라데이션/발광 금지)
  - 단일 패널(콜라주/멀티패널 금지)
  - view token 강제 + view_plane/projection와의 정합 규칙 명시
  - axial/coronal/sagittal → 단일 단면처럼(멀티레벨 금지)
  - laterality/topology self-check(출력 비노출)

- **S2_SYSTEM**
  - entity_type ↔ exam_focus 허용값 강제(위반=FAIL)
  - 질문 intent별 Answer 형식 강제(진단 vs 소견/descriptor)
  - circular answer 금지(why/purpose 직접 답)
  - 한글 의학용어/오타 내부 체크리스트
  - MCQ 구조 제약(옵션 5, correct_index 0–4, 중복 금지)

- **S1_SYSTEM**
  - 현행 용어 우선 + (formerly …) 보조 규칙
  - 숫자 cutoff/정의는 반드시 명시
  - 표 작성 self-check(용어/기준/수치)


