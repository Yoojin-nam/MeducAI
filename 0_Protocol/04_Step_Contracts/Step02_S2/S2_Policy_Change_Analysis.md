# S2 정책 변경 사항 분석 (Policy Change Analysis)

**Status:** **SUPERSEDED** (Historical Reference)  
**Version:** 1.0  
**Last Updated:** 2025-12-19  
**Superseded Date:** 2025-12-20  
**Purpose:** 새로운 정책 문서(`S2_Cardset_Image_Placement_Policy_Canonical.md` v1.3)를 표준으로 채택할 때 필요한 변경 사항 검토

**⚠️ IMPORTANT:** This document is **superseded**. All changes described in this document have been **implemented and completed** (2025-12-20). The current canonical policy is `S2_Cardset_Image_Placement_Policy_Canonical.md` v1.3.

**Current Status:**
- ✅ S2 output schema updated (card_role, image_hint added)
- ✅ S3 ImageSpec compiler implemented
- ✅ All checklist items completed

This document is retained as a **historical reference** for the v1.2 → v1.3 migration process.

---

## 1. 개요 (Executive Summary)

새로운 정책 문서(v1.3)는 기존 v1.2와 비교하여 **S3 ImageSpec 컴파일러** 개념을 도입하고, **S2 출력에 image_hint 필드**를 추가합니다. 이는 S2-S3-S4 간 이미지 파이프라인을 더욱 deterministic하게 만듭니다.

**주요 변경 사항:**
1. ✅ S2 출력 스키마에 `image_hint` 객체 추가 (Q1 필수, Q2 권장, Q3 금지)
2. ✅ S3에 ImageSpec 컴파일러 역할 추가 (LLM 없이 deterministic 컴파일)
3. ✅ S3 출력에 `s3_image_spec.jsonl` 아티팩트 추가
4. ✅ Card role (Q1/Q2/Q3) 명시적 정의 및 placement 매핑
5. ⚠️ S3 정의와의 충돌 가능성 검토 필요

---

## 2. 문서별 변경 사항 상세 분석

### 2.1 S2_Cardset_Image_Placement_Policy_Canonical.md

**현재 버전:** v1.2  
**새 버전:** v1.3 (REPLACEMENT)

#### 변경 사항:

1. **제목 변경**
   - 기존: "No-Per-Entity-Necessity"
   - 신규: "S3 ImageSpec Handoff"

2. **S3 역할 확장 (섹션 5.3)**
   - 기존: "Resolver / Enforcer" (placement 해석 및 제약 강제)
   - 신규: "Resolver + ImageSpec compiler" (추가로 S1 visual context + S2 image hints를 컴파일)

3. **Image Hint 개념 추가 (섹션 8)**
   - **새로 추가됨**: S2 → S3 간 image hint 객체 정의
   - S2 출력에 `image_hint` 필드 추가 (Q1 필수, Q2 권장, Q3 금지)
   - Image hint 스키마 정의:
     ```json
     {
       "image_hint": {
         "modality_preferred": "XR|CT|MRI|US|Angio|NM|PETCT|Other",
         "anatomy_region": "free text (short)",
         "key_findings_keywords": ["keyword1", "keyword2", "keyword3"],
         "view_or_sequence": "optional (e.g., axial T2, PA view)",
         "exam_focus": "optional (diagnosis|sign|pattern|differential)"
       }
     }
     ```

4. **S3 ImageSpec 컴파일러 규칙 (섹션 8.3)**
   - **새로 추가됨**: S3가 LLM 없이 deterministic하게 image_spec 생성
   - S1 master table row context 활용
   - Template 기반 prompt_en 생성

5. **ImageSpec 스키마 추가 (섹션 8.4)**
   - **새로 추가됨**: S3 출력 스키마 정의
   - `s3_image_spec.jsonl` 아티팩트 정의

6. **아티팩트 추가 (섹션 11)**
   - `image_hint_manifest.jsonl` (S2 출력, 권장)
   - `s3_image_spec.jsonl` (S3 출력, authoritative for S4)

7. **Validator 체크 추가 (섹션 12)**
   - Image hint compliance 체크 추가
   - Q1은 image_hint 필수, Q3는 image_hint 금지

---

### 2.2 S2_Contract_and_Schema_Canonical.md

**현재 버전:** v3.0  
**필요한 변경:** v3.1 또는 v4.0

#### 변경 사항:

1. **Anki Card Object Schema 확장 (섹션 6)**

   **현재:**
   ```json
   {
     "card_id": "...",
     "card_type": "BASIC|MCQ",
     "front": "...",
     "back": "...",
     "tags": ["..."]
   }
   ```

   **변경 후:**
   ```json
   {
     "card_id": "...",
     "card_type": "BASIC|MCQ",
     "front": "...",
     "back": "...",
     "tags": ["..."],
     "card_role": "Q1|Q2|Q3",  // 새로 추가
     "image_hint": {            // 조건부 추가 (Q1 필수, Q2 권장, Q3 금지)
       "modality_preferred": "...",
       "anatomy_region": "...",
       "key_findings_keywords": ["..."],
       "view_or_sequence": "...",
       "exam_focus": "..."
     }
   }
   ```

2. **제약 조건 추가**
   - Q1 카드: `image_hint` 필수
   - Q2 카드: `image_hint` 권장 (strongly preferred)
   - Q3 카드: `image_hint` 금지 (없어야 함)

3. **Fail-fast 규칙 업데이트 (섹션 7)**
   - Q1 카드에 `image_hint`가 없으면 FAIL
   - Q3 카드에 `image_hint`가 있으면 FAIL

---

### 2.3 S2_Policy_and_Implementation_Summary.md

**현재 버전:** v1.0  
**필요한 변경:** v1.1

#### 변경 사항:

1. **출력 스키마 업데이트 (섹션 2.2)**
   - `anki_cards` 배열의 각 카드 객체에 `card_role` 및 `image_hint` 필드 추가

2. **내부 처리 흐름 업데이트 (섹션 3)**
   - S2 실행 후 S3 ImageSpec 컴파일 단계 추가 설명

3. **프롬프트 업데이트 (섹션 4)**
   - S2_USER_ENTITY 프롬프트에 image_hint 생성 지시 추가 필요

4. **새로운 섹션 추가**
   - "S3 ImageSpec 컴파일러" 섹션 추가
   - S2 → S3 → S4 이미지 파이프라인 설명

---

### 2.4 S2 프롬프트 파일

**영향받는 파일:**
- `3_Code/prompt/S2_SYSTEM__v5.md`
- `3_Code/prompt/S2_USER_ENTITY__v5.md`

#### 변경 사항:

1. **S2_SYSTEM 프롬프트**
   - Image hint 생성 규칙 추가
   - Q1/Q2/Q3 역할별 image_hint 요구사항 명시

2. **S2_USER_ENTITY 프롬프트**
   - Image hint 객체 생성 지시 추가
   - 출력 스키마에 `card_role` 및 `image_hint` 필드 포함
   - Q1: image_hint 필수, Q2: image_hint 권장, Q3: image_hint 금지

---

### 2.5 코드 구현 변경 사항

**영향받는 파일:**
- `3_Code/src/01_generate_json.py`

#### 변경 사항:

1. **validate_stage2() 함수 (라인 1351-1381)**
   ```python
   # 현재: image_hint 처리 없음
   # 변경 후:
   - card_role 추출 및 검증
   - image_hint 추출 및 검증
   - Q1: image_hint 필수 체크
   - Q3: image_hint 금지 체크
   ```

2. **write_s2_results_jsonl() 함수 (라인 1308-1350)**
   ```python
   # 현재: card_role, image_hint 출력 없음
   # 변경 후:
   - card_role 필드 출력
   - image_hint 필드 출력 (조건부)
   ```

3. **프롬프트 포맷팅 (라인 1751-1765)**
   ```python
   # S2_USER_ENTITY 프롬프트에 card_role 및 image_hint 생성 지시 추가
   ```

---

### 2.6 S3 관련 문서 및 구현

**영향받는 문서:**
- `0_Protocol/04_Step_Contracts/Step03_S3/Entity_Definition_S3_Canonical.md`
- `0_Protocol/04_Step_Contracts/S3_to_S4_Input_Contract_Canonical.md`

#### 변경 사항:

1. **S3 정의 업데이트 필요**
   - **현재 정의**: "S3 is a state-only selection and QA gate"
   - **새 요구사항**: S3가 ImageSpec 컴파일러 역할도 수행
   - **충돌 가능성**: 기존 정의에서 "S3 does not generate content"와 충돌
   - **해결 방안**: 
     - Option A: S3 정의를 확장하여 "deterministic compiler" 역할 추가
     - Option B: ImageSpec 컴파일을 별도 단계(S3.5)로 분리
     - Option C: S3를 "Selection & QA Gate + ImageSpec Compiler"로 재정의

2. **S3 구현 필요**
   - **새로 구현 필요**: ImageSpec 컴파일러 로직
   - S1 master table row context 파싱
   - S2 image_hint 읽기
   - Template 기반 prompt_en 생성
   - `s3_image_spec.jsonl` 출력

3. **S3_to_S4_Input_Contract 업데이트**
   - ImageSpec 스키마 정의 추가
   - S4 입력 스키마 업데이트

---

## 3. 변경 우선순위 및 단계별 구현 계획

### Phase 1: 문서 업데이트 (즉시)

1. ✅ `S2_Cardset_Image_Placement_Policy_Canonical.md` v1.3으로 교체
2. ⚠️ `S2_Contract_and_Schema_Canonical.md` v3.1 또는 v4.0으로 업데이트
3. ⚠️ `S2_Policy_and_Implementation_Summary.md` v1.1으로 업데이트
4. ⚠️ S3 정의 문서 검토 및 업데이트 필요성 판단

### Phase 2: 프롬프트 업데이트 (우선)

1. `S2_SYSTEM__v5.md` → `S2_SYSTEM__v6.md` (image_hint 규칙 추가)
2. `S2_USER_ENTITY__v5.md` → `S2_USER_ENTITY__v6.md` (image_hint 생성 지시 추가)

### Phase 3: 코드 구현 (중요)

1. **S2 출력 스키마 확장**
   - `validate_stage2()` 함수에 card_role, image_hint 검증 추가
   - `write_s2_results_jsonl()` 함수에 card_role, image_hint 출력 추가

2. **프롬프트 번들 업데이트**
   - 새로운 프롬프트 파일 로드

3. **S3 ImageSpec 컴파일러 구현** (새로 구현)
   - S1 master table 파싱
   - S2 image_hint 읽기
   - Template 기반 컴파일
   - `s3_image_spec.jsonl` 출력

### Phase 4: 검증 및 테스트

1. S2 출력 검증 (image_hint compliance)
2. S3 ImageSpec 컴파일 검증
3. End-to-end 테스트 (S1 → S2 → S3 → S4)

---

## 4. 주의사항 및 리스크

### 4.1 S3 정의 충돌

**문제:**
- 기존 S3 정의: "S3 does not generate content"
- 새 요구사항: S3가 ImageSpec을 "컴파일" (template 기반 생성)

**해결 방안:**
- "Generate"와 "Compile"의 의미 구분 필요
- Template 기반 deterministic 컴파일은 "generation"이 아닌 "transformation"으로 해석 가능
- S3 정의 문서에 명시적 예외 추가 권장

### 4.2 하위 호환성

**문제:**
- 기존 S2 출력에 `card_role` 및 `image_hint`가 없음
- 기존 S3가 ImageSpec을 생성하지 않음

**해결 방안:**
- 마이그레이션 스크립트 작성
- 또는 기존 아티팩트 재생성 필요

### 4.3 S1 Master Table 파싱

**문제:**
- S3가 S1 master table에서 visual keywords를 추출해야 함
- Table 파싱 로직 구현 필요

**해결 방안:**
- S1 출력에 이미 구조화된 필드가 있는지 확인
- 없으면 markdown table 파싱 로직 구현

---

## 5. 체크리스트

### 문서 업데이트
- [ ] `S2_Cardset_Image_Placement_Policy_Canonical.md` v1.3으로 교체
- [ ] `S2_Contract_and_Schema_Canonical.md` 업데이트 (card_role, image_hint 추가)
- [ ] `S2_Policy_and_Implementation_Summary.md` 업데이트
- [ ] S3 정의 문서 검토 및 업데이트 필요성 판단

### 프롬프트 업데이트
- [ ] `S2_SYSTEM__v6.md` 생성 (image_hint 규칙 추가)
- [ ] `S2_USER_ENTITY__v6.md` 생성 (image_hint 생성 지시 추가)
- [ ] 프롬프트 번들 업데이트

### 코드 구현
- [ ] `validate_stage2()` 함수 업데이트 (card_role, image_hint 검증)
- [ ] `write_s2_results_jsonl()` 함수 업데이트 (card_role, image_hint 출력)
- [ ] S2 프롬프트 포맷팅 업데이트
- [ ] S3 ImageSpec 컴파일러 구현 (새로 구현)
- [ ] S3 출력 스키마 정의 및 구현

### 검증 및 테스트
- [ ] S2 출력 검증 (image_hint compliance)
- [ ] S3 ImageSpec 컴파일 검증
- [ ] End-to-end 테스트

---

## 6. 참고 문서

- 새로운 정책 문서: `/path/to/workspace/Downloads/S2_Cardset_Image_Placement_Policy_Canonical.REPLACEMENT.md`
- 현재 정책 문서: `0_Protocol/04_Step_Contracts/Step02_S2/S2_Cardset_Image_Placement_Policy_Canonical.md`
- S2 Contract: `0_Protocol/04_Step_Contracts/Step02_S2/S2_Contract_and_Schema_Canonical.md`
- S3 정의: `0_Protocol/04_Step_Contracts/Step03_S3/Entity_Definition_S3_Canonical.md`

