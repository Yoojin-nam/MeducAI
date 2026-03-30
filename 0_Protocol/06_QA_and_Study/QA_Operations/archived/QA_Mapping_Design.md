# QA Mapping 설계 및 실행 가이드

**Date:** 2025-12-20  
**Status:** Design Document  
**Purpose:** S0 QA를 위한 평가자 배정 및 매핑 설계

---

## Executive Summary

**권장 방식:**
1. ✅ **리뷰어 이름은 나중에 매칭** (privacy, blinding 유지)
2. ✅ **전공의/전문의는 `role` 필드로 구분** (resident/attending)
3. ✅ **Pseudonymized ID 사용** (reviewer_id)
4. ✅ **실제 이름-이메일 매핑은 별도 파일로 관리**

---

## 1. 리뷰어 정보 관리 방식

### 1.1 두 가지 접근 방식 비교

#### 옵션 A: 지금 이름 제공

**장점:**
- ✅ 배정 알고리즘에 subspecialty, institution 정보 활용 가능
- ✅ 초기 설계 단계에서 제약 조건 반영 용이

**단점:**
- ⚠️ Privacy 문제 (이름이 코드베이스에 저장됨)
- ⚠️ Blinding 유지 어려움 (이름 노출 가능성)
- ⚠️ 리뷰어 변경 시 재작업 필요

#### 옵션 B: 나중에 매칭 (권장) ⭐

**장점:**
- ✅ **Privacy 보호** (이름이 코드베이스에 저장되지 않음)
- ✅ **Blinding 유지 용이** (pseudonymized ID만 사용)
- ✅ **유연성** (리뷰어 변경 시 재작업 최소화)
- ✅ **보안** (실제 이름과 배정 정보 분리)

**단점:**
- ⚠️ 배정 알고리즘에 subspecialty/institution 정보 활용 어려움
- ⚠️ 나중에 매칭 작업 필요

**권장: 옵션 B (나중에 매칭)**

---

## 2. 전공의/전문의 구분 방법

### 2.1 Role 필드 사용

**구조:**
- `role`: `resident` 또는 `attending`
- `reviewer_id`: pseudonymized ID (예: `rev_001`, `rev_002`)

**예시:**
```csv
reviewer_id,role
rev_001,resident
rev_002,attending
rev_003,resident
...
```

### 2.2 배정 규칙

**S0 QA 배정 규칙 (QA Framework v2.0):**
- **Per set:** 1 Resident + 1 Attending (paired cross-evaluation)
- **Total sets:** 108 sets (18 groups × 6 arms)
- **Workload:** 1인당 약 12–15 sets

**필요한 리뷰어 수:**
- **Residents:** 약 7–9명 (108 sets ÷ 12–15 sets per person)
- **Attendings:** 약 7–9명 (108 sets ÷ 12–15 sets per person)

---

## 3. 데이터 구조 설계

### 3.1 파일 구조

#### 파일 1: `reviewer_master.csv` (나중에 생성)

**목적:** 실제 이름-이메일-role 매핑 (QA 운영자만 접근)

**컬럼:**
- `reviewer_id`: pseudonymized ID
- `reviewer_name`: 실제 이름 (선택적, privacy 고려)
- `reviewer_email`: 이메일 주소
- `role`: `resident` 또는 `attending`
- `institution`: 기관명 (선택적)
- `subspecialty`: 전문 분야 (선택적)

**예시:**
```csv
reviewer_id,reviewer_name,reviewer_email,role,institution,subspecialty
rev_001,Reviewer_11,reviewer1@example.com,resident,Asan Medical Center,
rev_002,Reviewer_04,reviewer2@example.com,attending,Samsung Changwon Hospital,Musculoskeletal
...
```

**보안:**
- ⚠️ **QA 운영자만 접근 가능**
- ⚠️ **Git에 커밋하지 않음** (`.gitignore`에 추가)
- ⚠️ **평가자에게 절대 공유하지 않음**

**참고:** `reviewer_master.csv` 파일이 생성되었습니다 (2025-12-20).
- 위치: `1_Secure_Participant_Info/reviewer_master.csv` (개인정보 보호를 위해 보안 디렉토리에 저장)
- Residents: rev_001 ~ rev_010 (10명)
- Attendings: rev_011 ~ rev_018 (8명)

---

#### 파일 2: `assignment_map.csv` (지금 생성)

**목적:** 평가자별 Set 배정 매핑 (통계분석용)

**컬럼:**
- `reviewer_id`: pseudonymized ID
- `local_qid`: Q01~Q12 (평가자별 로컬 Q 번호)
- `set_id`: 실제 Set 식별자
- `group_id`: Group ID
- `arm_id`: Arm ID (A-F)
- `role`: `resident` 또는 `attending` (선택적, 중복 정보)

**예시:**
```csv
reviewer_id,local_qid,set_id,group_id,arm_id,role
rev_001,Q01,set_045,group_12,A,resident
rev_001,Q02,set_012,group_05,B,resident
rev_001,Q03,set_089,group_18,C,resident
...
rev_001,Q12,set_067,group_03,F,resident
rev_002,Q01,set_012,group_05,B,attending
rev_002,Q02,set_045,group_12,A,attending
...
```

**특징:**
- ✅ **실제 이름 없음** (privacy 보호)
- ✅ **Git에 커밋 가능** (pseudonymized ID만 포함)
- ✅ **통계분석에 사용**

---

#### 파일 3: `surrogate_map.csv` (지금 생성)

**목적:** 블라인딩을 위한 Set surrogate ID 매핑

**컬럼:**
- `group_id`: Group ID
- `arm`: Arm ID (A-F)
- `surrogate_set_id`: 블라인딩용 surrogate ID

**예시:**
```csv
group_id,arm,surrogate_set_id
group_12,A,SET_001
group_12,B,SET_002
group_12,C,SET_003
...
```

---

### 3.2 데이터 흐름

```
1. assignment_map.csv 생성 (지금)
   - reviewer_id, local_qid, set_id, group_id, arm_id, role
   - 실제 이름 없음

2. reviewer_master.csv 생성 (나중에)
   - reviewer_id, reviewer_name, reviewer_email, role, institution, subspecialty
   - 실제 이름-이메일 매핑

3. 배포 시 조인
   - assignment_map.csv + reviewer_master.csv → 배포용 매핑
   - reviewer_email로 Google Drive 폴더 생성
   - reviewer_email로 Google Form 링크 전송
```

---

## 4. 배정 알고리즘 설계

### 4.1 기본 원칙

**S0 QA 배정 규칙 (QA Framework v2.0):**
1. **Per set:** 1 Resident + 1 Attending
2. **Total sets:** 108 sets
3. **Workload:** 1인당 약 12–15 sets

### 4.2 제약 조건

**QA Assignment Plan v2.0에 따른 제약:**

1. **Subspecialty De-correlation**
   - 가능하면 본인 주 subspecialty group은 배정 제외
   - ⚠️ **나중에 매칭 방식에서는 이 제약 적용 어려움**
   - 대안: 배정 후 검증 단계에서 확인

2. **Institution De-correlation**
   - 동일 Set에 동일 기관 reviewer 2인 이상 배정 금지
   - ⚠️ **나중에 매칭 방식에서는 이 제약 적용 어려움**
   - 대안: 배정 후 검증 단계에서 확인

### 4.3 배정 알고리즘 (간단 버전)

**단계 1: 리뷰어 풀 생성**
```python
# Resident 풀
residents = [f"rev_{i:03d}" for i in range(1, 10)]  # rev_001 ~ rev_009

# Attending 풀
attendings = [f"rev_{i:03d}" for i in range(10, 20)]  # rev_010 ~ rev_019
```

**단계 2: Set 배정**
```python
# 108 sets 순회
for set_idx, (group_id, arm_id) in enumerate(all_sets):
    # Round-robin 방식으로 배정
    resident = residents[set_idx % len(residents)]
    attending = attendings[set_idx % len(attendings)]
    
    # assignment_map.csv에 기록
    # local_qid는 각 리뷰어별로 Q01~Q12 순서대로 부여
```

**단계 3: Local QID 할당**
```python
# 각 리뷰어별로 배정된 Set을 Q01~Q12로 매핑
for reviewer_id in all_reviewers:
    assigned_sets = get_assigned_sets(reviewer_id)
    for idx, set_info in enumerate(assigned_sets, 1):
        local_qid = f"Q{idx:02d}"  # Q01, Q02, ..., Q12
```

---

## 5. 실행 계획

### 5.1 Phase 1: 지금 할 작업

**목적:** 배정 알고리즘 실행 및 매핑 파일 생성

**작업:**
1. ✅ 리뷰어 풀 생성 (pseudonymized ID만)
   - Residents: rev_001 ~ rev_009 (예상 9명)
   - Attendings: rev_010 ~ rev_019 (예상 9명)
2. ✅ 배정 알고리즘 실행
   - 108 sets에 대해 1 Resident + 1 Attending 배정
   - Round-robin 또는 랜덤 배정
3. ✅ `assignment_map.csv` 생성
   - reviewer_id, local_qid, set_id, group_id, arm_id, role
4. ✅ `surrogate_map.csv` 생성
   - group_id, arm, surrogate_set_id

**출력:**
- `assignment_map.csv` (Git에 커밋 가능)
- `surrogate_map.csv` (Git에 커밋 가능)

---

### 5.2 Phase 2: 나중에 할 작업

**목적:** 실제 리뷰어 정보 매핑

**작업:**
1. ✅ 리뷰어 목록 수집
   - 이름, 이메일, role, institution, subspecialty
2. ✅ `reviewer_master.csv` 생성
   - reviewer_id와 실제 정보 매핑
3. ✅ 배정 검증
   - Subspecialty de-correlation 확인
   - Institution de-correlation 확인
   - 필요 시 재배정
4. ✅ 배포 준비
   - Google Drive 폴더 생성
   - 이메일 발송

**출력:**
- `reviewer_master.csv` (Git에 커밋하지 않음, `.gitignore`)

---

## 6. 권장 사항

### 6.1 리뷰어 이름 관리

**권장: 나중에 매칭**

**이유:**
1. ✅ **Privacy 보호** (이름이 코드베이스에 저장되지 않음)
2. ✅ **Blinding 유지** (pseudonymized ID만 사용)
3. ✅ **유연성** (리뷰어 변경 시 재작업 최소화)
4. ✅ **보안** (실제 이름과 배정 정보 분리)

**대안 (subspecialty/institution 정보 필요 시):**
- 리뷰어 이름 대신 **subspecialty/institution 정보만** 제공
- 예: `reviewer_specialty.csv` (reviewer_id, subspecialty, institution)
- 실제 이름은 나중에 매칭

---

### 6.2 전공의/전문의 구분

**권장: `role` 필드 사용**

**구조:**
- `role`: `resident` 또는 `attending`
- `reviewer_id`: pseudonymized ID

**배정 규칙:**
- S0 QA: Per set = 1 Resident + 1 Attending
- 총 108 sets → 약 7–9명씩 필요

---

## 7. 구현 예시

### 7.1 배정 스크립트 구조

```python
# assignment_generator.py

import csv
import random
from pathlib import Path

def generate_assignment_map():
    # 1. 리뷰어 풀 생성
    residents = [f"rev_{i:03d}" for i in range(1, 10)]
    attendings = [f"rev_{i:03d}" for i in range(10, 20)]
    
    # 2. 108 sets 생성 (18 groups × 6 arms)
    all_sets = []
    for group_id in [f"group_{i:02d}" for i in range(1, 19)]:
        for arm_id in ['A', 'B', 'C', 'D', 'E', 'F']:
            all_sets.append((group_id, arm_id))
    
    # 3. 배정 실행
    assignments = []
    reviewer_assignments = {r: [] for r in residents + attendings}
    
    for set_idx, (group_id, arm_id) in enumerate(all_sets):
        set_id = f"set_{group_id}_{arm_id}"
        
        # Round-robin 배정
        resident = residents[set_idx % len(residents)]
        attending = attendings[set_idx % len(attendings)]
        
        reviewer_assignments[resident].append((set_id, group_id, arm_id))
        reviewer_assignments[attending].append((set_id, group_id, arm_id))
    
    # 4. Local QID 할당
    assignment_map = []
    for reviewer_id, sets in reviewer_assignments.items():
        role = "resident" if reviewer_id.startswith("rev_00") else "attending"
        for idx, (set_id, group_id, arm_id) in enumerate(sets, 1):
            local_qid = f"Q{idx:02d}"
            assignment_map.append({
                'reviewer_id': reviewer_id,
                'local_qid': local_qid,
                'set_id': set_id,
                'group_id': group_id,
                'arm_id': arm_id,
                'role': role
            })
    
    # 5. CSV 저장
    with open('assignment_map.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['reviewer_id', 'local_qid', 'set_id', 'group_id', 'arm_id', 'role'])
        writer.writeheader()
        writer.writerows(assignment_map)

if __name__ == '__main__':
    generate_assignment_map()
```

---

## 8. 체크리스트

### Phase 1: 지금 할 작업
- [ ] 리뷰어 풀 생성 (pseudonymized ID만)
- [ ] 배정 알고리즘 설계
- [ ] `assignment_map.csv` 생성
- [ ] `surrogate_map.csv` 생성
- [ ] 데이터 검증 (각 리뷰어당 12개 Q 확인)

### Phase 2: 나중에 할 작업
- [ ] 리뷰어 목록 수집
- [ ] `reviewer_master.csv` 생성
- [ ] 배정 검증 (subspecialty/institution 제약 확인)
- [ ] 필요 시 재배정
- [ ] 배포 준비

---

## 결론

**권장 방식:**
1. ✅ **리뷰어 이름은 나중에 매칭** (privacy, blinding 유지)
2. ✅ **전공의/전문의는 `role` 필드로 구분** (resident/attending)
3. ✅ **지금은 pseudonymized ID만 사용하여 배정 진행**
4. ✅ **나중에 실제 이름-이메일 매핑 추가**

이 방식의 장점:
- Privacy 보호
- Blinding 유지
- 유연성 (리뷰어 변경 시 재작업 최소화)
- 보안 (실제 이름과 배정 정보 분리)

