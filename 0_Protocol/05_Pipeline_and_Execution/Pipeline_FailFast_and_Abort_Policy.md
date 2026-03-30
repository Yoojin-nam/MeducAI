# Pipeline Fail-Fast & Abort Policy

**Status:** Canonical
**Applies to:** MeducAI Pipeline (S0, S1, S2, S3, S4, FINAL)
**Purpose:** 실험 안정성, 재현성, IRB 대응을 위해 *FAIL 발생 시 중단 범위, 아티팩트 보존, QA 활용 가능성*을 단일 규칙으로 고정한다.

---

## 1. Core Principles (Non-Negotiable)

1. **Fail-Fast 우선 원칙**  
   모든 단계는 오류를 발견하는 즉시 중단해야 하며, 오류를 "우회"하거나 "보정"하여 계속 실행하는 행위는 금지된다.

2. **결정 단위 명확화**  
   FAIL의 영향 범위는 단계별로 명시된 *Abort Scope*에 의해 결정된다.

3. **Artifact 보존 원칙**  
   FAIL 이전에 생성된 산출물은 *재현성·감사 목적*으로 보존하되, 배포·분석 사용 가능 여부는 단계별로 다르게 규정한다.

4. **IRB-Safe Logging**  
   FAIL 로그와 메타데이터는 IRB 감사 및 논문 Methods에 활용 가능해야 한다.

---

## 2. Abort Scope Definitions

| Scope | 의미 |
|------|------|
| **RUN** | 전체 RUN_TAG 즉시 중단 |
| **ARM** | 특정 arm 중단, 다른 arm은 계속 |
| **GROUP** | 특정 group만 중단 |
| **SET** | S0의 group×arm 단위 중단 |

---

## 3. Stage-by-Stage Fail-Fast Rules

### 3.1 Preflight / Configuration

**Fail Conditions**
- 필수 Canonical 문서 누락
- groups.csv SSOT 위반
- ARM_CONFIGS 해석 불가

**Abort Scope:** RUN

**Artifacts**
- 생성 없음
- 로그만 기록

**QA / IRB 사용:** 가능 (실험 실패 기록)

---

### 3.2 S0 Allocation (Fixed Payload)

**Fail Conditions**
- allocation artifact schema 위반
- set_target_cards ≠ 12
- selected_entity 불일치

**Abort Scope:** SET (group×arm)

**Artifacts**
- 실패한 set의 allocation artifact 보존

**QA / IRB 사용**
- ✔ 메타데이터, 실패율 분석 가능
- ✖ 콘텐츠 품질 평가에는 사용 불가

---

### 3.3 Step01 (S1 – JSONL Generation)

**Fail Conditions**
- JSONL schema violation
- MI-CLEAR-LLM 필수 metadata 누락
- IMG_REQ 조건 위반

**Abort Scope:** ARM

**Artifacts**
- 성공한 group JSONL은 보존
- 실패 arm은 불완전 JSONL로 표시

**QA / IRB 사용**
- ✔ 구조/안전성 분석 가능
- ✖ 학습 콘텐츠 평가 불가

---

### 3.4 Step02 (S2 – Execution Engine)

**Fail Conditions**
- len(cards) ≠ cards_for_entity_exact
- forbidden field 존재

**Abort Scope:** GROUP

**Artifacts**
- 실패 entity 결과 보존

**QA / IRB 사용**
- ✔ execution 정확성 지표 가능
- ✖ 콘텐츠 품질 비교 불가

---

### 3.5 Step03 (S3 – State-only QA Gate)

**Fail Conditions**
- quota mismatch
- forbidden semantic field 존재
- schema violation

**Abort Scope:** GROUP (FINAL) / SET (S0)

**Artifacts**
- selection_trace, qa_log 보존

**QA / IRB 사용**
- ✔ PASS/FAIL 비율, rule violation 분석 가능
- ✔ arm 비교 가능 (AC 충족 시)

---

### 3.6 Step04 (S4 – Rendering)

**Fail Conditions**
- lane 혼합 (CONCEPT/EXAM)
- forbidden upstream modification

**Abort Scope:** GROUP

**Artifacts**
- 생성된 이미지 보존
- 실패 이미지는 invalid 표시

**QA / IRB 사용**
- ✔ 이미지 파이프라인 안정성 분석
- ✖ 콘텐츠 품질 평가 불가

---

### 3.7 FINAL Allocation

**Fail Conditions**
- Σ group_target_cards ≠ TOTAL_CARDS
- cap/min 규칙 위반

**Abort Scope:** RUN

**Artifacts**
- allocation 계획 파일 보존

**QA / IRB 사용**
- ✔ 커버리지·분배 분석 가능

---

## 4. Artifact Preservation Matrix

| Stage | 보존 | 배포 사용 | QA 통계 | IRB 증빙 |
|------|------|----------|---------|----------|
| Preflight | Log | ✖ | ✔ | ✔ |
| S0 Allocation | ✔ | ✖ | ✔ | ✔ |
| S1 JSONL | ✔ | ✖ | ✔ | ✔ |
| S2 Output | ✔ | ✖ | ✔ | ✔ |
| S3 Logs | ✔ | ✖ | ✔ | ✔ |
| S4 Images | ✔ | ✖ | 제한 | ✔ |
| FINAL Allocation | ✔ | ✔ | ✔ | ✔ |

---

## 5. Hard Prohibitions

- FAIL 이후 자동 재시도
- 부분 성공 결과를 "정상"으로 취급
- FAIL run 결과를 FINAL 배포에 사용
- FAIL 원인 미기록 상태로 다음 단계 진행

---

## 6. Canonical Summary (One-Line)

> **Any FAIL stops execution at the defined scope immediately; artifacts are preserved for audit, but only fully PASSed pipelines may be used for deployment or learner-facing evaluation.**

---

**This document is Canonical and Frozen.**