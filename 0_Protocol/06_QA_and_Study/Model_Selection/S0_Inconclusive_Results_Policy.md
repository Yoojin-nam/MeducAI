# S0 비열등성 검정 미결정 시 정책

**Status:** Canonical (Updated)  
**Date:** 2025-12-29  
**Last Updated:** 2025-12-29  
**Related Documents:**
- `S0_Noninferiority_Criteria_Canonical.md`
- `QA_Framework.md` (Section 2.10)
- `S1_S2_Independent_Execution_Design.md`

---

## 중요 전제 조건

### 1. IRB 승인 불필요
- **QA 연구는 IRB 제출 대상이 아님**
- 생성물에 대한 인간 평가이므로 IRB 불필요
- 따라서 IRB 승인 관련 조건은 적용되지 않음

### 2. 비용 효과성 고려
- **비용 효과적인 문제로 S1, S2에 각각 다른 모델 사용 필요**
- 이는 실용적이고 정당한 운영 결정

### 3. Step별 별도 평가
- **설문조사에서 S1, S2, S4에 대한 평가는 별개로 이루어짐**
- 각 Step의 성능을 독립적으로 평가 가능
- 이 점을 반영하여 설문조사 결과를 해석해야 함

---

## 문제 상황

**질문:** S0에서 통계적으로 유의미한 결론이 나오지 않을 경우, 정성적으로 E를 S1에, C를 S2에, D를 S5에 사용해도 되는가?

---

## 현재 프로토콜 요약

### 1. S0 목적 (QA_Framework.md)

> **Step S0는 6-arm 실험을 통해 Deployment Model을 선정하고, 이후 전체 생성에서 설정 변경 금지가 가능한 근거를 확보한다.**

**핵심 원칙:**
- **Deployment Model** 선택 (단일 또는 Step별)
- **설정 변경 금지** (Freeze)
- 통계적 근거 확보

### 2. Step별 다른 Arm 사용의 정당성

**비용 효과성 고려:**
- **S1, S2에 각각 다른 모델 사용이 비용 효과적**
- 이는 실용적이고 정당한 운영 결정
- 기술적으로도 가능 (S1/S2 독립 실행 설계)

**설문조사 구조:**
- **S1, S2, S4에 대한 평가는 별개로 이루어짐**
- 각 Step의 성능을 독립적으로 평가 가능
- Step별 arm 선택에 대한 통계적 근거 확보 가능

### 3. S1/S2 독립 실행 (S1_S2_Independent_Execution_Design.md)

**기술적 가능성:**
- S2는 다른 S1 arm의 출력을 사용할 수 있음 (`--s1_arm` 옵션)
- **Deployment 목적에서도 사용 가능**
- Step별 최적화를 위한 설계

---

## Step별 다른 Arm 사용의 해석 방법

### 1. 설문조사 결과 해석

**중요:**
- **S1, S2, S4 평가가 별개로 이루어졌으므로**, 각 Step별로 arm 성능을 비교 가능
- 설문조사 결과를 Step별로 분리하여 해석해야 함
- 예:
  - S1 관련 평가 항목: Table & Infographic 평가 (C 섹션)
  - S2 관련 평가 항목: Card Quality 평가 (B 섹션)
  - S4 관련 평가 항목: Image 관련 평가 (있는 경우)

### 2. 통계적 근거 확보 방법

**Step별 arm 성능 비교:**
- S1 성능: Table/Infographic 평가 결과 (C 섹션)를 arm별로 비교
- S2 성능: Card Quality 평가 결과 (B 섹션)를 arm별로 비교
- S4 성능: Image 평가 결과를 arm별로 비교 (있는 경우)

**결과:**
- "E가 S1에 좋다"는 주장: Table/Infographic 평가 결과로 근거 확보 가능
- "C가 S2에 좋다"는 주장: Card Quality 평가 결과로 근거 확보 가능
- "D가 S5에 좋다"는 주장: Validation 관련 평가 결과로 근거 확보 가능

### 3. 재현성 및 문서화

**요구사항:**
- Step별 arm 선택 근거를 명확히 문서화
- 설문조사 결과를 Step별로 분리하여 분석
- 논문 Methods 섹션에 "Step별 최적화"로 명시

---

## 권장 대안

### Option 1: Step별 Arm 선택 (권장)

**정책:**
- S0 설문조사 결과를 **Step별로 분리하여 분석**
- 각 Step에서 가장 우수한 arm 선택:
  - **S1**: Table/Infographic 평가 결과 기반 (C 섹션)
  - **S2**: Card Quality 평가 결과 기반 (B 섹션)
  - **S4**: Image 평가 결과 기반 (있는 경우)
  - **S5**: Validation 관련 평가 결과 기반

**근거:**
- 설문조사에서 S1, S2, S4 평가가 별개로 이루어졌으므로, 각 Step별로 통계적 근거 확보 가능
- 비용 효과성 고려
- 실용적이고 정당한 운영 결정

**분석 방법:**
1. 설문조사 결과를 Step별로 분리
2. 각 Step별로 arm 성능 비교 (Non-inferiority 또는 descriptive)
3. 각 Step에서 가장 우수한 arm 선택
4. 논문 Methods 섹션에 "Step별 최적화"로 명시

### Option 2: Fallback Policy (단일 Arm)

**정책:**
- S0에서 비열등 arm이 없으면, **Baseline Arm (E)를 단일 Deployment Model로 선택**
- S1, S2, S5 모두 **동일한 arm (E) 사용**

**근거:**
- 가장 안전한 선택
- 단순성
- 하지만 비용 효과성 측면에서 최적이 아닐 수 있음

---

## 결론 및 권장사항

### ✅ 권장: Step별 Arm 선택 (설문조사 결과 기반)

**권장 사항:**
1. **S0 설문조사 결과를 Step별로 분리하여 분석**
   - S1: Table/Infographic 평가 (C 섹션)
   - S2: Card Quality 평가 (B 섹션)
   - S4: Image 평가 (있는 경우)
2. **각 Step별로 가장 우수한 arm 선택**
   - 통계적 근거 확보 (Non-inferiority 또는 descriptive)
   - 비용 효과성 고려
3. **논문 Methods 섹션에 "Step별 최적화"로 명시**
   - "비용 효과성을 고려하여 각 Step에서 가장 우수한 arm 선택"
   - "설문조사에서 S1, S2, S4 평가가 별개로 이루어졌으므로, 각 Step별로 arm 성능 비교 가능"

### ⚠️ 대안: Fallback Policy (단일 Arm)

**조건:**
- Step별 분석이 어렵거나 결과가 불명확한 경우
- 가장 안전한 선택이 필요한 경우
- Baseline Arm (E)를 단일 Deployment Model로 선택

---

## 다음 단계

1. **S0 최종 분석 결과 확인**
   - 모든 응답 수집 후 최종 NI 분석 실행
   - 결과에 따라 결정

2. **결과가 미결정인 경우:**
   - Option 1 (Step별 Arm 선택) 권장:
     - 설문조사 결과를 Step별로 분리하여 분석
     - 각 Step별로 가장 우수한 arm 선택
     - 통계적 근거 확보
   - Option 2 (Fallback Policy)를 선택하려면:
     - Baseline Arm (E)를 단일 Deployment Model로 선택

3. **문서화:**
   - 선택한 정책과 근거를 명확히 문서화
   - 논문 Methods 섹션에 반영
   - "Step별 최적화" 또는 "단일 Deployment Model" 명시

---

**작성자:** MeducAI Research Team  
**검토 필요:** Co-authors

