# S1 프롬프트 수정 방향성 제안

**작성일**: 2025-12-23  
**기준**: Reviewer_02 선생님 코멘트 + 킥오프 미팅 피드백  
**목적**: S1_SYSTEM__v12.md와 S1_USER_GROUP__v11.md 수정 방향 제시

---

## 1. 핵심 피드백 요약

### 1.1 표 관련 피드백 (Reviewer_02 선생님)
- **열(column) 수가 너무 많음** → 가독성 저하
- **학습 목표 순서대로 정리되지 않음** → 무작위 나열
- **소단원과 맞지 않는 내용 포함** → 범위 초과
- **글씨가 너무 작고 내용이 많음** → 정보 과다

### 1.2 시험 경향 관련 피드백 (킥오프 미팅)
- **한국 시험 패턴과 불일치** → "미국 보드 연습문제 필" 느낌
- **기출/전평 미반영** → 시험 경향과 차이
- **1차 시험**: 치료/해결 능력 중심
- **2차 시험**: 진단 중심 (100%)
- **주관식 배제** (1차에서도 사라짐)

### 1.3 연구 목표 관련
- **목표 A**: 학습 도구 (암기 도움)
- **목표 B**: 한국 시험 적합 문제 생성
- **목표 C**: 출제 지원

---

## 2. 수정 방향성 (우선순위별)

### 2.1 [P0] 학습 목표 순서 준수 (HARD CONSTRAINT 추가)

**현재 문제:**
- 표의 Entity 순서가 학습 목표 순서와 무관하게 생성됨
- 예: 아드넥사에서 "심플 시스트 → 씨러스 시스트 → 갑자기 미쉬너스 튜머" 순서로 나열

**수정 방향:**
```
S1_SYSTEM__v12.md에 추가:

10) Learning Objective Order Compliance (HARD)
- The master table rows MUST follow the exact order of learning objectives provided in the input.
- If learning objectives are grouped by category (e.g., benign → malignant), 
  the table rows MUST reflect this logical progression.
- Do NOT rearrange entities based on alphabetical order, frequency, or other criteria.
- The first row should correspond to the first learning objective, and so on.
```

**S1_USER_GROUP__v11.md에 추가:**
```
Instructions:
...
3) Create ONE master table...
   - CRITICAL: Table rows MUST follow the exact order of learning objectives provided above.
   - If objectives are grouped (e.g., benign lesions first, then malignant), 
     maintain this logical sequence in the table.
```

---

### 2.2 [P0] 소단원 범위 준수 (HARD CONSTRAINT 추가)

**현재 문제:**
- 아드넥사 소단원에 펠비 컨저스천이 포함되는 등 범위 초과

**수정 방향:**
```
S1_SYSTEM__v12.md에 추가:

11) Subgroup Scope Compliance (HARD)
- The master table MUST contain ONLY entities that are directly relevant to 
  the provided learning objectives.
- Do NOT include entities from adjacent subgroups or parent groups.
- If an entity appears in the learning objectives, it MUST be included.
- If an entity does NOT appear in the learning objectives, it MUST NOT be included.
- When in doubt, err on the side of exclusion rather than inclusion.
```

**S1_USER_GROUP__v11.md에 추가:**
```
Input Context:
- Group Path: {group_path}
- Subgroup Scope: This group represents a specific subgroup. 
  Do NOT include entities from other subgroups or parent groups.

Learning Objectives:
{objective_bullets}
```

---

### 2.3 [P1] 열(Column) 수 감소 전략

**현재 상태:**
- 모든 visual_type_category가 7개 열 사용
- Reviewer_02 선생님: "열이 너무 많아서 보기 어려움"

**수정 방향 (옵션 A: 열 수 감소):**
```
각 visual_type_category별로 필수 열만 유지:

A) Anatomy_Map (7열 → 5열)
  | Entity name | 해부학적 구조 | 위치/경계 | 혈관/신경 관계 | 시험포인트 |
  (정상변이, 수술/접근 경로 제거 또는 통합)

B) Pathology_Pattern (7열 → 5열)
  | Entity name | 질환/개념 | 영상 소견 키워드 | 병리·기전/특징 | 시험포인트 |
  (모달리티별 핵심 소견, 감별 질환 제거 또는 통합)

C) Pattern_Collection (7열 → 5열)
  | Entity name | 패턴명 | 영상 소견 키워드 | 패턴 특징 | 시험포인트 |
  (모달리티별 핵심 소견, 유사/대조 패턴 제거 또는 통합)

D) Physiology_Process (7열 → 5열)
  | Entity name | 생리 과정/단계 | 원인/조건 | 시간축/순서 | 시험포인트 |
  (영상 표현, 대상/조건 제거 또는 통합)

E) Equipment (7열 → 5열)
  | Entity name | 장비/기기명 | 원리/기술 | 적응증/용도 | 시험포인트 |
  (세팅/파라미터, 아티팩트/제한 제거 또는 통합)

F) QC (7열 → 5열)
  | Entity name | 품질 지표 | 허용 범위/기준 | 교정 조치 | 시험포인트 |
  (측정 방법, 실패 원인 제거 또는 통합)

G) General (7열 → 5열)
  | Entity name | 핵심 개념 | 영상 소견 키워드 | 병리·기전/특징 | 시험포인트 |
  (모달리티별 핵심 소견, 감별 질환 제거 또는 통합)
```

**수정 방향 (옵션 B: 열 통합):**
```
열 수는 유지하되, 정보 밀도를 낮춤:
- 각 열의 내용을 더 간결하게 (현재 Verbosity Budget 유지)
- 불필요한 중복 정보 제거
- 핵심 정보만 포함
```

**권장안:** 옵션 A (열 수 감소)가 가독성 개선에 더 효과적

---

### 2.4 [P1] 한국 시험 패턴 반영 (SOFT CONSTRAINT 추가)

**현재 문제:**
- "미국 보드 연습문제 필" 느낌
- 한국 시험의 중요 포인트 비중/강조와 차이

**수정 방향:**
```
S1_SYSTEM__v12.md에 추가:

12) Korean Board Exam Alignment (SOFT)
- This content is designed for Korean Radiology Board Exam preparation.
- Prioritize knowledge points that are frequently tested in Korean board exams.
- Focus on diagnostic patterns and findings that align with Korean exam style.
- Avoid overly basic knowledge that is not typically tested.
- When structuring entities, consider the relative importance in Korean exam context.

Note: While we aim for alignment, perfect match with actual exam questions 
is not guaranteed due to exam autonomy and evolving patterns.
```

**S1_USER_GROUP__v11.md에 추가:**
```
Instructions:
...
1) Infer the coherent conceptual scope...
   - Prioritize knowledge points that are frequently tested in Korean board exams.
   - Avoid including overly basic knowledge that is not typically tested.
   - Consider the relative importance of each concept in Korean exam context.
```

**추가 고려사항:**
- 대한의학회 출제요강 분석 결과를 별도 문서로 작성 후 참조 지시
- R타입/K타입 패턴은 S2 단계에서 반영하는 것이 더 적절할 수 있음 (문제 생성 단계)

---

### 2.5 [P2] Verbosity Budget 강화

**현재 상태:**
- 이미 Verbosity Budget이 있으나, Reviewer_02 선생님: "글씨가 너무 작고 내용이 많음"

**수정 방향:**
```
S1_SYSTEM__v12.md 수정:

9) Verbosity Budget & Language Policy (HARD) [REVISED v11]
...
9.1) Bullet Budget Per Cell (HARD)
- For EVERY cell (including '시험포인트'): use AT MOST 1 micro-bullet (prefer 1).
  [기존: AT MOST 2 micro-bullets (prefer 1–2)]
- Each micro-bullet MUST be short:
  - Prefer ≤ 60 characters OR ≤ 8–10 space-separated tokens (whichever is easier).
  [기존: ≤ 90 characters OR ≤ 12–16 tokens]

9.2) Atomic Facts Packing Rule (HARD)
- Each micro-bullet should pack 2–3 atomic facts using ";" or "/" or ",".
  [기존: 2–4 atomic facts]
- Avoid vague prose, filler, and connectors that add length without information.

9.3) Exam Density Requirement (HARD)
- Even under the budget, maintain high-yield density:
  - Non-'시험포인트' cells: total 2–4 atomic facts per cell (prefer fewer if still specific).
  [기존: 3–6 atomic facts]
  - '시험포인트' cell: total 2–4 atomic facts per cell (prefer fewer if still specific).
  [기존: 3–6 atomic facts]
```

---

### 2.6 [P2] Anti-Redundancy 규칙 강화

**현재 상태:**
- Pathology_Pattern과 General에만 Anti-Redundancy 규칙이 있음
- 다른 카테고리에도 적용 필요할 수 있음

**수정 방향:**
```
S1_SYSTEM__v12.md 수정:

8) Anti-Redundancy Rules (HARD) [EXPANDED]
- Column 1 "Entity name" is the downstream identifier. It is the canonical entity label.
- Column 2 MUST NOT repeat or paraphrase Column 1 in ANY visual_type_category.
- For ALL categories:
  - If Entity name is a diagnosis label, Column 2 must provide subtype/spectrum/alias/definition scope.
  - If Entity name is a pattern/sign label, Column 2 should be representative diagnoses or key characteristics.
- This rule applies to ALL visual_type_categories, not just Pathology_Pattern and General.
```

---

### 2.7 [P3] 모델별 품질 관리 힌트

**현재 문제:**
- 떨어지는 모델: 학습 목표를 다 커버 못할 정도로 적게 만듦
- 비싼 모델: 학습 목표를 넘어서 더 자세하게 만듦

**수정 방향:**
```
S1_SYSTEM__v12.md에 추가:

13) Coverage Balance (SOFT)
- Ensure ALL learning objectives are represented in the master table.
- Do NOT create fewer rows than the number of distinct learning objectives.
- Do NOT create significantly more rows than necessary (prefer 8–14 rows total).
- If you have 10 learning objectives, aim for 10–12 rows (allowing for logical grouping).
- If you have 5 learning objectives, aim for 5–8 rows (allowing for sub-entities).
```

---

## 3. 수정 우선순위 요약

### 즉시 반영 (P0)
1. ✅ **학습 목표 순서 준수** (HARD CONSTRAINT)
2. ✅ **소단원 범위 준수** (HARD CONSTRAINT)

### 단기 반영 (P1)
3. ✅ **열(Column) 수 감소** (7열 → 5열)
4. ✅ **한국 시험 패턴 반영** (SOFT CONSTRAINT)

### 중기 반영 (P2)
5. ✅ **Verbosity Budget 강화** (1 micro-bullet, ≤60 chars)
6. ✅ **Anti-Redundancy 규칙 확장** (모든 카테고리)

### 장기 검토 (P3)
7. ✅ **모델별 품질 관리 힌트** (Coverage Balance)

---

## 4. 구현 전략

### 4.1 단계적 적용
1. **1단계**: P0 항목만 먼저 반영 → 테스트
2. **2단계**: P1 항목 추가 → 전문가 피드백 수집
3. **3단계**: P2 항목 추가 → 최종 검증

### 4.2 버전 관리
- 현재: `S1_SYSTEM__v12.md`, `S1_USER_GROUP__v11.md`
- 수정 후: `S1_SYSTEM__v12.md`, `S1_USER_GROUP__v11.md`
- 변경 사항: `3_Code/prompt/CHANGELOG.md`에 기록

### 4.3 테스트 계획
- 기존 생성된 표와 비교 (아드넥사 등 문제 있었던 그룹)
- 학습 목표 순서 준수 여부 검증
- 열 수 감소 후 가독성 평가
- 전문가 피드백 재수집

---

## 5. 추가 고려사항

### 5.1 연구 목표에 따른 조건부 적용
- **목표 A (학습 도구)**: 현재 방향 유지, 가독성 개선 중심
- **목표 B (한국 시험 적합)**: 한국 시험 패턴 반영 강화 필요
- **목표 C (출제 지원)**: 별도 프롬프트 버전 고려

### 5.2 S2 단계와의 연계
- 한국 시험 패턴 (R타입/K타입)은 S2 단계에서 반영하는 것이 더 적절
- S1은 구조화에 집중, S2는 문제 생성에 집중

### 5.3 이미지 관련
- Reviewer_02 선생님: "이미지 제거 권고"
- S1 프롬프트는 이미지 생성과 무관하므로 영향 없음
- S3/S4 단계에서 이미지 전략 재검토 필요

---

## 6. 다음 단계

1. **의사결정**: 열 수 감소 옵션 A vs B 선택
2. **프롬프트 수정**: P0 항목부터 단계적 적용
3. **테스트**: 수정된 프롬프트로 샘플 생성
4. **피드백 수집**: 전문가 재평가
5. **반복 개선**: 피드백 기반 추가 수정

---

**작성자**: Assistant (프롬프트 수정 방향 제안)  
**검토 필요**: 연구 목표 A/B/C 우선순위 확정 후 최종 결정

