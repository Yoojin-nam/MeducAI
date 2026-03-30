# 문서 간 충돌 지점 분석 (전체)

**생성일:** 2025-12-19  
**수정 완료일:** 2025-12-19  
**상태:** ✅ **모든 충돌 해결 완료** (Historical Reference)  
**Last Updated:** 2025-12-20  
**목적:** Allocation 외 다른 영역의 문서 간 충돌 지점 정리 및 해결

**⚠️ IMPORTANT:** This document is a **Historical Reference**. All conflicts described in this document have been **resolved** (2025-12-19). The current canonical documents are up-to-date and consistent. This document is retained for historical context.

---

## 🔴 Critical 충돌 (즉시 수정 필요)

### 충돌 1: S1 Schema 버전 불일치

#### 📄 문서 A (S1 Schema)
```
**위치:** `0_Protocol/04_Step_Contracts/Step01_S1/S1_Stage1_Struct_JSON_Schema_Canonical.md`
**버전:** v1.3
**schema_version:** "S1_STRUCT_v1.3"
```

#### 📄 문서 B (S2 Contract)
```
**위치:** `0_Protocol/04_Step_Contracts/Step02_S2/S2_Contract_and_Schema_Canonical.md`
**버전:** 3.0
**섹션 4:** "S2 MUST consume stage1_struct.jsonl that conforms to S1_STRUCT_v1.1"
```

**충돌 상태:** ⚠️ **S2 Contract가 구버전 S1 Schema(v1.1)를 참조**

**영향:** S2가 최신 S1 스키마를 올바르게 검증하지 못할 수 있음

---

### 충돌 2: visual_type_category Enum 불일치

#### 📄 문서 (S1 Schema v1.3)
```
**위치:** `0_Protocol/04_Step_Contracts/Step01_S1/S1_Stage1_Struct_JSON_Schema_Canonical.md`
**섹션 4:** Canonical Enum

포함 항목:
- Anatomy_Map
- Pathology_Pattern
- Pattern_Collection
- Comparison
- Algorithm
- Classification
- Sign_Collection
- Physiology_Process
- Treatment_Workflow  ←
- Modality_Protocol   ←
- Normal_Variants     ←
- Artifacts_Pitfalls  ←
- Reporting_Template  ←
- Equipment
- QC
- General
- Other               ←
```

#### 💻 코드 (01_generate_json.py)
```python
**위치:** `3_Code/src/01_generate_json.py` (라인 1164-1176)

VISUAL_ENUM = {
    "Anatomy_Map",
    "Pathology_Pattern",
    "Pattern_Collection",
    "Comparison",
    "Algorithm",
    "Classification",
    "Sign_Collection",
    "Physiology_Process",
    "Equipment",
    "QC",
    "General",
    # 누락: Treatment_Workflow, Modality_Protocol, Normal_Variants,
    #       Artifacts_Pitfalls, Reporting_Template, Other
}
```

#### 💻 코드 (validate_stage1_struct.py)
```python
**위치:** `3_Code/src/validate_stage1_struct.py` (라인 35-49)

ALLOWED_VISUAL_CATEGORIES = {
    "Anatomy_Map",
    "Pathology_Pattern",
    "Pattern_Collection",
    "Comparison",
    "Algorithm",
    "Classification",
    "Sign_Collection",
    "Physiology_Process",
    "Workflow",           ← (Treatment_Workflow 아님)
    "Other",             ← 포함
    "Equipment",
    "QC",
    "General",
    # 누락: Modality_Protocol, Normal_Variants, Artifacts_Pitfalls,
    #       Reporting_Template, Treatment_Workflow
}
```

**충돌 상태:** ⚠️ **3곳에서 서로 다른 enum 정의**

**영향:** 
- S1 Schema 문서와 코드 검증 로직이 불일치
- 일부 카테고리가 허용되지 않거나, 허용되어야 할 카테고리가 거부될 수 있음

---

### 충돌 3: Card Type Enum 불일치

#### 📄 문서 A (S2_CARDSET_POLICY)
```
**위치:** `0_Protocol/04_Step_Contracts/Step02_S2/S2_CARDSET_POLICY_V1.md`

"유형/이미지 배치 고정:
- Q1: BASIC + IMAGE_ON_FRONT
- Q2: MCQ + IMAGE_ON_BACK
- Q3: MCQ + NO_IMAGE"
```

#### 📄 문서 B (S2 Contract)
```
**위치:** `0_Protocol/04_Step_Contracts/Step02_S2/S2_Contract_and_Schema_Canonical.md`
**섹션 6:** Anki Card Object Schema

"card_type: string, one of Cloze, MCQ"
```

**충돌 상태:** ⚠️ **S2_CARDSET_POLICY는 BASIC을 사용, S2_Contract는 Cloze를 사용**

**영향:** 
- S2 출력 스키마와 실제 카드 생성 정책이 불일치
- BASIC vs Cloze 용어 혼동

---

## 🟡 Medium 충돌 (수정 권장)

### 충돌 4: Entity List 타입 설명 불일치

#### 📄 문서 (S1 Schema v1.3)
```
**위치:** `0_Protocol/04_Step_Contracts/Step01_S1/S1_Stage1_Struct_JSON_Schema_Canonical.md`
**섹션 6.1:** "Each object in entity_list MUST include: entity_id, entity_name"
```

#### 📄 문서 (Weekly SSOT)
```
**위치:** `0_Protocol/01_Execution_Safety/stabilization/Weekly_Integrated_Conclusion_Operating_SSOT.md`
**섹션 2.5:** "inconsistent entity_list typing (string vs object)"
```

**충돌 상태:** ⚠️ **과거에 string vs object 혼동이 있었음 (해결되었을 수 있으나 문서에 흔적 남아있음)**

**영향:** 낮음 (과거 이슈 기록)

---

### 충돌 5: Master Table 필드명 불일치

#### 📄 문서 (S1 Schema v1.3)
```
**위치:** `0_Protocol/04_Step_Contracts/Step01_S1/S1_Stage1_Struct_JSON_Schema_Canonical.md`
**필드명:** `master_table_markdown_kr` (필수)
```

#### 💻 코드 (01_generate_json.py)
```python
**위치:** `3_Code/src/01_generate_json.py` (라인 1507-1508)

"master_table_markdown": str(s1_json.get("master_table_markdown") or 
                              s1_json.get("master_table_markdown_kr") or "").strip(),
"master_table_markdown_kr": str(s1_json.get("master_table_markdown_kr") or "").strip(),
```

**충돌 상태:** ⚠️ **코드가 `master_table_markdown` (kr 없음)도 허용하는 fallback 로직**

**영향:** 낮음 (하위 호환성 유지용일 수 있음)

---

## 📊 상세 비교표

### visual_type_category Enum 비교

| 카테고리 | S1 Schema v1.3 | 01_generate_json.py | validate_stage1_struct.py |
|---------|---------------|---------------------|---------------------------|
| Anatomy_Map | ✅ | ✅ | ✅ |
| Pathology_Pattern | ✅ | ✅ | ✅ |
| Pattern_Collection | ✅ | ✅ | ✅ |
| Comparison | ✅ | ✅ | ✅ |
| Algorithm | ✅ | ✅ | ✅ |
| Classification | ✅ | ✅ | ✅ |
| Sign_Collection | ✅ | ✅ | ✅ |
| Physiology_Process | ✅ | ✅ | ✅ |
| Treatment_Workflow | ✅ | ❌ | ❌ |
| Modality_Protocol | ✅ | ❌ | ❌ |
| Normal_Variants | ✅ | ❌ | ❌ |
| Artifacts_Pitfalls | ✅ | ❌ | ❌ |
| Reporting_Template | ✅ | ❌ | ❌ |
| Equipment | ✅ | ✅ | ✅ |
| QC | ✅ | ✅ | ✅ |
| General | ✅ | ✅ | ✅ |
| Other | ✅ | ❌ | ✅ |
| Workflow | ❌ | ❌ | ✅ |

---

### Card Type 비교

| Card Type | S2_CARDSET_POLICY | S2_Contract | 실제 사용 |
|-----------|------------------|------------|----------|
| BASIC | ✅ | ❌ | ? |
| MCQ | ✅ | ✅ | ? |
| Cloze | ❌ | ✅ | ? |

---

## 🎯 수정 권장사항

### 우선순위 1 (Critical): S2 Contract Schema 버전 업데이트

**수정 대상:**
- `0_Protocol/04_Step_Contracts/Step02_S2/S2_Contract_and_Schema_Canonical.md`

**수정 내용:**
```markdown
## 4. Input Dependency

S2 MUST consume `stage1_struct.jsonl` that conforms to `S1_STRUCT_v1.3`.
```

---

### 우선순위 2 (Critical): visual_type_category Enum 동기화

**수정 대상:**
1. `3_Code/src/01_generate_json.py` - VISUAL_ENUM 업데이트
2. `3_Code/src/validate_stage1_struct.py` - ALLOWED_VISUAL_CATEGORIES 업데이트

**수정 내용:**
- S1 Schema v1.3의 전체 enum 리스트로 통일
- "Other" 포함
- "Workflow" → "Treatment_Workflow"로 수정

---

### 우선순위 3 (Critical): Card Type 용어 통일

**확인 필요:**
- BASIC과 Cloze가 동일한 의미인지?
- 아니면 서로 다른 카드 타입인지?

**수정 방안 (선택지):**

**옵션 A:** BASIC = Cloze로 간주
- S2_CARDSET_POLICY에서 "BASIC" → "Cloze"로 변경
- 또는 S2_Contract에서 "Cloze" → "BASIC"으로 변경

**옵션 B:** BASIC과 Cloze는 별개
- S2_Contract에 "BASIC" 추가
- S2_CARDSET_POLICY에 "Cloze" 추가 (또는 제거)

---

### 우선순위 4 (Medium): Master Table 필드명 정리

**수정 대상:**
- `3_Code/src/01_generate_json.py`

**수정 내용:**
- `master_table_markdown` fallback 로직 제거 또는 명확한 주석 추가
- Canonical 필드명은 `master_table_markdown_kr`만 사용

---

## ✅ 해결 완료 사항

**사용자 결정사항 (2025-12-19):**

1. **Card Type:** ✅ BASIC과 CLOZE는 별개, CLOZE는 만들지 않음
2. **visual_type_category:** ✅ Other 폐기, 코드의 11개 항목으로 통일
3. **S2 Schema 버전:** ✅ S1_STRUCT_v1.3으로 업데이트

---

## 📝 수정 완료 내역

### 1. S2_Contract_and_Schema_Canonical.md ✅
- 섹션 4: S1_STRUCT_v1.3으로 업데이트
- 섹션 6: card_type enum에서 Cloze 제거, BASIC 추가

### 2. S1_Stage1_Struct_JSON_Schema_Canonical.md ✅
- 섹션 4: visual_type_category enum을 11개로 축소
- Other 및 추가 카테고리 제거 (deprecated 명시)

### 3. validate_stage1_struct.py ✅
- ALLOWED_VISUAL_CATEGORIES를 11개로 축소
- Workflow, Other 제거

### 4. Weekly_Integrated_Conclusion_Operating_SSOT.md ✅
- D3 섹션: Other 제거 반영

---

## ✅ 최종 상태

모든 충돌이 해결되었으며, 코드와 문서가 일관된 정책을 반영합니다:
- **Card Type:** BASIC, MCQ (CLOZE 제거)
- **visual_type_category:** 11개 항목으로 통일 (Other 제거)
- **S2 Schema:** S1_STRUCT_v1.3 참조

---

**참고 문서:**
- `0_Protocol/04_Step_Contracts/Step01_S1/S1_Stage1_Struct_JSON_Schema_Canonical.md` (v1.3, 최신)
- `0_Protocol/04_Step_Contracts/Step02_S2/S2_Contract_and_Schema_Canonical.md` (v3.0, 구버전 참조)
- `0_Protocol/04_Step_Contracts/Step02_S2/S2_CARDSET_POLICY_V1.md` (BASIC 사용)

