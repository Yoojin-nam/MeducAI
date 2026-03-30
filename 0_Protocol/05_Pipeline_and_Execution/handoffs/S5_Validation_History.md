# S5 Validation History

**Last Updated**: 2026-01-15  
**Purpose**: S5 validation agent 개발, 점수 체계 구현, 그리고 검증 작업 전체 기록  
**Scope**: FINAL_DISTRIBUTION armG의 S5 validation 작업 전체 타임라인

---

## 개요

본 문서는 MeducAI FINAL_DISTRIBUTION armG 파이프라인에서 수행된 모든 S5 validation 관련 작업을 시간순으로 정리합니다.

S5 Validation의 주요 역할:
- S1 테이블 및 인포그래픽 품질 검증
- S2 카드 텍스트 및 이미지 품질 검증
- Regeneration trigger score 계산 (PASS/REGEN 판정)
- Repair agent를 위한 feedback 제공

---

## Timeline

### 2026-01-15: S5 Regeneration Trigger Score 계산 최적화

**문서**: `HANDOFF_2026-01-15_S5_Regeneration_Score_Optimization.md`

#### 변경 배경

**문제점**: `regeneration_trigger_score`가 **Option C repair 실행 시점**에 계산되어 중복 계산 발생

**개선 방향**: S5 validation 단계에서 이미 계산된 점수를 기록하여:
- ✅ 자원 절약: Option C repair에서 중복 계산 불필요
- ✅ 효율성 향상: LLM 호출 없이 즉시 PASS/REGEN 판정 가능
- ✅ 일관성 보장: 동일한 validation 결과로 항상 동일한 점수

#### 변경 내용

**수정된 파일**: `3_Code/src/05_s5_validator.py`

**추가된 Score Calculator Import**:
```python
from tools.multi_agent.score_calculator import (
    calculate_s5_regeneration_trigger_score,
    calculate_s5_card_regeneration_trigger_score,
    calculate_s5_image_regeneration_trigger_score,
)
```

**카드 Validation 결과에 점수 기록**:

`validate_s2_card()` 함수에서 각 카드 validation 완료 후 다음 점수들을 계산하여 기록:

```python
# 추가된 필드
result["regeneration_trigger_score"] = ...        # 전체 점수 (카드 + 이미지)
result["card_regeneration_trigger_score"] = ...   # 카드 텍스트만 (CARD_REGEN 판정용)
result["image_regeneration_trigger_score"] = ...  # 이미지만 (IMAGE_ONLY_REGEN 판정용)
```

#### 점수 필드 설명

**1. regeneration_trigger_score**
- **용도**: 전체 평가 (카드 텍스트 + 이미지)
- **범위**: 0-100
- **판정 기준**:
  - Hard trigger (30.0): blocking_error, technical_accuracy=0.0, image_blocking_error, image_safety_flag
  - Weighted sum: TA(50점) + EQ(30점) + Image Quality(20점)
- **사용처**: Legacy 호환성 (기존 PASS/REGEN 이진 판정)

**2. card_regeneration_trigger_score**
- **용도**: 카드 텍스트만 평가 (CARD_REGEN 판정용)
- **범위**: 0-100
- **판정 기준**:
  - Hard trigger (30.0): blocking_error, technical_accuracy=0.0
  - Weighted sum: TA(50점) + EQ(50점)
- **사용처**: CARD_REGEN 결정, Option C repair에서 카드 전체 재생성 여부 판정

**3. image_regeneration_trigger_score**
- **용도**: 이미지만 평가 (IMAGE_ONLY_REGEN 판정용)
- **범위**: 0-100 또는 None (이미지 없으면 None)
- **판정 기준**:
  - Hard trigger (30.0): image_blocking_error, image_safety_flag, anatomical_accuracy=0.0
  - Weighted sum: Anatomical Accuracy(40점) + Prompt Compliance(30점) + Image Quality(30점)
- **사용처**: IMAGE_ONLY_REGEN 결정, 이미지만 재생성 여부 판정

#### Three-Way Decision Logic

**S5_DECISION 판정 기준** (`card_threshold=80`, `image_threshold=80`):

| Case | card_score | img_score | Decision | 재생성 대상 |
|------|-----------|-----------|----------|----------|
| 1 | < 80 | < 80 | **CARD_REGEN** | 카드 전체 (텍스트+이미지) |
| 2 | < 80 | ≥ 80 | **CARD_REGEN** | 카드 전체 (텍스트+이미지) |
| 3 | ≥ 80 | < 80 | **IMAGE_REGEN** | 이미지만 |
| 4 | ≥ 80 | ≥ 80 | **PASS** | 재생성 불필요 |

**로직**:
```python
if card_score < card_threshold:
    return "CARD_REGEN"  # 텍스트 문제 → 전체 재생성
elif img_score < image_threshold:
    return "IMAGE_REGEN"  # 이미지만 문제 → 이미지만 재생성
else:
    return "PASS"  # 문제 없음
```

#### Backward Compatibility

**하위 호환성 보장**:
- 기존 S5 validation 파일 (점수 필드 없음)도 정상 동작
- Backfill 스크립트로 기존 파일에 점수 추가 가능
- 점수가 없으면 default logic으로 fallback

---

### 2026-01-06: S5 Regen Validation Plan

**문서**: `HANDOFF_2026-01-06_S5_Regen_Validation_Plan.md`

#### 목적

**Primary**: 사람이 재생성 이미지 품질을 리뷰하여 배포 수용 여부 결정  
**Secondary**: S5 점수와 사람 판단의 correlation 분석 (실험용)

**⚠️ 중요**: 이 S5 validation은 실험용/참고 자료입니다.

> **최종 수용 여부는 사람이 직접 판단합니다.**  
> S5 점수는 사람 판단과의 correlation을 분석하기 위한 보조 자료로만 사용됩니다.

#### Validation 범위

**검증 대상**: 831개 regen 이미지

| 유형 | 개수 | 설명 |
|------|------|------|
| **Card-regen** | 304 | 텍스트 변경 + 이미지 재생성 |
| **Image-only regen** | 223 | 이미지만 재생성 (S6 강화) |
| **Bonus (Entity 쌍)** | 278 | 추가 생성된 PASS 카드 |
| **S1 Visuals** | 26? | S1 table visuals 재생성 |
| **총계** | **831** | images_regen/ 전체 |

#### S5 Validation 구조

```
Baseline S5:
  s5_validation__armG.jsonl
  ↓
  - 기존 이미지 검증 (images/)
  - Before 점수 기준

Regen S5:
  s5_validation__armG__regen.jsonl  🆕
  ↓
  - 재생성 이미지 검증 (images_regen/)
  - After 점수
  - Before와 비교 가능
```

#### 실행 명령어

```bash
python3 3_Code/src/05_s5_validation_agent.py \
  --base_dir /path/to/workspace/workspace/MeducAI \
  --run_tag FINAL_DISTRIBUTION \
  --arm G \
  --spec_path 2_Data/metadata/generated/FINAL_DISTRIBUTION/s3_image_spec__armG__regen.jsonl \
  --manifest_path 2_Data/metadata/generated/FINAL_DISTRIBUTION/s4_image_manifest__armG__regen.jsonl \
  --output_suffix regen
```

**중요**: `--output_suffix regen`으로 설정하여 baseline S5와 구분

#### Human Review Plan

**Sample Selection**:
- 총 75장 샘플 (allocation 553개 중 13.5%)
- Score-based stratification:
  - Very Low (0-50): 모두 리뷰
  - Low (50-70): 50% 샘플
  - Medium (70-80): 30% 샘플
  - High (80-90): 10% 샘플
  - Very High (90-100): 5% 샘플

**Review Criteria**:
1. Anatomical accuracy
2. Key finding visibility
3. Prompt compliance
4. Clinical utility
5. Educational value

**Review Form**: Google Form or AppSheet

#### Correlation Analysis Plan

**Analysis**:
1. Pearson correlation (S5 score vs Human rating)
2. Confusion matrix (PASS/REGEN vs Human accept/reject)
3. Score calibration (adjust thresholds based on results)

**Expected Outcome**:
- Correlation ≥ 0.7: S5 is reliable
- Correlation < 0.5: S5 needs recalibration

---

### 2026-01-06: S1 Trigger Score 구현

**문서**: `HANDOFF_2026-01-06_S1_Trigger_Score_Implementation.md`

#### 요약

S1 Table에 S2 Cards와 동일한 **0-100 trigger score 체계**를 도입하여 일관된 평가 기준을 확립했습니다.

#### 구현 결과

| 항목 | 내용 |
|------|------|
| **구현 범위** | S1 table_regeneration_trigger_score 추가 |
| **영향 받는 파일** | 3개 (score_calculator.py, 05_s5_validator.py, batch_text_repair.py) |
| **프로토콜 문서** | 1개 업데이트 (S5_Validation_Schema_Canonical.md) |
| **하위 호환성** | ✅ 완전 보장 (기존 S5 파일도 동작) |
| **배포 상태** | ✅ 준비 완료 (즉시 사용 가능) |

#### 주요 변경사항

1. **일관성 확보**: S1/S2 모두 0-100 점수 체계 사용
2. **유연한 threshold**: 90점 기준 적용 가능 (기존 TA<1.0보다 유연)
3. **우선순위 설정**: 점수 기반 batch 분할 가능
4. **분석 가능**: 점수 분포 및 개선도 측정 가능

#### Score Calculator 함수

**추가 함수**:
```python
def calculate_s1_table_regeneration_trigger_score(
    s1_table_validation: Dict[str, Any]
) -> float:
    """
    S1 Table trigger score (0-100, lower => more likely to regenerate).
    
    Hard triggers (returns 30.0):
    - blocking_error == True
    - technical_accuracy == 0.0
    
    Else weighted sum:
    - Technical accuracy: 50 points (0.0/0.5/1.0 scaled to 0-50)
    - Educational quality: 50 points (1-5 Likert scaled to 0-50)
    """
```

**계산 공식**:
- **Hard triggers**: blocking_error=True OR TA=0.0 → 30점
- **Weighted sum**: (TA × 50) + ((EQ/5) × 50)
- **Range**: 0-100점 (낮을수록 수정 필요)

**점수 예시**:

| TA | EQ | Calculation | Score | 현재(TA<1.0) | 90점 기준 |
|----|----|----|-------|----------|----------|
| 1.0 | 5 | 50 + 50 | **100** | ✅ 통과 | ✅ 통과 |
| 1.0 | 4 | 50 + 40 | **90** | ✅ 통과 | ✅ 통과 (경계) |
| 0.5 | 5 | 25 + 50 | **75** | ⚠️ 수정 | ✅ 통과 |
| 0.5 | 4 | 25 + 40 | **65** | ⚠️ 수정 | ⚠️ 수정 |
| 0.0 | any | - | **30** | ⚠️ 수정 | ⚠️ 수정 |

#### S5 Validator 변경

**변경사항**:
1. Import 추가:
   ```python
   from tools.multi_agent.score_calculator import (
       calculate_s1_table_regeneration_trigger_score,  # NEW
       ...
   )
   ```

2. S1 validation result에 trigger score 추가:
   ```python
   # NEW: Calculate S1 table regeneration trigger score
   try:
       table_trigger_score = calculate_s1_table_regeneration_trigger_score({
           "blocking_error": blocking_error,
           "technical_accuracy": technical_accuracy,
           "educational_quality": educational_quality,
       })
       result["table_regeneration_trigger_score"] = table_trigger_score
   except Exception as e:
       logger.warning(f"Failed to calculate S1 trigger score: {e}")
       result["table_regeneration_trigger_score"] = None
   ```

#### Threshold 비교

**기존 방식 (TA < 1.0)**:
- Binary 판정: 통과/실패
- TA=0.5일 때 무조건 수정 필요

**새 방식 (Score < 90)**:
- Continuous 판정: 0-100 점수
- TA=0.5, EQ=5일 때 75점 → 통과 가능
- 더 유연한 판정

#### Backfill Tool

**스크립트**: `3_Code/src/tools/s5/backfill_regeneration_scores.py`

**기능**:
- 기존 S5 validation 파일에 trigger scores 추가
- S1 table_regeneration_trigger_score 계산
- S2 card_regeneration_trigger_score, image_regeneration_trigger_score 계산

**사용법**:
```bash
python3 3_Code/src/tools/s5/backfill_regeneration_scores.py \
  --input 2_Data/metadata/generated/FINAL_DISTRIBUTION/s5_validation__armG.jsonl \
  --output 2_Data/metadata/generated/FINAL_DISTRIBUTION/s5_validation__armG__with_scores.jsonl
```

---

### 2026-01-06: S5 Data Restoration Complete

**문서**: `HANDOFF_2026-01-06_S5_Restoration_Complete.md`

#### 작업 요약

S5 validation 데이터 8개 그룹 복원 완료:

- ✅ 8 groups (206 cards) 복원
- ✅ S5 validation scores backfilled
- ✅ Allocation 불일치 해결

#### 복원 방법

**Source**: `s5_validation__armG__backup_before_score_backfill.jsonl`

**Affected Groups** (8 groups):
- grp_01eafd919c (28 cards)
- grp_0ea7736c3e (28 cards)
- grp_096e9cf20e (34 cards)
- grp_0a2b68b8e4 (11 cards in alloc, 22 in S5)
- grp_043427ea12 (26 cards)
- grp_023d60ba08 (22 cards)
- grp_0bddd64828 (11 cards in alloc, 22 in S5)
- grp_0a283963db (24 cards)

**Result**: All 206 cards restored successfully

---

### 2026-01-06: S1 Visual Data Restoration

**문서**: `HANDOFF_2026-01-06_S1_Visual_Data_Restoration_Complete.md`

#### 작업 요약

S1 visual 데이터 복원:

- ✅ 8 groups S1 table validation 복원
- ✅ S5 validation file 병합 완료
- ✅ 321 groups 전체 S5 validation 완성

---

### 2026-01-05: S5R Merge Verification Complete

**문서**: `HANDOFF_2026-01-05_S5R_Merge_Verification_Complete.md`

#### 작업 요약

S5R (S5 Regeneration) validation 병합 검증 완료:

- ✅ S5 baseline과 S5R regen 파일 병합
- ✅ 중복 제거 및 데이터 일관성 확인
- ✅ Regeneration trigger score 일관성 검증

---

### 2026-01-05: S5 Card Validation Enhancement

**문서**: `HANDOFF_2026-01-05_S5_Card_Validation_Enhancement.md`

#### 배경

2024년 영상의학과 기출문제 분석 결과를 바탕으로 S5 검증 기준 강화

#### 기출문제 분석 결과

| 문제 유형 | 비율 | 예시 |
|----------|------|------|
| 영상 진단 | 53% | "진단은?", "다음 질환은?" |
| 추가검사 선택 | 11% | "추가검사는?" |
| 해부구조 식별 | 10% | "화살표한 구조물은?" |
| 원인/병인 | 8% | "다음 질환의 원인은?" |
| 영상 품질/물리 | 다수 | artifact, DRL, 피폭 저감 |

**Source**: `2_Data/raw/2024/*.pptx` (4개 파일, 692 슬라이드)

#### S2 카드 샘플 평가 결과 (10개 샘플)

| 평가 항목 | 결과 | 비율 |
|----------|------|------|
| 정답-설명 일치 | 10/10 | 100% |
| Multiple Answer Risk 없음 | 10/10 | 100% |
| 난이도 적절 | 9/10 | 90% |
| 영상의학과 적합 | 8/10 | 80% |
| Q2 인지목표 적합 | 10/10 | 100% |
| 평균 Educational Quality | 4.6/5 | - |

#### 발견된 문제 케이스

**Case 1: 영상의학과 적합성 문제**
- **Entity**: Petrous Apex Lesions
- **문제**: Gradenigo triad (임상 징후)를 묻는 문제 - 영상 소견 없음
- **S5 Issue Type**: `radiology_relevance_concern`
- **재생성 방향**: "추체첨부염의 CT/MRI 영상 소견"으로 변환

**Case 2: 난이도 문제 (단순 암기)**
- **Entity**: Intraparenchymal Hematoma
- **문제**: AAST Grade III = 10cm 초과 (숫자 암기)
- **S5 Issue Type**: `difficulty_too_easy`
- **재생성 방향**: "응급 수술이 필요한 CT 소견"으로 변환

#### 프롬프트 개선

**수정할 파일**:

| 파일 | 현재 버전 | 목표 버전 | 주요 변경 |
|------|----------|----------|----------|
| `S5_USER_CARD__S5R2__v4.md` | v4 | **v5** | MCQ 검증 + 난이도 + 영상의학과 적합성 + Q2 |
| `S5_USER_CARD_IMAGE__S5R2__v3.md` | v3 | **v4** | 난이도 + 영상의학과 적합성 + Q2 |

**추가된 검증 항목**:

1. **MCQ correctness** (structured fields 검증)
2. **Q2 Radiology Board Relevance** - 영상의학과 시험 적합성
3. **Q2 Difficulty Refinement** - 난이도 조절 (숫자 암기 방지)
4. **Q2 Verification** - 2개 검증 항목 추가

---

## S5 Validation Schema

### 출력 구조

```json
{
  "group_id": "grp_xxx",
  "run_tag": "FINAL_DISTRIBUTION",
  "arm": "G",
  "s1_table_validation": {
    "blocking_error": false,
    "technical_accuracy": 1.0,
    "educational_quality": 5,
    "issues": [],
    "table_regeneration_trigger_score": 100.0,  // 🆕
    "rag_evidence": {...}
  },
  "s2_cards_validation": {
    "cards": [
      {
        "entity_id": "DERIVED:xxx",
        "card_role": "Q1",
        "blocking_error": false,
        "technical_accuracy": 1.0,
        "educational_quality": 5,
        "issues": [],
        "regeneration_trigger_score": 95.0,  // 🆕 Legacy
        "card_regeneration_trigger_score": 100.0,  // 🆕 Card text
        "image_regeneration_trigger_score": 90.0,  // 🆕 Image only
        "card_image_validation": {
          "blocking_error": false,
          "anatomical_accuracy": 1.0,
          "prompt_compliance": 0.9,
          "image_quality": 0.95,
          "issues": []
        }
      }
    ]
  }
}
```

### Score Fields 요약

| Field | 범위 | 용도 | 계산 방법 |
|-------|------|------|----------|
| `table_regeneration_trigger_score` | 0-100 | S1 테이블 PASS/REGEN | TA(50) + EQ(50) |
| `regeneration_trigger_score` | 0-100 | S2 전체 (legacy) | TA(50) + EQ(30) + Img(20) |
| `card_regeneration_trigger_score` | 0-100 | S2 텍스트 PASS/REGEN | TA(50) + EQ(50) |
| `image_regeneration_trigger_score` | 0-100 | S2 이미지 PASS/REGEN | AA(40) + PC(30) + IQ(30) |

**Hard Triggers** (모든 score에서 30.0 반환):
- blocking_error = True
- technical_accuracy = 0.0
- (image only) image_blocking_error = True
- (image only) image_safety_flag = True

---

## S5 Validation Modes

### Mode 1: Full Validation
```bash
python3 3_Code/src/05_s5_validator.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G
```
- S1 table + S2 cards 전체 검증
- 가장 일반적인 모드

### Mode 2: S2 Only
```bash
python3 3_Code/src/05_s5_validator.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G \
  --s5_mode s2_only
```
- S2 cards만 검증
- S1 table 제외

### Mode 3: S1 Table Visual Only
```bash
python3 3_Code/src/05_s5_validator.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G \
  --mode table_visual_only
```
- S1 table visuals만 검증
- S2 cards 제외

---

## Model Policy

### S5 Model 정책

```python
# 현재 05_s5_validator.py 설정
S5_S1_TABLE_MODEL = "gemini-3-pro-preview"    # S1 테이블: Pro
S5_S2_CARD_MODEL = "gemini-3-flash-preview"   # S2 카드: Flash
```

**이유**:
- S1 테이블: 복잡한 레이아웃 분석 필요 → Pro
- S2 카드: 단순 텍스트 검증 → Flash (비용 효율)

---

## Threshold Policy

### Initial: Threshold 90 (2026-01-05)
- S5 validation에서 90점 기준으로 PASS/REGEN 판정
- 엄격한 품질 관리

### Updated: Threshold 80 (2026-01-06)
- S5 validation 결과 분석 후 80점으로 하향 조정
- 더 유연한 판정
- 관련 문서: `DECISION_2026-01-06_Threshold_80_Rationale.md`

### Current: Flexible Thresholds (2026-01-15)
- `card_threshold` and `image_threshold` 독립 설정 가능
- 기본값: 80.0
- Use case별로 조정 가능

---

## 관련 스크립트

### S5 Validation
```
3_Code/src/
  └── 05_s5_validation_agent.py      # Main validator
```

### Score Calculator
```
3_Code/src/tools/multi_agent/
  └── score_calculator.py             # Score calculation functions
```

### Backfill Tools
```
3_Code/src/tools/s5/
  └── backfill_regeneration_scores.py  # Add scores to existing S5 files
```

---

## 프롬프트 버전 이력

### S5 Card Validation
- **v4**: Initial version
- **v5**: + MCQ verification + Radiology relevance + Difficulty check

### S5 Card Image Validation
- **v3**: Initial version
- **v4**: + Radiology relevance + Difficulty check (MCQ already exists)

### S5 Table Validation
- **Current**: Stable version (no recent changes)

---

## 참고 문서

### Protocol 문서
- `0_Protocol/05_Pipeline_and_Execution/S5_Decision_Definition_Canonical.md`
- `0_Protocol/05_Pipeline_and_Execution/S5_Validation_Plan_OptionB_Canonical.md`
- `0_Protocol/04_Step_Contracts/Step05_S5/S5_Validation_Schema_Canonical.md`

### 5_Meeting 원본 문서
- `HANDOFF_2026-01-15_S5_Regeneration_Score_Optimization.md`
- `HANDOFF_2026-01-06_S5_Regen_Validation_Plan.md`
- `HANDOFF_2026-01-06_S5_Restoration_Complete.md`
- `HANDOFF_2026-01-06_S5_Data_Recovery_and_Missing_S2_Cards.md`
- `HANDOFF_2026-01-06_S1_Visual_Data_Restoration_Complete.md`
- `HANDOFF_2026-01-06_S1_Trigger_Score_Implementation.md`
- `HANDOFF_2026-01-05_S5R_Merge_Verification_Complete.md`
- `HANDOFF_2026-01-05_S5_Card_Validation_Enhancement.md`

---

**문서 작성일**: 2026-01-15  
**최종 업데이트**: 2026-01-15  
**상태**: 통합 완료

