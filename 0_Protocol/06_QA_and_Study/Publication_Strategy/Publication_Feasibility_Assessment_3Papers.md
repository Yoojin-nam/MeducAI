# Revision 및 Accept 가능성 평가

**Status:** Reference (Publication Feasibility)  
**Version:** 1.0  
**Date:** 2026-01-15  
**Purpose:** 각 논문별 보완 방안으로 revision과 accept가 가능한지 현실적 평가

---

## 종합 평가 요약

| 논문 | 현재 상태 | 보완 후 Accept 가능성 | 주요 리스크 | 권장 전략 |
|------|----------|---------------------|-----------|----------|
| **Paper 1** | ⭐⭐⭐⭐ | **⭐⭐⭐⭐⭐ (90-95%)** | 낮음 | 보완 방안 충실히 적용 |
| **Paper 2** | ⭐⭐⭐ | **⭐⭐⭐⭐ (75-85%)** | 중간 | 일부 설계 한계 인정 |
| **Paper 3** | ⭐⭐ | **⭐⭐⭐ (60-75%)** | 높음 | 보수적 저널 선택 권장 |

---

## Paper 1: S5 Multi-agent 신뢰도 검증

### Accept 가능성: ⭐⭐⭐⭐⭐ (90-95%)

#### 강점 (현재 상태)

1. **대규모 샘플 크기**
   - n=1,100-1,300 (PASS group)는 매우 충분
   - Clopper-Pearson exact CI는 보수적이고 신뢰할 수 있음
   - FN < 0.3% threshold는 명확하고 해석하기 쉬움

2. **견고한 연구 설계**
   - Partial Overlap Design (33개 × 3명)는 통계적으로 견고
   - Specialty-Stratified는 일반화 가능성 높음
   - REGEN Census Review는 투명성 강조

3. **명확한 Primary Endpoint**
   - Safety validation은 임상적으로 중요
   - 통계적 방법론이 표준적이고 검증됨

#### 예상 Revision 지적사항

**Minor Revision 가능성 높음:**

1. **"PASS 샘플 크기 변동성에 대한 설명 부족"**
   - **대응**: Worst-case scenario analysis 추가
   - **난이도**: ⭐ (쉬움)
   - **Accept 가능성**: 95% (명확한 대응 가능)

2. **"REGEN cap=200의 통계적 근거 부족"**
   - **대응**: Bootstrap sampling error 정량화 + FPC
   - **난이도**: ⭐⭐ (중간)
   - **Accept 가능성**: 90% (실용적 제약 인정 가능)

3. **"ICC가 낮으면 어떻게 하나?"**
   - **대응**: ICC sensitivity by specialty 분석
   - **난이도**: ⭐ (쉬움)
   - **Accept 가능성**: 95% (사전 분석 계획)

**Major Revision 가능성 낮음:**

- Reviewer가 "샘플 크기를 고정해야 한다"고 요구할 가능성: **낮음**
  - 이유: "Selection and Focus" 전략이 통계적으로 합리적
  - 대응: Worst-case analysis로 robustness 입증

#### Accept 가능성 평가

**✅ 매우 높음 (90-95%)**

**이유:**
1. **보완 방안이 명확하고 실행 가능**
2. **통계적 방법론이 표준적**
3. **Primary endpoint가 임상적으로 중요**
4. **대규모 샘플로 통계적 파워 충분**

**예상 시나리오:**
- **Best case**: Minor revision → Accept (1-2라운드)
- **Typical case**: Minor revision → Accept (2-3라운드)
- **Worst case**: Major revision → Accept (3-4라운드, 드뭄)

---

## Paper 2: MLLM 이미지 신뢰도

### Accept 가능성: ⭐⭐⭐⭐ (75-85%)

#### 강점 (현재 상태)

1. **Paired Comparison Design**
   - Within-subject design은 통계적 파워 높음
   - Bias 제거 효과

2. **Inter-rater Reliability**
   - 2-rater design (Resident + Specialist)
   - Modality-specific ICC 계산 가능

3. **Expertise × Modality Interaction**
   - 2×2 mixed-effects model
   - 교육적 함의 있음

#### 예상 Revision 지적사항

**Minor Revision 가능성 높음:**

1. **"Table Infographic n=100이 충분한가?"**
   - **대응**: FPC 적용 + Sampling strategy 정당화
   - **난이도**: ⭐⭐ (중간)
   - **Accept 가능성**: 80% (실용적 제약 인정 가능)

2. **"Order effect를 통제했나?"**
   - **대응**: Order effect analysis 추가
   - **난이도**: ⭐ (쉬움)
   - **Accept 가능성**: 85% (명확한 대응 가능)

3. **"Fatigue effect를 고려했나?"**
   - **대응**: Fatigue effect analysis 추가
   - **난이도**: ⭐ (쉬움)
   - **Accept 가능성**: 85% (명확한 대응 가능)

**Major Revision 가능성 중간:**

1. **"Table Infographic 전체 평가 필요"**
   - **대응**: FPC + Sampling error 정량화로 대응
   - **난이도**: ⭐⭐⭐ (어려움 - 추가 데이터 수집 필요할 수 있음)
   - **Accept 가능성**: 70% (추가 평가 필요할 수 있음)

2. **"Order effect를 완전히 통제하려면 역순 그룹 필요"**
   - **대응**: 이미 평가 완료라면 시뮬레이션 또는 인정
   - **난이도**: ⭐⭐⭐ (어려움 - 설계상 한계)
   - **Accept 가능성**: 75% (설계 한계 인정 가능)

#### Accept 가능성 평가

**✅ 높음 (75-85%)**

**이유:**
1. **대부분의 보완 방안이 실행 가능**
2. **일부는 설계상 한계이지만 합리적 정당화 가능**
3. **Primary endpoint (Paired comparison, ICC)는 견고**

**예상 시나리오:**
- **Best case**: Minor revision → Accept (1-2라운드)
- **Typical case**: Minor revision → Accept (2-3라운드)
- **Worst case**: Major revision → Accept (3-4라운드, Table 추가 평가 필요할 수 있음)

**리스크:**
- Table Infographic n=100이 가장 큰 리스크
- Reviewer가 "전체 평가" 요구할 가능성: 30-40%

---

## Paper 3: 교육효과 전향적 연구

### Accept 가능성: ⭐⭐⭐ (60-75%)

#### 강점 (현재 상태)

1. **Prospective Design**
   - Baseline → FINAL 설계는 longitudinal
   - Within-subject change 측정 가능

2. **Multiple Co-primary Outcomes**
   - Hierarchical testing으로 multiplicity 통제
   - 이론적 + 실용적 outcomes 모두 포함

3. **Dose-Response Analysis**
   - 사용량-효과 관계는 인과성 시사

#### 예상 Revision 지적사항

**Minor Revision 가능성 높음:**

1. **"Confounding을 충분히 통제했나?"**
   - **대응**: Propensity Score Matching / IPW 추가
   - **난이도**: ⭐⭐ (중간)
   - **Accept 가능성**: 70% (PSM은 표준적 방법)

2. **"Self-reported outcomes의 신뢰도?"**
   - **대응**: Objective measures (Anki logs) validation
   - **난이도**: ⭐⭐ (중간)
   - **Accept 가능성**: 75% (객관적 측정 추가)

3. **"Missing data 처리는 적절한가?"**
   - **대응**: Multiple imputation + MNAR sensitivity
   - **난이도**: ⭐⭐ (중간)
   - **Accept 가능성**: 80% (표준적 방법)

**Major Revision 가능성 높음:**

1. **"Observational design의 근본적 한계"**
   - **대응**: PSM/IPW로 완화하지만 완전한 해결 불가
   - **난이도**: ⭐⭐⭐⭐ (매우 어려움 - 설계상 한계)
   - **Accept 가능성**: 60% (Observational design의 한계 인정 필요)

2. **"RCT가 필요하지 않나?"**
   - **대응**: Observational design의 정당화 (실용성, 윤리적 고려)
   - **난이도**: ⭐⭐⭐⭐ (매우 어려움 - 설계 변경 불가)
   - **Accept 가능성**: 50% (일부 reviewer는 RCT 요구 가능)

3. **"Sample size 및 power 계산 부족"**
   - **대응**: Post-hoc power analysis
   - **난이도**: ⭐⭐ (중간)
   - **Accept 가능성**: 70% (Post-hoc는 제한적)

#### Accept 가능성 평가

**⚠️ 중간 (60-75%)**

**이유:**
1. **Observational design의 근본적 한계**
   - Confounding 완전 통제 불가
   - 일부 reviewer는 RCT 요구 가능

2. **Self-reported outcomes의 bias**
   - Objective validation으로 완화 가능하지만 완전하지 않음

3. **Sample size 불확실성**
   - Post-hoc power analysis는 제한적

**예상 시나리오:**
- **Best case**: Minor revision → Accept (2-3라운드)
- **Typical case**: Major revision → Accept (3-4라운드)
- **Worst case**: Reject → 다른 저널 재투고 (RCT 요구)

**리스크:**
- **높음**: Observational design의 한계
- **중간**: Self-reported outcomes
- **낮음**: Missing data, Power

**권장 전략:**
1. **보수적 저널 선택**: BMC Medical Education 등 (RCT 요구 덜함)
2. **Observational design 정당화 강화**: 실용성, 윤리적 고려
3. **Causal inference language 회피**: "Association" 강조, "Causation" 회피

---

## 종합 전략 및 권장사항

### Paper 1: 최우선 투고

**전략:**
- ✅ **보완 방안 충실히 적용**
- ✅ **Worst-case analysis 필수**
- ✅ **Bootstrap sampling error 정량화**
- ✅ **ICC sensitivity analysis**

**예상 결과:**
- **Accept 확률**: 90-95%
- **Revision 라운드**: 1-2라운드
- **저널**: npj Digital Medicine, JMIR 등

---

### Paper 2: 신중한 투고

**전략:**
- ✅ **Order/Fatigue effect analysis 필수**
- ✅ **Table Infographic FPC + Sampling strategy 정당화**
- ⚠️ **Table n=100에 대한 합리적 정당화 준비**
- ⚠️ **추가 평가 필요할 경우 대비**

**예상 결과:**
- **Accept 확률**: 75-85%
- **Revision 라운드**: 2-3라운드
- **저널**: Medical Image Analysis, npj Digital Medicine

**리스크 관리:**
- Table Infographic이 문제될 경우, "pilot evaluation"으로 재정의 가능
- 또는 "ongoing evaluation"으로 future work 언급

---

### Paper 3: 보수적 전략

**전략:**
- ✅ **PSM/IPW 필수 적용**
- ✅ **Objective validation (Anki logs) 필수**
- ✅ **Multiple imputation + MNAR sensitivity**
- ⚠️ **Observational design 정당화 강화**
- ⚠️ **보수적 저널 선택 (BMC Medical Education 등)**

**예상 결과:**
- **Accept 확률**: 60-75%
- **Revision 라운드**: 3-4라운드 (또는 Reject 후 재투고)
- **저널**: BMC Medical Education, Medical Teacher (RCT 요구 덜함)

**리스크 관리:**
- **RCT 요구 시**: "실용적 고려사항", "윤리적 제약" 정당화
- **Causal language 회피**: "Association", "Relationship" 사용
- **Future work**: "RCT를 통한 인과성 검증 필요" 언급

---

## Revision 대응 체크리스트

### Paper 1 체크리스트

- [ ] Worst-case scenario analysis (REGEN=200)
- [ ] Bootstrap sampling error 정량화 (REGEN cap)
- [ ] ICC sensitivity by specialty
- [ ] Specialist-Resident agreement analysis
- [ ] Methods 섹션에 모든 보완 분석 명시

### Paper 2 체크리스트

- [ ] Table Infographic FPC + Sampling strategy 정당화
- [ ] Order effect analysis
- [ ] Fatigue effect analysis
- [ ] Table Infographic inter-rater reliability
- [ ] Limitations에 설계상 한계 명시

### Paper 3 체크리스트

- [ ] Propensity Score Matching / IPW
- [ ] Post-hoc power analysis
- [ ] Objective measures validation (Anki logs)
- [ ] Multiple imputation + MNAR sensitivity
- [ ] FDR control for exploratory analyses
- [ ] Observational design 정당화 강화

---

## 최종 권장사항

### 투고 순서

1. **Paper 1 (QA 신뢰도)** - 최우선
   - Accept 확률 높음
   - 보완 방안 명확
   - 빠른 출판 가능

2. **Paper 2 (이미지 신뢰도)** - 2순위
   - Accept 확률 중간-높음
   - 일부 설계 한계 있지만 정당화 가능

3. **Paper 3 (교육 효과)** - 3순위
   - Accept 확률 중간
   - 보수적 저널 선택 권장
   - RCT 요구 대비 필요

### 공통 전략

1. **Pre-emptive Analysis**
   - Revision 전에 모든 보완 분석 미리 수행
   - Supplementary Material에 포함

2. **Transparent Reporting**
   - Limitations 섹션에 설계상 한계 명시
   - Future work에 개선 방향 제시

3. **Conservative Language**
   - "Association" vs "Causation" 구분
   - "Suggests" vs "Demonstrates" 구분

---

**Document Status**: Reference (Publication Feasibility)  
**Last Updated**: 2026-01-15  
**Owner**: MeducAI Research Team

