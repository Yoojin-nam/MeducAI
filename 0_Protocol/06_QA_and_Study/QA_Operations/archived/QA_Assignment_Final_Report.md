# QA Assignment 최종 리포트

**Date:** 2025-12-20  
**Status:** ✅ 배정 완료  
**Purpose:** S0 QA 배정 최종 요약

---

## 배정 완료 현황

### 리뷰어 구성

**Residents (전공의): 9명**
- rev_001: Reviewer_11 (서울아산병원)
- rev_002: Reviewer_12 (경희대학교병원)
- rev_003: Reviewer_05 (경희대학교병원)
- rev_004: Reviewer_03 (강남세브란스병원)
- rev_005: Reviewer_01 (서울아산병원)
- rev_006: Reviewer_06 (강남세브란스병원)
- rev_007: 주요한 (세브란스병원)
- rev_008: Reviewer_02 (여의도성모병원)
- rev_009: Reviewer_08 (고려대학교병원)

**Attendings (전문의): 9명 (모두 균등 배정)**
- rev_010: 심용식 (삼성서울병원, 신경두경부영상) - 12 sets ✅
- rev_011: Reviewer_14 (National Jewish Health, 흉부영상) - 12 sets ✅
- rev_012: Reviewer_09 (서울대학교, 흉부영상) - 12 sets ✅
- rev_013: Reviewer_10 (삼성창원병원, 인터벤션) - 12 sets ✅
- rev_014: Reviewer_04 (삼성창원병원, 근골격영상) - 12 sets ✅
- rev_015: Reviewer_13 (분당서울대학교병원, 비뇨생식기영상) - 12 sets ✅
- rev_016: 안태인 (동탄성심병원, 흉부영상) - 12 sets ✅
- rev_017: Reviewer_07 (서울아산병원, 복부영상) - 12 sets ✅
- rev_018: [PI] (삼성창원병원, 흉부영상) - 12 sets ✅

---

## 배정 통계

### Role별 배정

| Role | 리뷰어 수 | 총 배정 | 평균 sets/인 | 범위 |
|------|----------|---------|-------------|------|
| **Resident** | 9명 | 108 sets | 12.0 sets/인 | 12 sets (균등) |
| **Attending** | 9명 | 108 sets | 12.0 sets/인 | 12 sets (균등) |

### 리뷰어별 배정 상세

**Residents (각 12 sets):**
- 모든 전공의가 정확히 12 sets씩 균등 배정
- Local QID: Q01~Q12

**Attendings (각 12 sets):**
- 모든 전문의가 정확히 12 sets씩 균등 배정
- [Study Coordinator](rev_010) 포함하여 9명 모두 균등 배정
- Local QID: Q01~Q12

---

## 검증 결과

### ✅ 통과 항목

1. **Set별 배정:** 모든 Set에 정확히 2명 배정됨 (1 Resident + 1 Attending)
2. **Local QID:** 모든 리뷰어의 QID가 Q01부터 순차적으로 할당됨
3. **Institution De-correlation:** 정상 (모든 Set에서 동일 기관 reviewer 없음)
4. **[Study Coordinator] 재배정:** 완료 ([Study Coordinator]에게 배정 없음)

### ✅ 완료 사항

1. **완전 균등 배정**
   - Residents: 9명, 각 12 sets (완전 균등)
   - Attendings: 9명, 각 12 sets (완전 균등, [Study Coordinator] 포함)

2. **[Study Coordinator](rev_010) 배정 완료**
   - [Study Coordinator]은 전문의로 분류되어 12 sets 배정 완료
   - 모든 전문의가 균등하게 12 sets씩 배정됨

---

## 생성된 파일

1. ✅ `reviewer_master.csv`
   - 위치: `1_Secure_Participant_Info/reviewer_master.csv`
   - [Study Coordinator](rev_010) role: `attending`으로 업데이트

2. ✅ `assignment_map.csv`
   - 위치: `0_Protocol/06_QA_and_Study/QA_Operations/assignment_map.csv`
   - 총 216개 배정 기록 (108 sets × 2 reviewers)
   - [Study Coordinator] 배정 제외, 다른 전문의에게 재배정 완료

3. ✅ `surrogate_map.csv`
   - 위치: `0_Protocol/06_QA_and_Study/QA_Operations/surrogate_map.csv`
   - 108개 surrogate 매핑

---

## 다음 단계

1. **S0 실행** (S1/S2)
   - 실제 group_id 확정
   - `assignment_map.csv`의 placeholder group_id 업데이트

2. **Subspecialty 검증**
   - 실제 group_id 확정 후 검증
   - 필요 시 재배정

3. **S3/S4 실행**
   - 이미지 스펙 생성 및 이미지 생성

4. **PDF 생성 및 배포**
   - Google Drive 폴더 생성
   - Google Form 생성
   - 이메일 발송

---

## 참고사항

### 완전 균등 배정

- **Residents:** 완전 균등 (각 12 sets)
- **Attendings:** 완전 균등 (각 12 sets, [Study Coordinator] 포함)
- **장점:**
  - 모든 리뷰어의 workload 균등
  - 통계 분석 시 편향 최소화
  - 평가자 피로도 균등 분산

### [Study Coordinator](rev_010) 처리

- **상태:** 전문의로 분류되어 12 sets 배정 완료
- **배정:** Q01~Q12, 총 12 sets
- **영향:** 모든 전문의가 균등하게 평가 수행

---

**Status:** ✅ 배정 완료, S0 실행 준비 완료

