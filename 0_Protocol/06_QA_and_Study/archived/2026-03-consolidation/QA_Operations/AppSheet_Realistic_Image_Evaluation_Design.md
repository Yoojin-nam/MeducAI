# AppSheet Realistic Image 평가 도입 설계

**작성일:** 2025-01-01  
**목적:** 전문의 + 전공의 대상 Realistic Image 평가 시스템 설계 (v4.0: pre-S5에 realistic 이미지가 있는 경우에만 조건부 표시)  
**연구 배경:** S5와 무관한 별개 연구로, Realistic Image 품질 평가 및 MLLM 해석 정확도 평가를 위한 데이터 수집

---

## 0. 이미지 폴더 구조 및 파일명 규칙

### 0.1 폴더 구조
- `images/`: 기본 Anki 이미지 (CLI 인자 없이 실행 시)
- `images_anki/`: Anki 이미지 (`--image_type anki` 지정 시)
- `images_realistic/`: Realistic 이미지 (`--image_type realistic` 지정 시)
- `images_regen/`: Regen 이미지 (`--image_type regen` 지정 시) ✅ **구현 완료 (2026-01-05)**

### 0.2 파일명 규칙
- **기본 (Anki)**: `IMG__RUN_20251220__G001__E001__Q1.jpg` (suffix 없음)
- **Realistic**: `IMG__RUN_20251220__G001__E001__Q1_realistic.jpg` (확장자 바로 앞에 `_realistic` 추가)
- **Regen**: `IMG__RUN_20251220__G001__E001__Q1_regen.jpg` (확장자 바로 앞에 `_regen` 추가) ✅ **구현 완료**
  - Same RUN_TAG as baseline (폴더 + suffix로 구분)
  - S5 `prompt_patch_hint` 기반 positive regen
  - 참조: `S5_Positive_Regen_Procedure.md`

### 0.3 Realistic 이미지 생성
```bash
python 3_Code/src/04_s4_image_generator.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G \
  --image_type realistic
# 결과: images_realistic/IMG__...Q1_realistic.jpg
```

**참고**: 이미지 생성 단계에서 이미 적절한 폴더(`images_realistic/`)와 파일명(`_realistic` suffix 포함)으로 저장되므로, export 단계에서는 이미 저장된 경로를 그대로 참조합니다.

---

## 1. 연구 목적 및 범위

### 1.1 연구 목적
- **Realistic Image 품질 평가 및 MLLM 해석 정확도 평가**
- Realistic image의 교육적 효과 평가
- 전문의 수준의 이미지 품질 평가 데이터 수집

### 1.2 평가 대상
- **전공의 + 전문의 모두 평가** (v2.0 변경)
- 전문의 330문항 중 **286개**에 대해 Resident + Specialist 모두 Realistic 이미지 평가
  - **참고**: 원본 293개 spec 중 7개(2.4%)가 그래프/다이어그램 유형으로 필터링됨
  - 필터링 정책: `0_Protocol/04_Step_Contracts/Step04_S4/Realistic_Image_Filtering_Policy.md` 참조
- Realistic image는 S5 평가 대상이 아님 (별개 연구)
- 기존 Pre/Post 평가와 **시간 측정이 독립적으로** 진행

### 1.2.1 평가 구조 (v2.0, v5.0 업데이트)

| 평가자 | Illustration | Realistic | 총 평가량 |
|--------|--------------|-----------|-----------|
| **Resident (9명)** | 1,350개 | **~286개** (필터링 후) | ~1,636개 |
| **Specialist (11명)** | 330개 | ~286개 (필터링 후) | ~616개 |

> **Note (v5.0)**: 원본 293개 spec 중 그래프/다이어그램 유형 7개가 필터링되어 최종 286개 Realistic 이미지만 평가 대상임. AppSheet에서 `realistic_image_filename`이 없으면 자동으로 평가 건너뜀.

### 1.2.2 Calibration 중복 유지 (시나리오 A)

Calibration 30개가 전문의 330개에 포함된 경우:
- **Illustration**: 3명 Resident + 1명 Specialist = 4명
- **Realistic**: 같은 3명 Resident + 같은 1명 Specialist = 4명
- **Paired comparison**: 같은 평가자가 두 modality 평가

```
Calibration 30개:
- Illustration: 3명 Resident (calibration) + 1명 Specialist
- Realistic: 같은 3명 Resident + 같은 1명 Specialist
- 총 평가자/item: 4명
- 총 evaluations/item: 8 (4명 × 2 modality)
```

### 1.3 평가 항목
**Realistic Image 품질 평가 (4개 항목 - 기존 이미지 평가와 동일):**
- Image blocking error (Yes/No)
- Image anatomical accuracy (0, 0.5, 1)
- Image quality (1-5)
- Image-text consistency (0, 0.5, 1)

### 1.4 시간 측정 독립성
**⚠️ 중요:** Realistic Image 평가 시간이 멀티에이전트 평가 연구(Pre/Post 평가)에 영향을 주지 않도록:
- **별도 Slice와 Form으로 분리**
- Pre 평가 완료 후, Post 평가 전에 **선택적으로** 평가 가능
- Realistic Image 평가 시간은 Pre/Post 평가 시간과 독립적으로 측정

---

## 2. 시스템 설계

### 2.1 권한 설정 (전문의만 접근)

#### 2.1.1 Rater Role 구분
**Google Sheets에 `Raters` 테이블 추가 또는 `reviewer_master.csv` 활용:**

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `rater_email` | Email | 평가자 이메일 |
| `rater_role` | Enum | `"SPECIALIST"` 또는 `"RESIDENT"` |
| `subspecialty` | Text | 전문 분과 |

#### 2.1.2 AppSheet Security Filter
**Ratings 테이블에 Realistic Image 평가 섹션 접근 제한:**

```appsheet
AND(
  [rater_email] = USEREMAIL(),
  [rater_email].[Raters].[rater_role] = "SPECIALIST"
)
```

**별도 Slice 생성 (권장):**
- `MyRealisticImageQueue`: 전문의만 볼 수 있는 Realistic Image 평가 대기열
- Filter: `AND([rater_email] = USEREMAIL(), [rater_email].[Raters].[rater_role] = "SPECIALIST", NOT(ISBLANK([pre_submitted_ts])), ISBLANK([realistic_image_submitted_ts]))`
- **설명:** Pre 평가 완료 후, Realistic Image 평가 미완료 항목만 표시

**⚠️ 중요: Realistic Image 존재 조건 추가 (v4.0)**
- **조건부 표시:** `Cards` 테이블의 `realistic_image_filename`이 있는 경우에만 평가 항목 표시
- **이유:** pre-S5 데이터에 realistic 이미지가 있는 경우에만 평가하도록 하여, 전문의/전공의 모두 평가 가능하고 세팅이 편함
- **조건 추가:** 모든 Realistic Image 평가 관련 Show_If, Editable_If, Filter에 다음 조건 추가:
  ```appsheet
  NOT(ISBLANK([card_uid].[Cards].[realistic_image_filename]))
  ```

---

## 3. 데이터 스키마

### 3.1 Ratings 테이블 확장 (Realistic Image 평가 컬럼 추가)

#### 3.1.1 Realistic Image 평가 항목 (8개)

**Realistic Image 평가 항목 (4개 - 기존 이미지 평가와 동일):**
| 컬럼명 | 타입 | 설명 | 평가 척도 |
|--------|------|------|-----------|
| `realistic_image_blocking_error` | Yes/No | 이미지 차단 오류 | Yes/No |
| `realistic_image_anatomical_accuracy` | Enum | 이미지 해부학적 정확도 | 0, 0.5, 1 |
| `realistic_image_quality` | Enum | 이미지 품질 | 1-5 |
| `realistic_image_text_consistency` | Enum | 이미지-텍스트 일관성 | 0, 0.5, 1 |

**메타데이터 (3개):**
| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `realistic_image_started_ts` | Date/Time | Realistic Image 평가 시작 시각 |
| `realistic_image_submitted_ts` | Date/Time | Realistic Image 평가 제출 시각 |
| `realistic_image_duration_sec` | Number | Realistic Image 평가 소요 시간 (초) |

#### 3.1.2 Editable_If 조건
**전문의만 편집 가능 + Realistic Image 존재 조건 (v4.0):**
```appsheet
AND(
  [rater_email] = USEREMAIL(),
  [rater_email].[Raters].[rater_role] = "SPECIALIST",
  ISBLANK([realistic_image_submitted_ts]),
  NOT(ISBLANK([card_uid].[Cards].[realistic_image_filename]))
)
```

**전공의도 편집 가능 (v3.0 변경 반영):**
```appsheet
AND(
  [rater_email] = USEREMAIL(),
  OR(
    [rater_email].[Raters].[rater_role] = "SPECIALIST",
    [rater_email].[Raters].[rater_role] = "RESIDENT"
  ),
  ISBLANK([realistic_image_submitted_ts]),
  NOT(ISBLANK([card_uid].[Cards].[realistic_image_filename]))
)
```

#### 3.1.3 Show_If 조건 (Detail View)
**전문의 + 전공의 표시 + Realistic Image 존재 조건 (v4.0):**
```appsheet
AND(
  [rater_email] = USEREMAIL(),
  OR(
    [rater_email].[Raters].[rater_role] = "SPECIALIST",
    [rater_email].[Raters].[rater_role] = "RESIDENT"
  ),
  NOT(ISBLANK([card_uid].[Cards].[realistic_image_filename]))
)
```

---

## 4. 평가 프롬프트

### 4.1 Realistic Image 품질 평가 프롬프트

**목적:** Realistic image의 품질을 객관적으로 평가 (기존 이미지 평가 항목과 동일)

**참고:** 이 프롬프트는 `AppSheet_Column_Descriptions.md` Section 3.2와 4.6-4.9의 이미지 평가 항목 설명을 기반으로 합니다.

**프롬프트:**

```
# Realistic Image 품질 평가

이 카드에 포함된 **Realistic Image**를 평가해주세요.

## 평가 기준

### 1. Image Blocking Error (이미지 차단 오류) - Yes/No

**질문:** 이미지에 학습자나 임상 판단을 잘못 유도할 수 있는 심각한 오류가 있습니까?

**Yes (차단 오류 있음):**
- **모달리티 불일치**: 카드 텍스트에서 언급한 모달리티(CT, MRI, US 등)와 이미지의 실제 모달리티가 다름
  - 예: 카드에서 "CT 영상"이라고 했으나 이미지는 "US 영상"
- **좌우 구분 오류**: Axial convention이 잘못되어 좌우가 반대로 표시됨
  - 예: viewer-left = patient-left로 잘못 표시 (올바른 convention: viewer-left = patient-right)
- **심각한 해부학적 오류**: 해부학적 구조가 명백히 잘못되어 진단 오류 위험이 있음
  - 예: 좌심실을 우심실로 표시, 해부학적 위치가 완전히 잘못됨
- **안전성 문제**: 부적절한 내용이나 환자 식별 정보 포함

**No (차단 오류 없음):**
- 이미지에 심각한 오류가 없음
- 모달리티가 일치함
- 좌우 구분이 정확함
- 해부학적 구조가 정확하거나, 오류가 있어도 학습 목표 달성에 큰 영향을 주지 않음

---

### 2. Image Anatomical Accuracy (이미지 해부학적 정확도) - 0, 0.5, 1

**질문:** 이미지의 해부학적 구조가 의학적으로 정확합니까?

**1.0 (완전 정확):**
- 해부학적 구조가 의학적으로 완전히 정확함
- 필수 랜드마크가 모두 표시되어 있음
- 좌우 구분(Laterality)이 명확하고 정확함
- 해부학적 관계가 정확하게 표현됨

**0.5 (부분 정확):**
- 핵심 해부학적 구조는 정확하나, 일부 랜드마크가 누락되거나 불명확함
- 해부학적 관계는 대체로 정확하나 일부 표현이 모호함
- 좌우 구분은 있으나 다소 불명확함
- 전반적으로 정확하나 일부 보완 필요

**0.0 (부정확):**
- 해부학적 구조가 잘못 표시됨
- 필수 랜드마크가 누락되어 해석이 어려움
- 좌우 구분이 잘못되었거나 혼란스러움
- 해부학적 관계가 잘못 표현되어 오해의 소지가 있음
- 수정이 반드시 필요함

**평가 시 고려사항:**
- 필수 랜드마크: 이미지에 표시되어야 할 핵심 해부학적 구조가 모두 있는가?
- 좌우 구분: Axial convention (viewer-left = patient-right)이 정확한가?
- 해부학적 관계: 구조 간의 관계가 정확하게 표현되었는가?
- 의학적 정확성: 전문의가 보기에 해부학적으로 타당한가?

---

### 3. Image Quality (이미지 품질) - 1-5

**질문:** 이미지의 해상도, 가독성, 대비, 아티팩트를 종합 평가하세요.

**5 (매우 좋음):**
- 해상도가 충분하여 모든 구조를 명확히 식별 가능
- 대비가 적절하여 구조 구분이 명확함
- 아티팩트가 없거나 미미함
- 가독성이 매우 우수함
- 교육 자료로 즉시 사용 가능

**4 (좋음):**
- 해상도가 충분하여 대부분의 구조를 식별 가능
- 대비가 적절하나 일부 구조가 다소 불명확함
- 아티팩트가 있으나 해석에 큰 영향 없음
- 전반적으로 우수하나 소폭 개선 여지

**3 (보통):**
- 해상도가 기본 요건은 충족하나 일부 구조 식별이 어려움
- 대비가 다소 부족하여 구조 구분이 모호함
- 아티팩트가 있어 일부 해석에 영향
- 교육 자료로 사용 가능하나 개선 권장

**2 (나쁨):**
- 해상도가 부족하여 핵심 구조 식별이 어려움
- 대비가 부족하여 구조 구분이 어려움
- 아티팩트가 많아 해석에 상당한 영향
- 교육 자료로 사용하기에는 부족
- 상당한 개선 필요

**1 (매우 나쁨):**
- 해상도가 매우 부족하여 구조 식별이 거의 불가능
- 대비가 매우 부족하여 구조 구분이 불가능
- 심각한 아티팩트로 해석이 어려움
- 교육 자료로 부적합
- 전면적 수정 또는 재생성 필요

**평가 시 고려사항:**
- 해상도: 이미지 해상도가 충분한가? 구조를 명확히 식별할 수 있는가?
- 가독성: 해부학적 구조를 명확히 구분할 수 있는가?
- 아티팩트: 이미지에 아티팩트가 있는가? 해석에 영향을 주는가?
- 대비: 구조 간 대비가 적절한가? 모든 구조를 구분할 수 있는가?

---

### 4. Image-Text Consistency (이미지-텍스트 일관성) - 0, 0.5, 1

**질문:** 이미지가 카드의 front/back 텍스트와 일치하고 진단/소견을 뒷받침합니까?

**1.0 (완전 일치):**
- 이미지가 카드 텍스트와 완전히 일치함
- 이미지가 진단/소견을 명확히 뒷받침함
- 텍스트에서 언급한 소견이 이미지에서 명확히 확인됨
- 이미지와 텍스트가 서로 보완적으로 작용함

**0.5 (대체로 일치):**
- 이미지가 카드 텍스트와 대체로 일치하나, 일부 불일치가 있음
- 이미지가 진단/소견을 대체로 뒷받침하나, 일부 모호함
- 텍스트에서 언급한 소견이 이미지에서 대부분 확인되나 일부 누락
- 전반적으로 일치하나 일부 보완 필요

**0.0 (불일치):**
- 이미지가 카드 텍스트와 명백히 불일치함
- 이미지가 진단/소견을 뒷받침하지 않음
- 텍스트에서 언급한 소견이 이미지에서 확인되지 않음
- 이미지와 텍스트가 서로 모순됨
- 수정이 반드시 필요함

**평가 시 고려사항:**
- 텍스트 일치: 카드의 front/back 텍스트에서 언급한 내용이 이미지에 나타나는가?
- 진단 뒷받침: 이미지가 카드에서 설명하는 진단/소견을 뒷받침하는가?
- 소견 확인: 텍스트에서 언급한 핵심 소견이 이미지에서 확인되는가?
- 모순 여부: 이미지와 텍스트가 서로 모순되는가?

**주의사항:**
- 이미지가 텍스트를 단순히 반복하는 것이 아니라, 텍스트를 시각적으로 뒷받침해야 합니다
- 텍스트에서 언급하지 않은 소견이 이미지에 나타나는 것은 문제가 아닙니다 (추가 정보는 허용)
- 하지만 텍스트에서 언급한 핵심 소견이 이미지에 없으면 문제입니다

---

## 전체 주의사항

- 이 평가는 **S5 결과와 무관**합니다
- Realistic image만 보고 평가하세요
- 객관적이고 일관된 기준을 적용하세요
- 기존 이미지 평가 항목(`image_blocking_error_post`, `image_anatomical_accuracy_post`, `image_quality_post`, `image_text_consistency_post`)과 **동일한 기준**을 사용합니다
- 평가 시간은 Pre/Post 평가 시간과 독립적으로 측정됩니다
```

---

## 5. 워크플로우 설계

### 5.1 전체 워크플로우 (v2.0 - 전공의 + 전문의)

**Pre 평가 완료 후 워크플로우 (자동 조건부 네비게이션):**

```
[Pre 평가 Submit 버튼 클릭]
    ↓
[Pre 평가 제출 완료]
    ↓
┌─────────────────────────────────────────┐
│ Realistic Image가 있는가?               │
└─────────────────────────────────────────┘
    │                      │
    YES                    NO
    ↓                      ↓
[RealisticImage_Form]    [Post 평가 Form]
    (자동 이동)            (자동 이동)
    ↓
[Submit Realistic Image]
    ↓
[Post 평가 Form]
    (자동 이동)
```

### 5.2 워크플로우 상세

#### 5.2.1 Pre 평가 Submit 후 조건부 자동 네비게이션

**설계 방식:**
- Pre 평가 Form의 Submit 버튼을 누르면, Submit 액션의 On success에서 조건부로 네비게이션
- **Realistic Image가 있는 경우**: RealisticImage_Form으로 자동 이동
- **Realistic Image가 없는 경우**: Post 평가 Form으로 자동 이동

**전문의 (모든 카드에 Realistic Image 포함):**
- Pre 평가 Submit → 자동으로 RealisticImage_Form으로 이동
- Realistic Image 평가 완료 → Post 평가 Form으로 자동 이동

**전공의 (일부 카드에만 Realistic Image 포함):**
- Pre 평가 Submit:
  - **Realistic Image가 있는 경우**: 자동으로 RealisticImage_Form으로 이동
    - Realistic Image 평가 완료 → Post 평가 Form으로 자동 이동
  - **Realistic Image가 없는 경우**: 자동으로 Post 평가 Form으로 이동

**구현 방법 (AppSheet 액션):**
- Pre 평가 Submit 액션의 On success에 두 개의 Navigate 액션 추가:
  1. **Navigate to RealisticImage_Form** (Run_If: `NOT(ISBLANK([card_uid].[Cards].[realistic_image_filename]))`)
  2. **Navigate to Post_Form** (Run_If: `ISBLANK([card_uid].[Cards].[realistic_image_filename]))`)
- AppSheet는 Run_If 조건이 True인 첫 번째 액션만 실행하므로, Realistic Image가 있으면 RealisticImage_Form으로, 없으면 Post_Form으로 이동

#### 5.2.2 Illustration 평가 완료 후 (참고)
- **전공의**: 1,350개 Illustration 평가 완료 후 → 330개 Realistic 평가
- **전문의**: 330개 Illustration 평가 완료 후 → 330개 Realistic 평가

#### 5.2.2 Realistic Image 평가 (전공의 + 전문의) (v4.0 업데이트)
- **Slice**: `MyRealisticImageQueue`
  - **전공의 Filter**: `AND([rater_email] = USEREMAIL(), [card_uid] IN [specialist_330_pool], NOT(ISBLANK([illustration_submitted_ts])), ISBLANK([realistic_image_submitted_ts]), NOT(ISBLANK([card_uid].[Cards].[realistic_image_filename])))`
  - **전문의 Filter**: `AND([rater_email] = USEREMAIL(), [rater_email].[Raters].[rater_role] = "SPECIALIST", NOT(ISBLANK([illustration_submitted_ts])), ISBLANK([realistic_image_submitted_ts]), NOT(ISBLANK([card_uid].[Cards].[realistic_image_filename])))`
  - **⚠️ 중요:** `realistic_image_filename`이 있는 경우에만 Slice에 표시됨
- **Form**: `RealisticImage_Form`
  - 별도 Form으로 시간 측정 독립성 보장
  - Illustration 평가와 완전히 분리된 평가 세션
  - **⚠️ 중요:** `realistic_image_filename`이 있는 카드에 대해서만 Form이 표시됨

#### 5.2.3 Calibration 처리 (Partial Overlap)
- **Calibration 30개**: Illustration에서 3명 Resident가 평가한 문항
- **Realistic에서도 같은 3명이 평가**: Paired comparison 일관성 유지
- **전문의**: 330개 모두 평가 (Calibration 포함)

#### 5.2.4 전공의 Realistic 평가량

| 항목 | 값 |
|------|-----|
| Calibration (중복) | 30개 × 3명 = 90 slots |
| Non-calibration | 300개 × 1명 = 300 slots |
| **총 Realistic slots** | **390** |
| **1인당 추가 평가** | 390 ÷ 9 = **~43개** |

### 5.3 시간 측정 독립성

**Pre/Post 평가 시간:**
- `pre_started_ts` → `pre_submitted_ts` → `pre_duration_sec`
- `post_started_ts` → `post_submitted_ts` → `post_duration_sec`

**Realistic Image 평가 시간 (독립):**
- `realistic_image_started_ts` → `realistic_image_submitted_ts` → `realistic_image_duration_sec`
- Pre/Post 평가 시간에 **영향 없음**

---

## 6. 데이터 스키마

### 6.1 Ratings 테이블 확장 (권장)

**목적:** 기존 Ratings 테이블에 Realistic Image 평가 컬럼 추가

**추가 컬럼 (7개):**

```python
# Realistic Image 평가 항목 (4개 - 기존 이미지 평가와 동일)
"realistic_image_blocking_error",          # Yes/No
"realistic_image_anatomical_accuracy",     # Enum: 0, 0.5, 1
"realistic_image_quality",                 # Enum: 1-5
"realistic_image_text_consistency",        # Enum: 0, 0.5, 1

# 메타데이터 (3개)
"realistic_image_started_ts",               # Date/Time
"realistic_image_submitted_ts",            # Date/Time
"realistic_image_duration_sec",            # Number
```

**CSV Export 순서:**
```python
ratings_fieldnames = [
    # ... 기존 컬럼들 ...
    # Realistic Image 평가 (전문의 전용, 시간 독립)
    "realistic_image_blocking_error",
    "realistic_image_anatomical_accuracy",
    "realistic_image_quality",
    "realistic_image_text_consistency",
    "realistic_image_started_ts",
    "realistic_image_submitted_ts",
    "realistic_image_duration_sec",
]
```

**장점:**
- 기존 시스템과 통합 용이
- 최소한의 변경으로 구현 가능
- 데이터 분석이 단순함
- Pre/Post 평가와 동일 테이블에서 관리

**단점:**
- 상세한 코멘트나 근거 기록이 어려움 (필요 시 LongText 컬럼 추가 가능)

---

## 7. AppSheet 설정 상세

### 7.1 Slice 생성: `MyRealisticImageQueue`

**AppSheet 메뉴 경로:** `Data` → `Tables` → `Ratings` → `+ Add slice`

1. `Data` → `Tables` → `Ratings` 클릭
2. `+ Add slice` 클릭
3. Slice name: `MyRealisticImageQueue`
4. Filter expression:
   ```
   AND(
     [rater_email] = USEREMAIL(),
     OR(
       [rater_email].[Raters].[rater_role] = "SPECIALIST",
       [rater_email].[Raters].[rater_role] = "RESIDENT"
     ),
     NOT(ISBLANK([pre_submitted_ts])),
     ISBLANK([realistic_image_submitted_ts]),
     NOT(ISBLANK([card_uid].[Cards].[realistic_image_filename]))
   )
   ```
   **설명:**
   - 전문의 + 전공의 접근 가능 (v3.0)
   - Pre 평가 완료 후에만 표시
   - Realistic Image 평가 미완료 항목만 표시
   - **⚠️ 중요 (v4.0):** `Cards` 테이블의 `realistic_image_filename`이 있는 경우에만 표시
5. Sort by: `assignment_order` (ascending)
6. `Save`

### 7.2 Form 생성: `RealisticImage_Form`

**AppSheet 메뉴 경로:** `UX` → `Views` → `+ Add view` → `Form`

1. `UX` → `Views` → `+ Add view` 클릭
2. View name: `RealisticImage_Form`
3. View type: `Form` 선택
4. Table: `Ratings` 선택
5. **Form 필드 추가:**
   - `view_question_image` (Virtual Column) - Realistic Image 표시
     - **Show_If**: `NOT(ISBLANK([card_uid].[Cards].[realistic_image_filename]))` (v4.0)
   - `realistic_image_blocking_error` (Yes/No)
     - **Show_If**: `NOT(ISBLANK([card_uid].[Cards].[realistic_image_filename]))` (v4.0)
   - `realistic_image_anatomical_accuracy` (Enum: 0, 0.5, 1)
     - **Show_If**: `NOT(ISBLANK([card_uid].[Cards].[realistic_image_filename]))` (v4.0)
   - `realistic_image_quality` (Enum: 1-5)
     - **Show_If**: `NOT(ISBLANK([card_uid].[Cards].[realistic_image_filename]))` (v4.0)
   - `realistic_image_text_consistency` (Enum: 0, 0.5, 1)
     - **Show_If**: `NOT(ISBLANK([card_uid].[Cards].[realistic_image_filename]))` (v4.0)
6. **Form 설정:**
   - `Auto save`: ON
   - `Finish view`: `MyRealisticImageQueue` (또는 `Ratings_List`)
7. `Save`

### 7.3 액션 설정

#### 7.3.1 "Start Realistic Image Evaluation" 액션

**AppSheet 메뉴 경로:** `UX` → `Actions` → `+ Add action`

1. `UX` → `Actions` → `+ Add action`
2. Action name: `Start Realistic Image Evaluation`
3. Table: `Ratings` 선택
4. Action type: `Update row`
5. Row: `Current row`
6. Update column: `realistic_image_started_ts`
7. Update value: `NOW()`
8. Show_If:
   ```
   AND(
     [rater_email] = USEREMAIL(),
     OR(
       [rater_email].[Raters].[rater_role] = "SPECIALIST",
       [rater_email].[Raters].[rater_role] = "RESIDENT"
     ),
     NOT(ISBLANK([pre_submitted_ts])),
     ISBLANK([realistic_image_started_ts]),
     NOT(ISBLANK([card_uid].[Cards].[realistic_image_filename]))
   )
   ```
   **⚠️ 중요 (v4.0):** `realistic_image_filename`이 있는 경우에만 버튼 표시
9. Run_If: 동일하게 설정
10. On success → `+ Add action` → `Navigate`
    - View: `RealisticImage_Form`
    - Row: `Current row`
11. `Save`

#### 7.3.2 "Submit Realistic Image Evaluation" 액션

**AppSheet 메뉴 경로:** `UX` → `Actions` → `+ Add action`

1. `UX` → `Actions` → `+ Add action`
2. Action name: `Submit Realistic Image Evaluation`
3. Table: `Ratings` 선택
4. Action type: `Update row`
5. Row: `Current row`
6. Update column: `realistic_image_submitted_ts`
7. Update value: `NOW()`
8. Show_If:
   ```
   AND(
     [rater_email] = USEREMAIL(),
     OR(
       [rater_email].[Raters].[rater_role] = "SPECIALIST",
       [rater_email].[Raters].[rater_role] = "RESIDENT"
     ),
     NOT(ISBLANK([realistic_image_started_ts])),
     ISBLANK([realistic_image_submitted_ts]),
     NOT(ISBLANK([card_uid].[Cards].[realistic_image_filename]))
   )
   ```
   **⚠️ 중요 (v4.0):** `realistic_image_filename`이 있는 경우에만 버튼 표시
9. Run_If:
   ```
   AND(
     NOT(ISBLANK([realistic_image_started_ts])),
     ISBLANK([realistic_image_submitted_ts]),
     ISNOTBLANK([realistic_image_blocking_error]),
     ISNOTBLANK([realistic_image_anatomical_accuracy]),
     ISNOTBLANK([realistic_image_quality]),
     ISNOTBLANK([realistic_image_text_consistency])
   )
   ```
   **설명:** 모든 평가 항목이 채워져야 제출 가능
10. On success → `+ Add action` → `Update row`
    - Update column: `realistic_image_duration_sec`
    - Update value: `([realistic_image_submitted_ts] - [realistic_image_started_ts]) * 24 * 60 * 60`
11. On success → `+ Add action` → `Navigate`
    - View: `MyRealisticImageQueue` (또는 다음 항목)
12. `Save`

### 7.4 컬럼 타입 설정

#### 7.4.1 `realistic_image_blocking_error`
1. `Data` → `Tables` → `Ratings` → `realistic_image_blocking_error` 클릭
2. `Type`: `Yes/No` 선택
3. `Display name`: `이미지 차단 오류 (Realistic Image)`
4. `Description`: 기존 `image_blocking_error`와 동일한 설명 사용
5. `Save`

#### 7.4.2 `realistic_image_anatomical_accuracy`
1. `Data` → `Tables` → `Ratings` → `realistic_image_anatomical_accuracy` 클릭
2. `Type`: `Enum` 선택
3. `Options`: `0`, `0.5`, `1` (각각 한 줄씩)
4. `Display name`: `이미지 해부학적 정확도 (Realistic Image)`
5. `Description`: 기존 `image_anatomical_accuracy`와 동일한 설명 사용
6. `Save`

#### 7.4.3 `realistic_image_quality`
1. `Data` → `Tables` → `Ratings` → `realistic_image_quality` 클릭
2. `Type`: `Enum` 선택
3. `Options`: `1`, `2`, `3`, `4`, `5` (각각 한 줄씩)
4. `Display name`: `이미지 품질 (Realistic Image)`
5. `Description`: 기존 `image_quality`와 동일한 설명 사용
6. `Save`

#### 7.4.4 `realistic_image_text_consistency`
1. `Data` → `Tables` → `Ratings` → `realistic_image_text_consistency` 클릭
2. `Type`: `Enum` 선택
3. `Options`: `0`, `0.5`, `1` (각각 한 줄씩)
4. `Display name`: `이미지-텍스트 일관성 (Realistic Image)`
5. `Description`: 기존 `image_text_consistency`와 동일한 설명 사용
6. `Save`

### 7.5 Editable_If 조건

**Realistic Image 평가 필드 (v4.0 업데이트):**
```appsheet
AND(
  [rater_email] = USEREMAIL(),
  OR(
    [rater_email].[Raters].[rater_role] = "SPECIALIST",
    [rater_email].[Raters].[rater_role] = "RESIDENT"
  ),
  NOT(ISBLANK([realistic_image_started_ts])),
  ISBLANK([realistic_image_submitted_ts]),
  NOT(ISBLANK([card_uid].[Cards].[realistic_image_filename]))
)
```
**⚠️ 중요 (v4.0):** 
- 전문의 + 전공의 모두 편집 가능 (v3.0 변경 반영)
- `realistic_image_filename`이 있는 경우에만 편집 가능

---

## 8. 구현 단계

### 8.1 Phase 1: 데이터 스키마 확장
1. **Google Sheets 컬럼 추가**: Ratings 탭에 7개 컬럼 추가
2. **CSV Export 스크립트 업데이트**: `export_appsheet_tables.py`
3. **Raters 테이블 생성**: `reviewer_master.csv` 기반 또는 Google Sheets에 직접 생성

### 8.2 Phase 2: AppSheet 설정
1. **Slice 생성**: `MyRealisticImageQueue`
2. **Form 생성**: `RealisticImage_Form`
3. **액션 생성**: "Start Realistic Image Evaluation", "Submit Realistic Image Evaluation"
4. **컬럼 타입 설정**: Realistic Image 평가 필드 (Section 7.4 참조)
5. **Editable_If 설정**: Realistic Image 평가 필드

### 8.3 Phase 3: 평가 프롬프트 배포
1. **프롬프트**: RealisticImage_Form의 Description에 평가 기준 추가

### 8.4 Phase 4: 테스트 및 검증
1. **소규모 테스트**: 전문의 1-2명으로 테스트
2. **시간 측정 검증**: `realistic_image_duration_sec`가 Pre/Post 시간과 독립적으로 측정되는지 확인
3. **권한 설정 검증**: Resident는 접근 불가 확인
4. **워크플로우 검증**: 
   - Pre → Realistic Image (있는 경우) → Post 순서 확인
   - Realistic Image가 없는 경우 Pre → Post 직접 이동 확인
   - 조건부 버튼 표시 (Realistic Image가 있는 경우에만 "Start Realistic Image Evaluation" 버튼 표시) 확인

---

## 9. 프롬프트 공개 가능성 평가

### 9.1 Realistic Image 품질 평가 프롬프트
**공개 가능성: ⭐⭐⭐⭐⭐ (매우 높음)**

**이유:**
- 평가 기준이 명확하고 객관적임
- 의학적 전문 용어 사용이 적절함
- 연구 재현성을 위해 공개가 유리함
- 논문에 포함하기에 적합한 수준

**개선 제안:**
- 평가 척도별 예시 케이스 추가 (선택사항)
- Inter-rater agreement를 위한 구체적 가이드라인 추가 (선택사항)

---

## 10. 권장 사항

### 10.1 워크플로우 통합
- **Pre 평가 완료 후**: 전문의에게 `MyRealisticImageQueue` 표시
- **선택적 평가**: Realistic Image 평가는 필수가 아님 (건너뛰고 Post 평가 진행 가능)
- **시간 독립성**: Realistic Image 평가 시간은 Pre/Post 평가 시간과 완전히 분리

### 10.2 데이터 수집 전략
- **전문의 배정**: Realistic Image 평가는 Pre 평가 완료 항목에 대해 자동으로 대기열에 표시
- **배치 관리**: 기존 Pre/Post 평가와 동일 배치로 관리 (별도 배정 불필요)
- **진행률 추적**: `MyRealisticImageQueue` Slice로 진행률 모니터링

### 10.3 사용자 경험
- **명확한 안내**: Realistic Image 평가는 선택사항임을 명시
- **빠른 접근**: `MyRealisticImageQueue`에서 바로 평가 가능
- **시간 측정**: 별도 Form으로 시간 측정 독립성 보장

---

## 11. 참고 문서

- **기본 설정 가이드**: `AppSheet_QA_Setup_Guide.md`
- **프로덕션 강화 가이드**: `AppSheet_QA_Production_Hardening.md`
- **이미지 평가 요약**: `AppSheet_Image_Evaluation_Summary.md`
- **컬럼 설명**: `AppSheet_Column_Descriptions.md`
  - Section 3.2: 이미지 평가 항목 (간결 버전)
  - Section 4.6-4.9: 이미지 평가 항목 상세 안내문
  - **참고:** Realistic Image 평가는 기존 이미지 평가 항목과 동일한 기준을 사용합니다

---

**문서 버전:** 5.0  
**최종 업데이트:** 2026-01-05  
**주요 변경사항 (v5.0):**
- **Realistic 이미지 최종 개수 반영**: 293개 → 286개 (그래프/다이어그램 유형 7개 필터링)
- **필터링 정책 문서 참조 추가**: `Realistic_Image_Filtering_Policy.md`
- **통계적 영향 확인**: 2.4% 감소는 통계적 유의성에 영향 없음

**이전 변경사항 (v4.0):**
- **조건부 표시 추가**: `Cards` 테이블의 `realistic_image_filename`이 있는 경우에만 평가 항목 표시
- **이유**: pre-S5 데이터에 realistic 이미지가 있는 경우에만 평가하도록 하여, 전문의/전공의 모두 평가 가능하고 세팅이 편함
- 모든 Show_If, Editable_If, Filter 조건에 `NOT(ISBLANK([card_uid].[Cards].[realistic_image_filename]))` 추가
- Slice, Form, 액션 버튼 등 모든 Realistic Image 평가 관련 UI 요소에 조건 추가

**이전 변경사항 (v3.0):**
- **전공의도 Realistic 평가** (기존: 전문의만)
- 전공의 330개 Realistic 추가 (1인당 ~43개)
- **Calibration 중복 유지** (시나리오 A): Illustration과 같은 3명이 Realistic도 평가
- Calibration 30개에서 4명(3 Resident + 1 Specialist)이 Realistic 평가
- Paired comparison을 위한 동일 평가자 구조
- 전공의 총 workload: ~193개/인 (Illustration 150 + Realistic ~43)

**이전 변경사항 (v2.0):**
- Infographic 비교 평가 제거
- 별도 Slice와 Form 설계 추가
- 시간 측정 독립성 강조
- 워크플로우 상세화


