# Table/Infographic 경량 평가 설계

**Status:** Canonical  
**Version:** 1.1  
**Date:** 2026-01-05  
**Purpose:** Multiagent 및 MLLM 연구를 위한 Table/Infographic 경량 평가 설계  
**참조 문헌:** Lee et al., Radiology 2025 (Visual Abstract 평가 방법론)

---

## 1. 개요

### 1.1 목적

Table/Infographic 평가를 **카드 평가와 별도로** 경량화하여 진행:
- **Paper 1 (Multi-agent)**: S5가 Table/Infographic을 제대로 판별했는지 검증
- **Paper 2 (MLLM)**: MLLM이 생성한 Table/Infographic의 품질 검증

### 1.2 설계 원칙

| 원칙 | 설명 |
|------|------|
| **경량화** | "잘 된다" 정도만 확인 (정밀 추정 아님) |
| **전공의만 참여** | 전문의 없이 9명 전공의로 진행 |
| **Partial Overlap** | Calibration subsample로 ICC 계산 |
| **PDF + Google Form** | 간단한 도구로 진행 |

---

## 2. 평가 대상

### 2.1 전체 모집단

| 항목 | 개수 |
|------|------|
| **전체 Table Infographic** | 833개 |
| **클러스터 포함 이미지** | 98개 |
| **평균 이미지/그룹** | ~2.6개 |

### 2.2 S5 Decision 분류

S5 파이프라인에서 Table/Infographic도 카드와 마찬가지로 **PASS/REGEN** 판정을 받음:

| S5 Decision | 정의 | 예상 비율 |
|-------------|------|----------|
| **PASS** | S5 평가 통과, 수정 없이 배포 가능 | ~90-95% |
| **REGEN** | Option C로 재생성됨 | ~5-10% |

> **Note**: 실제 REGEN 개수는 S5 실행 후 확정. 예상 REGEN: 40-80개

### 2.3 평가 샘플

| 항목 | 개수 | 비율 |
|------|------|------|
| **총 평가 이미지 (unique)** | 100개 | 12% |
| **- PASS pool에서** | ~90개 | - |
| **- REGEN 전수 포함** | ~10개 (또는 전체 REGEN) | - |
| **Calibration (ICC용)** | 33개 | 4% |
| **Individual** | 67개 | 8% |

### 2.4 REGEN 샘플링 전략

카드 평가와 동일하게 **REGEN 우선 포함**:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    REGEN 샘플링 전략                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Case 1: REGEN ≤ 20개                                                   │
│  ├── REGEN 전수 포함 (Census)                                           │
│  └── 나머지 (100 - REGEN개)는 PASS에서 랜덤 샘플링                        │
│                                                                         │
│  Case 2: REGEN > 20개                                                   │
│  ├── REGEN 20개 Cap (랜덤 샘플링)                                        │
│  └── 나머지 80개는 PASS에서 랜덤 샘플링                                   │
│                                                                         │
│  목적: REGEN 항목에 대한 완전성 확보 + PASS 안전성 검증                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. 평가 설계

### 3.1 설계 개요: 9명 전공의 Partial Overlap

```
┌─────────────────────────────────────────────────────────────────────────┐
│              Table/Infographic Evaluation - 경량 설계                    │
│                         (9명 전공의)                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Tier 1: Calibration (ICC 계산용, Partial Overlap)                      │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  33개 × 3명 = 99 slots                                          │   │
│  │  • 각 전공의: 11개 calibration                                   │   │
│  │  • 분과별 균등: 11분과 × 3개                                     │   │
│  │  • Inter-rater reliability (ICC, Fleiss' κ) 계산                │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  Tier 2: Individual (중복 없음)                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  67개 × 1명 = 67 slots                                          │   │
│  │  • 각 전공의: ~7-8개 individual                                  │   │
│  │  • Error rate 추정을 위한 주요 데이터                             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  총 평가량: 99 + 67 = 166 slots                                        │
│  Unique items: 33 + 67 = 100개 (12% coverage)                          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 평가자 할당

| 평가자 | Calibration | Individual | 총 평가량 | 예상 소요시간 |
|--------|-------------|------------|-----------|--------------|
| R1 | 11개 | 7개 | **18개** | ~27분 |
| R2 | 11개 | 7개 | **18개** | ~27분 |
| R3 | 11개 | 7개 | **18개** | ~27분 |
| R4 | 11개 | 7개 | **18개** | ~27분 |
| R5 | 11개 | 8개 | **19개** | ~28분 |
| R6 | 11개 | 8개 | **19개** | ~28분 |
| R7 | 11개 | 8개 | **19개** | ~28분 |
| R8 | 11개 | 8개 | **19개** | ~28분 |
| R9 | 11개 | 7개 | **18개** | ~27분 |
| **총계** | 99 slots | 67 slots | **166 slots** | **~4시간** |

### 3.3 카드 평가와 통합 시 워크로드

| 구분 | 카드 평가 | Table 평가 | 합계 |
|------|----------|-----------|------|
| 1인당 평가 | ~194개 | **+18개** | **~212개** |
| 소요시간 | ~6.5시간 | **+27분** | **~7시간** |
| 추가 부담 | - | **+9%** | - |

---

## 4. 평가 항목

### 4.1 Primary Outcomes

| 항목 | 필드명 | 타입 | 설명 |
|------|--------|------|------|
| **Critical Error** | `critical_error` | Yes/No | 임상 판단을 심각히 왜곡할 수 있는 사실 오류 |
| **Scope Alignment** | `scope_alignment_failure` | Yes/No | Group Path / objectives와의 명백한 불일치 |
| **Information Accuracy** | `information_accuracy` | 0.0/0.5/1.0 | 테이블 정보의 사실적 정확성 |

### 4.2 Secondary Outcomes

| 항목 | 필드명 | 타입 | 설명 |
|------|--------|------|------|
| **Visual Clarity** | `visual_clarity` | 1-5 Likert | 시각적 명료성, 가독성 |
| **Educational Value** | `educational_value` | 1-5 Likert | 교육적 가치, 학습 효과 |

### 4.3 Conditional Fields

| 항목 | 필드명 | 조건 | 설명 |
|------|--------|------|------|
| **Error Comment** | `error_comment` | Critical Error = Yes | 오류 내용 간략 기술 |

### 4.4 평가 기준 상세

#### Critical Error (치명 오류)

**정의**: 임상 판단이나 시험 정답을 직접적으로 잘못 유도할 가능성이 큰 오류

**예시**:
- ❌ "PE CT에서 filling defect를 정상으로 기술"
- ❌ "해부학적 구조 명칭 오류"
- ❌ "수치/단위 오류 (예: mm → cm)"

#### Scope Alignment Failure

**정의**: Group Path 또는 학습 목표와 명백히 불일치

**예시**:
- ❌ "Chest 그룹인데 Abdomen 내용이 주로 포함"
- ❌ "학습 목표와 무관한 내용이 대부분"

#### Information Accuracy

| 점수 | 정의 |
|------|------|
| **1.0** | 모든 정보가 정확하고 완전함 |
| **0.5** | 대부분 정확하나 경미한 오류 또는 누락 있음 |
| **0.0** | 핵심 정보에 오류가 있거나 오해 유발 가능 |

#### Visual Clarity / Educational Value

| 점수 | 정의 |
|------|------|
| **5** | 매우 우수 |
| **4** | 우수 |
| **3** | 보통 |
| **2** | 미흡 |
| **1** | 매우 미흡 |

---

## 5. S5 평가 워크플로우

### 5.1 평가 화면 구성 (S5 결과 표시)

카드 평가와 동일하게 **S5 평가 결과를 먼저 보여주고** Post-S5 평가 진행:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    평가 화면 레이아웃                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Image ID: TI-042                                               │   │
│  │  Group: Chest > Lung Cancer > Staging                           │   │
│  │                                                                 │   │
│  │  ╔═══════════════════════════════════════════════════════════╗ │   │
│  │  ║              S5 AI 평가 결과 (참고용)                       ║ │   │
│  │  ╠═══════════════════════════════════════════════════════════╣ │   │
│  │  ║  S5 Decision: [PASS] or [REGEN]                           ║ │   │
│  │  ║  S5 Score: 85.2/100                                       ║ │   │
│  │  ║  S5 평가 요약:                                             ║ │   │
│  │  ║  • Information Accuracy: Good                             ║ │   │
│  │  ║  • Visual Clarity: Acceptable                             ║ │   │
│  │  ║  • Scope Alignment: Aligned                               ║ │   │
│  │  ╚═══════════════════════════════════════════════════════════╝ │   │
│  │                                                                 │   │
│  │  [Table/Infographic 이미지]                                    │   │
│  │                                                                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  📝 Post-S5 Human Evaluation                                   │   │
│  │  ─────────────────────────────────────────────────────────────  │   │
│  │  Q1. Critical Error: ○ Yes  ● No                               │   │
│  │  Q2. Scope Alignment Failure: ○ Yes  ● No                      │   │
│  │  Q3. Information Accuracy: ○ 0.0  ○ 0.5  ● 1.0                 │   │
│  │  Q4. Visual Clarity: ○1 ○2 ○3 ●4 ○5                            │   │
│  │  Q5. Educational Value: ○1 ○2 ○3 ●4 ○5                         │   │
│  │                                                                 │   │
│  │  [REGEN인 경우 추가 질문]                                       │   │
│  │  Q6. Accept-as-is: ○ Yes  ○ No                                 │   │
│  │  Q7. REGEN Quality: ○1 ○2 ○3 ○4 ○5                             │   │
│  │                                                                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.2 PASS vs REGEN 평가 항목

#### 5.2.1 공통 평가 항목 (PASS & REGEN 모두)

| 항목 | 필드명 | 타입 | 목적 |
|------|--------|------|------|
| Critical Error | `critical_error` | Yes/No | 치명적 오류 탐지 |
| Scope Alignment | `scope_alignment_failure` | Yes/No | 학습목표 일치도 |
| Information Accuracy | `information_accuracy` | 0/0.5/1.0 | 정보 정확성 |
| Visual Clarity | `visual_clarity` | 1-5 | 시각적 명료성 |
| Educational Value | `educational_value` | 1-5 | 교육적 가치 |

#### 5.2.2 REGEN 전용 평가 항목

| 항목 | 필드명 | 타입 | 설명 |
|------|--------|------|------|
| **Accept-as-is** | `regen_accept` | Yes/No | 재생성 결과를 수정 없이 수용 가능한가? |
| **REGEN Quality** | `regen_quality` | 1-5 | 재생성 결과의 전반적 품질 |
| **Improvement** | `regen_improved` | Yes/No/Unknown | 원본 대비 개선되었는가? (원본 제공 시) |

### 5.3 S5 Decision별 분석 목적

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    S5 Decision별 분석 목적                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  PASS Items (~90개)                                             │   │
│  │  ─────────────────────────────────────────────────────────────  │   │
│  │  목적: S5가 PASS 판정한 것이 실제로 안전한지 검증                  │   │
│  │                                                                 │   │
│  │  분석:                                                          │   │
│  │  • False Negative Rate = (Human FAIL) / (S5 PASS)              │   │
│  │  • 타겟: FN < 5% (Table은 카드보다 느슨한 기준)                  │   │
│  │                                                                 │   │
│  │  Human FAIL 정의:                                               │   │
│  │  • Critical Error = Yes, OR                                    │   │
│  │  • Information Accuracy = 0.0                                  │   │
│  │                                                                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  REGEN Items (~10개)                                            │   │
│  │  ─────────────────────────────────────────────────────────────  │   │
│  │  목적: Option C 재생성 결과가 수용 가능한지 검증                  │   │
│  │                                                                 │   │
│  │  분석:                                                          │   │
│  │  • Accept-as-is Rate = (Accept = Yes) / (Total REGEN)          │   │
│  │  • REGEN Quality Mean                                          │   │
│  │  • 원본 대비 개선 비율 (Improvement Rate)                        │   │
│  │                                                                 │   │
│  │  Paper 1 Claim:                                                 │   │
│  │  "REGEN items were reviewed and X% were accepted as-is"        │   │
│  │                                                                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.4 REGEN 평가 상세 워크플로우

REGEN 항목의 경우 **원본(Pre-REGEN)과 재생성 결과(Post-REGEN)** 비교 가능:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    REGEN 평가 워크플로우                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Option A: Post-REGEN만 평가 (권장, 간단)                               │
│  ├── 재생성된 최종 결과물만 평가                                        │
│  ├── Accept-as-is 여부 판단                                            │
│  └── 워크로드 최소화                                                    │
│                                                                         │
│  Option B: Pre vs Post 비교 평가 (상세)                                 │
│  ├── 원본(Pre-REGEN)과 재생성(Post-REGEN) 모두 표시                    │
│  ├── 둘 다 평가 후 Improvement 여부 판단                                │
│  └── 워크로드 2배, 더 풍부한 분석 가능                                  │
│                                                                         │
│  권장: Option A (경량 설계 원칙에 부합)                                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.5 S5 결과 데이터 필요 항목

Google Form에 S5 결과를 표시하기 위해 필요한 데이터:

| 필드 | 소스 | 용도 |
|------|------|------|
| `s5_decision` | S5 output | PASS/REGEN 표시 |
| `s5_score` | S5 output | S5 점수 표시 (0-100) |
| `s5_info_accuracy` | S5 output | S5 정보정확성 평가 |
| `s5_visual_clarity` | S5 output | S5 시각명료성 평가 |
| `s5_scope_alignment` | S5 output | S5 스코프 일치도 |
| `s5_was_regenerated` | S5 output | REGEN 여부 |
| `pre_regen_image_path` | S5 output | 원본 이미지 (Option B용) |
| `post_regen_image_path` | S5 output | 재생성 이미지 |

---

## 6. 통계적 근거

### 6.1 Partial Overlap ICC의 타당성

#### 문헌 근거

> "For reliability studies, a minimum of 30 subjects and 3 raters is generally recommended."
> — Koo & Li (2016), J Chiropr Med

| 권장 사항 | 문헌 권장 | 우리 설계 | 충족 |
|----------|----------|-----------|------|
| 최소 문항 수 (n) | 30개 이상 | **33개** | ✅ |
| 최소 평가자 수 (k) | 3명 이상 | **3명** | ✅ |

#### Reliability Subsample 방법론

대규모 연구에서 전체 샘플의 일부만 중복 평가하여 ICC를 구하는 것은 **표준 관행**:

| 용어 | 설명 |
|------|------|
| **Reliability subsample** | 전체 중 일부를 다수 평가자가 평가 |
| **Calibration sample** | 평가 기준 일치도 확인용 표본 |

### 6.2 Lee et al. (2025)와의 비교

| 항목 | Lee 2025 (Radiology 게재) | 우리 설계 |
|------|---------------------------|-----------|
| **평가 대상** | Visual Abstract 75개 | Table Infographic 100개 |
| **평가자** | 4명 (편집위원급) | 9명 (전공의) |
| **ICC 방식** | 전체 Full Overlap | **Partial Overlap** |
| **ICC 결과** | < 0.16 (낮음) | 계산 예정 |
| **게재 저널** | *Radiology* | - |

**시사점**:
- Lee 2025에서도 ICC < 0.16으로 낮았으나 게재됨
- Visual content 평가는 본질적으로 주관적
- 낮은 ICC도 limitation으로 보고하면 됨

### 6.3 통계적 보장

| 메트릭 | 값 | 해석 |
|--------|-----|------|
| **Error rate margin** | ±5-6% (95% CI) | 합리적 추정 |
| **ICC 정밀도** | 95% CI 폭 ~0.30 | 문헌 권장 충족 |
| **Coverage** | 12% (100/833) | 충분한 대표성 |

---

## 7. 진행 방식: PDF + Google Form

### 7.1 방식 개요

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    진행 방식: PDF + Google Form                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Option A: PDF 별도 + Form 응답                                         │
│  ├── PDF: 이미지 모음 (ID 라벨링)                                       │
│  ├── Form: 각 ID별 평가 질문                                            │
│  └── 진행: PDF 열어두고 Form 응답                                       │
│                                                                         │
│  Option B: Form에 이미지 직접 삽입 ⭐ 권장                               │
│  ├── Form: 각 질문에 이미지 직접 삽입                                   │
│  ├── 진행: Form만 보면서 응답                                           │
│  └── 장점: 한 화면에서 완료, 이미지-질문 매칭 확실                       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Google Form 구조

```
Section 0: 평가자 정보
├── 이름/ID
└── 평가 시작 시간 (자동)

Section 1-N: 각 이미지 평가 (반복)
├── "이미지 ID: TI-001" (제목)
├── [S5 Decision Badge: PASS 또는 REGEN]
├── [S5 Score: 85.2/100]
├── [S5 평가 요약 텍스트]
├── [Table/Infographic 이미지 삽입]
│
├── === 공통 평가 항목 ===
├── Q1. Critical Error 있음? (Yes/No)
├── Q2. Scope Alignment Failure? (Yes/No)
├── Q3. Information Accuracy (0/0.5/1.0)
├── Q4. Visual Clarity (1-5)
├── Q5. Educational Value (1-5)
├── Q6. 코멘트 (선택, Critical Error=Yes 시)
│
├── === REGEN 전용 (조건부 표시) ===
├── Q7. Accept-as-is? (Yes/No) - REGEN인 경우만
├── Q8. REGEN Quality (1-5) - REGEN인 경우만
└── Q9. 원본 대비 개선됨? (Yes/No/모름) - REGEN인 경우만

Section Final: 완료
└── 제출
```

### 7.3 PASS vs REGEN Form 분기

Google Form의 조건부 표시 기능 활용:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Form 분기 로직                                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  방법 1: 단일 Form + 조건부 섹션 (권장)                                  │
│  ├── S5 Decision을 숨겨진 필드로 전달                                   │
│  ├── REGEN인 경우 추가 질문 섹션 표시                                   │
│  └── Google Form 조건부 로직 사용                                       │
│                                                                         │
│  방법 2: 별도 Form                                                      │
│  ├── PASS용 Form: 기본 5개 질문                                        │
│  ├── REGEN용 Form: 기본 5개 + REGEN 3개 질문                           │
│  └── 평가자별로 적절한 Form 배포                                        │
│                                                                         │
│  권장: 방법 1 (관리 단순화)                                              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 6.3 Form 구성

| Form 유형 | 내용 | 대상 |
|----------|------|------|
| **Calibration Form** | 공통 33개 이미지 | 9명 공유 (각자 11개씩 랜덤 배정) |
| **Individual Form 1-9** | 개별 7-8개 이미지 | 각 평가자별 별도 |

---

## 8. 샘플링 전략

### 8.1 Calibration 33개 선택

**방법**: Stratified Random Sampling

```python
# 분과별 균등 샘플링 (seed 고정)
calibration_33 = stratified_sample(
    population=833_infographics,
    n=33,
    strata='specialty',  # 11분과 × 3개
    seed=20260201
)
```

**분과별 배정**:

| 분과 | Calibration 문항 |
|------|-----------------|
| neuro_hn_imaging | 3개 |
| breast_rad | 3개 |
| thoracic_radiology | 3개 |
| interventional_radiology | 3개 |
| musculoskeletal_radiology | 3개 |
| gu_radiology | 3개 |
| cardiovascular_rad | 3개 |
| abdominal_radiology | 3개 |
| physics_qc_informatics | 3개 |
| pediatric_radiology | 3개 |
| nuclear_med | 3개 |
| **총계** | **33개** |

### 8.2 Individual 67개 선택

**방법**: Simple Random Sampling (Calibration 제외)

```python
# Calibration 제외 후 랜덤 샘플링
remaining = 833_infographics - calibration_33
individual_67 = random_sample(remaining, n=67, seed=20260201)

# 9명에게 분배
for i, resident in enumerate(residents):
    resident.assign(individual_67[i*7:(i+1)*7 + (1 if i >= 5 else 0)])
```

### 8.3 Calibration 할당 (Partial Overlap)

```python
# 각 calibration 문항을 3명에게 배정 (균형 배정)
def assign_calibration(items_33, residents_9, seed=20260201):
    """
    33개 문항을 3명씩 배정, 각 전공의가 11개씩 받도록
    """
    # Balanced Incomplete Block Design
    # 33 items × 3 raters = 99 slots
    # 9 residents × 11 items = 99 slots
    ...
```

---

## 9. 분석 계획

### 9.1 Inter-rater Reliability (Calibration 33개)

| 변수 유형 | 메트릭 | 타겟 |
|----------|--------|------|
| Binary (Critical Error, Scope) | **Fleiss' κ** | > 0.6 (substantial) |
| Ordinal (Accuracy, Clarity, Value) | **ICC(3,k)** | > 0.7 (good) |

### 9.2 Quality Metrics by S5 Decision

#### 9.2.1 PASS Items (~90개)

| 메트릭 | 분석 | 보고 형식 | 목적 |
|--------|------|-----------|------|
| **Critical Error Rate** | Proportion | % ± 95% CI | S5 False Negative 추정 |
| **Scope Failure Rate** | Proportion | % ± 95% CI | S5 판정 정확도 |
| **Information Accuracy** | Mean | Mean ± SD | 품질 수준 |
| **Visual Clarity** | Mean | Mean ± SD | 품질 수준 |
| **Educational Value** | Mean | Mean ± SD | 품질 수준 |

**S5 Validation 분석**:
```
False Negative Rate = (PASS items with Critical Error=Yes or Accuracy=0) / (Total PASS items)
Target: FN < 5% (Table은 카드보다 느슨한 기준)
```

#### 9.2.2 REGEN Items (~10개)

| 메트릭 | 분석 | 보고 형식 | 목적 |
|--------|------|-----------|------|
| **Accept-as-is Rate** | Proportion | % ± 95% CI | REGEN 수용률 |
| **REGEN Quality** | Mean | Mean ± SD | REGEN 품질 수준 |
| **Improvement Rate** | Proportion | % | 원본 대비 개선 비율 |
| **Critical Error Rate** | Proportion | % ± 95% CI | REGEN 후 오류율 |

**REGEN Validation 분석**:
```
Accept-as-is Rate = (REGEN items with Accept=Yes) / (Total REGEN items)
Claim: "X% of regenerated items were accepted without further modification"
```

### 9.3 Paper별 활용

#### Paper 1: Multi-agent 신뢰도 (S5 검증)

| 분석 | 데이터 소스 | Claim |
|------|------------|-------|
| **S5 PASS 안전성** | PASS ~90개 | "S5 PASS 판정의 FN < 5%" |
| **S5 REGEN 효과성** | REGEN ~10개 | "REGEN 후 X% 수용 가능" |
| **Pre vs Post-S5** | 전체 100개 | "S5가 Table 품질을 정확히 평가" |

#### Paper 2: MLLM 이미지 신뢰도

| 분석 | 데이터 소스 | Claim |
|------|------------|-------|
| **Table 품질** | 전체 100개 | "Critical Error Rate < X%" |
| **MLLM 생성 신뢰도** | PASS + REGEN | "Information Accuracy Mean = X" |
| **시각적 품질** | 전체 100개 | "Visual Clarity Mean = X/5" |

---

## 10. 실행 타임라인

### 10.1 준비 단계

| 단계 | 소요 시간 | 담당 |
|------|----------|------|
| 샘플링 스크립트 작성 | 30분 | 개발팀 |
| 100개 이미지 추출 | 30분 | 개발팀 |
| Google Form 제작 | 2-3시간 | 연구팀 |
| 테스트 | 30분 | 연구팀 |
| **총 준비 시간** | **~4시간** | - |

### 10.2 평가 단계

| 단계 | 소요 시간 | 담당 |
|------|----------|------|
| 평가 안내 | 10분 | 연구팀 |
| 평가 진행 | ~30분/인 | 전공의 9명 |
| **총 평가 시간** | **~30분/인** | - |

### 10.3 분석 단계

| 단계 | 소요 시간 | 담당 |
|------|----------|------|
| 데이터 정리 | 1시간 | 연구팀 |
| ICC, Fleiss' κ 계산 | 1시간 | 연구팀 |
| Quality metrics 계산 | 1시간 | 연구팀 |
| **총 분석 시간** | **~3시간** | - |

---

## 11. 논문 Methods 섹션 (Draft)

### 11.1 영문 초안

> **Table Infographic Quality Assessment**
>
> To assess the quality of MLLM-generated table infographics, we randomly sampled 100 images (12%) from 833 total infographics using stratified sampling by subspecialty. Nine radiology residents independently evaluated each image using a structured assessment form.
>
> Inter-rater reliability was assessed using a calibration subsample of 33 items, each evaluated by 3 randomly assigned residents, following established guidelines for reliability studies (Koo & Li, 2016). This partial overlap design provides sufficient statistical power while maintaining practical feasibility.
>
> Each image was evaluated for: (1) critical factual errors (binary), (2) scope alignment with learning objectives (binary), (3) information accuracy (0/0.5/1.0), (4) visual clarity (5-point Likert), and (5) educational value (5-point Likert).
>
> Inter-rater reliability was assessed using Fleiss' kappa for binary variables and intraclass correlation coefficient (ICC; two-way mixed, absolute agreement) for ordinal variables. Quality metrics were reported as proportions with 95% confidence intervals for binary outcomes and means with standard deviations for continuous outcomes.

### 11.2 한글 초안

> **Table Infographic 품질 평가**
>
> MLLM이 생성한 테이블 인포그래픽의 품질을 평가하기 위해 전체 833개 중 100개(12%)를 분과별 층화 추출하였다. 9명의 영상의학과 전공의가 구조화된 평가 양식을 사용하여 각 이미지를 독립적으로 평가하였다.
>
> 평가자 간 신뢰도는 33개의 calibration 표본을 사용하여 산출하였으며, 각 문항은 무작위로 배정된 3명의 전공의가 평가하였다. 이 partial overlap 설계는 신뢰도 연구 가이드라인(Koo & Li, 2016)을 따른다.
>
> 각 이미지에 대해 (1) 치명적 사실 오류, (2) 학습 목표 일치도, (3) 정보 정확성, (4) 시각적 명료성, (5) 교육적 가치를 평가하였다.

---

## 12. 관련 문서

| 문서 | 경로 |
|------|------|
| 기존 Table Infographic 계획 (상세) | `archived/2026-03-consolidation/Table_Infographic_Evaluation_Plan.md` (archived) |
| FINAL QA 연구 설계 | `Paper1_S5_Validation/Paper1_Paper2_Research_Design_Spec.md` |
| 3-Paper 연구 인덱스 | `MeducAI_3Paper_Research_Index.md` |

---

## 13. 참고문헌

1. **Lee T, Chae S, Park SH, et al.** Using a Vision-Language Model to Generate Visual Abstracts for Radiology Journals. *Radiology*. 2025;316(3):e251458. https://doi.org/10.1148/radiol.251458

2. **Koo TK, Li MY.** A Guideline of Selecting and Reporting Intraclass Correlation Coefficients for Reliability Research. *J Chiropr Med*. 2016;15(2):155-163.

---

## 14. 버전 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|-----------|
| 1.1 | 2026-01-05 | S5 평가 워크플로우 추가: S5 결과 표시, PASS/REGEN 분기, Accept-as-is 평가 |
| 1.0 | 2026-01-05 | 초기 버전: 경량 설계 (9명, 100개, Partial Overlap) |

---

**Document Status**: Canonical  
**Last Updated**: 2026-01-05  
**Owner**: MeducAI Research Team

