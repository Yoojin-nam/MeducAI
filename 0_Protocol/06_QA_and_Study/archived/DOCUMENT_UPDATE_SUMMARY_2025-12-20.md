# QA 및 Study 문서 업데이트 요약 (2025-12-20)

**업데이트 일자:** 2025-12-20  
**목적:** 실제 구현(`s0_noninferiority.py`)과 문서 간 불일치 해결 및 문서 정리

---

## 1. 주요 변경 사항

### 1.1 QA Framework v2.0 업데이트

**변경 내용:**
- Section 2.7: Non-Inferiority Framework를 **Two-Layer Decision Framework**로 업데이트
  - **Layer 1: Safety Endpoint** (RD0 ≤ 0.02)
  - **Layer 2: Primary NI Endpoint** (Mean Accuracy Score, Δ = 0.05)
- **Endpoint 변경:** Overall Card Quality (Likert 1–5) → **Mean Accuracy Score (0/0.5/1)**
- **Margin 변경:** Δ = 0.5 (Likert scale) → **Δ = 0.05 (mean score scale)**
- **Baseline Arm:** Arm E → **Arm A (default), Arm E (alternative)**
- Section 2.10: Decision Rules에 Two-Layer Framework 반영

**Canonical Reference 추가:**
- `0_Protocol/06_QA_and_Study/QA_Operations/S0_Noninferiority_Criteria_Canonical.md`
- `3_Code/src/tools/qa/s0_noninferiority.py`

### 1.2 Statistical Analysis Plan v2.0 업데이트

**변경 내용:**
- Section 8.1.1: Step S0 Non-Inferiority Analysis 업데이트
  - Two-Layer Decision Framework 반영
  - Endpoint: Mean Accuracy Score (0/0.5/1)
  - Margin: Δ = 0.05 (default)
  - Baseline: Arm A (default), Arm E (alternative)
  - Statistical Method: Clustered paired bootstrap

### 1.3 S0_Non-Inferiority_QA_and_Final_Model_Selection_Protocol.md

**변경 내용:**
- Status: **FROZEN (Canonical)** → **SUPERSEDED**
- Superseded by 문서 목록 추가
- 실제 구현과의 차이점 명시

### 1.4 S0_S1 Completion Checklist 업데이트

**변경 내용:**
- S0-ANA-02: Non-inferiority test 파라미터 업데이트
  - Δ_quality=0.5, Reference: Arm E → **Two-layer: Safety + NI, Δ=0.05, Baseline: Arm A default**
- S0-D-02: NI test 규칙 업데이트
  - NI test vs Reference (Arm E) → **Two-layer gate: Safety (RD0 ≤ 0.02) + NI (LowerCI(d) > -Δ, Δ=0.05)**

### 1.5 Reference_Arm_Recommendation.md 업데이트

**변경 내용:**
- Implementation Note 추가
  - 현재 구현: Arm A (Baseline) default
  - 권장사항: Arm E (High-End)는 `--baseline_arm E`로 설정 가능
  - Canonical Reference 링크 추가

### 1.6 QA_Plan_Review_Report.md 업데이트

**변경 내용:**
- 상태 섹션 추가: **이슈 해결 완료 (2025-12-20)**
- 해결된 이슈 목록 명시
- 원본 검토 보고서는 보존

---

## 2. 문서 상태 정리

### 2.1 Canonical Documents (현재 사용)

1. **QA_Framework.md** - 메인 프레임워크 문서
2. **S0_Noninferiority_Criteria_Canonical.md** - S0 NI 분석 canonical reference
3. **Statistical_Analysis_Plan.md** - 통계 분석 계획
4. **S0_S1_Completion_Checklist_and_Final_Freeze.md** - 실행 체크리스트
5. **Reference_Arm_Recommendation.md** - Reference Arm 권장사항 (권장사항 문서)

### 2.2 Superseded Documents

1. **S0_Non-Inferiority_QA_and_Final_Model_Selection_Protocol.md (v1.1)**
   - Status: SUPERSEDED
   - Superseded by: QA_Framework v2.0, S0_Noninferiority_Criteria_Canonical.md, Statistical_Analysis_Plan.md

### 2.3 Historical Documents (보존)

1. **QA_Plan_Review_Report.md**
   - 상태: 이슈 해결 완료 표시 추가
   - 목적: 검토 이력 보존

---

## 3. 구현과의 일치성 확인

### 3.1 실제 구현 (`s0_noninferiority.py`)

- **Endpoint:** Mean Accuracy Score (0/0.5/1)
- **Margin:** Δ = 0.05 (default, configurable)
- **Baseline:** Arm A (default, configurable via `--baseline_arm`)
- **Method:** Clustered paired bootstrap
- **Two-Layer Framework:**
  - Safety: `UpperCI(RD0) ≤ 0.02`
  - NI: `LowerCI(d) > -Δ`

### 3.2 문서 일치성

✅ **모든 문서가 실제 구현과 일치**
- QA Framework v2.0: ✅
- Statistical Analysis Plan v2.0: ✅
- S0_Noninferiority_Criteria_Canonical.md: ✅
- S0_S1 Completion Checklist: ✅

---

## 4. 주요 결정 사항

### 4.1 Primary Endpoint

**결정:** Mean Accuracy Score (0/0.5/1)
- **이유:** 
  - S0의 고정 12-card payload에 적합
  - 이미 수집되는 데이터 활용
  - 통계적으로 의미 있는 margin (Δ = 0.05) 설정 가능

### 4.2 Non-Inferiority Margin

**결정:** Δ = 0.05 (mean score scale)
- **이유:**
  - 12-card set에서 0.6 points degradation 허용 (교육적으로 의미 있음)
  - 통계적으로 방어 가능
  - 더 큰 Δ 값(0.5, 1.0)은 12-card set에 부적합

### 4.3 Baseline Arm

**결정:** Arm A (Baseline) - default
- **구현:** `s0_noninferiority.py` 기본값
- **권장사항:** Arm E (High-End) - `Reference_Arm_Recommendation.md`에서 권장
- **설정 가능:** `--baseline_arm E`로 변경 가능

### 4.4 Two-Layer Framework

**결정:** Safety Gate + NI Gate
- **Layer 1 (Safety):** Major error 증가 방지 (RD0 ≤ 0.02)
- **Layer 2 (NI):** Mean accuracy 비열등성 검증 (LowerCI(d) > -Δ)

---

## 5. 다음 단계

### 5.1 문서 검토 완료

✅ 모든 주요 문서 업데이트 완료
✅ Superseded 문서 표시 완료
✅ Canonical reference 명확화 완료

### 5.2 실행 준비

- S0 QA 실행 시 `s0_noninferiority.py` 사용
- Baseline arm은 기본값(Arm A) 또는 `--baseline_arm E`로 설정
- Two-layer decision framework 적용

---

## 6. 참고 문서

### Canonical References

1. **QA Framework v2.0**
   - `0_Protocol/06_QA_and_Study/QA_Framework.md`

2. **S0 Non-Inferiority Criteria (Canonical)**
   - `0_Protocol/06_QA_and_Study/QA_Operations/S0_Noninferiority_Criteria_Canonical.md`

3. **Statistical Analysis Plan**
   - `0_Protocol/06_QA_and_Study/Study_Design/Statistical_Analysis_Plan.md`

4. **Implementation Script**
   - `3_Code/src/tools/qa/s0_noninferiority.py`

### Supporting Documents

- `0_Protocol/06_QA_and_Study/Reference_Arm_Recommendation.md`
- `0_Protocol/06_QA_and_Study/S0_S1_Completion_Checklist_and_Final_Freeze.md`
- `0_Protocol/06_QA_and_Study/QA_Plan_Review_Report.md` (historical)

---

**작성일:** 2025-12-20  
**작성자:** Document Consolidation Task  
**상태:** 완료

