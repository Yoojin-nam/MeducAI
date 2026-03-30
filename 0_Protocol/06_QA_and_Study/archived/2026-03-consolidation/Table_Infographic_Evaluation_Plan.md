# Table Infographic 평가 계획서

**Status:** Canonical  
**Version:** 1.0  
**Date:** 2026-01-04  
**Purpose:** Paper 2 (MLLM 생성 이미지 신뢰도) 연구를 위한 Table Infographic 평가 설계  
**Execution Timeline:** 2026년 2월 전문의 시험 종료 후

---

## 1. 연구 배경 및 목적

### 1.1 연구 배경

MeducAI 파이프라인에서 S4 단계는 S1에서 생성된 Master Table을 시각적 인포그래픽으로 변환합니다. 이 Table Infographic은 학습자가 복잡한 의학 정보를 빠르게 파악할 수 있도록 돕는 핵심 교육 자료입니다.

### 1.2 연구 목적

1. **품질 검증**: Table Infographic의 정보 정확성 및 교육적 가치 평가
2. **신뢰도 확립**: 평가자 간 일치도(Inter-rater reliability) 검증
3. **Error Rate 추정**: Critical Error 및 Scope Alignment Failure 비율 추정
4. **Paper 2 통합**: MLLM 생성 이미지 신뢰도 연구의 일부로 활용

### 1.3 관련 논문

본 평가는 **Paper 2: MLLM 생성 이미지의 신뢰도** 연구의 일부입니다.

| 논문 | 주제 | 데이터 소스 |
|------|------|-------------|
| Paper 1 | S5 Multi-agent 신뢰도 | FINAL QA (카드 평가) |
| **Paper 2** | **MLLM 이미지 신뢰도** | **Visual Sub-study + Table Infographic** |
| Paper 3 | 교육효과 전향적 연구 | Baseline + FINAL 설문 |

---

## 2. 평가 대상

### 2.1 전체 모집단

| 항목 | 개수 |
|------|------|
| **전체 그룹 수** | 321개 |
| **전체 Table Infographic 이미지** | 833개 |
| **클러스터가 있는 이미지** | 98개 |
| **평균 이미지/그룹** | ~2.6개 |

### 2.2 평가 샘플

| 항목 | 개수 | 비율 |
|------|------|------|
| **총 평가 이미지** | 250개 | 30% |
| **공통 평가 (ICC)** | 50개 | 6% |
| **개별 평가** | 200개 | 24% |

---

## 3. 평가 설계

### 3.1 설계 개요: 5명 평가자 3-Tier Sampling

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Table Infographic Evaluation Design                   │
│                         (5명 평가자 설계)                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Tier 1: Calibration (ICC 계산용, 공통 평가)                             │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  50개 × 5명 = 250 평가                                          │   │
│  │  • 모든 평가자가 동일한 50개 이미지 평가                          │   │
│  │  • Inter-rater reliability (ICC, Fleiss' Kappa) 계산            │   │
│  │  • 평가 기준 calibration 및 일관성 검증                          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  Tier 2: Main Evaluation (개별 할당, 중복 없음)                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  200개 × 1명 = 200 평가                                         │   │
│  │  • 각 평가자에게 40개씩 개별 할당                                 │   │
│  │  • Error rate 추정을 위한 주요 데이터                            │   │
│  │  • 중복 없이 효율적으로 커버리지 확보                             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  총 평가 이미지: 50 + 200 = 250개 (전체 833개 중 30%)                   │
│  총 평가량: (50 × 5) + 200 = 450 평가                                   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 평가자 할당

| 평가자 | 공통 평가 (Tier 1) | 개별 평가 (Tier 2) | 총 평가량 | 예상 소요시간 |
|--------|-------------------|-------------------|-----------|--------------|
| 평가자 A | 50개 | 40개 | **80개** | ~2시간 |
| 평가자 B | 50개 | 40개 | **80개** | ~2시간 |
| 평가자 C | 50개 | 40개 | **80개** | ~2시간 |
| 평가자 D | 50개 | 40개 | **80개** | ~2시간 |
| 평가자 E | 50개 | 40개 | **80개** | ~2시간 |
| **총계** | 250 평가 | 200 평가 | **450 평가** | **~10시간** |

### 3.3 시간 추정 근거

| 평가 유형 | 시간/개 | 근거 |
|-----------|---------|------|
| Safety Gate (Critical + Scope) | ~45초 | 빠른 Yes/No 판단 |
| Full Evaluation (5개 항목) | ~1.5분 | 상세 평가 |
| **평균** | **~1.5분** | 5개 항목 전체 평가 기준 |

---

## 4. 평가 항목

### 4.1 Primary Outcomes (필수)

| 항목 | 필드명 | 타입 | 설명 |
|------|--------|------|------|
| **Critical Error** | `critical_error` | Yes/No | 임상 판단·학습을 심각히 왜곡할 수 있는 사실 오류 |
| **Scope Alignment** | `scope_alignment_failure` | Yes/No | Group Path / objectives와의 명백한 불일치 |
| **Information Accuracy** | `information_accuracy` | 0.0/0.5/1.0 | 테이블 정보의 사실적 정확성 |

### 4.2 Secondary Outcomes (필수)

| 항목 | 필드명 | 타입 | 설명 |
|------|--------|------|------|
| **Visual Clarity** | `visual_clarity` | 1-5 Likert | 시각적 명료성, 가독성 |
| **Educational Value** | `educational_value` | 1-5 Likert | 교육적 가치, 학습 효과 |

### 4.3 Conditional Fields (조건부)

| 항목 | 필드명 | 조건 | 설명 |
|------|--------|------|------|
| **Error Comment** | `error_comment` | Critical Error = Yes | 오류 내용 간략 기술 (1줄) |
| **Scope Comment** | `scope_comment` | Scope Alignment Failure = Yes | 불일치 내용 간략 기술 (1줄) |

### 4.4 평가 기준 상세

#### 4.4.1 Critical Error (치명 오류)

**정의**: 임상 판단이나 시험 정답을 직접적으로 잘못 유도할 가능성이 큰 오류

**예시**:
- ❌ "PE CT에서 filling defect를 정상으로 기술"
- ❌ "MRI DWI 고신호를 T2 shine-through로 오해할 수 있는 표현"
- ❌ "해부학적 구조 명칭 오류"
- ❌ "수치/단위 오류 (예: mm → cm)"

#### 4.4.2 Scope Alignment Failure (스코프 불일치)

**정의**: Group Path 또는 학습 목표(objectives)와 명백히 불일치

**예시**:
- ❌ "Chest 그룹인데 Abdomen 내용이 주로 포함"
- ❌ "학습 목표와 무관한 내용이 대부분"
- ❌ "다른 전문분야 내용이 혼입"

#### 4.4.3 Information Accuracy (정보 정확성)

| 점수 | 정의 |
|------|------|
| **1.0** | 모든 정보가 정확하고 완전함 |
| **0.5** | 대부분 정확하나 경미한 오류 또는 누락 있음 |
| **0.0** | 핵심 정보에 오류가 있거나 오해 유발 가능 |

#### 4.4.4 Visual Clarity (시각적 명료성)

| 점수 | 정의 |
|------|------|
| **5** | 매우 명확, 한눈에 정보 파악 가능 |
| **4** | 명확, 약간의 개선 여지 있음 |
| **3** | 보통, 일부 정보 파악에 노력 필요 |
| **2** | 불명확, 정보 파악에 상당한 노력 필요 |
| **1** | 매우 불명확, 정보 파악 어려움 |

#### 4.4.5 Educational Value (교육적 가치)

| 점수 | 정의 |
|------|------|
| **5** | 매우 높음, 시험 준비에 직접적 도움 |
| **4** | 높음, 중요한 개념 효과적으로 전달 |
| **3** | 보통, 유용하나 개선 여지 있음 |
| **2** | 낮음, 제한적 교육 효과 |
| **1** | 매우 낮음, 학습에 도움 안 됨 |

---

## 5. 샘플링 전략

### 5.1 공통 평가용 50개 (Tier 1)

**방법**: Stratified Random Sampling

**층화 기준**:
- **Specialty**: Chest, Neuro, Abdomen, MSK 등 11개 subspecialty
- **Entity Type**: Pathology, QC_Equipment, Pattern_Collection 등

**선택 규칙**:
```python
# 층화 샘플링 (seed 고정)
common_50 = stratified_sample(
    population=833_infographics,
    n=50,
    strata=['specialty', 'entity_type'],
    min_per_stratum=2,
    seed=20260201
)
```

### 5.2 개별 평가용 200개 (Tier 2)

**방법**: Simple Random Sampling (공통 50개 제외 후)

**할당 규칙**:
```python
# 공통 50개 제외
remaining = 833_infographics - common_50

# 개별 200개 랜덤 샘플링
individual_200 = random_sample(remaining, n=200, seed=20260201)

# 5명에게 40개씩 할당
for i, evaluator in enumerate(['A', 'B', 'C', 'D', 'E']):
    evaluator.assign(individual_200[i*40:(i+1)*40])
```

### 5.3 Seed 및 재현성

| 항목 | 값 |
|------|-----|
| **Random Seed** | 20260201 |
| **샘플링 스크립트** | `3_Code/Scripts/sample_infographics_for_evaluation.py` (예정) |
| **재현성** | 동일 seed → 동일 샘플 보장 |

---

## 6. 평가자 요건

### 6.1 자격 요건

| 요건 | 설명 |
|------|------|
| **전문성** | 영상의학과 전공의 3-4년차 또는 전문의 |
| **경험** | MeducAI 학습 자료 사용 경험 권장 |
| **가용성** | 2시간 연속 평가 가능 |

### 6.2 평가자 구성 권장

| 구성 | 인원 |
|------|------|
| **전공의** | 3-4명 |
| **전문의** | 1-2명 |
| **총계** | **5명** |

### 6.3 교육 및 Calibration

**평가 전 교육 내용**:
1. 평가 항목 및 기준 설명 (15분)
2. 예시 이미지 3-5개로 연습 (15분)
3. 질의응답 (10분)
4. **총 교육 시간: ~40분**

---

## 7. 통계 분석 계획

### 7.1 Inter-rater Reliability (공통 50개)

#### 7.1.1 Continuous/Ordinal Variables

| 메트릭 | 분석 방법 | 타겟 |
|--------|-----------|------|
| Information Accuracy | ICC(3,k) | > 0.7 (good) |
| Visual Clarity | ICC(3,k) | > 0.7 (good) |
| Educational Value | ICC(3,k) | > 0.7 (good) |

**ICC 유형**: Two-way mixed, absolute agreement

#### 7.1.2 Binary Variables

| 메트릭 | 분석 방법 | 타겟 |
|--------|-----------|------|
| Critical Error | Fleiss' Kappa | > 0.6 (substantial) |
| Scope Alignment Failure | Fleiss' Kappa | > 0.6 (substantial) |

### 7.2 Quality Metrics (전체 250개)

| 메트릭 | 분석 | 보고 형식 |
|--------|------|-----------|
| **Critical Error Rate** | Proportion | % ± 95% CI |
| **Scope Failure Rate** | Proportion | % ± 95% CI |
| **Information Accuracy** | Mean | Mean ± SD |
| **Visual Clarity** | Mean | Mean ± SD |
| **Educational Value** | Mean | Mean ± SD |

### 7.3 통계적 파워

| 메트릭 | 샘플 크기 | 가정 | Margin of Error |
|--------|-----------|------|-----------------|
| Error Rate | 250개 | p=5% | **±2.7%** (95% CI) |
| Error Rate | 250개 | p=10% | **±3.7%** (95% CI) |

**공식**: `E = Z × √(p(1-p)/n)` where Z=1.96 for 95% CI

### 7.4 Subgroup Analysis (탐색적)

| 분석 | 비교 그룹 |
|------|-----------|
| **Entity Type별** | Pathology vs QC_Equipment vs Pattern_Collection |
| **Specialty별** | Chest vs Neuro vs Abdomen vs MSK 등 |
| **Cluster 유무별** | Single image vs Multi-cluster |

---

## 8. 평가 워크플로우

### 8.1 평가 순서

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Evaluation Workflow                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Step 1: 교육 및 Calibration (40분)                                     │
│  ├── 평가 기준 설명 (15분)                                              │
│  ├── 예시 이미지 연습 (15분)                                            │
│  └── 질의응답 (10분)                                                    │
│                                                                         │
│  Step 2: 공통 평가 - Tier 1 (50개, ~75분)                               │
│  ├── 모든 평가자가 동일한 50개 이미지 평가                               │
│  ├── 순서: 랜덤화 (평가자마다 다른 순서)                                 │
│  └── 제출 후 수정 불가                                                  │
│                                                                         │
│  Step 3: 휴식 (10분)                                                    │
│                                                                         │
│  Step 4: 개별 평가 - Tier 2 (40개, ~60분)                               │
│  ├── 각 평가자에게 할당된 40개 이미지 평가                               │
│  ├── 순서: 랜덤화                                                       │
│  └── 제출 후 수정 불가                                                  │
│                                                                         │
│  총 소요시간: ~3시간 (교육 포함) / ~2시간 (평가만)                        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 8.2 평가 인터페이스 요구사항

| 요구사항 | 설명 |
|----------|------|
| **이미지 표시** | 고해상도, 확대/축소 가능 |
| **Group 정보 표시** | Group Path, Objectives (참조용) |
| **평가 폼** | 5개 항목 한 화면에 표시 |
| **진행 상황** | 현재/전체 표시 (예: 15/50) |
| **자동 저장** | 각 이미지 평가 완료 시 |

---

## 9. 데이터 수집 및 관리

### 9.1 수집 데이터 형식

```json
{
  "evaluation_id": "eval_001_A",
  "evaluator_id": "A",
  "image_id": "IMG__FINAL_DISTRIBUTION__grp_abc123__TABLE.jpg",
  "group_id": "grp_abc123",
  "tier": "common",
  "timestamp": "2026-02-20T14:30:00Z",
  "evaluation": {
    "critical_error": false,
    "scope_alignment_failure": false,
    "information_accuracy": 1.0,
    "visual_clarity": 4,
    "educational_value": 5,
    "error_comment": null,
    "scope_comment": null
  },
  "time_spent_sec": 85
}
```

### 9.2 데이터 저장 위치

| 데이터 | 위치 |
|--------|------|
| 원본 평가 데이터 | `2_Data/qa_responses/table_infographic_evaluation/` |
| 분석 결과 | `2_Data/processed/table_infographic_analysis/` |
| 보고서 | `5_Meeting/Table_Infographic_Evaluation_Report.md` |

### 9.3 익명화

| 항목 | 처리 |
|------|------|
| 평가자 식별 | 익명 ID (A, B, C, D, E) |
| 이미지 ID | 원본 유지 (개인정보 없음) |

---

## 10. 실행 타임라인

### 10.1 전체 일정

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Execution Timeline                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  2월 중순 (전문의 시험 종료 후)                                          │
│  ├── Week 1: 준비                                                       │
│  │   ├── 평가자 모집 (5명)                                              │
│  │   ├── 샘플링 스크립트 실행                                           │
│  │   ├── 평가 인터페이스 준비                                           │
│  │   └── 평가 교육 자료 준비                                            │
│  │                                                                      │
│  ├── Week 2: 평가 진행                                                  │
│  │   ├── Day 1-2: 교육 및 Tier 1 평가                                   │
│  │   └── Day 3-5: Tier 2 평가 완료                                      │
│  │                                                                      │
│  ├── Week 3: 분석                                                       │
│  │   ├── 데이터 정리 및 검증                                            │
│  │   ├── ICC, Fleiss' Kappa 계산                                        │
│  │   └── Quality metrics 계산                                           │
│  │                                                                      │
│  └── Week 4: 보고서 작성                                                │
│      └── Paper 2 통합 준비                                              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 10.2 마일스톤

| 마일스톤 | 예상 일정 | 담당 |
|----------|-----------|------|
| 평가자 모집 완료 | 시험 후 1주 | 연구 담당자 |
| 샘플링 완료 | 시험 후 1주 | 개발팀 |
| 평가 교육 완료 | 시험 후 2주 | 연구 담당자 |
| 평가 완료 | 시험 후 2주 | 평가자 5명 |
| 분석 완료 | 시험 후 3주 | 연구팀 |
| 보고서 완료 | 시험 후 4주 | 연구팀 |

---

## 11. 품질 관리

### 11.1 평가 전 검증

- [ ] 샘플링 스크립트 검증 (seed 재현성)
- [ ] 250개 이미지 접근 가능 확인
- [ ] 평가 인터페이스 테스트
- [ ] 평가 기준 문서 배포

### 11.2 평가 중 모니터링

- [ ] 평가 진행률 추적
- [ ] 이상치 탐지 (극단적 평가 패턴)
- [ ] 질문/이슈 대응

### 11.3 평가 후 검증

- [ ] 데이터 완결성 확인 (누락 없음)
- [ ] ICC/Kappa 계산 및 타겟 달성 확인
- [ ] Subgroup 분석 수행

---

## 12. 관련 문서

| 문서 | 위치 |
|------|------|
| Paper 2 연구 설계 | `0_Protocol/06_QA_and_Study/FINAL_QA_Research_Design_Spec.md` |
| S4 이미지 생성 정책 | `0_Protocol/04_Step_Contracts/Step04_S4/` |
| QA Metric 정의 | `0_Protocol/05_Pipeline_and_Execution/QA_Metric_Definitions.md` |
| Table Infographic 샘플링 전략 | `0_Protocol/05_Pipeline_and_Execution/FINAL_QA_Table_Infographic_Sampling_Strategy.md` |

---

## 13. 요약

### 13.1 핵심 수치

| 항목 | 값 |
|------|-----|
| **전체 인포그래픽** | 833개 |
| **평가 샘플** | 250개 (30%) |
| **공통 평가 (ICC)** | 50개 |
| **개별 평가** | 200개 (40개/인) |
| **평가자 수** | 5명 |
| **1인당 평가량** | 80개 |
| **1인당 소요시간** | ~2시간 |
| **통계적 보장** | Error rate margin ±2.7% |

### 13.2 평가 항목

| 항목 | 타입 |
|------|------|
| Critical Error | Yes/No |
| Scope Alignment Failure | Yes/No |
| Information Accuracy | 0.0/0.5/1.0 |
| Visual Clarity | 1-5 Likert |
| Educational Value | 1-5 Likert |

### 13.3 타임라인

| 단계 | 일정 |
|------|------|
| 평가자 모집 | 시험 후 1주 |
| 평가 완료 | 시험 후 2주 |
| 분석 완료 | 시험 후 3주 |
| Paper 2 통합 | 시험 후 4주 |

---

## 14. 버전 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|-----------|
| 1.0 | 2026-01-04 | 초기 버전 작성 (5명 평가자 설계) |

---

**Document Status**: Canonical  
**Last Updated**: 2026-01-04  
**Owner**: MeducAI Research Team


