# S0 QA 실행 워크플로우 가이드

**Date:** 2025-12-20  
**Status:** Canonical  
**Purpose:** S0 QA 실행부터 PDF 생성 및 배포까지 전체 워크플로우 가이드

---

## 📋 개요

이 문서는 S0 QA 실행의 전체 워크플로우를 단계별로 설명합니다:

1. **Phase 1: S0 실행 (S1/S2)** - 콘텐츠 생성
2. **Phase 2: Group ID 업데이트** - assignment_map 업데이트
3. **Phase 3: S3 실행** - 이미지 스펙 생성
4. **Phase 4: S4 실행** - 이미지 생성
5. **Phase 5: PDF 생성 및 배포** - Reviewer별 배포

---

## Phase 1: S0 실행 (S1/S2)

### 목적
- 18개 그룹 선택 (S0 canonical rule)
- 6개 arm (A-F)에 대해 S1/S2 실행
- 108 sets 생성 (18 groups × 6 arms)

### 실행 명령어

```bash
cd /path/to/workspace/workspace/MeducAI
python3 3_Code/src/tools/qa/run_s0_qa_6arm.py \
    --base_dir . \
    --run_tag S0_QA_20251220 \
    --seed 42
```

### 단계별 실행 (문제 발생 시)

#### 1. S1만 실행
```bash
python3 3_Code/src/tools/qa/run_s0_qa_6arm.py \
    --base_dir . \
    --run_tag S0_QA_20251220 \
    --seed 42 \
    --skip_s1_gate --skip_allocation --skip_s2
```

#### 2. S1 Gate 검증
```bash
python3 3_Code/src/validate_stage1_struct.py \
    --base_dir . \
    --run_tag S0_QA_20251220
```

#### 3. Allocation 생성
```bash
for arm in A B C D E F; do
  python3 3_Code/src/tools/allocation/s0_allocation.py \
    --base_dir . \
    --run_tag S0_QA_20251220 \
    --arm $arm
done
```

#### 4. S2만 실행
```bash
python3 3_Code/src/tools/qa/run_s0_qa_6arm.py \
    --base_dir . \
    --run_tag S0_QA_20251220 \
    --seed 42 \
    --skip_s1 --skip_s1_gate --skip_allocation
```

### 출력 파일

- `2_Data/metadata/generated/S0_QA_20251220/selected_18_groups.json` - 선택된 18개 그룹
- `2_Data/metadata/generated/S0_QA_20251220/stage1_struct__arm{A-F}.jsonl` - S1 출력
- `2_Data/metadata/generated/S0_QA_20251220/s2_results__arm{A-F}.jsonl` - S2 출력 (legacy format, S0 QA에서는 S1과 S2가 같은 arm 사용)
- `2_Data/metadata/generated/S0_QA_20251220/allocation/` - Allocation artifacts
- **Note (2025-12-23):** 새로운 형식 `s2_results__s1arm{S1_ARM}__s2arm{S2_ARM}.jsonl`도 지원되지만, S0 QA에서는 일반적으로 S1과 S2가 같은 arm을 사용하므로 legacy 형식이 사용됨

### 검증

```bash
# S1 출력 확인
ls -lh 2_Data/metadata/generated/S0_QA_20251220/stage1_struct__arm*.jsonl

# S2 출력 확인
ls -lh 2_Data/metadata/generated/S0_QA_20251220/s2_results__arm*.jsonl

# 각 arm별 레코드 수 확인
for arm in A B C D E F; do
  echo "Arm $arm:"
  wc -l 2_Data/metadata/generated/S0_QA_20251220/stage1_struct__arm${arm}.jsonl
  wc -l 2_Data/metadata/generated/S0_QA_20251220/s2_results__arm${arm}.jsonl
done
```

**예상 결과:**
- S1: 각 arm당 18개 레코드 (18 groups)
- S2: 각 arm당 약 216개 레코드 (18 groups × 12 cards)

---

## Phase 2: Group ID 업데이트

### 목적
- `assignment_map.csv`의 placeholder group_id (`group_01` ~ `group_18`)를 실제 group_id (`G0123` 등)로 업데이트
- S1 출력에서 실제 group_id 추출 및 매핑

### 자동 업데이트 (distribute_qa_packets.py에서 자동 수행)

`distribute_qa_packets.py` 실행 시 자동으로 업데이트됩니다.

### 수동 업데이트 (필요 시)

```bash
python3 3_Code/src/tools/qa/distribute_qa_packets.py \
    --base_dir . \
    --run_tag S0_QA_20251220 \
    --skip_pdf --skip_organize --skip_zip --skip_email
```

이 명령어는 `assignment_map.csv`를 업데이트하고 `assignment_map_updated.csv`를 생성합니다.

### 검증

```bash
# 업데이트된 assignment_map 확인
head -20 0_Protocol/06_QA_and_Study/QA_Operations/assignment_map_updated.csv

# Placeholder가 실제 group_id로 변경되었는지 확인
grep "group_01" 0_Protocol/06_QA_and_Study/QA_Operations/assignment_map_updated.csv
# 결과가 없어야 함 (모두 실제 group_id로 변경됨)
```

---

## Phase 3: S3 실행 (이미지 스펙 생성)

### 목적
- 이미지 정책 해석 및 이미지 스펙 컴파일
- 이미지 생성은 하지 않음 (스펙만 생성)

### 실행 명령어

```bash
for arm in A B C D E F; do
  python3 3_Code/src/03_s3_policy_resolver.py \
    --base_dir . \
    --run_tag S0_QA_20251220 \
    --arm $arm
done
```

### 출력 파일

- `2_Data/metadata/generated/S0_QA_20251220/image_policy_manifest__arm{A-F}.jsonl`
- `2_Data/metadata/generated/S0_QA_20251220/s3_image_spec__arm{A-F}.jsonl`

### 검증

```bash
# S3 출력 확인
ls -lh 2_Data/metadata/generated/S0_QA_20251220/image_policy_manifest__arm*.jsonl
ls -lh 2_Data/metadata/generated/S0_QA_20251220/s3_image_spec__arm*.jsonl

# 레코드 수 확인
for arm in A B C D E F; do
  echo "Arm $arm:"
  wc -l 2_Data/metadata/generated/S0_QA_20251220/image_policy_manifest__arm${arm}.jsonl
  wc -l 2_Data/metadata/generated/S0_QA_20251220/s3_image_spec__arm${arm}.jsonl
done
```

---

## Phase 4: S4 실행 (이미지 생성)

### 목적
- S3 스펙 기반으로 이미지 생성
- 모든 카드 및 테이블 이미지 생성

### 실행 명령어

```bash
for arm in A B C D E F; do
  python3 3_Code/src/04_s4_image_generator.py \
    --base_dir . \
    --run_tag S0_QA_20251220 \
    --arm $arm
done
```

### 출력 파일

- `2_Data/metadata/generated/S0_QA_20251220/images/IMG__*.png` - 이미지 파일들
- `2_Data/metadata/generated/S0_QA_20251220/s4_image_manifest__arm{A-F}.jsonl` - 이미지 매핑 정보

### 검증

```bash
# 이미지 파일 확인
ls -lh 2_Data/metadata/generated/S0_QA_20251220/images/ | head -20

# 이미지 개수 확인
find 2_Data/metadata/generated/S0_QA_20251220/images/ -name "IMG__*.png" | wc -l

# S4 manifest 확인
ls -lh 2_Data/metadata/generated/S0_QA_20251220/s4_image_manifest__arm*.jsonl
```

**예상 결과:**
- 각 arm당 약 216개 이미지 (18 groups × 12 cards)
- 총 약 1,296개 이미지 (6 arms × 216)

---

## Phase 5: PDF 생성 및 배포

### 목적
- 108개 set별 PDF 생성 (blinded mode, surrogate ID 사용)
- Reviewer별로 Q01~Q12 PDF 폴더 구성
- Reviewer별 zip 파일 생성
- 이메일 발송

### 전체 실행 (권장)

```bash
python3 3_Code/src/tools/qa/distribute_qa_packets.py \
    --base_dir . \
    --run_tag S0_QA_20251220 \
    --smtp_server smtp.gmail.com \
    --smtp_port 587 \
    --smtp_user your_email@gmail.com \
    --smtp_password your_app_password \
    --from_email your_email@gmail.com
```

### 단계별 실행

#### 1. PDF만 생성 (테스트)

```bash
python3 3_Code/src/tools/qa/distribute_qa_packets.py \
    --base_dir . \
    --run_tag S0_QA_20251220 \
    --skip_organize --skip_zip --skip_email \
    --dry_run
```

#### 2. PDF 생성 (실제)

```bash
python3 3_Code/src/tools/qa/distribute_qa_packets.py \
    --base_dir . \
    --run_tag S0_QA_20251220 \
    --skip_organize --skip_zip --skip_email
```

#### 3. PDF 생성 + 폴더 구성

```bash
python3 3_Code/src/tools/qa/distribute_qa_packets.py \
    --base_dir . \
    --run_tag S0_QA_20251220 \
    --skip_zip --skip_email
```

#### 4. 압축까지

```bash
python3 3_Code/src/tools/qa/distribute_qa_packets.py \
    --base_dir . \
    --run_tag S0_QA_20251220 \
    --skip_email
```

#### 5. 이메일 발송

```bash
python3 3_Code/src/tools/qa/distribute_qa_packets.py \
    --base_dir . \
    --run_tag S0_QA_20251220 \
    --skip_pdf --skip_organize --skip_zip \
    --smtp_server smtp.gmail.com \
    --smtp_port 587 \
    --smtp_user your_email@gmail.com \
    --smtp_password your_app_password \
    --from_email your_email@gmail.com
```

### 출력 구조

```
6_Distributions/QA_Packets/
├── SET_001.pdf, SET_002.pdf, ... (108개 PDF)
├── by_reviewer/
│   ├── rev_001/
│   │   ├── Q01.pdf
│   │   ├── Q02.pdf
│   │   └── ... (Q12.pdf)
│   ├── rev_002/
│   │   └── ...
│   └── ... (18개 reviewer)
└── zip/
    ├── rev_001_QA_Packets.zip
    ├── rev_002_QA_Packets.zip
    └── ... (18개 zip)
```

### 검증

```bash
# PDF 개수 확인
ls -1 6_Distributions/QA_Packets/SET_*.pdf | wc -l
# 예상: 108개

# Reviewer별 폴더 확인
ls -d 6_Distributions/QA_Packets/by_reviewer/rev_* | wc -l
# 예상: 18개

# 각 reviewer의 PDF 개수 확인
for rev in rev_001 rev_002 rev_003; do
  echo "$rev: $(ls -1 6_Distributions/QA_Packets/by_reviewer/$rev/*.pdf | wc -l) PDFs"
done
# 예상: 각 12개

# Zip 파일 확인
ls -lh 6_Distributions/QA_Packets/zip/*.zip
# 예상: 18개 zip 파일
```

---

## 전체 워크플로우 요약

### 빠른 실행 (전체 자동화)

```bash
# 1. S0 실행 (S1/S2)
python3 3_Code/src/tools/qa/run_s0_qa_6arm.py \
    --base_dir . \
    --run_tag S0_QA_20251220 \
    --seed 42

# 2. S3 실행
for arm in A B C D E F; do
  python3 3_Code/src/03_s3_policy_resolver.py \
    --base_dir . \
    --run_tag S0_QA_20251220 \
    --arm $arm
done

# 3. S4 실행
for arm in A B C D E F; do
  python3 3_Code/src/04_s4_image_generator.py \
    --base_dir . \
    --run_tag S0_QA_20251220 \
    --arm $arm
done

# 4. PDF 생성 및 배포
python3 3_Code/src/tools/qa/distribute_qa_packets.py \
    --base_dir . \
    --run_tag S0_QA_20251220 \
    --smtp_server smtp.gmail.com \
    --smtp_port 587 \
    --smtp_user your_email@gmail.com \
    --smtp_password your_app_password \
    --from_email your_email@gmail.com
```

### 단계별 체크리스트

- [ ] Phase 1: S0 실행 (S1/S2) 완료
  - [ ] 18개 그룹 선택 확인
  - [ ] S1 출력 확인 (각 arm당 18개)
  - [ ] S1 Gate 통과
  - [ ] Allocation 생성 완료
  - [ ] S2 출력 확인 (각 arm당 약 216개)
- [ ] Phase 2: Group ID 업데이트 완료
  - [ ] assignment_map_updated.csv 생성 확인
- [ ] Phase 3: S3 실행 완료
  - [ ] image_policy_manifest 생성 확인
  - [ ] s3_image_spec 생성 확인
- [ ] Phase 4: S4 실행 완료
  - [ ] 이미지 파일 생성 확인
  - [ ] s4_image_manifest 생성 확인
- [ ] Phase 5: PDF 생성 및 배포 완료
  - [ ] 108개 PDF 생성 확인
  - [ ] Reviewer별 폴더 구성 확인
  - [ ] 18개 zip 파일 생성 확인
  - [ ] 이메일 발송 완료

---

## 주의사항

### 1. 이미지 없이 PDF 생성

S4 실행 전에 **미리보기/디버그용** PDF를 생성하려면 `--allow_missing_images` 옵션이 필요합니다. `distribute_qa_packets.py`는 운영상(초기/부분 산출물) 이 옵션을 기본 사용합니다.

**정책:** 최종 QA 배포용 PDF는 **S4 완료 후** `--allow_missing_images` 없이 생성해야 합니다. 콘텐츠 품질 판정/게이트는 PDF 생성기가 아니라 **Option C(S5 triage → S6 export gate)** 에서 수행합니다.

### 2. 이메일 발송 설정

Gmail 사용 시:
1. Google 계정에서 "2단계 인증" 활성화
2. "앱 비밀번호" 생성
3. 생성된 앱 비밀번호를 `--smtp_password`에 사용

### 3. Run Tag 일관성

모든 단계에서 동일한 `--run_tag`를 사용해야 합니다.

### 4. 파일 경로

- `assignment_map.csv`: `0_Protocol/06_QA_and_Study/QA_Operations/assignment_map.csv`
- `surrogate_map.csv`: `0_Protocol/06_QA_and_Study/QA_Operations/surrogate_map.csv`
- `reviewer_master.csv`: `1_Secure_Participant_Info/reviewer_master.csv`

---

## 문제 해결

### S1 실행 실패

```bash
# 개별 arm 테스트
python3 3_Code/src/tools/qa/run_s0_qa_6arm.py \
    --base_dir . \
    --run_tag S0_QA_20251220 \
    --seed 42 \
    --arms A
```

### PDF 생성 실패

```bash
# 개별 set PDF 생성 테스트
python3 3_Code/src/07_build_set_pdf.py \
    --base_dir . \
    --run_tag S0_QA_20251220 \
    --arm A \
    --group_id G0123 \
    --out_dir 6_Distributions/QA_Packets \
    --blinded \
    --set_surrogate_csv 0_Protocol/06_QA_and_Study/QA_Operations/surrogate_map.csv \
    --allow_missing_images
```

### 이메일 발송 실패

```bash
# Dry-run으로 테스트
python3 3_Code/src/tools/qa/distribute_qa_packets.py \
    --base_dir . \
    --run_tag S0_QA_20251220 \
    --skip_pdf --skip_organize --skip_zip \
    --dry_run
```

---

## 참고 문서

- `QA_Mapping_Progress_Summary.md` - QA Mapping 진행사항
- `S0_Execution_Plan_Without_S4.md` - S0 실행 계획
- `PDF_Packet_Builder_README.md` - PDF 생성 가이드
- `Google_Form_Design_Specification.md` - Google Form 설계

---

**작성일:** 2025-12-20  
**최종 업데이트:** 2025-12-20

