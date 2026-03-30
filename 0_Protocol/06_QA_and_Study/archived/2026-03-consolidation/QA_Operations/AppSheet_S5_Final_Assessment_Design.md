# AppSheet S5 Final Assessment 단계 설계 가이드

**작성일:** 2025-01-01  
**목적:** 멀티에이전트 시스템의 Self-Improvement 과정을 검증하는 S5 (Final Assessment) 단계 구현  
**상태:** 설계 단계 (구현 전)

---

## 1. 개요

### 1.1 S5 단계의 목적

S5 단계는 **AI의 자기 개선(Self-Improvement) 과정을 검증**하는 단계입니다:

1. **AI 자가 평가 검증**: 멀티에이전트가 스스로 매긴 점수의 신뢰도 평가
2. **수정된 결과물 검토**: 낮은 점수로 인해 재생성된 콘텐츠(텍스트/이미지) 검토
3. **최종 수용 결정**: AI의 수정 제안을 최종 판독에 반영할지 결정

### 1.2 워크플로우

```
Pre-Reading → Reveal S5 → Post-Reading → S5 Final Assessment → Complete
   (1단계)      (2단계)       (3단계)          (4단계)            (완료)
```

**조건부 활성화:**
- S5 단계는 멀티에이전트 평가 점수가 특정 기준(예: 70점 미만) 이하일 때만 활성화
- 또는 모든 경우에 활성화하되, 재생성 콘텐츠는 조건부로 표시

---

## 2. 데이터 모델 설계

### 2.1 Ratings 테이블에 추가할 컬럼

#### 2.1.1 AI 자가 평가 관련

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `ai_self_reliability` | Number (1-5) | AI 자가 평가 신뢰도 (1-5 Likert) |
| `ai_self_reliability_comment` | LongText | 신뢰도 평가 근거 (선택) |

**Display Name / Description:**
- **Display Name**: `AI 자가 평가 신뢰도`
- **Description**: `멀티에이전트가 스스로 도출한 평가 결과가 타당하다고 생각하십니까?`

#### 2.1.2 재생성 콘텐츠 관련

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `s5_regenerated_front` | LongText | 재생성된 문제 텍스트 (Virtual Column 또는 Reference) |
| `s5_regenerated_image` | Image | 재생성된 이미지 (Virtual Column 또는 Reference) |
| `s5_regenerated_back` | LongText | 재생성된 정답 텍스트 (Virtual Column 또는 Reference) |
| `s5_regeneration_trigger_score` | Number | 재생성을 트리거한 평가 점수 (예: 70점 미만) |

**Virtual Column 설계:**
- `s5_regenerated_front`: `[card_uid].[S5_regenerated].[front]` (S5 테이블에 재생성 데이터 저장)
- `s5_regenerated_image`: `[card_uid].[S5_regenerated].[image_filename]`
  - **Regen 이미지 경로**: `images_regen/IMG__*_regen.jpg` (Same RUN_TAG, 폴더/suffix로 구분) ✅ **구현 완료 (2026-01-05)**
  - S5 `prompt_patch_hint` 기반 positive regen
  - 참조: `S5_Positive_Regen_Procedure.md`
- `s5_regenerated_back`: `[card_uid].[S5_regenerated].[back]`

#### 2.1.3 수용 결정 관련

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `accept_ai_correction` | Enum | AI 수정안 수용 여부 |
| `ai_correction_quality` | Number (1-5) | AI 수정안의 품질 평가 (1-5 Likert) |
| `ai_correction_comment` | LongText | 수용/거부 근거 |
| `s5_started_ts` | Date/Time | S5 단계 시작 시점 (Initial Value: `NOW()`) |
| `s5_submitted_ts` | Date/Time | S5 단계 제출 시점 |
| `s5_duration_sec` | Number | S5 단계 소요 시간 (초) |

**Enum 옵션 (`accept_ai_correction`):**
- `ACCEPT` - AI 수정안 수용
- `REJECT` - 초기안 유지
- `PARTIAL` - 부분 수용 (향후 확장)

**Display Name / Description:**
- **Display Name**: `AI 수정안 수용 여부`
- **Description**: `AI의 수정 사항을 최종 결과로 채택하시겠습니까? 아니면 초기안을 유지하시겠습니까?`

---

## 3. S5 슬라이스 설계

### 3.1 슬라이스 생성

**AppSheet 메뉴 경로:** `Data` → `Tables` → `Ratings` → `Slices` → `+ Add slice`

**슬라이스명:** `SLICE_S5`

**Filter 조건:**
```
AND(
  NOT(ISBLANK([post_submitted_ts])),
  ISBLANK([s5_submitted_ts])
)
```

**설명:**
- Post 단계가 완료되었고 (`post_submitted_ts`가 있음)
- S5 단계가 아직 완료되지 않았을 때 (`s5_submitted_ts`가 없음)

**Update Mode:** `Updates` (S5 단계에서 데이터 수정 필요)

---

## 4. Detail View 설계

### 4.1 컬럼 순서

**AppSheet 메뉴 경로:** `UX` → `Views` → `Ratings_Detail` (기존 Detail View에 추가)

1. **[기존 Pre/Post 단계 컬럼들]**
   - Pre Input Fields
   - Submit Pre-S5 Rating
   - Reveal S5 Results
   - S5 Reference Section
   - Post Input Fields
   - Submit Post-S5 Rating

2. **[S5 Final Assessment 섹션]** ⭐ **신규**
   - **"Start S5 Final Assessment" (Action Button)**
     - `Show_If`: `AND(NOT(ISBLANK([post_submitted_ts])), ISBLANK([s5_started_ts]))`
     - `Run_If`: `NOT(ISBLANK([post_submitted_ts]))`
     - 액션: `Update row` → `s5_started_ts` = `NOW()`

   - **"S5 Final Assessment" (Section Header)**
     - `Show_If`: `NOT(ISBLANK([s5_started_ts]))`

   - **AI 자가 평가 신뢰도**
     - `ai_self_reliability` (Number, 1-5)
     - `Show_If`: `NOT(ISBLANK([s5_started_ts]))`
     - `Editable_If`: `AND(NOT(ISBLANK([s5_started_ts])), ISBLANK([s5_submitted_ts]))`
     - `Required_If`: `AND(NOT(ISBLANK([s5_started_ts])), ISBLANK([s5_submitted_ts]))`

   - **재생성된 콘텐츠 섹션** (조건부)
     - `s5_regenerated_front` (Virtual Column)
     - `s5_regenerated_image` (Virtual Column)
     - `s5_regenerated_back` (Virtual Column)
     - `Show_If`: `AND(NOT(ISBLANK([s5_started_ts])), [card_uid].[S5_one].[s5_decision] <> "PASS")`
     - **설명:** S5 decision이 REGEN인 경우에만 표시 (PASS가 아닌 경우)

   - **AI 수정안 수용 여부**
     - `accept_ai_correction` (Enum)
     - `Show_If`: `AND(NOT(ISBLANK([s5_started_ts])), [card_uid].[S5_one].[s5_decision] <> "PASS")`
     - `Editable_If`: `AND(NOT(ISBLANK([s5_started_ts])), ISBLANK([s5_submitted_ts]), [card_uid].[S5_one].[s5_decision] <> "PASS")`
     - `Required_If`: `AND(NOT(ISBLANK([s5_started_ts])), ISBLANK([s5_submitted_ts]), [card_uid].[S5_one].[s5_decision] <> "PASS")`

   - **AI 수정안 품질 평가**
     - `ai_correction_quality` (Number, 1-5)
     - `Show_If`: `AND(NOT(ISBLANK([s5_started_ts])), [card_uid].[S5_one].[s5_decision] <> "PASS")`
     - `Editable_If`: `AND(NOT(ISBLANK([s5_started_ts])), ISBLANK([s5_submitted_ts]), [card_uid].[S5_one].[s5_decision] <> "PASS")`

   - **수용/거부 근거**
     - `ai_correction_comment` (LongText)
     - `Show_If`: `AND(NOT(ISBLANK([s5_started_ts])), [card_uid].[S5_one].[s5_decision] <> "PASS")`
     - `Editable_If`: `AND(NOT(ISBLANK([s5_started_ts])), ISBLANK([s5_submitted_ts]), [card_uid].[S5_one].[s5_decision] <> "PASS")`

   - **"Submit S5 Final Assessment" (Action Button)**
     - `Show_If`: `AND(NOT(ISBLANK([s5_started_ts])), ISBLANK([s5_submitted_ts]))`
     - `Run_If`: 아래 조건 참조

---

## 5. 액션 설계

### 5.1 "Start S5 Final Assessment" 액션

**AppSheet 메뉴 경로:** `UX` → `Actions` → `+ Add action`

1. `Action name`: `Start S5 Final Assessment`
2. `Table`: `Ratings` 선택
3. `Action type`: `Update row`
4. `Row`: `Current row`
5. `Update column`: `s5_started_ts`
6. `Update value`: `NOW()`
7. `Run_If`: `AND(NOT(ISBLANK([post_submitted_ts])), ISBLANK([s5_started_ts]))`
8. `On success`: (선택) `Navigate` → `Ratings_Detail` (현재 행 유지)

---

### 5.2 "Submit S5 Final Assessment" 액션

**AppSheet 메뉴 경로:** `UX` → `Actions` → `+ Add action`

1. `Action name`: `Submit S5 Final Assessment`
2. `Table`: `Ratings` 선택
3. `Action type`: `Update row`
4. `Row`: `Current row`
5. `Update column`: `s5_submitted_ts`
6. `Update value`: `NOW()`
7. `Run_If`:
   ```
   AND(
     NOT(ISBLANK([s5_started_ts])),
     ISBLANK([s5_submitted_ts]),
     ISNOTBLANK([ai_self_reliability]),
     OR(
       [card_uid].[S5_one].[s5_decision] = "PASS",
       AND(
         [card_uid].[S5_one].[s5_decision] <> "PASS",
         ISNOTBLANK([accept_ai_correction]),
         ISNOTBLANK([ai_correction_quality])
       )
     )
   )
   ```
   **설명:**
   - S5 단계가 시작되었고 아직 제출되지 않았음
   - `ai_self_reliability`는 필수
   - S5 decision이 PASS이면 바로 제출 가능
   - S5 decision이 REGEN이면 `accept_ai_correction`과 `ai_correction_quality` 필수
   - **변경 사항**: `s5_regeneration_trigger_score` 대신 `s5_decision` 사용

8. `On success` → `+ Add action` → `Update row`:
   - `Update column`: `s5_duration_sec`
   - `Update value`: `TOTAL_SECONDS([s5_submitted_ts] - [s5_started_ts])`

---

## 6. S5 테이블 확장 설계

### 6.1 재생성 데이터 저장

**옵션 1: S5 테이블에 재생성 데이터 추가 (기존 컬럼과 통합)**

S5 테이블에 다음 컬럼 추가 (기존 `s5_front_modified`, `s5_back_modified`, `s5_modified_timestamp`와 통합):
- `s5_regenerated_front` (LongText) - 기존 `s5_front_modified`와 통합
- `s5_regenerated_back` (LongText) - 기존 `s5_back_modified`와 통합
- `s5_regenerated_image_filename` (Image) - 새로 추가
- `s5_regeneration_timestamp` (Date/Time) - 기존 `s5_modified_timestamp`와 통합
- `s5_regeneration_trigger_score` (Number) - 새로 추가

**통합 규칙:**
- 기존 컬럼(`s5_front_modified`, `s5_back_modified`, `s5_modified_timestamp`)이 있으면 우선 사용
- 새 컬럼(`s5_regenerated_*`)이 있으면 새 컬럼 사용
- `export_appsheet_tables.py`에서 자동으로 병합 처리

**옵션 2: 별도 테이블 생성**

`S5_Regenerated` 테이블 생성:
- Key: `card_uid` (Reference → Cards)
- 컬럼: `regenerated_front`, `regenerated_image_filename`, `regenerated_back`, `regeneration_trigger_score`, `regeneration_timestamp`

**권장:** 옵션 1 (S5 테이블 확장) - 데이터 구조가 단순하고 관리가 용이

---

## 7. Virtual Column 설계

### 7.1 재생성 콘텐츠 Virtual Columns

**AppSheet 메뉴 경로:** `Data` → `Tables` → `Ratings` → `+ Add column` → `Type = Virtual`

#### `s5_regenerated_front`

1. 컬럼명: `s5_regenerated_front`
2. `Type`: `Virtual`
3. `Virtual column expression`:
   ```
   [card_uid].[S5_one].[s5_regenerated_front]
   ```
4. `Show_If`: `AND(NOT(ISBLANK([s5_started_ts])), [card_uid].[S5_one].[s5_decision] <> "PASS")`
   - **변경 사항**: `s5_regeneration_trigger_score` 대신 `s5_decision` 사용
   - **설명**: S5 decision이 PASS가 아닌 경우 (REGEN인 경우)에만 표시

#### `s5_regenerated_image`

1. 컬럼명: `s5_regenerated_image`
2. `Type`: `Virtual`
3. `Virtual column expression`:
   ```
   [card_uid].[S5_one].[s5_regenerated_image_filename]
   ```
4. `Show_If`: `AND(NOT(ISBLANK([s5_started_ts])), [card_uid].[S5_one].[s5_decision] <> "PASS")`
   - **변경 사항**: `s5_regeneration_trigger_score` 대신 `s5_decision` 사용
   - **설명**: S5 decision이 PASS가 아닌 경우 (REGEN인 경우)에만 표시

#### `s5_regenerated_back`

1. 컬럼명: `s5_regenerated_back`
2. `Type`: `Virtual`
3. `Virtual column expression`:
   ```
   [card_uid].[S5_one].[s5_regenerated_back]
   ```
4. `Show_If`: `AND(NOT(ISBLANK([s5_started_ts])), [card_uid].[S5_one].[s5_decision] <> "PASS")`
   - **변경 사항**: `s5_regeneration_trigger_score` 대신 `s5_decision` 사용
   - **설명**: S5 decision이 PASS가 아닌 경우 (REGEN인 경우)에만 표시

---

## 8. 데이터 흐름 및 최종 판정 로직

### 8.1 최종 판정 데이터 저장

**시나리오 1: AI 수정안 수용 (ACCEPT)**

- `accept_ai_correction` = `ACCEPT`
- 최종 판정 데이터는 `s5_regenerated_*` 필드 사용
- 또는 별도 `final_*` 컬럼에 `s5_regenerated_*` 값 복사

**시나리오 2: 초기안 유지 (REJECT)**

- `accept_ai_correction` = `REJECT`
- 최종 판정 데이터는 기존 `pre_*` 또는 `post_*` 필드 사용

**구현 방법:**

Virtual Column `final_front` 생성:
```
IF(
  AND(
    NOT(ISBLANK([s5_submitted_ts])),
    [accept_ai_correction] = "ACCEPT",
    NOT(ISBLANK([s5_regenerated_front]))
  ),
  [s5_regenerated_front],
  [card_uid].[front]
)
```

---

## 9. 연구 가치 (Research Points)

### 9.1 정량적 분석 가능 데이터

1. **AI 자가 평가 신뢰도 분포**
   - `ai_self_reliability` (1-5 Likert)
   - 전문가가 AI의 자가 평가를 얼마나 신뢰하는지

2. **AI 수정안 수용률**
   - `accept_ai_correction` = `ACCEPT` 비율
   - 재생성된 콘텐츠가 실제로 더 나은지 검증

3. **AI 수정안 품질 평가**
   - `ai_correction_quality` (1-5 Likert)
   - 수용된 수정안의 품질 분포

4. **프롬프트 엔지니어링 효과**
   - `regeneration_trigger_score`와 최종 수용률의 상관관계
   - 낮은 점수로 인한 재생성이 실제로 품질을 개선했는지

### 9.2 논문 작성 시 활용

- **"AI Self-Reflection and Human Validation"** 섹션
- **"Prompt Engineering Effectiveness"** 분석
- **"User Acceptance of AI Corrections"** 통계

---

## 10. 구현 체크리스트

### 10.1 데이터 모델

- [ ] `Ratings` 테이블에 S5 관련 컬럼 추가
  - [ ] `ai_self_reliability` (Number, 1-5)
  - [ ] `ai_self_reliability_comment` (LongText, 선택)
  - [ ] `accept_ai_correction` (Enum: ACCEPT/REJECT)
  - [ ] `ai_correction_quality` (Number, 1-5)
  - [ ] `ai_correction_comment` (LongText, 선택)
  - [ ] `s5_started_ts` (Date/Time)
  - [ ] `s5_submitted_ts` (Date/Time)
  - [ ] `s5_duration_sec` (Number, Virtual)

- [ ] `S5` 테이블에 재생성 데이터 컬럼 추가
  - [ ] `regenerated_front` (LongText)
  - [ ] `regenerated_image_filename` (Image)
  - [ ] `regenerated_back` (LongText)
  - [ ] `regeneration_trigger_score` (Number)
  - [ ] `regeneration_timestamp` (Date/Time)

- [ ] Virtual Columns 생성
  - [ ] `s5_regenerated_front`
  - [ ] `s5_regenerated_image`
  - [ ] `s5_regenerated_back`
  - [ ] `final_front` (최종 판정용, 선택)

### 10.2 슬라이스 및 뷰

- [ ] `SLICE_S5` 슬라이스 생성
- [ ] `Ratings_Detail` 뷰에 S5 섹션 추가
- [ ] 각 컬럼의 `Show_If`, `Editable_If`, `Required_If` 설정

### 10.3 액션

- [ ] "Start S5 Final Assessment" 액션 생성
- [ ] "Submit S5 Final Assessment" 액션 생성
- [ ] `s5_duration_sec` 자동 계산 로직 추가

### 10.4 데이터 Export

- [ ] `export_appsheet_tables.py` 업데이트
  - [ ] S5 테이블에 재생성 데이터 컬럼 추가
  - [ ] Ratings 테이블에 S5 관련 컬럼 추가

---

## 11. 향후 확장 가능성

### 11.1 다중 재생성 지원

- 첫 번째 재생성 후에도 점수가 낮으면 두 번째 재생성
- 재생성 횟수 추적 (`regeneration_count`)

### 11.2 부분 수용 (PARTIAL)

- `accept_ai_correction`에 `PARTIAL` 옵션 추가
- 어떤 부분을 수용했는지 상세 기록

### 11.3 A/B 테스트

- 초기안과 수정안을 나란히 보여주고 선택
- 시각적 비교 인터페이스

---

## 12. 참고 문서

- **시스템 스펙**: `AppSheet_QA_System_Specification.md`
- **설정 가이드**: `AppSheet_QA_Setup_Guide.md`
- **프로덕션 강화**: `AppSheet_QA_Production_Hardening.md`
- **컬럼 설명**: `AppSheet_Column_Descriptions.md`

---

---

## 13. 변경 이력

### 2026-01-15: s5_decision 기반 조건으로 변경

**변경 사항:**
- `ISNOTBLANK([card_uid].[S5_one].[s5_regeneration_trigger_score])` 조건을 `[card_uid].[S5_one].[s5_decision] <> "PASS"`로 변경
- 재생성 콘텐츠 표시 조건을 `s5_decision` 기반으로 통일
- `s5_decision` 값: `"PASS"`, `"CARD_REGEN"`, `"IMAGE_ONLY_REGEN"` (legacy 호환: `"REGEN"`)

**영향 범위:**
- 재생성된 콘텐츠 섹션 Show_If 조건
- AI 수정안 수용 여부 Show_If/Editable_If/Required_If 조건
- AI 수정안 품질 평가 Show_If/Editable_If 조건
- 수용/거부 근거 Show_If/Editable_If 조건
- Virtual Column Show_If 조건
- Submit 액션 Run_If 조건

**참조:**
- [S5_Decision_Definition_Canonical.md](../../05_Pipeline_and_Execution/S5_Decision_Definition_Canonical.md)

---

**문서 버전:** 1.1  
**최종 업데이트:** 2026-01-15  
**상태:** 설계 완료, 구현 대기

