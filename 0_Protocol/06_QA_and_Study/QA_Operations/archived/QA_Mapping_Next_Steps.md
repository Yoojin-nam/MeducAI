# QA Mapping 다음 단계 가이드

**Date:** 2025-12-20  
**Status:** Ready for S0 Execution  
**Purpose:** QA Mapping 완료 후 다음 단계 안내

---

## ✅ 완료된 작업

1. ✅ `reviewer_master.csv` 생성 (18명 리뷰어 정보)
2. ✅ `assignment_map.csv` 생성 (108 sets 배정)
3. ✅ `surrogate_map.csv` 생성 (블라인딩용 surrogate ID)
4. ✅ Institution de-correlation 검증 및 재배정 완료
5. ✅ 배정 검증 완료

---

## 다음 단계

### Step 1: S0 실행 (S1/S2)

**목적:** 108 sets 생성 및 실제 group_id 확정

**작업:**
```bash
# S1 실행 (모든 arm)
for arm in A B C D E F; do
  python3 3_Code/src/01_generate_json.py \
    --base_dir . \
    --run_tag S0_QA_20251220 \
    --arm $arm \
    --mode S0 \
    --stage 1
done

# S1 Gate 검증
python3 3_Code/src/validate_stage1_struct.py \
  --base_dir . \
  --run_tag S0_QA_20251220

# Allocation 생성
for arm in A B C D E F; do
  python3 3_Code/src/tools/allocation/s0_allocation.py \
    --base_dir . \
    --run_tag S0_QA_20251220 \
    --arm $arm
done

# S2 실행 (모든 arm)
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
- `stage1_struct__arm{A-F}.jsonl` (실제 group_id 포함)
- `s2_results__arm{A-F}.jsonl`

---

### Step 2: Group ID 업데이트

**목적:** `assignment_map.csv`의 placeholder group_id를 실제 ID로 업데이트

**작업:**
1. S1 출력에서 실제 group_id 추출
2. `assignment_map.csv`의 `group_01` ~ `group_18`을 실제 ID로 매핑
3. 검증 스크립트 실행

**스크립트 예시:**
```python
# update_group_ids.py
import csv
import json

# S1 출력에서 실제 group_id 추출
actual_group_ids = []
for arm in ['A', 'B', 'C', 'D', 'E', 'F']:
    with open(f'2_Data/metadata/generated/S0_QA_20251220/stage1_struct__arm{arm}.jsonl', 'r') as f:
        for line in f:
            record = json.loads(line)
            if record['group_id'] not in actual_group_ids:
                actual_group_ids.append(record['group_id'])

# Placeholder와 실제 ID 매핑 (순서대로)
group_mapping = {
    f'group_{i:02d}': actual_group_ids[i-1] 
    for i in range(1, 19)
}

# assignment_map.csv 업데이트
assignments = []
with open('0_Protocol/06_QA_and_Study/QA_Operations/assignment_map.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        old_group_id = row['group_id']
        new_group_id = group_mapping.get(old_group_id, old_group_id)
        row['group_id'] = new_group_id
        row['set_id'] = f"set_{new_group_id}_{row['arm_id']}"
        assignments.append(row)

# 저장
with open('0_Protocol/06_QA_and_Study/QA_Operations/assignment_map.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['reviewer_id', 'local_qid', 'set_id', 'group_id', 'arm_id', 'role'])
    writer.writeheader()
    writer.writerows(assignments)
```

---

### Step 3: Subspecialty 검증

**목적:** Subspecialty de-correlation 검증

**작업:**
1. 실제 group_id와 subspecialty 매칭
2. 각 리뷰어의 주 subspecialty와 배정된 group의 subspecialty 비교
3. 위반 사항 확인 및 필요 시 재배정

**검증 스크립트:**
```python
# verify_subspecialty.py
import csv

# reviewer_master.csv에서 subspecialty 정보 읽기
reviewer_specialty = {}
with open('1_Secure_Participant_Info/reviewer_master.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['subspecialty']:
            reviewer_specialty[row['reviewer_id']] = row['subspecialty']

# group_id와 subspecialty 매핑 (groups_canonical.csv 또는 EDA 데이터에서)
group_specialty = {}  # 실제 데이터로 채워야 함

# assignment_map.csv 읽기
assignments = []
with open('0_Protocol/06_QA_and_Study/QA_Operations/assignment_map.csv', 'r') as f:
    reader = csv.DictReader(f)
    assignments = list(reader)

# 검증
violations = []
for a in assignments:
    reviewer_id = a['reviewer_id']
    group_id = a['group_id']
    
    if reviewer_id in reviewer_specialty and group_id in group_specialty:
        reviewer_spec = reviewer_specialty[reviewer_id]
        group_spec = group_specialty[group_id]
        
        # 주 subspecialty와 group의 subspecialty가 일치하는지 확인
        if reviewer_spec == group_spec:
            violations.append((reviewer_id, group_id, reviewer_spec))

if violations:
    print(f"⚠️  Subspecialty de-correlation 위반: {len(violations)}건")
    # 재배정 고려
else:
    print("✅ Subspecialty de-correlation: 정상")
```

---

### Step 4: S3 실행 (이미지 스펙 생성)

**목적:** 이미지 정책 해석 및 이미지 스펙 컴파일

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

---

### Step 5: S4 실행 (이미지 생성) - 나중에

**목적:** 이미지 생성 (S4 API 문제 해결 후)

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

---

### Step 6: PDF 생성 및 배포 준비

**목적:** QA 평가용 PDF 생성 및 배포

**작업:**
1. PDF 생성 (이미지 포함 또는 `--allow_missing_images`)
2. Google Drive 폴더 생성
3. Google Form 생성
4. 이메일 발송

**상세 가이드:**
- `Google_Form_Design_Specification.md` 참조

---

## 체크리스트

### Phase 1: S0 실행
- [ ] S1 실행 (6 arms)
- [ ] S1 Gate 검증
- [ ] Allocation 생성
- [ ] S2 실행 (6 arms)
- [ ] 실제 group_id 확인

### Phase 2: 배정 업데이트
- [ ] Group ID 업데이트 스크립트 실행
- [ ] assignment_map.csv 업데이트
- [ ] Subspecialty 검증
- [ ] 필요 시 재배정

### Phase 3: S3/S4 실행
- [ ] S3 실행 (이미지 스펙 생성)
- [ ] S4 실행 (이미지 생성, API 문제 해결 후)

### Phase 4: 배포 준비
- [ ] PDF 생성
- [ ] Google Drive 폴더 생성
- [ ] Google Form 생성
- [ ] 이메일 발송

---

## 참고 문서

- `QA_Mapping_Design.md`: 배정 설계 문서
- `QA_Assignment_Summary.md`: 배정 요약
- `S0_Execution_Plan_Without_S4.md`: S0 실행 계획
- `Google_Form_Design_Specification.md`: Google Form 설계

---

**Status:** ✅ QA Mapping 완료, S0 실행 준비 완료

