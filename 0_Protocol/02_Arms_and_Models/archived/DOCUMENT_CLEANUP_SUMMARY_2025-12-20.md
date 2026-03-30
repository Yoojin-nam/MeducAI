# Arms and Models 문서 정리 요약 (2025-12-20)

**정리 일자:** 2025-12-20  
**목적:** 최근 변경 사항 반영, 문서 구조 개선, 상태 명확화

---

## 1. 문서 구조 및 상태

### 1.1 Canonical Documents (최신 상태)

**메인 정책 문서:**
- ✅ **ARM_CONFIGS_Provider_Model_Resolution.md** - Canonical (Frozen for Step01)
  - Provider/Model resolution protocol
  - ARM_CONFIGS 정의 (A-F)
  - Gemini 3 모델 사용 (`thinking_level`)
  - RAG/Thinking acceptance gate
  - Last Updated: 2025-12-19

### 1.2 Reference Documents

**Code Review:**
- ✅ **GEMINI_3_CODE_REVIEW.md** - Reference (Code Review)
  - Gemini 3 가이드라인 준수 여부 검토
  - 코드 구현 검토 결과
  - 주요 완료 사항 및 남은 검토 사항 정리

**MI-CLEAR-LLM Report:**
- ✅ **appendum/MI_CLEAR_LLM_Run_Report_2025-12-13.json** - Reference
  - MI-CLEAR-LLM 실행 보고서

### 1.3 Historical Reference (Superseded)

**Superseded Documents:**
- ⚠️ **appendum/protocol_addendum_s_0_rag_thinking_option_b.md** - SUPERSEDED
  - Superseded by: `ARM_CONFIGS_Provider_Model_Resolution.md`
  - Historical: Implementation & verification details
  - Status: **SUPERSEDED** (Historical Reference)

- ⚠️ **appendum/S0 Thinking Policy — Gemini 2.5 Flash.md** - SUPERSEDED
  - Superseded by: `ARM_CONFIGS_Provider_Model_Resolution.md`
  - Historical: Gemini 2.5 Flash-specific thinking control
  - Status: **SUPERSEDED** (Historical Reference)
  - Note: Current implementation uses Gemini 3 with `thinking_level`, not Gemini 2.5 Flash

---

## 2. 주요 정책 요약

### 2.1 ARM_CONFIGS (Current)

**Arm Definitions (Gemini 3):**
- **Arm A (Baseline)**: `gemini-3-flash-preview`, thinking=False, rag=False, `thinking_level="minimal"`
- **Arm B (RAG_Only)**: `gemini-3-flash-preview`, thinking=False, rag=True, `thinking_level="minimal"`
- **Arm C (Thinking)**: `gemini-3-flash-preview`, thinking=True, rag=False, `thinking_level="high"`
- **Arm D (Synergy)**: `gemini-3-flash-preview`, thinking=True, rag=True, `thinking_level="high"`
- **Arm E (High_End)**: `gemini-3-pro-preview`, thinking=True, rag=True, `thinking_budget=2048`
- **Arm F (Benchmark)**: `gpt-5.2-2025-12-11`, thinking=True, rag=True, `temp_stage1=0.0, temp_stage2=0.0`

**Key Changes:**
- Gemini 3 models (A-D, E): Use `thinking_level` ("minimal", "low", "medium", "high")
- Gemini 3 Pro (E): Uses `thinking_budget` (2048) for backward compatibility
- GPT-5.2 (F): Uses OpenAI Responses API with `reasoning.effort="medium"`

### 2.2 Resolution Algorithm

**Provider Resolution:**
- Source of Truth: `ARM_CONFIGS[arm].provider`
- CLI input NOT consulted
- Environment variables NOT consulted

**Model Resolution:**
1. CLI `--model` override (if provided)
2. `MODEL_CONFIG[provider].default_model`
3. Hard-coded safe fallback

### 2.3 RAG/Thinking Acceptance Gate

**Hard Rule for S0:**
- RAG and Thinking are **experimental factors**
- Must be **actually executed and measurably logged**
- Minimum Acceptance Criteria:
  - `rag_enabled`, `thinking_enabled` recorded in metadata
  - Non-null retrieval evidence when enabled (`rag_sources_count > 0`)
  - Explicit thinking control applied at API level
  - Latency and tokens recorded

---

## 3. 문서 정리 결과

### 3.1 유지된 문서

**Canonical Documents:**
- ✅ ARM_CONFIGS_Provider_Model_Resolution.md - 최신 상태 (Canonical, Frozen)

**Reference Documents:**
- ✅ GEMINI_3_CODE_REVIEW.md - 코드 검토 결과 (Reference)
- ✅ appendum/MI_CLEAR_LLM_Run_Report_2025-12-13.json - 실행 보고서 (Reference)

**Historical Reference:**
- ✅ appendum/protocol_addendum_s_0_rag_thinking_option_b.md - SUPERSEDED (Historical)
- ✅ appendum/S0 Thinking Policy — Gemini 2.5 Flash.md - SUPERSEDED (Historical)

### 3.2 업데이트 사항

**Superseded 문서 명확화:**
- `protocol_addendum_s_0_rag_thinking_option_b.md`에 **SUPERSEDED** 상태 명확히 표시
- `S0 Thinking Policy — Gemini 2.5 Flash.md`에 **SUPERSEDED** 상태 명확히 표시
- 현재 구현이 Gemini 3를 사용한다는 점 명시

**README.md 업데이트:**
- 문서 분류 명확화 (Canonical / Reference / Historical)
- Superseded 문서 상태 명시

**GEMINI_3_CODE_REVIEW.md 업데이트:**
- Status 및 Purpose 명시

### 3.3 중복 문서 확인

**결과:**
- 중복 문서 없음
- 각 문서가 고유한 역할 수행
- 병합 불필요

---

## 4. 문서 관계도

```
ARM_CONFIGS_Provider_Model_Resolution.md (Canonical)
├── GEMINI_3_CODE_REVIEW.md (Reference: Code Review)
└── appendum/
    ├── protocol_addendum_s_0_rag_thinking_option_b.md (⚠️ SUPERSEDED: Historical)
    ├── S0 Thinking Policy — Gemini 2.5 Flash.md (⚠️ SUPERSEDED: Historical)
    └── MI_CLEAR_LLM_Run_Report_2025-12-13.json (Reference: Report)
```

---

## 5. 구현 상태 요약

### 5.1 Current Implementation

**Gemini 3 Models:**
- ✅ `thinking_level` 파라미터 사용 (A-D)
- ✅ `thinking_budget` 파라미터 사용 (E, Pro)
- ✅ RAG 지원 (B, D, E)
- ✅ max_output_tokens: 64k (가이드라인 준수)

**GPT-5.2 (Arm F):**
- ✅ OpenAI Responses API 사용
- ✅ `reasoning.effort="medium"` 적용
- ✅ Temperature: 0.0

### 5.2 Code Review Status

**완료된 개선사항:**
- ✅ max_output_tokens 제한: 가이드라인의 64k에 맞춰 조정 완료
  - Stage1: 8192
  - Stage2: 61440 (Pro/Flash 통일)

**남은 검토 사항:**
- ⚠️ temperature 기본값: 가이드라인 권장값(1.0)과 현재 코드(0.2)의 차이 검증 필요

---

## 6. Deprecated/Historical References

### 6.1 Superseded Documents

**protocol_addendum_s_0_rag_thinking_option_b.md:**
- Superseded by: `ARM_CONFIGS_Provider_Model_Resolution.md`
- Historical: Implementation & verification details
- Status: **SUPERSEDED** (Historical Reference)

**S0 Thinking Policy — Gemini 2.5 Flash.md:**
- Superseded by: `ARM_CONFIGS_Provider_Model_Resolution.md`
- Historical: Gemini 2.5 Flash-specific thinking control
- Status: **SUPERSEDED** (Historical Reference)
- Note: Current implementation uses Gemini 3 with `thinking_level`

### 6.2 Model Migration

**Gemini 2.5 → Gemini 3:**
- Old: `gemini-2.5-flash` with `thinkingBudget` (0 or -1)
- New: `gemini-3-flash-preview` with `thinking_level` ("minimal", "low", "medium", "high")
- Migration: Completed (2025-12-19)

---

## 7. 문서 정리 완료

### 7.1 정리 완료

✅ **모든 Canonical 문서 최신 상태 확인**
✅ **Superseded 문서 명확히 표시**
✅ **문서 관계 명확화**
✅ **README.md 업데이트**
✅ **중복 문서 없음 확인**

### 7.2 유지된 문서 구조

```
0_Protocol/02_Arms_and_Models/
├── ARM_CONFIGS_Provider_Model_Resolution.md (✅ Canonical, Frozen)
├── GEMINI_3_CODE_REVIEW.md (✅ Reference)
├── README.md (✅ Updated)
└── appendum/
    ├── protocol_addendum_s_0_rag_thinking_option_b.md (⚠️ SUPERSEDED)
    ├── S0 Thinking Policy — Gemini 2.5 Flash.md (⚠️ SUPERSEDED)
    └── MI_CLEAR_LLM_Run_Report_2025-12-13.json (✅ Reference)
```

---

## 8. 다음 단계

### 8.1 문서 유지

- 모든 Canonical 문서는 최신 상태 유지
- Superseded 문서는 Historical Reference로 보존
- Code Review 문서는 지속적으로 업데이트

### 8.2 향후 개선 사항

- Temperature 기본값 검증 (가이드라인 권장값 1.0 vs 현재 0.2)
- Gemini 3 Pro `thinking_budget` vs `thinking_level` 통일 검토

---

**작성일:** 2025-12-20  
**작성자:** Document Cleanup Task  
**상태:** 완료

