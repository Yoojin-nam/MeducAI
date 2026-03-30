# PR Implementation Checklist (v1.2)

**Applies to:** v1.2 (Step02 minimal runner + runtime_manifest)
**Purpose:** Canonical 계약 위반을 PR 단계에서 차단 (Fail Fast)

---

## 0. PR Meta

* **PR Title:**
* **PR Type:** ☐ Feature ☐ Refactor ☐ Bugfix ☐ Docs ☐ Infra
* **Target Version:** v1.2
* **Related Canonical Docs:**

  * `Code_to_Protocol_Traceability.md (v1.2)`
  * `Step02_S2_Execution_Contract_Canonical.md` *(if Step02)*
  * `Runtime_Artifact_Manifest_Spec.md` *(if manifest)*

---

## 1. Scope Declaration (필수)

> **이 PR에서 구현/변경하는 Step을 명시**

* ☐ Step01 (S1)
* ☐ Allocation (S0)
* ☑ Step02 (S2)
* ☑ Runtime Manifest
* ☐ Step03 (S3)
* ☐ Step04 (S4)

☐ 위 체크 외 Step/Policy를 **암묵적으로 변경하지 않았다**

---

## 2. Step02 — Entity Execution (필수 검사)

### 2.1 입력 계약

* ☐ Step01 output을 **read-only**로 소비한다
* ☐ Allocation artifact를 **read-only**로 소비한다
* ☐ Allocation이 정의한 `allocated_N`을 재해석/수정하지 않는다

### 2.2 핵심 불변조건 (Hard Gates)

* ☐ `len(cards_out) == allocated_N`을 **강제**한다
* ☐ 부족 시 보정·완화·fallback 없이 **FAIL**한다
* ☐ 카드 스키마 필수 필드 누락 시 **FAIL**한다

### 2.3 역할 경계

* ☐ 카드 수 결정 로직이 없다 (CP-1 안전)
* ☐ Step03/Step04 역할(선별·이미지)을 침범하지 않는다

### 2.4 산출물

* ☐ 파일 경로:
  `{RUN_TAG}/step02/cards_s2__group_{G}__arm_{A}.jsonl`
* ☐ JSONL 1-record-per-line 유지
* ☐ 경로 생성은 `generated_paths.py`만 사용

---

## 3. Runtime Manifest (필수 검사)

### 3.1 생성 시점

* ☐ Step02 완료 후 1회 생성
* ☐ Fail-Fast 발생 시에도 **부분 정보 포함하여 생성** *(가능한 경우)*

### 3.2 최소 스키마 준수

* ☐ `run_tag`
* ☐ `created_at`
* ☐ `required`

  * ☐ `step01_outputs`
  * ☐ `allocation_outputs`
  * ☐ `step02_outputs`
* ☐ `status: PASS | FAIL | WARN`
* ☐ `fail_reasons` (빈 리스트 허용)

### 3.3 Hard Gate 연동

* ☐ required artifact 누락 시 정책에 따라 FAIL/WARN
* ☐ status 값이 실제 실행 결과와 불일치하지 않는다

### 3.4 산출물 경로

* ☐ `{RUN_TAG}/runtime_manifest.json`
* ☐ 경로 생성은 `generated_paths.py`만 사용

---

## 4. Runtime Path & Safety

* ☐ RUN_TAG 미정의 시 즉시 FAIL
* ☐ provider/arm 기반 폴더 분기 없음
* ☐ 상대경로 하드코딩 없음

---

## 5. Fail-Fast & Abort Policy 정합성

* ☐ FAIL은 **조용히 넘어가지 않는다**
* ☐ FAIL 시 이후 Step을 실행하지 않는다
* ☐ 로그에 FAIL 사유가 남는다

---

## 6. Traceability Update (필수)

* ☐ `Code_to_Protocol_Traceability.md` v1.2에 **본 PR 변경 사항 반영**
* ☐ Step02 / Manifest Status가 `Implement-Ready → Implemented`로 업데이트됨

---

## 7. Reviewer Quick Verdict

> 리뷰어는 아래 3가지만 보고도 merge 여부 판단 가능해야 한다.

* ☐ CP-1 위반 없음 (카드 수 결정권 침범 없음)
* ☐ CP-2/3 위반 없음 (스키마·역할 경계)
* ☐ runtime_manifest로 결과 추적 가능

☐ **PASS → Merge 가능**
☐ **FAIL → 수정 후 재요청**

---

## 8. (선택) Reviewer Notes

*
*

---

### 운영 원칙 (중요)

* 이 체크리스트는 **문서가 아니라 “게이트”**다.
* 하나라도 ☐가 남아 있으면 **merge 금지**가 원칙이다.
* “나중에 고치자”는 **Canonical 위반**으로 간주한다.