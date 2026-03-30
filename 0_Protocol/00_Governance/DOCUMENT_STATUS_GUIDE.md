# 0_Protocol 문서 참고 가이드

**목적:** 0_Protocol 디렉토리의 문서들이 현재 참고 가능한지, 어떤 우선순위로 읽어야 하는지 안내합니다.

---

## 📋 핵심 원칙

### 1. Canonical 문서 시스템
- **Canonical 문서 = 현재 유효한 최종 문서** (단 하나만 존재)
- **Archived 문서 = 과거 버전** (참고용, 현재 기준으로 사용 금지)
- **Level 3 문서 = 근거 자료** (Canonical 해석 권한 없음, 참고만 가능)

### 2. 문서 우선순위 (Level 순서)
1. **Level 0** - Pipeline 헌법 (최상위)
2. **Level 1** - 실행 규정
3. **Level 2** - Step 계약
4. **Level 3** - 안정화 로그/근거 자료

---

## ✅ 현재 참고 가능한 Canonical 문서들

### 🔴 Level 0 - Pipeline Constitution (최상위 헌법)

**위치:** `0_Protocol/05_Pipeline_and_Execution/`

| 문서 | 상태 | 용도 |
|------|------|------|
| `Pipeline_Canonical_Specification.md` | Canonical | 파이프라인 철학과 목적 |
| `Pipeline_Execution_Plan.md` | Canonical | 실행 계획 |

**참고 방법:** 모든 해석의 최종 기준

---

### 🟠 Level 1 - Execution Governance (실행 규정)

**위치:** `0_Protocol/05_Pipeline_and_Execution/`

| 문서 | 상태 | 용도 |
|------|------|------|
| `Pipeline_FailFast_and_Abort_Policy.md` | Canonical | FAIL 시 중단 규칙 |
| `Runtime_Artifact_Manifest_Spec.md` | Canonical | 정상 run 정의 |

**위치:** `0_Protocol/01_Execution_Safety/`

| 문서 | 상태 | 용도 |
|------|------|------|
| `Prompt_Rendering_Safety_Rule.md` | Canonical | 프롬프트 안전 규칙 |
| `File_Replacement_Patch_Delivery_Rule.md` | Canonical | 파일 교체 패치 규칙 |

**참고 방법:** 실행 중 FAIL/WARN 판단의 최종 기준

---

### 🟡 Level 2 - Step & Allocation Contracts

#### Step 계약
**위치:** `0_Protocol/04_Step_Contracts/`

| 문서 | 상태 | 용도 |
|------|------|------|
| `S3_to_S4_Input_Contract_Canonical.md` | Canonical | S3→S4 인터페이스 (✅ 구현 완료 2025-12-20) |
| `Step01_S1/` 하위 문서 | Canonical | S1 계약 |
| `Step02_S2/` 하위 문서 | Canonical | S2 계약 (✅ 안정화 완료 2025-12-20) |
| `Step03_S3/` 하위 문서 | Canonical | S3 계약 (✅ 구현 완료 2025-12-20) |
| `Step04_S4/` 하위 문서 | Canonical | S4 계약 (✅ 구현 완료 2025-12-20) |

#### Allocation & Card Count
**위치:** `0_Protocol/03_CardCount_and_Allocation/`

| 문서 | 상태 | 용도 |
|------|------|------|
| `S0_Allocation/S0_Allocation_Artifact_Spec.md` | Canonical | S0 할당 규칙 |
| `S0_vs_FINAL_CardCount_Policy.md` | Canonical | 카드 수 정책 |
| `FINAL_Allocation/` 하위 문서 | Canonical | FINAL 할당 규칙 |

#### Arms & Models
**위치:** `0_Protocol/02_Arms_and_Models/`

| 문서 | 상태 | 용도 |
|------|------|------|
| `ARM_CONFIGS_Provider_Model_Resolution.md` | Canonical | Arm/Provider 해석 규칙 |
| `README.md` | Canonical | Arm 개요 |

---

### 🟢 Level 3 - Stabilization & Operating SSOT

#### 현재 활성화된 운영 SSOT
**위치:** `0_Protocol/01_Execution_Safety/stabilization/`

| 문서 | 상태 | 용도 |
|------|------|------|
| `Weekly_Integrated_Conclusion_Operating_SSOT.md` | **Canonical (Active)** | **현재 주 운영 결정사항** |
| `s_1_gate_checklist_canonical.md` | Canonical (Frozen) | S1 Gate 체크리스트 |
| `E2E_S0_6Arm_Runbook.md` | Canonical | S0 실행 가이드 |

**⚠️ 중요:** `Weekly_Integrated_Conclusion_Operating_SSOT.md`는 **현재 주의 운영 결정사항**을 담고 있어 가장 최신의 실무 기준입니다.

---

### 📚 Governance & Reference

**위치:** `0_Protocol/00_Governance/`

| 문서 | 상태 | 용도 |
|------|------|------|
| `meduc_ai_pipeline_canonical_governance_index.md` | **Canonical (Frozen)** | **문서 계층 구조의 최종 인덱스** |
| `Implementation_Change_Log_2025-12-20.md` | Reference | 2025-12-20 구현 변경사항 통합 로그 |
| `Canonical_Merge_Log_2025-12-17.md` | Historical Reference | Canonical 병합 기록 |
| `MeducAI_Document_Versioning_Policy.md` | Canonical | 문서 버전 관리 정책 |
| `Objective_Source_Traceability_Spec.md` | Canonical | Objective 출처 추적 |
| `Evaluation_Unit_and_Scope_Definition.md` | Canonical | 평가 단위 정의 |
| `Groups_Canonical_Freeze.md` | Canonical | Groups 고정 규칙 |
| `MeducAI_Terminology_Glossary.md` | Canonical | 용어집 |
| `MeducAI_Variable_and_Identifier_Registry.md` | Canonical (Frozen) | 변수/식별자 등록부 |

---

### 🔬 QA & Study

**위치:** `0_Protocol/06_QA_and_Study/`

| 문서 | 상태 | 용도 |
|------|------|------|
| `QA_Framework.md` | Canonical | QA 프레임워크 |
| `S0_S1_Configuration_Log.md` | Canonical (Frozen) | S0/S1 설정 로그 |
| `S0_S1_Completion_Checklist_and_Final_Freeze.md` | Active | 완료 체크리스트 |
| `QA_Operations/` 하위 문서 | Canonical | QA 운영 문서 |
| `Study_Design/` 하위 문서 | Canonical | 연구 설계 |

---

## ❌ 참고 주의가 필요한 문서들

### Archived 문서 (과거 버전)

**위치:** `0_Protocol/archive/`

이 디렉토리의 문서들은 **과거 버전**이므로:
- ✅ **참고용으로만** 읽을 수 있음 (과거 결정의 맥락 이해)
- ❌ **현재 기준으로 사용하면 안 됨**
- ❌ **코드나 실행에 직접 적용하면 안 됨**

**주요 Archived 문서:**
- `QA_Framework_v1.0.md` ~ `v1.8.md` → 현재는 `QA_Framework.md` 사용
- `S0_Allocation_Artifact_Spec_v1.0.md` → 현재는 `S0_Allocation/` 하위 문서 사용
- `Entity_Definition_S1_Canonical.md`, `S2_Canonical.md` → 현재는 `04_Step_Contracts/` 하위 문서 사용

### Deprecated 문서 (구버전, 대체 문서 존재)

**위치:** `0_Protocol/05_Pipeline_and_Execution/`

| 문서 | 상태 | 대체 문서 |
|------|------|----------|
| `expert_qa_accuracy_evaluation_form.md` | ⚠️ Deprecated | `06_QA_and_Study/QA_Operations/QA_Evaluation_Rubric.md` |

**주의사항:**
- Deprecated 문서는 **사용하지 마세요**
- 대체 문서를 사용하세요

---

## 📖 문서 읽기 전략

### 1. 처음 시작할 때

1. **최상위 인덱스 확인:**
   ```
   0_Protocol/00_Governance/meduc_ai_pipeline_canonical_governance_index.md
   ```
   → 전체 문서 계층 구조 파악

2. **현재 운영 상태 확인:**
   ```
   0_Protocol/01_Execution_Safety/stabilization/Weekly_Integrated_Conclusion_Operating_SSOT.md
   ```
   → 최신 실무 결정사항 확인

3. **관심 영역의 Canonical 문서 읽기:**
   - Step 계약 → `04_Step_Contracts/`
   - QA → `06_QA_and_Study/QA_Framework.md`
   - Allocation → `03_CardCount_and_Allocation/`

### 2. 특정 주제를 찾을 때

**Canonical Governance Index 참조:**
```
0_Protocol/00_Governance/meduc_ai_pipeline_canonical_governance_index.md
```

이 문서의 "IRB / QA / Methods Reference Map" 섹션에서 질문별로 참조할 Canonical을 찾을 수 있습니다.

### 3. 충돌이 발생할 때

1. **Level이 높은 문서가 우선**
2. **동일 Level 내에서는 더 최근 Canonical이 우선**
3. **Level 3 문서는 Level 0-2를 재정의할 수 없음**

---

## 🔍 문서 상태 확인 방법

### 문서 헤더 확인

모든 Canonical 문서는 상단에 상태를 명시합니다:

```markdown
**Status:** Canonical
**Version:** 2.0
**Frozen:** Yes (as of 2025-12-17)
**Supersedes:** v1.0
```

### Archived 문서 헤더

```markdown
**Status:** Archived
**Version:** 1.0
**Superseded by:** <Canonical file name>
**Do not use for new analyses**
```

---

## ✅ 빠른 체크리스트

코드 수정이나 실행 전에 확인:

- [ ] 관련 Canonical 문서 확인 (`meduc_ai_pipeline_canonical_governance_index.md` 참조)
- [ ] 현재 운영 SSOT 확인 (`Weekly_Integrated_Conclusion_Operating_SSOT.md`)
- [ ] Archived 문서가 아닌지 확인 (파일 경로에 `archive/` 포함 여부)
- [ ] 문서 헤더의 Status가 "Canonical"인지 확인

---

## 📝 요약

| 문서 유형 | 참고 가능? | 사용 가능? | 우선순위 |
|----------|----------|----------|---------|
| **Canonical (Level 0-2)** | ✅ | ✅ **권장** | 최우선 |
| **Canonical (Level 3)** | ✅ | ⚠️ **근거 자료로만** | 참고용 |
| **Operating SSOT** | ✅ | ✅ **현재 기준** | 실무 최우선 |
| **Archived** | ✅ | ❌ **금지** | 과거 맥락만 |

---

**최종 권장사항:**

> **항상 `meduc_ai_pipeline_canonical_governance_index.md`를 먼저 읽고,  
> 해당 주제의 Canonical 문서를 찾아서 참조하세요.  
> Archived 문서는 과거 맥락 이해용으로만 사용하고,  
> 현재 기준으로는 사용하지 마세요.**

---

## 📝 최근 업데이트 (2025-12-20)

### 문서 정리 완료
- ✅ 모든 하위 폴더 문서 정리 완료
- ✅ 충돌 문서 해결 완료
- ✅ Superseded 문서 명확히 표시
- ✅ 파일명 정리 완료

### 주요 변경사항
- `0_Protocol_Prompt_Rendering_Safety_Rule_UPDATED_v1.1.md` → `Prompt_Rendering_Safety_Rule.md`
- 충돌 분석 문서들은 Historical Reference로 표시
- Implementation Change Log는 Reference로 분류

**최신 정리 요약:**
- `00_Governance/DOCUMENT_CLEANUP_SUMMARY_2025-12-20.md`
- `01_Execution_Safety/DOCUMENT_CLEANUP_SUMMARY_2025-12-20.md`
- `02_Arms_and_Models/DOCUMENT_CLEANUP_SUMMARY_2025-12-20.md`
- `03_CardCount_and_Allocation/DOCUMENT_CLEANUP_SUMMARY_2025-12-20.md`
- `04_Step_Contracts/DOCUMENT_CLEANUP_SUMMARY_2025-12-20.md`
- `05_Pipeline_and_Execution/DOCUMENT_CLEANUP_SUMMARY_2025-12-20.md`
- `06_QA_and_Study/DOCUMENT_UPDATE_SUMMARY_2025-12-20.md`

