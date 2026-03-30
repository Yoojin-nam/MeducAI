# QA Assignment Summary

**Date:** 2025-12-20  
**Status:** Initial Assignment Complete  
**Purpose:** S0 QA 배정 요약 및 다음 단계 가이드

---

## 배정 완료 현황

### 생성된 파일

1. ✅ `reviewer_master.csv`
   - 위치: `1_Secure_Participant_Info/reviewer_master.csv`
   - 리뷰어: 총 18명 (Residents 9명, Attendings 9명)
   - **업데이트:** [Study Coordinator](rev_010)을 전문의로 재분류

2. ✅ `assignment_map.csv`
   - 위치: `0_Protocol/06_QA_and_Study/QA_Operations/assignment_map.csv`
   - 배정 기록: 216개 (108 sets × 2 reviewers)

3. ✅ `surrogate_map.csv`
   - 위치: `0_Protocol/06_QA_and_Study/QA_Operations/surrogate_map.csv`
   - Surrogate 매핑: 108개

---

## 배정 통계

### 리뷰어별 배정

**Residents (9명):**
- 평균: 12.0 sets/인
- 범위: 12 sets/인 (균등 배정)
- Local QID: Q01~Q12

**Attendings (8명, [Study Coordinator] 제외):**
- 평균: 13.5 sets/인
- 범위: 6–15 sets/인
- Local QID: Q01~Q15 (또는 Q01~Q12)
- **참고:** [Study Coordinator](rev_010)은 전문의로 분류되었으나 배정에서 제외됨 (다른 전문의에게 재배정 완료)

### 배정 검증 결과

- ✅ **Set별 배정:** 모든 Set에 정확히 2명 배정됨 (1 Resident + 1 Attending)
- ✅ **Local QID:** 모든 리뷰어의 QID가 Q01부터 순차적으로 할당됨
- ✅ **총 Sets:** 108개 (18 groups × 6 arms)
- ✅ **Institution De-correlation:** 정상 (모든 Set에서 동일 기관 reviewer 없음)

---

## 주의사항

### 1. Group ID Placeholder

**현재 상태:**
- `assignment_map.csv`의 `group_id`는 placeholder (`group_01` ~ `group_18`)
- 실제 group_id는 S0 실행 시 확정됨

**다음 단계:**
- S0 실행 후 실제 group_id로 업데이트 필요

### 2. Institution/Subspecialty 검증

**검증 완료:**
- ✅ **Institution de-correlation:** 정상 (모든 Set에서 동일 기관 reviewer 없음)
- ⚠️ **Subspecialty de-correlation:** 실제 group_id 확정 후 검증 필요

**검증 방법:**
- `reviewer_master.csv`의 institution/subspecialty 정보 활용
- 배정 스크립트로 자동 검증 완료

---

## 다음 단계

### Phase 1: S0 실행 및 Group ID 업데이트

1. **S0 실행**
   - S1/S2로 108 sets 생성
   - 실제 group_id 확정

2. **Group ID 업데이트**
   - `assignment_map.csv`의 placeholder group_id를 실제 ID로 업데이트
   - 검증 스크립트 실행

### Phase 2: 배정 검증 및 최적화

1. **Institution/Subspecialty 검증**
   - 자동 검증 스크립트 실행
   - 위반 사항 확인

2. **필요 시 재배정**
   - 위반 사항이 있으면 재배정
   - 재배정 후 재검증

### Phase 3: 배포 준비

1. **Google Drive 폴더 생성**
   - 평가자별 개인 폴더 생성
   - Q01~Q12 PDF 파일 업로드

2. **Google Form 생성**
   - Section 1: 평가자 정보
   - Section 2~13: Q01~Q12 평가

3. **배포**
   - 이메일 발송 (Drive 링크 + Form 링크)
   - 평가 가이드 포함

---

## 검증 스크립트

배정 검증을 위한 Python 스크립트:

```python
# verify_assignment.py
import csv
from collections import defaultdict

# reviewer_master.csv 읽기
reviewer_master = {}
with open('1_Secure_Participant_Info/reviewer_master.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        reviewer_master[row['reviewer_id']] = row

# assignment_map.csv 읽기
assignments = []
with open('0_Protocol/06_QA_and_Study/QA_Operations/assignment_map.csv', 'r') as f:
    reader = csv.DictReader(f)
    assignments = list(reader)

# Institution de-correlation 검증
set_institutions = defaultdict(set)
for a in assignments:
    reviewer_id = a['reviewer_id']
    set_key = (a['group_id'], a['arm_id'])
    institution = reviewer_master.get(reviewer_id, {}).get('institution', '')
    if institution:
        set_institutions[set_key].add(institution)

violations = []
for set_key, institutions in set_institutions.items():
    if len(institutions) < 2:  # 동일 기관 reviewer 2인 이상
        violations.append(set_key)

if violations:
    print(f"⚠️  Institution de-correlation 위반: {len(violations)}개 Set")
else:
    print("✅ Institution de-correlation: 정상")
```

---

## 참고 문서

- `QA_Mapping_Design.md`: 배정 설계 문서
- `QA_Assignment_Plan.md`: 배정 원칙 및 규칙
- `Google_Form_Design_Specification.md`: Google Form 설계 명세

---

**Status:** ✅ 배정 완료, 다음 단계 대기 중

