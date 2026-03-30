# S0 실행 계획: S4 없이 S1/S2 먼저 진행

**Date:** 2025-12-20  
**Status:** Execution Plan  
**Purpose:** S4 API 요청 문제로 인해 S1/S2를 먼저 진행하고, 나중에 S4를 실행하는 계획

---

## Executive Summary

**결론: 가능합니다.** S4 없이도 S1/S2/S3를 먼저 진행하고, PDF를 이미지 없이 생성할 수 있습니다. 나중에 S4를 실행하여 이미지를 추가한 후 PDF를 재생성하면 됩니다.

**평가 진행 옵션:**
- **옵션 A:** 이미지 없이 평가 시작 → S4 완료 후 이미지 포함 완성본으로 평가 계속
- **옵션 B:** 이미지 없이 완성 → S4 완료 후 이미지 포함 완성본으로 평가 진행 (권장)

---

## 1. 실행 순서

### 1.1 Phase 1: QA Mapping 준비

**목적:** 평가자 배정 및 매핑 파일 생성

**작업:**
1. 평가자 목록 수집 (전문의/전공의)
2. 평가자별 Set 배정 (assignment algorithm)
3. `assignment_map.csv` 생성 및 검증
   - `reviewer_id`, `local_qid` (Q01~Q12), `set_id`, `group_id`, `arm_id`, `role`
4. Surrogate mapping 생성 (`surrogate_map.csv`)

**출력:**
- `assignment_map.csv`
- `surrogate_map.csv`

---

### 1.2 Phase 2: S1/S2 실행 (108 sets)

**목적:** 콘텐츠 생성 (Master Table + Anki Cards)

**작업:**

#### Step 1: S1 실행 (모든 arm)

```bash
# 6 arm 순차 실행
for arm in A B C D E F; do
  python3 3_Code/src/01_generate_json.py \
    --base_dir . \
    --run_tag S0_QA_20251220 \
    --arm $arm \
    --mode S0 \
    --stage 1
done
```

**출력:**
- `stage1_struct__arm{A-F}.jsonl` (18 groups × 6 arms = 108 sets)

#### Step 2: S1 Gate 검증

```bash
python3 3_Code/src/validate_stage1_struct.py \
  --base_dir . \
  --run_tag S0_QA_20251220
```

#### Step 3: Allocation 생성

```bash
for arm in A B C D E F; do
  python3 3_Code/src/tools/allocation/s0_allocation.py \
    --base_dir . \
    --run_tag S0_QA_20251220 \
    --arm $arm
done
```

#### Step 4: S2 실행 (모든 arm)

```bash
for arm in A B C D E F; do
  python3 3_Code/src/01_generate_json.py \
    --base_dir . \
    --run_tag S0_QA_20251220 \
    --arm $arm \
    --mode S0 \
    --stage 2
done
```

**출력:**
- `s2_results__arm{A-F}.jsonl` (108 sets, 각 Set당 12 cards)

---

### 1.3 Phase 3: S3 실행 (이미지 스펙 생성)

**목적:** 이미지 정책 해석 및 이미지 스펙 컴파일 (이미지 생성은 안 함)

**작업:**

```bash
for arm in A B C D E F; do
  python3 3_Code/src/03_s3_policy_resolver.py \
    --base_dir . \
    --run_tag S0_QA_20251220 \
    --arm $arm \
    --mode S0
done
```

**출력:**
- `image_policy_manifest__arm{A-F}.jsonl` (이미지 배치 정책)
- `s3_image_spec__arm{A-F}.jsonl` (이미지 생성 스펙, S4 입력용)

**중요:** S3는 이미지를 생성하지 않습니다. 이미지 스펙만 생성합니다.

---

### 1.4 Phase 4: PDF 생성 (이미지 없이)

**목적:** QA 평가용 PDF 생성 (이미지 없이)

**작업:**

```bash
# 모든 Set에 대해 PDF 생성 (이미지 없이)
for arm in A B C D E F; do
  # 18 groups 순회
  for group_id in G0001 G0002 ... G0018; do
    python3 3_Code/src/07_build_set_pdf.py \
      --base_dir . \
      --run_tag S0_QA_20251220 \
      --arm $arm \
      --group_id $group_id \
      --out_dir 6_Distributions/QA_Packets \
      --blinded \
      --set_surrogate_csv 0_Protocol/06_QA_and_Study/QA_Operations/surrogate_map.csv \
      --allow_missing_images
  done
done
```

**출력:**
- `SET_<surrogate>.pdf` (108 PDFs, 이미지 없이)

**특징:**
- `--allow_missing_images` 옵션 사용
- 이미지가 필요한 위치에 "(IMAGE MISSING)" 플레이스홀더 표시
- PDF 구조는 완전함 (Master Table + Cards)

---

### 1.5 Phase 5: QA 평가 진행 (옵션 선택)

**두 가지 옵션이 있습니다:**

#### 옵션 A: 이미지 없이 평가 시작 (부분 평가)

**목적:** 이미지 없이도 평가 가능한 항목부터 평가 시작

**평가 가능 항목:**
- ✅ Master Table 평가
- ✅ Card 텍스트 평가 (Accuracy, Quality, Clarity, Relevance)
- ✅ Blocking Error 판정
- ⚠️ 이미지 관련 평가는 나중에 (S4 완료 후)

**Google Form 배포:**
- 평가자별 PDF 폴더 (Google Drive) + Google Form 링크 전송
- 이미지 없이도 평가 가능

**장점:**
- 평가를 즉시 시작 가능
- 시간 절약

**단점:**
- 이미지 포함 평가는 나중에 별도로 진행 필요
- 평가가 두 단계로 나뉨

---

#### 옵션 B: 이미지 포함 완성본으로 평가 진행 (권장) ⭐

**목적:** S4 완료 후 이미지 포함 완성본으로 평가 진행

**작업 순서:**
1. S1/S2/S3 완료 (이미지 없이)
2. PDF 생성 (이미지 없이, `--allow_missing_images`)
3. **S4 문제 해결 대기**
4. S4 실행 (이미지 생성)
5. PDF 재생성 (이미지 포함)
6. **이미지 포함 완성본으로 평가 진행**

**평가 항목 (전체):**
- ✅ Master Table 평가
- ✅ Card 텍스트 평가 (Accuracy, Quality, Clarity, Relevance)
- ✅ Blocking Error 판정
- ✅ 이미지 관련 평가 (이미지 포함 완성본)

**Google Form 배포:**
- S4 완료 후 이미지 포함 PDF 배포
- 한 번에 전체 평가 진행

**장점:**
- ✅ 평가를 한 번에 완료 (효율적)
- ✅ 이미지 포함 완성본으로 정확한 평가 가능
- ✅ 평가자 피로도 감소 (한 번만 평가)

**단점:**
- S4 문제 해결까지 대기 필요

**권장:** 옵션 B (이미지 포함 완성본으로 평가 진행)

---

### 1.6 Phase 6: S4 실행 (나중에, 이미지 생성)

**목적:** 이미지 생성 (S3 스펙 기반)

**작업:**

```bash
for arm in A B C D E F; do
  python3 3_Code/src/04_s4_image_generator.py \
    --base_dir . \
    --run_tag S0_QA_20251220 \
    --arm $arm \
    --mode S0
done
```

**출력:**
- `IMG__*.png` (이미지 파일들)
- `s4_image_manifest__arm{A-F}.jsonl` (이미지 매핑 정보)

---

### 1.7 Phase 7: PDF 재생성 (이미지 포함)

**목적:** 이미지가 포함된 최종 PDF 생성

**작업:**

```bash
# 모든 Set에 대해 PDF 재생성 (이미지 포함)
for arm in A B C D E F; do
  for group_id in G0001 G0002 ... G0018; do
    python3 3_Code/src/07_build_set_pdf.py \
      --base_dir . \
      --run_tag S0_QA_20251220 \
      --arm $arm \
      --group_id $group_id \
      --out_dir 6_Distributions/QA_Packets \
      --blinded \
      --set_surrogate_csv 0_Protocol/06_QA_and_Study/QA_Operations/surrogate_map.csv
      # --allow_missing_images 옵션 제거 (이미지 필수)
  done
done
```

**출력:**
- `SET_<surrogate>.pdf` (108 PDFs, 이미지 포함)

---

## 2. 장점

### 2.1 병렬 작업 가능

- ✅ S1/S2/S3는 S4와 독립적으로 실행 가능
- ✅ QA 평가를 이미지 없이 먼저 시작 가능
- ✅ S4 API 문제가 해결되면 나중에 이미지만 추가

### 2.2 리스크 관리

- ✅ S4 API 요청 문제가 전체 파이프라인을 막지 않음
- ✅ 콘텐츠 품질 평가는 이미지 없이도 가능
- ✅ 이미지는 나중에 추가 가능

### 2.3 시간 절약

- ✅ S1/S2/S3를 먼저 완료하여 콘텐츠 검증 가능
- ✅ QA 평가를 병렬로 진행 가능
- ✅ S4는 나중에 배치로 실행

---

## 3. 주의사항

### 3.1 이미지 의존성

**평가 항목:**
- ⚠️ 이미지 관련 평가는 S4 완료 후에만 가능
- ✅ 텍스트 기반 평가는 이미지 없이도 가능

**PDF 구조:**
- ✅ `--allow_missing_images` 옵션으로 PDF 생성 가능
- ✅ "(IMAGE MISSING)" 플레이스홀더로 구조 유지

### 3.2 데이터 일관성

**중요:**
- ✅ S1/S2/S3 출력은 S4 실행 전에 고정됨
- ✅ S4는 S3 스펙을 읽기만 하므로, S3 출력이 변경되지 않으면 안전
- ⚠️ S4 실행 전에 S3 출력을 수정하면 안 됨

### 3.3 PDF 재생성

**필수:**
- ✅ S4 완료 후 PDF를 재생성해야 함
- ✅ 기존 PDF는 이미지 없이 생성된 버전
- ✅ 최종 PDF는 이미지 포함 버전

---

## 4. 실행 체크리스트

### Phase 1: QA Mapping
- [ ] 평가자 목록 수집
- [ ] 평가자별 Set 배정
- [ ] `assignment_map.csv` 생성 및 검증
- [ ] `surrogate_map.csv` 생성

### Phase 2: S1/S2
- [ ] S1 실행 (6 arms)
- [ ] S1 Gate 검증
- [ ] Allocation 생성
- [ ] S2 실행 (6 arms)
- [ ] S2 출력 검증

### Phase 3: S3
- [ ] S3 실행 (6 arms)
- [ ] `image_policy_manifest` 검증
- [ ] `s3_image_spec` 검증

### Phase 4: PDF 생성 (이미지 없이)
- [ ] PDF 생성 스크립트 준비
- [ ] 모든 Set에 대해 PDF 생성 (`--allow_missing_images`)
- [ ] PDF 구조 검증

### Phase 5: QA 평가 (옵션 선택)
- [ ] **옵션 선택:**
  - [ ] 옵션 A: 이미지 없이 평가 시작
  - [ ] 옵션 B: 이미지 포함 완성본으로 평가 진행 (권장)
- [ ] Google Form 생성
- [ ] Google Drive 폴더 준비
- [ ] 평가자 배포
- [ ] 평가 진행

### Phase 6: S4 (나중에)
- [ ] S4 API 문제 해결 확인
- [ ] S4 실행 (6 arms)
- [ ] 이미지 생성 검증
- [ ] `s4_image_manifest` 검증

### Phase 7: PDF 재생성 (이미지 포함)
- [ ] PDF 재생성 (이미지 포함)
- [ ] 최종 PDF 검증
- [ ] 평가자에게 최종 PDF 배포 (선택적)

---

## 5. FAQ

### Q1. 이미지 없이 평가해도 되나요?

**A:** 네, 가능합니다. QA Framework v2.0에서 평가 항목은:
- Accuracy (텍스트 기반)
- Overall Card Quality (텍스트 기반)
- Clarity/Readability (텍스트 기반)
- Clinical Relevance (텍스트 기반)
- Blocking Error (텍스트 기반)

이미지는 시각적 보조 자료이지만, 텍스트 기반 평가는 이미지 없이도 가능합니다.

### Q2. S4를 나중에 실행해도 데이터 일관성이 유지되나요?

**A:** 네, 유지됩니다. S4는 S3 출력을 읽기만 하므로, S3 출력이 변경되지 않으면 안전합니다. S4 실행 전에 S1/S2/S3 출력을 수정하지 않으면 됩니다.

### Q3. PDF를 두 번 생성해야 하나요?

**A:** 옵션에 따라 다릅니다:

**옵션 A (이미지 없이 평가 시작):**
- 첫 번째: 이미지 없이 (`--allow_missing_images`) - 부분 평가용
- 두 번째: 이미지 포함 - 완성본 평가용

**옵션 B (이미지 포함 완성본으로 평가, 권장):**
- 첫 번째: 이미지 없이 (`--allow_missing_images`) - 검증용 (선택적)
- 두 번째: 이미지 포함 - 평가용 (필수)

**권장:** 옵션 B의 경우, 첫 번째 PDF 생성은 선택사항입니다. S4 완료 후 한 번만 생성해도 됩니다.

### Q4. S3는 반드시 실행해야 하나요?

**A:** 네, 필수입니다. PDF 빌더는 `image_policy_manifest`를 필요로 합니다. S3는 이미지를 생성하지 않지만, 이미지 배치 정책을 생성합니다.

---

## 6. 참고 문서

- QA Framework v2.0
- Pipeline Canonical Specification v1.0
- S1/S2 Independent Execution Design
- PDF Packet Builder README
- Google Form Design Specification

---

## 결론

**제안하신 순서로 진행 가능합니다:**

### 권장 워크플로우 (옵션 B)

1. ✅ QA mapping 먼저
2. ✅ S1/S2로 108 set 진행
3. ✅ S3 실행 (이미지 스펙 생성)
4. ⏸️ **S4 문제 해결 대기**
5. ✅ S4 실행 (이미지 생성)
6. ✅ PDF 생성 (이미지 포함, 최종 완성본)
7. ✅ **이미지 포함 완성본으로 평가 진행** ⭐

### 대안 워크플로우 (옵션 A)

1. ✅ QA mapping 먼저
2. ✅ S1/S2로 108 set 진행
3. ✅ S3 실행 (이미지 스펙 생성)
4. ✅ PDF 생성 (이미지 없이, `--allow_missing_images`)
5. ✅ QA 평가 시작 (이미지 없이, 부분 평가)
6. ✅ S4 실행 (나중에, 이미지 생성)
7. ✅ PDF 재생성 (이미지 포함)
8. ✅ 이미지 포함 완성본으로 평가 계속

### 권장 이유 (옵션 B)

- ✅ **평가를 한 번에 완료** (효율적)
- ✅ **이미지 포함 완성본으로 정확한 평가** 가능
- ✅ **평가자 피로도 감소** (한 번만 평가)
- ✅ S4 API 문제가 전체 파이프라인을 막지 않음 (S1/S2/S3는 먼저 진행)

**결론: 먼저 완성한 뒤, S4 문제 해결되면 이미지 추가해서 완성본으로 평가 진행하는 것이 권장됩니다.**

