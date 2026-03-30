# MeducAI QA 및 Study 계획 검토 보고서

**검토일:** 2025-12-20  
**업데이트:** 2025-12-20 (이슈 해결 완료)  
**검토 범위:** `0_Protocol/06_QA_and_Study/` 전체 문서  
**버전:** QA Framework v2.0 기준

---

## ⚠️ 상태: 이슈 해결 완료 (2025-12-20)

본 보고서에서 지적한 **모든 불일치 사항이 해결되었습니다:**

✅ **S0 Non-Inferiority Primary Endpoint 통일 완료**
- QA Framework v2.0 Section 2.7 업데이트: Mean Accuracy Score (0/0.5/1), Δ = 0.05
- Statistical Analysis Plan v2.0 Section 8.1.1 업데이트: 실제 구현과 일치
- S0_Non-Inferiority_QA_and_Final_Model_Selection_Protocol.md v1.1 → SUPERSEDED 표시

✅ **Two-Layer Decision Framework 반영 완료**
- Safety gate (RD0 ≤ 0.02) + NI gate (LowerCI(d) > -Δ)
- S0_Noninferiority_Criteria_Canonical.md가 canonical reference로 명시

✅ **Reference Arm 정리 완료**
- Baseline: Arm A (default), Arm E (alternative)
- Reference_Arm_Recommendation.md에서 Arm E 권장사항 유지

**현재 상태:** 모든 문서가 실제 구현(`s0_noninferiority.py`)과 일치하며, canonical reference가 명확히 정의되어 있습니다.

---

## Executive Summary (Original)

전반적으로 **체계적이고 통계적으로 엄밀한 QA 프레임워크**가 구축되어 있습니다. 특히 S0/S1 2단계 설계, non-inferiority 프레임워크, acceptance sampling 방법론 등이 잘 설계되었습니다.

다만, **문서 간 일관성 문제**가 발견되어 즉시 해결이 필요합니다. 특히 S0 non-inferiority의 primary endpoint 정의가 문서마다 다릅니다.

**[위 이슈는 2025-12-20에 해결되었습니다. 아래 내용은 원본 검토 보고서입니다.]**

---

## 1. 주요 강점 (Strengths)

### 1.1 통계적 엄밀성
- ✅ **Non-inferiority 프레임워크**가 명확히 정의됨
- ✅ **Acceptance sampling (S1)**에서 Clopper-Pearson 방법 사용으로 통계적 보장 제공
- ✅ Sample size가 통계적으로 정당화됨 (n=838, c=2 for S1)
- ✅ Primary/secondary outcomes가 명확히 구분됨

### 1.2 연구 설계
- ✅ **2단계 설계 (S0: 모델 선택 → S1: 배포 승인)**가 목적에 적합
- ✅ **6-arm factorial design**으로 모델 비교가 체계적
- ✅ **Safety hard gate** (blocking error ≤1%)가 명확히 설정됨
- ✅ Resident-Attending pairing으로 전문성 차이 정량화 가능

### 1.3 재현성 및 감사 가능성
- ✅ **MI-CLEAR-LLM 준수** (prompt hash, config snapshot 등)
- ✅ 모든 설정이 사전 고정(freeze)되어 있음
- ✅ Versioning policy가 명확함

### 1.4 운영적 실현 가능성
- ✅ Workload 가정이 현실적 (set당 10분, S1 총 3-4시간)
- ✅ Blinding 절차가 명확함
- ✅ Assignment plan이 구체적임

---

## 2. 중요 불일치 사항 (Critical Inconsistencies)

### 🔴 **CRITICAL: S0 Non-Inferiority Primary Endpoint 불일치**

#### 발견된 불일치

1. **QA_Framework.md** (Canonical)
   - Section 2.6.1: Primary optimizer = **Editing Time (min per set)**
   - Section 2.7: Non-inferiority endpoint = **Editing Time**, Δ = **1.0 minute per set**

2. **S0_Non-Inferiority_QA_and_Final_Model_Selection_Protocol.md** (v1.1, FROZEN)
   - Section 3.1: Primary Endpoint = **Overall Card Quality (1–5 Likert)**
   - Section 3.2: Non-inferiority margin = **Δ = 0.5 (on 1–5 Likert scale)**
   - Section 10.1: Statistical model = `overall_card_quality ~ arm + ...`

3. **Statistical_Analysis_Plan.md**
   - Section 8.1.1: Endpoint = **Editing Time (minutes per set)**, Δ = **1.0 minute per set**
   - QA_Framework v2.0과 일치

#### 영향도 분석

이 불일치는 **연구 설계의 핵심**에 영향을 미칩니다:
- 평가자가 측정해야 할 주요 지표가 다름
- 통계 분석 모델이 달라짐
- Non-inferiority 판정 기준이 상이함
- 논문 Methods 섹션 작성 시 혼란 초래 가능

#### 권장 조치

**즉시 결정 필요:** 다음 중 하나를 선택하여 모든 문서를 일관되게 업데이트해야 합니다.

**옵션 A: Editing Time을 Primary로 (권장)**
- QA_Framework v2.0과 SAP v2.0이 이미 이를 채택
- 운영 효율성 최적화 목적에 부합
- Continuous variable로 통계 분석이 더 용이

**옵션 B: Overall Card Quality를 Primary로**
- S0_Non-Inferiority_QA_Protocol v1.1이 채택
- 하지만 이 문서는 "FROZEN"이지만 v2.0보다 낮은 버전
- Framework v2.0과의 정합성 문제

**권장:** QA_Framework v2.0이 최신 Canonical이므로, **옵션 A (Editing Time)**를 채택하고, S0_Non-Inferiority_QA_Protocol 문서를 v2.0으로 업데이트하거나 명시적으로 superseded 처리 필요.

---

### 🟡 **중요: Editing Time 측정 방식 불일치**

#### 발견 사항

1. **QA_Framework.md**
   - Editing Time = **minutes (continuous)**
   - Resident가 실제 편집 수행 기준으로 측정

2. **S0_QA_Form_One-Screen_Layout.md**
   - Edit Time = **bucket (0–1 / 1–3 / 3–5 / >5분)**
   - 구간값(bucket)으로 기록

3. **QA_Evaluation_Rubric.md**
   - Editing Time = **minutes (continuous)**

#### 영향도

Bucket 방식은 non-inferiority 통계 분석에 부적합합니다:
- Mixed-effects model에서 continuous variable이 필요
- Δ = 1.0 minute를 bucket으로는 정확히 판정 불가
- 통계 검정력 감소

#### 권장 조치

- **S0 QA Form을 continuous minutes로 변경** (최소한 분 단위 정수라도)
- 또는 bucket을 매우 세분화 (예: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10+ 분)
- **실제 타이머 측정 강제** (self-reported bucket 금지)

---

### 🟡 **중요: Unit of Analysis 불일치**

#### 발견 사항

1. **QA_Framework.md**
   - S0 unit = **Set** (group × arm)

2. **S0_Non-Inferiority_QA_Protocol.md**
   - Statistical unit = **Group (n = 18)**
   - "반복측정(paired) 구조" 언급

#### 영향도

통계 분석 단위가 모호하면:
- Sample size 계산이 달라짐
- Mixed-effects model의 random effects 구조가 불명확
- 통계 검정력 계산 오류 가능

#### 권장 조치

명확히 정의 필요:
- **Analysis unit: Set (n = 108 sets)**
- **Group을 random effect로** 포함: `(1 | group)`
- 18 groups는 **strata/covariate**가 아니라 **clustering unit**임을 명시

---

## 3. 개선 권장 사항 (Recommendations)

### 3.1 문서 정합성 확보

1. **Primary endpoint 통일**
   - 모든 문서에서 S0 primary endpoint를 명확히 통일
   - 권장: Editing Time (continuous, minutes)

2. **버전 관리 명확화**
   - S0_Non-Inferiority_QA_Protocol v1.1이 v2.0보다 낮은 버전인데 "FROZEN" 상태
   - Framework v2.0과 충돌 시, 어느 문서가 우선인지 명시 필요
   - 또는 superseded 문서로 명시적 처리

3. **용어 통일**
   - "Primary endpoint" vs "Primary optimizer" 용어 통일
   - "Set" vs "Group" 단위 명확화

### 3.2 통계 분석 보완

1. **Sample size justification**
   - S0: n=18 groups, 108 sets의 검정력 계산 근거 추가 권장
   - Non-inferiority에서 n=18은 작을 수 있음 (early-phase pilot로 정당화는 가능하지만)

2. **Missing data 처리**
   - Set 평가 누락 시 처리 방법 명시 필요
   - Per-protocol vs intention-to-treat 접근 명시

3. **Multiplicity 조정**
   - 6-arm 비교에서 multiple comparisons 문제
   - Pairwise comparisons vs global test 명시 필요

### 3.3 운영 절차 보완

1. **Editing Time 측정 표준화**
   - 실제 타이머 사용 강제
   - 측정 시작/종료 시점 명확화
   - "배포 가능한 수준"의 기준 명확화

2. **Adjudication 절차**
   - S1에서 Resident 불일치 시 Attending adjudication 절차 더 구체화
   - Timeline 및 우선순위 명시

3. **Quality control**
   - 평가자 훈련(calibration) 절차 추가 권장
   - Interim monitoring 계획 (있는 경우)

### 3.4 보고 및 문서화

1. **Reporting template**
   - Paper-1 Methods 섹션용 템플릿 제공 권장
   - CONSORT 확장 가이드라인 준수 고려

2. **Sensitivity analysis**
   - Primary analysis 외 sensitivity analysis 계획 명시
   - 예: per-protocol analysis, different margin values 등

---

## 4. 추가 확인 필요 사항

### 4.1 Reference Arm 정의

- Non-inferiority에서 **reference arm**이 무엇인지 명확하지 않음
- Arm E (High-End) 또는 Arm F (Benchmark) 중 어느 것을 reference로 할지?
- 또는 각 candidate arm이 모두 reference(E/F)와 비교하는가?

**권장:** Reference arm을 명시적으로 정의 (예: Arm E 또는 F 중 하나)

### 4.2 Safety Gate와 Non-inferiority의 관계

- Safety gate (blocking error ≤1%)를 통과한 arm만 NI 평가 대상인가?
- 아니면 Safety gate와 NI를 독립적으로 평가하는가?

**현재 Framework v2.0 Section 2.10에 따르면:**
1. Safety hard gate 통과 필수
2. 그 중 Editing Time 최소 arm 우선
3. NI constraint는 저비용 arm 채택 시에만 적용

이 로직이 명확하지만, **통계적 순서**를 명시하는 것이 좋습니다.

### 4.3 S1 Sampling Frame

- S1에서 "전체 그룹에서 생성된 모든 카드"가 정확히 무엇을 의미하는지
- S0에서 사용된 18 groups의 카드도 포함하는가?
- Coverage report의 구체적 기준 필요

---

## 5. 긍정적 발견 사항 (Additional Strengths)

### 5.1 이차 결과물 활용
- EDI (Expertise Discrepancy Index) 설계가 우수
- Resident-Attending pairing의 부가 가치를 잘 활용

### 5.2 Blinding 절차
- QA_Blinding_Procedure 문서가 상세함
- Surrogate ID 사용 등 실현 가능한 방법

### 5.3 IRB 준비
- Human-only QA의 canonical baseline 정의 (Appendix A)가 향후 비교 연구에 유용

---

## 6. 요약 및 우선순위

### 즉시 해결 필요 (P0)

1. ✅ **S0 Primary Endpoint 통일** (Editing Time vs Overall Quality)
2. ✅ **Editing Time 측정 방식 통일** (continuous vs bucket)
3. ✅ **Unit of Analysis 명확화** (Set vs Group)

### 단기 개선 권장 (P1)

4. Reference arm 정의
5. Sample size justification 보완
6. Missing data 처리 방법 명시
7. S0_Non-Inferiority_QA_Protocol 문서 버전 업데이트 또는 superseded 처리

### 장기 개선 권장 (P2)

8. 평가자 calibration 절차
9. Sensitivity analysis 계획
10. Reporting template 작성

---

## 7. 결론

QA Framework v2.0 전반은 **체계적이고 통계적으로 엄밀**합니다. 다만 문서 간 불일치가 있어, **즉시 문서 정합성 확보 작업이 필요**합니다.

특히 S0 non-inferiority의 primary endpoint가 문서마다 다르게 정의되어 있어, 이는 **연구 실행 전 반드시 해결해야 할 핵심 사항**입니다.

권장 조치:
1. QA_Framework v2.0을 기준으로 모든 문서 정렬
2. S0_Non-Inferiority_QA_Protocol을 v2.0으로 업데이트하거나 명시적으로 superseded 처리
3. Editing Time을 continuous variable로 측정하도록 QA Form 수정

이러한 수정 후, 본 QA Framework는 **공개 논문 발표에 적합한 수준**이 될 것입니다.

---

**검토자 주석:** 본 검토는 문서 기반 분석이며, 실제 구현 코드나 데이터 구조는 검토하지 않았습니다. 실제 실행 전 코드 레벨 검토도 권장합니다.

