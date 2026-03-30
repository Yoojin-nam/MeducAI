# S2 Implementation Update Log — 2025-12-20

**Status:** Canonical  
**Version:** 1.0  
**Last Updated:** 2025-12-20  
**Purpose:** S2 프롬프트 및 코드 구현 업데이트 및 중요 버그 수정 이력

---

## 개요

이 문서는 2025-12-20에 수행된 S2 (Stage 2) 프롬프트 개선, 코드 업데이트, 그리고 **중요한 버그 수정**을 기록합니다.

---

## 주요 변경 사항

### 1. S2 프롬프트 v7 개선

**파일:**
- `3_Code/prompt/S2_SYSTEM__v7.md`
- `3_Code/prompt/S2_USER_ENTITY__v7.md`

**프롬프트 레지스트리:**
- `3_Code/prompt/_registry.json`에 S2 v7 프롬프트 등록

#### 1.1 Q2/Q3 카드의 Front와 Options 분리 규칙 명확화

**변경 사항:**
- Q2, Q3 카드의 `front` 필드에는 문제만 포함하도록 명시
- `options` 배열에 선택지 포함하도록 명시
- Front 텍스트에 선택지 (①②③④⑤) 포함 금지

**목적:**
- MCQ 카드의 구조 명확화
- Anki 덱 생성 시 올바른 포맷 보장
- 프론트/백 분리 명확화

**예시:**
```json
// 올바른 형식
{
  "card_role": "Q2",
  "card_type": "MCQ",
  "front": "CT axial에서 저밀도 병변을 보인다. 가장 가능성이 높은 진단은?",
  "options": ["Osteoblastoma", "Osteoid Osteoma", "Brodie abscess", "Stress fracture", "Ewing sarcoma"],
  "correct_index": 1
}

// 잘못된 형식 (front에 선택지 포함)
{
  "front": "CT axial에서 저밀도 병변을 보인다. 가장 가능성이 높은 진단은? ① Osteoblastoma ② Osteoid Osteoma ..."
}
```

---

### 2. 코드 개선 및 버그 수정

#### 2.1 validate_stage2() 함수 개선

**파일:** `3_Code/src/01_generate_json.py`

**위치:** 라인 1754-1975

**변경 사항:**
- `options` 저장 로직 개선: 검증된 `options`와 `correct_index` 필드가 정확히 저장되도록 수정
- MCQ 카드에 대한 필수 필드 검증 강화
- 에러 메시지 개선

**개선 사항:**
- Priority 1: 검증된 값 사용 (validated_options, validated_correct_index)
- Priority 2: 원본 카드의 값 사용 (fallback)
- 최종 안전장치: options가 여전히 없으면 에러 발생

---

### 2.2 validate_and_fill_entity() 함수 수정 (중요한 버그 수정) ⚠️

**파일:** `3_Code/src/01_generate_json.py`

**위치:** 라인 375-441

#### 문제 증상

- Raw LLM 출력에는 `options`와 `correct_index`가 정상적으로 생성됨
- 하지만 `s2_results__armA.jsonl` 파일에는 `options` 필드가 없음
- 결과적으로 Anki 덱 생성 시 에러 발생: `MCQ must have exactly 5 options, got 0`

**영향받는 Run Tags:**
- `FULL_PIPELINE_V8_20251220_161953`
- `FULL_PIPELINE_V8_20251220_162628`
- `FULL_PIPELINE_V8_20251220_163147`
- `FULL_PIPELINE_V8_20251220_163907`
- `FULL_PIPELINE_V8_20251220_164637`
- `FULL_PIPELINE_V8_20251220_170722`

#### 근본 원인

- `validate_stage2()` 함수는 `options`를 올바르게 검증하고 저장함
- 하지만 `process_single_group()` 함수에서 `validate_and_fill_record()`가 호출됨
- `validate_and_fill_record()`는 모든 entity에 대해 `validate_and_fill_entity()`를 호출함
- **`validate_and_fill_entity()` 함수가 `options`와 `correct_index`를 보존하지 않았음** ← 근본 원인

#### 해결 방법

```python
# 수정 전: options와 correct_index가 보존되지 않음
cc = {
    "card_type": str(c.get("card_type") or "Basic").strip(),
    "front": str(c.get("front") or "").strip(),
    "back": str(c.get("back") or "").strip(),
    "tags": tags,
}
if card_role:
    cc["card_role"] = card_role
if image_hint is not None:
    cc["image_hint"] = image_hint
# options와 correct_index가 누락됨!

# 수정 후: options와 correct_index 보존
cc = {
    "card_type": str(c.get("card_type") or "Basic").strip(),
    "front": str(c.get("front") or "").strip(),
    "back": str(c.get("back") or "").strip(),
    "tags": tags,
}
if card_role:
    cc["card_role"] = card_role
if image_hint is not None:
    cc["image_hint"] = image_hint
# CRITICAL: MCQ fields 보존 추가
if options is not None:
    if isinstance(options, list):
        cc["options"] = options
if correct_index is not None:
    cc["correct_index"] = correct_index
```

**변경 내용:**
- `card_role`과 `image_hint`를 보존하는 것과 동일한 방식으로 `options`와 `correct_index` 보존
- MCQ 카드 (Q2, Q3)의 선택지 정보가 S2 출력에 정상적으로 포함되도록 수정

---

## 영향 및 호환성

### 하위 호환성

- ✅ S2 출력 스키마 변경 없음 (frozen)
- ✅ 기존 실행 결과와 호환됨 (단, 버그 수정 전 run tag는 재실행 필요)
- ⚠️ **중요**: options 필드 누락 문제가 있던 기존 run tag는 재실행 필요

### 마이그레이션 필요 사항

**버그 수정 전 run tag 사용자:**
1. S2 출력 파일에서 MCQ 카드의 `options` 필드 존재 여부 확인
2. 없으면 재실행 필요 (이미 저장된 파일은 수정 불가)

**재실행 방법:**
```bash
# 전체 파이프라인 재실행
NEW_RUN_TAG="FULL_PIPELINE_V8_$(date +%Y%m%d_%H%M%S)"
bash 3_Code/Scripts/run_full_pipeline_armA_sample_v8.sh "$NEW_RUN_TAG"
```

---

## 테스트 결과

### 테스트 실행 (버그 수정 검증)
- Run Tag: `TEST_OPTIONS_FIX_20251220_172357`
- 목적: `validate_and_fill_entity()` 함수 수정 후 options 필드 보존 검증

### 결과
- ✅ 전체 파이프라인 성공적으로 완료
- ✅ 8개 MCQ 카드 모두 `options`와 `correct_index` 필드 정상 저장 확인
- ✅ Anki 덱 생성: 성공 (에러 없음)
- ✅ PDF 생성: 성공

**검증 명령어:**
```bash
python3 3_Code/test_options_check.py 2_Data/metadata/generated/TEST_OPTIONS_FIX_20251220_172357/s2_results__armA.jsonl
```

**결과:**
```
Total MCQ cards: 8
MCQ with options: 8
MCQ without options: 0
✅ PASS: All 8 MCQ cards have options and correct_index
```

---

## 관련 문서

### 구현 로그
- `0_Protocol/00_Governance/Implementation_Change_Log_2025-12-20.md` (통합 로그)
- `HANDOVER_20251220.md` (인계 문서, 상세 디버깅 정보 포함)

### 프롬프트 파일
- `3_Code/prompt/S2_SYSTEM__v7.md`
- `3_Code/prompt/S2_USER_ENTITY__v7.md`
- `3_Code/prompt/_registry.json`

### 스키마 문서
- `0_Protocol/04_Step_Contracts/Step02_S2/S2_Contract_and_Schema_Canonical.md`
- `0_Protocol/04_Step_Contracts/Step02_S2/S2_Cardset_Image_Placement_Policy_Canonical.md`

---

## 변경 이력

- **2025-12-20**: S2 프롬프트 v7 개선 및 중요 버그 수정
  - Q2/Q3 front와 options 분리 규칙 명확화
  - validate_stage2() 함수 개선
  - **validate_and_fill_entity() 함수 수정 (options/correct_index 보존)** ← 중요 버그 수정
