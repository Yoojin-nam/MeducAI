# QA Mapping 진행사항 요약

**Date:** 2025-12-20  
**Status:** ✅ 완료  
**Purpose:** QA Mapping 작업 전체 진행사항 정리

---

## 📋 작업 개요

**목적:** S0 QA를 위한 평가자 배정 및 매핑 파일 생성  
**결과:** 완전 균등 배정 완료 (9명 × 12 sets = 108 sets)

---

## ✅ 완료된 작업

### 1. 리뷰어 정보 수집 및 분류

**작업:**
- 리뷰어 목록 수집 (전문의 9명, 전공의 9명)
- [Study Coordinator]을 전문의로 재분류 (초기 전공의로 잘못 분류됨)

**결과:**
- `reviewer_master.csv` 생성
  - 위치: `1_Secure_Participant_Info/reviewer_master.csv` (개인정보 보호)
  - 총 18명 리뷰어 정보
  - Residents: 9명 (rev_001 ~ rev_009)
  - Attendings: 9명 (rev_010 ~ rev_018, [Study Coordinator] 포함)

**리뷰어 구성:**

**전공의 (9명):**
1. rev_001: Reviewer_11 (서울아산병원)
2. rev_002: Reviewer_12 (경희대학교병원)
3. rev_003: Reviewer_05 (경희대학교병원)
4. rev_004: Reviewer_03 (강남세브란스병원)
5. rev_005: Reviewer_01 (서울아산병원)
6. rev_006: Reviewer_06 (강남세브란스병원)
7. rev_007: 주요한 (세브란스병원)
8. rev_008: Reviewer_02 (여의도성모병원)
9. rev_009: Reviewer_08 (고려대학교병원)

**전문의 (9명):**
1. rev_010: [Study Coordinator] (삼성창원병원) ⭐ 재분류 완료
2. rev_011: 윤순호 (National Jewish Health, 흉부영상)
3. rev_012: Reviewer_09 (서울대학교, 흉부영상)
4. rev_013: 이로운 (인하대, 근골격영상)
5. rev_014: Reviewer_04 (삼성창원병원, 근골격영상)
6. rev_015: Reviewer_13 (분당서울대학교병원, 비뇨생식기영상)
7. rev_016: 안태인 (동탄성심병원, 흉부영상)
8. rev_017: Reviewer_07 (서울아산병원, 복부영상)
9. rev_018: [PI] (삼성창원병원, 흉부영상)

---

### 2. 배정 알고리즘 설계 및 실행

**작업:**
- 배정 알고리즘 설계 (Institution de-correlation 제약 포함)
- 108 sets (18 groups × 6 arms) 배정
- 균등 분배 알고리즘 구현

**결과:**
- 완전 균등 배정 달성
  - Residents: 각 12 sets
  - Attendings: 각 12 sets ([Study Coordinator] 포함)

**배정 규칙:**
- Per set: 1 Resident + 1 Attending (paired cross-evaluation)
- Institution de-correlation: 동일 Set에 동일 기관 reviewer 2인 이상 배정 금지
- 균등 분배: 모든 리뷰어가 정확히 12 sets씩 배정

---

### 3. 매핑 파일 생성

**생성된 파일:**

#### 3.1 `reviewer_master.csv`
- **위치:** `1_Secure_Participant_Info/reviewer_master.csv`
- **내용:** 리뷰어 실제 정보 (이름, 이메일, role, institution, subspecialty)
- **보안:** Git에 커밋하지 않음 (개인정보 보호)

#### 3.2 `assignment_map.csv`
- **위치:** `0_Protocol/06_QA_and_Study/QA_Operations/assignment_map.csv`
- **내용:** 평가자별 Set 배정 매핑
- **컬럼:**
  - `reviewer_id`: pseudonymized ID
  - `local_qid`: Q01~Q12 (평가자별 로컬 Q 번호)
  - `set_id`: 실제 Set 식별자
  - `group_id`: Group ID (현재 placeholder: group_01 ~ group_18)
  - `arm_id`: Arm ID (A-F)
  - `role`: resident 또는 attending
- **총 기록:** 216개 (108 sets × 2 reviewers)

#### 3.3 `surrogate_map.csv`
- **위치:** `0_Protocol/06_QA_and_Study/QA_Operations/surrogate_map.csv`
- **내용:** 블라인딩을 위한 Set surrogate ID 매핑
- **컬럼:**
  - `group_id`: Group ID
  - `arm`: Arm ID (A-F)
  - `surrogate_set_id`: 블라인딩용 surrogate ID (SET_001 ~ SET_108)
- **총 기록:** 108개

---

### 4. 배정 검증 및 최적화

**검증 항목:**

1. ✅ **Set별 배정:** 모든 Set에 정확히 2명 배정됨 (1 Resident + 1 Attending)
2. ✅ **Local QID:** 모든 리뷰어의 QID가 Q01부터 순차적으로 할당됨
3. ✅ **Institution De-correlation:** 정상 (모든 Set에서 동일 기관 reviewer 없음)
4. ✅ **균등 분배:** 완전 균등 (모든 리뷰어가 정확히 12 sets씩)

**최적화 과정:**
- 초기 배정: Institution 위반 10개 Set 발견
- 재배정: Institution 제약을 고려한 재배정 알고리즘 적용
- 균등 분배: [Study Coordinator] 포함하여 모든 전문의가 12 sets씩 균등 배정

---

## 📊 최종 배정 통계

### Role별 배정

| Role | 리뷰어 수 | 총 배정 | 평균 sets/인 | 범위 |
|------|----------|---------|-------------|------|
| **Resident** | 9명 | 108 sets | 12.0 sets/인 | 12 sets (완전 균등) |
| **Attending** | 9명 | 108 sets | 12.0 sets/인 | 12 sets (완전 균등) |

### 리뷰어별 배정 상세

**Residents (각 12 sets):**
- rev_001 ~ rev_009: 각 12 sets
- Local QID: Q01~Q12

**Attendings (각 12 sets):**
- rev_010 ~ rev_018: 각 12 sets ([Study Coordinator] 포함)
- Local QID: Q01~Q12

---

## 🔍 주요 결정사항

### 1. 리뷰어 정보 관리 방식

**선택:** 나중에 매칭 방식

**이유:**
- ✅ Privacy 보호 (이름이 코드베이스에 저장되지 않음)
- ✅ Blinding 유지 (pseudonymized ID만 사용)
- ✅ 유연성 (리뷰어 변경 시 재작업 최소화)

**구현:**
- `reviewer_master.csv`: 실제 정보 (보안 디렉토리에 저장)
- `assignment_map.csv`: Pseudonymized ID만 포함 (Git 커밋 가능)

### 2. 전공의/전문의 구분

**방식:** `role` 필드 사용

**구조:**
- `role`: `resident` 또는 `attending`
- `reviewer_id`: pseudonymized ID (rev_001 ~ rev_018)

### 3. 균등 배정

**목표:** 모든 리뷰어가 정확히 12 sets씩 균등 배정

**결과:**
- ✅ 완전 균등 배정 달성
- ✅ 모든 리뷰어의 workload 균등
- ✅ 평가자 피로도 균등 분산

---

## 📁 생성된 파일 목록

### 보안 파일 (Git 커밋 안 함)

1. `1_Secure_Participant_Info/reviewer_master.csv`
   - 리뷰어 실제 정보 (이름, 이메일, institution, subspecialty)
   - 개인정보 포함

### 공개 파일 (Git 커밋 가능)

1. `0_Protocol/06_QA_and_Study/QA_Operations/assignment_map.csv`
   - 평가자별 Set 배정 매핑
   - Pseudonymized ID만 포함

2. `0_Protocol/06_QA_and_Study/QA_Operations/surrogate_map.csv`
   - 블라인딩용 surrogate ID 매핑

### 문서 파일

1. `QA_Mapping_Design.md` - 배정 설계 문서
2. `QA_Assignment_Summary.md` - 배정 요약
3. `QA_Assignment_Final_Report.md` - 최종 배정 리포트
4. `QA_Mapping_Next_Steps.md` - 다음 단계 가이드
5. `Google_Form_Design_Specification.md` - Google Form 설계 명세
6. `New_Google_Form_Design_Comparison.md` - 기존 QA와 비교 분석

---

## ✅ 검증 완료 항목

1. ✅ **배정 기본 구조:** 정상
   - 총 108 sets 모두 배정됨
   - 각 Set마다 1 Resident + 1 Attending

2. ✅ **균등 분배:** 완료
   - Residents: 각 12 sets
   - Attendings: 각 12 sets ([Study Coordinator] 포함)

3. ✅ **Institution De-correlation:** 정상
   - 모든 Set에서 동일 기관 reviewer 없음

4. ✅ **Local QID:** 정상
   - 모든 리뷰어의 QID가 Q01부터 순차적으로 할당됨

5. ✅ **[Study Coordinator] 재분류:** 완료
   - 전문의로 재분류
   - 12 sets 배정 완료

---

## ⚠️ 주의사항

### 1. Group ID Placeholder

**현재 상태:**
- `assignment_map.csv`의 `group_id`는 placeholder (`group_01` ~ `group_18`)
- 실제 group_id는 S0 실행 시 확정됨

**다음 단계:**
- S0 실행 후 실제 group_id로 업데이트 필요

### 2. Subspecialty 검증

**상태:** 아직 검증 안 됨

**이유:** 실제 group_id와 subspecialty 매칭이 필요

**다음 단계:**
- S0 실행 후 실제 group_id 확정
- Subspecialty de-correlation 검증
- 필요 시 재배정

---

## 🎯 다음 단계

### Phase 1: S0 실행 (S1/S2)

**목적:** 108 sets 생성 및 실제 group_id 확정

**작업:**
1. S1 실행 (6 arms)
2. S1 Gate 검증
3. Allocation 생성
4. S2 실행 (6 arms)

**출력:**
- `stage1_struct__arm{A-F}.jsonl` (실제 group_id 포함)
- `s2_results__arm{A-F}.jsonl`

### Phase 2: Group ID 업데이트

**목적:** `assignment_map.csv`의 placeholder를 실제 ID로 업데이트

**작업:**
1. S1 출력에서 실제 group_id 추출
2. Placeholder와 실제 ID 매핑
3. `assignment_map.csv` 업데이트
4. 검증

### Phase 3: Subspecialty 검증

**목적:** Subspecialty de-correlation 검증

**작업:**
1. 실제 group_id와 subspecialty 매칭
2. 각 리뷰어의 주 subspecialty와 배정된 group 비교
3. 위반 사항 확인 및 필요 시 재배정

### Phase 4: S3/S4 실행

**목적:** 이미지 스펙 생성 및 이미지 생성

**작업:**
1. S3 실행 (이미지 스펙 생성)
2. S4 실행 (이미지 생성, API 문제 해결 후)

### Phase 5: PDF 생성 및 배포

**목적:** QA 평가용 PDF 생성 및 배포

**작업:**
1. PDF 생성 (이미지 포함 또는 `--allow_missing_images`)
2. Google Drive 폴더 생성
3. Google Form 생성
4. 이메일 발송

---

## 📈 작업 타임라인

1. **QA Mapping 설계** ✅
   - 리뷰어 정보 관리 방식 결정
   - 배정 알고리즘 설계

2. **리뷰어 정보 수집** ✅
   - reviewer_master.csv 생성
   - [Study Coordinator] 재분류

3. **배정 실행** ✅
   - assignment_map.csv 생성
   - surrogate_map.csv 생성

4. **검증 및 최적화** ✅
   - Institution de-correlation 검증
   - 균등 배정 최적화

5. **최종 검증** ✅
   - 모든 검증 항목 통과
   - 완전 균등 배정 달성

---

## 🎉 완료 상태

**Status:** ✅ **QA Mapping 완료**

**완료된 작업:**
- ✅ 리뷰어 정보 수집 및 분류
- ✅ 배정 알고리즘 설계 및 실행
- ✅ 완전 균등 배정 (9명 × 12 sets)
- ✅ Institution de-correlation 검증
- ✅ 매핑 파일 생성

**준비 완료:**
- ✅ S0 실행 준비 완료
- ✅ 다음 단계 가이드 준비 완료

---

## 📚 참고 문서

- `QA_Mapping_Design.md`: 배정 설계 문서
- `QA_Assignment_Final_Report.md`: 최종 배정 리포트
- `QA_Mapping_Next_Steps.md`: 다음 단계 가이드
- `Google_Form_Design_Specification.md`: Google Form 설계 명세
- `S0_Execution_Plan_Without_S4.md`: S0 실행 계획

---

**작업 완료일:** 2025-12-20  
**다음 단계:** S0 실행 (S1/S2)

