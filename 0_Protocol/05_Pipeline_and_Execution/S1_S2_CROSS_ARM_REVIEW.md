# S1/S2 Cross-Arm 지원 검토 리포트

**검토 일자:** 2025-12-23  
**검토 범위:** `3_Code/src` 폴더 전체  
**목적:** S2 출력 파일명 변경 및 S1/S2 다른 arm 사용 지원 확인

---

## 1. S2 출력 파일명 변경 사항

### 변경 전
- `s2_results__arm{ARM}.jsonl`

### 변경 후
- `s2_results__s1arm{S1_ARM}__s2arm{S2_ARM}.jsonl` (new format)
- `s2_results__arm{ARM}.jsonl` (legacy format, backward compatible)

### 이유
- S1과 S2가 다른 arm을 사용할 때 같은 S2 arm이라도 다른 파일에 저장되어 덮어쓰기 방지
- 파일명만 봐도 어떤 S1 arm과 S2 arm 조합인지 명확히 알 수 있음

---

## 2. 파일별 검토 결과

### ✅ `01_generate_json.py`
**상태:** 완료

**변경 사항:**
- S2 출력 파일명에 S1 arm과 S2 arm 정보 포함
- `--s1_arm` 옵션 추가 (S2 실행 시 S1 출력을 읽을 arm 지정)
- `path_resolver.resolve_s2_results_path()` 사용 (하위 호환성)

**확인 사항:**
- ✅ S1 실행 시: `stage1_struct__arm{arm}.jsonl` 생성
- ✅ S2 실행 시: `s2_results__s1arm{s1_arm}__s2arm{arm}.jsonl` 생성
- ✅ `--s1_arm` 옵션으로 다른 S1 arm의 출력 읽기 가능

---

### ✅ `03_s3_policy_resolver.py`
**상태:** 완료 (2025-12-23 수정)

**변경 사항:**
- `--s1_arm` 옵션 추가
- `process_s3()` 함수에 `s1_arm` 파라미터 추가
- S1 struct 경로: `stage1_struct__arm{s1_arm_actual}.jsonl` 사용
- `resolve_s2_results_path()` 호출 시 `s1_arm` 전달

**확인 사항:**
- ✅ S2 결과 파일 경로: `resolve_s2_results_path(out_dir, arm, s1_arm=s1_arm_actual)`
- ✅ S1 구조 파일 경로: `stage1_struct__arm{s1_arm_actual}.jsonl`
- ✅ S1과 S2가 다른 arm일 때 올바른 파일 읽기 가능

---

### ✅ `04_s4_image_generator.py`
**상태:** 확인 완료 (수정 불필요)

**확인 사항:**
- ✅ S3 image spec만 읽음 (`s3_image_spec__arm{arm}.jsonl`)
- ✅ S2 결과나 S1 구조를 직접 읽지 않음
- ✅ S3가 올바르게 작동하면 S4도 문제없음
- ✅ S3에 `--s1_arm` 옵션이 추가되었으므로 간접적으로 지원됨

---

### ✅ `07_build_set_pdf.py`
**상태:** 완료

**변경 사항:**
- `--s1_arm` 옵션 추가
- `build_set_pdf()` 함수에 `s1_arm` 파라미터 추가
- S1 struct 경로: `stage1_struct__arm{s1_arm_actual}.jsonl` 사용
- `resolve_s2_results_path()` 호출 시 `s1_arm` 전달

**확인 사항:**
- ✅ S2 결과 파일 경로: `resolve_s2_results_path(gen_dir, arm, s1_arm=s1_arm_actual)`
- ✅ S1 구조 파일 경로: `stage1_struct__arm{s1_arm_actual}.jsonl`
- ✅ S1과 S2가 다른 arm일 때 올바른 파일 읽기 가능

---

### ✅ `07_export_anki_deck.py`
**상태:** 완료 (2025-12-23 수정)

**변경 사항:**
- `--s1_arm` 옵션 추가
- `process_export()` 함수에 `s1_arm` 파라미터 추가
- `resolve_s2_results_path()` 호출 시 `s1_arm` 전달

**확인 사항:**
- ✅ S2 결과 파일 경로: `resolve_s2_results_path(out_dir, arm, s1_arm=s1_arm_actual)`
- ✅ S1과 S2가 다른 arm일 때 올바른 파일 읽기 가능

---

## 3. 하위 호환성

### ✅ `path_resolver.py` 유틸리티
**위치:** `3_Code/src/tools/path_resolver.py`

**기능:**
- 새 형식 우선 시도: `s2_results__s1arm{S1_ARM}__s2arm{S2_ARM}.jsonl`
- Legacy 형식 fallback: `s2_results__arm{ARM}.jsonl`
- S0 결과와의 호환성 유지

**사용 위치:**
- `03_s3_policy_resolver.py`
- `07_build_set_pdf.py`
- `07_export_anki_deck.py`
- `tools/qa/retry_failed_s2_groups.py`
- `tools/qa/retry_failed_qa_groups.py`
- `tools/convert_s2_to_md.py`

---

## 4. S1/S2 다른 arm 사용 시나리오

### 시나리오: S1 A → S2 B

**1단계: S1 A 실행**
```bash
python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag FINAL_TEST \
  --arm A \
  --mode FINAL \
  --stage 1
```
**생성:** `stage1_struct__armA.jsonl`

**2단계: S2 B 실행 (S1 A 결과 사용)**
```bash
python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag FINAL_TEST \
  --arm B \
  --s1_arm A \
  --mode FINAL \
  --stage 2
```
**생성:** `s2_results__s1armA__s2armB.jsonl`

**3단계: S3 실행**
```bash
python3 3_Code/src/03_s3_policy_resolver.py \
  --base_dir . \
  --run_tag FINAL_TEST \
  --arm B \
  --s1_arm A
```
**읽기:**
- S2: `s2_results__s1armA__s2armB.jsonl` (path_resolver가 자동으로 찾음)
- S1: `stage1_struct__armA.jsonl`

**4단계: S4 실행**
```bash
python3 3_Code/src/04_s4_image_generator.py \
  --base_dir . \
  --run_tag FINAL_TEST \
  --arm B
```
**읽기:** `s3_image_spec__armB.jsonl` (S3가 생성)

**5단계: PDF 생성**
```bash
python3 3_Code/src/07_build_set_pdf.py \
  --base_dir . \
  --run_tag FINAL_TEST \
  --arm B \
  --s1_arm A \
  --group_id G0123 \
  --allow_missing_images
```
**읽기:**
- S2: `s2_results__s1armA__s2armB.jsonl` (path_resolver가 자동으로 찾음)
- S1: `stage1_struct__armA.jsonl`

**6단계: Anki Export**
```bash
python3 3_Code/src/07_export_anki_deck.py \
  --base_dir . \
  --run_tag FINAL_TEST \
  --arm B \
  --s1_arm A \
  --allow_missing_images
```
**읽기:** `s2_results__s1armA__s2armB.jsonl` (path_resolver가 자동으로 찾음)

---

## 5. 검증 체크리스트

### 파일명 변경 반영
- [x] ✅ `01_generate_json.py` - S2 출력 파일명 변경
- [x] ✅ `03_s3_policy_resolver.py` - path_resolver 사용
- [x] ✅ `07_build_set_pdf.py` - path_resolver 사용
- [x] ✅ `07_export_anki_deck.py` - path_resolver 사용
- [x] ✅ `tools/qa/retry_failed_s2_groups.py` - path_resolver 사용
- [x] ✅ `tools/qa/retry_failed_qa_groups.py` - path_resolver 사용
- [x] ✅ `tools/convert_s2_to_md.py` - path_resolver 사용

### S1/S2 다른 arm 지원
- [x] ✅ `01_generate_json.py` - `--s1_arm` 옵션 추가
- [x] ✅ `03_s3_policy_resolver.py` - `--s1_arm` 옵션 추가
- [x] ✅ `07_build_set_pdf.py` - `--s1_arm` 옵션 추가
- [x] ✅ `07_export_anki_deck.py` - `--s1_arm` 옵션 추가

### 하위 호환성
- [x] ✅ Legacy 형식 (`s2_results__arm{ARM}.jsonl`) 지원
- [x] ✅ `path_resolver.py`가 자동으로 올바른 파일 찾기
- [x] ✅ S0 결과와의 호환성 유지

---

## 6. 잠재적 이슈 및 권장사항

### 이슈 없음
모든 주요 파일이 올바르게 수정되었고, 하위 호환성도 유지됩니다.

### 권장사항
1. **RUN_TAG 분리 사용**: S1과 S2를 다른 RUN_TAG로 분리하여 관리하면 더욱 안전합니다.
2. **명시적 `--s1_arm` 지정**: S2 실행 시 `--s1_arm`을 명시적으로 지정하는 것을 권장합니다.
3. **문서화**: `CROSS_ARM_S1_S2_USAGE.md` 문서 참조

---

## 7. 테스트 시나리오

### 테스트 1: S1 A → S2 B
```bash
# S1 A 실행
python3 3_Code/src/01_generate_json.py --run_tag TEST --arm A --mode FINAL --stage 1

# S2 B 실행 (S1 A 결과 사용)
python3 3_Code/src/01_generate_json.py --run_tag TEST --arm B --s1_arm A --mode FINAL --stage 2

# S3 실행
python3 3_Code/src/03_s3_policy_resolver.py --run_tag TEST --arm B --s1_arm A

# PDF 생성
python3 3_Code/src/07_build_set_pdf.py --run_tag TEST --arm B --s1_arm A --group_id <GROUP_ID> --allow_missing_images

# Anki Export
python3 3_Code/src/07_export_anki_deck.py --run_tag TEST --arm B --s1_arm A --allow_missing_images
```

### 테스트 2: Legacy 형식 호환성
```bash
# S0 결과 (legacy 형식) 사용
python3 3_Code/src/07_build_set_pdf.py --run_tag S0_QA_20251220 --arm A --group_id <GROUP_ID>
# path_resolver가 자동으로 s2_results__armA.jsonl 찾음
```

---

## 8. 결론

✅ **모든 주요 파일이 올바르게 수정되었습니다.**

- S2 출력 파일명 변경이 모든 파일에 반영됨
- S1과 S2가 다른 arm을 사용할 수 있도록 모든 단계에서 지원
- 하위 호환성 유지 (S0 결과와의 호환성)
- `path_resolver.py` 유틸리티로 일관된 파일 경로 해결

**추가 작업 불필요**

