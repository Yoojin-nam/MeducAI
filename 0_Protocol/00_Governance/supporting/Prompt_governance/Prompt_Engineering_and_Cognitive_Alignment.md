# Prompt Engineering & Cognitive Alignment (Prompt Governance SSOT)

**Status:** Canonical (Prompt Governance SSOT)  
**Applies to:** `3_Code/prompt/` prompt bundle + Paper Methods (prompt engineering) + S2 prompt change control  
**Last Updated:** 2025-12-26  
**Core principle:** “프롬프트 개선”은 허용되지만, **스키마/계약 변경**과 혼동하지 않는다. (스키마 변경은 별도 Canonical 계약 문서에서만)

---

## 0. Why this document exists (SSOT)

이 문서는 다음을 한 곳에서 고정한다:
- **현재 실행에 실제로 사용되는 프롬프트 버전(코드 기준)**은 무엇인가
- **인지적 정렬(Cognitive alignment)**을 위해 프롬프트가 어떤 제약을 갖는가
- **S2 2-card policy(v8) 전환**은 무엇이며, 어디까지가 “계획(미실행)”인가
- 논문/IRB/리뷰 대응에서 “프롬프트 엔지니어링”을 **한 문단으로 설명**할 수 있는 Methods-ready 텍스트

---

## 1. Current implementation truth (Code-aligned; binding for “what is actually used”)

### 1.1 Prompt bundle selection is registry-driven

**Single Source of Truth (code):** `3_Code/prompt/_registry.json`

- Step 실행 시 프롬프트는 **registry가 가리키는 파일**로 고정된다.
- `3_Code/src/tools/prompt_bundle.py`의 `load_prompt_bundle()`가 registry를 읽고, 번들 해시(`prompt_bundle_hash`)를 계산해 실행 산출물에 기록한다.

### 1.2 Current active prompt versions (as of 2025-12-26)

현재 registry는 아래를 가리킨다:
- `S1_SYSTEM` → `S1_SYSTEM__v12.md`
- `S1_USER_GROUP` → `S1_USER_GROUP__v11.md`
- `S2_SYSTEM` → `S2_SYSTEM__v7.md`
- `S2_USER_ENTITY` → `S2_USER_ENTITY__v7.md`

> 즉, **S2 v8 2-card policy 문서(아래 3장)는 ‘계획’이며 아직 실행 번들로 활성화되지 않았다.**

### 1.3 Prompt rendering safety (fail-fast rule)

Step01 프롬프트 렌더링은 `str.format()` 직접 호출을 금지한다.  
모든 렌더링은 안전 렌더러를 통해 수행해야 한다.

- Canonical: `0_Protocol/01_Execution_Safety/Prompt_Rendering_Safety_Rule.md`

---

## 2. Cognitive alignment rationale (Yaacoub 2025; reference-backed)

### 2.1 핵심 교훈(요약)
- “명시적이고 상세한 프롬프트”는 교육용 AI 생성 질문의 **목표 인지 수준(Bloom’s taxonomy) 정렬**을 개선한다.
- 간소화/페르소나 기반 프롬프트는 질문 품질이 나쁘지 않더라도 **목표 인지 수준에서 이탈**하기 쉽다.

### 2.2 Reference (keep)
- Reference 요약 문서: `0_Protocol/00_Governance/supporting/Prompt_governance/Yaacoub_2025_Lightweight_Prompt_Engineering_Review.md`

---

## 3. Planned change: S2 v8 “2-card policy + cognitive alignment” (Not Yet Executed)

**Status:** 계획(Implementation-Ready) / 아직 registry에 반영되지 않음

### 3.1 What changes (high level)
- 3-card(Q1/Q2/Q3) → **2-card(Q1/Q2)** 전환
- Front 이미지 의존 제거(특히 Q1): **“영상 요약” 텍스트로 대체**
- Q1/Q2 모두 **BACK-only infographics** (각 카드별 독립 image_hint)
- “인지 수준”을 프롬프트에 명시:
  - Q1: APPLICATION(진단 적용)
  - Q2: APPLICATION 또는 KNOWLEDGE(개념/원리/치료/함정/물리)
- **Forbidden operations** 및 **self-verification**을 프롬프트에 포함

### 3.2 Why this is safe under governance
- **스키마/계약은 그대로**(prompt text만 개선) → 실행 계약 변경이 아님
- 단, 실제 실행에 반영하려면 registry 변경 및 관련 게이트/정책 정합성 점검이 필요(아래 4장)

---

## 4. Implementation checklist (when you actually switch to v8)

### 4.1 Minimal mechanical steps (required)
- `3_Code/prompt/`에 v8 프롬프트 파일을 추가(또는 기존 파일 교체)
- `3_Code/prompt/_registry.json`에서
  - `S2_SYSTEM`
  - `S2_USER_ENTITY`
  를 v8 파일로 변경
- 변경 후 **prompt_bundle_hash**가 바뀌므로, 실행 로그/메타데이터에 자동 반영되는지 확인

### 4.2 Required compatibility checks (must not regress)
- S2 출력 스키마 변경 금지(필드 추가/삭제 금지) — output contract 유지
- S3/S4/S5(이미지 정책/패키징)와 “이미지 배치(Back-only)”가 충돌하지 않는지 확인
- deictic image references 금지 규칙이 실제로 gate에 의해 검출되는지 확인(가능 시)

### 4.3 Execution artifacts & traceability (must remain audit-ready)
- 프롬프트 변경은 “모델 변경”이 아니라도, 실행 산출물에
  - `prompt_file_ids`
  - `prompt_bundle_hash`
  가 남아야 한다(재현성/감사 목적)

---

## 5. Methods-ready text (Paper / IRB reuse)

본 연구에서는 교육용 AI 생성 콘텐츠의 품질과 인지적 정렬을 보장하기 위해 **명시적이고 구조화된 프롬프트 엔지니어링 전략**을 채택하였다. 각 단계별로 System Prompt와 User Prompt를 분리하여 역할과 제약을 고정하였고, 카드 타입별로 목표 인지 수준(Bloom’s taxonomy)을 명시하며 기대 행동(Expected Behavior)과 금지 사항(Forbidden Operations), 자체 검증(Self-verification) 절차를 포함하였다. 이는 최근 연구에서 상세하고 명시적인 프롬프트가 목표 인지 수준 정렬을 향상시킨다는 근거(Yaacoub et al., 2025)에 기반한다.

---

## 6. Superseded documents (archived)

아래 문서들은 본 SSOT로 내용이 흡수되었으며, 더 이상 “현재 기준”으로 읽지 않는다:
- `Prompt_Engineering_and_Cognitive_Alignment.md` → superseded
- `Prompt_Engineering_and_Cognitive_Alignment.md` → superseded
- `Prompt_Engineering_and_Cognitive_Alignment.md` → superseded


