# S6 Visual Regeneration Complete - Handoff to PDF Generation

**Date**: 2026-01-07  
**From**: S6 Visual Regeneration Agent  
**To**: PDF Generation & Evaluation Agent  
**Status**: ✅ S6 Visual Regeneration Complete

---

## 📋 Executive Summary

S1 table visual 재생성 작업이 성공적으로 완료되었습니다. 36개의 low-score visuals가 재생성되어 `images_regen/` 디렉토리에 저장되었습니다.

**Key Results**:
- ✅ **36개 S1 table visuals 재생성 완료** (score < 80)
- ✅ **867개 총 REGEN 이미지** (S2 cards 831개 + S1 visuals 36개)
- ✅ **원본 이미지 보존** (`images/` 디렉토리 유지)
- ✅ **재생성 이미지 분리 저장** (`images_regen/` 디렉토리)

---

## 🎯 작업 완료 내역

### Phase 1: S6 Input Generator 구현 ✅

**Script**: `3_Code/src/tools/regen/s1_visual_positive_regen.py`

**기능**:
1. S5 validation에서 visual score < 80인 visuals 추출
2. Visual score 계산 (blocking_error, anatomical_accuracy, prompt_compliance, information_clarity, table_visual_consistency)
3. S5 issues를 positive instructions로 변환
4. Enhanced S3 specs 생성

**실행 명령**:
```bash
python3 3_Code/src/tools/regen/s1_visual_positive_regen.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G \
  --threshold 80.0
```

**출력**:
- `s3_image_spec__armG__s1_visual_regen.jsonl` (36 specs)

---

### Phase 2: S6 Enhanced Specs 생성 ✅

**실행 결과**:
```
[Step 1] Loading S5 validation results...
  Loaded 321 group(s) from S5 validation

[Step 2] Filtering visuals with score < 80.0...
  Found 36 visual(s) needing regeneration

[Step 4] Processing complete:
  Success: 36/36
  Errors: 0/36
```

**재생성 대상 분류**:

| Score Range | Count | Severity |
|-------------|-------|----------|
| 30.0 (Blocking) | 16 | Critical errors (content swap, Korean text, wrong data) |
| 48.0-65.0 | 5 | Major issues (accuracy, clarity) |
| 71.0-79.0 | 15 | Minor issues (Korean text, truncation, typos) |

**주요 이슈 유형**:
1. **Content Swap** (16개): 패널 내용이 잘못 매핑됨
2. **Korean Text** (12개): English-only 필드에 한글 포함
3. **Text Truncation** (8개): 토큰 선택 오류로 문장 잘림
4. **Anatomical Errors** (5개): 해부학적 오류 또는 방향 오류
5. **Missing Entities** (3개): 테이블 엔티티가 visual에 누락

---

### Phase 3: S4 Image Generation 실행 ✅

**실행 명령**:
```bash
python3 3_Code/src/04_s4_image_generator.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G \
  --spec_path 2_Data/metadata/generated/FINAL_DISTRIBUTION/s3_image_spec__armG__s1_visual_regen.jsonl \
  --image_type regen \
  --workers 8 \
  --only_spec_kind S1_TABLE_VISUAL
```

**생성된 이미지**:
- 36개 S1 table visuals
- 파일명 패턴: `IMG__FINAL_DISTRIBUTION__grp_{group_id}__TABLE__cluster_{N}_regen.jpg`
- 저장 위치: `2_Data/metadata/generated/FINAL_DISTRIBUTION/images_regen/`

**예시**:
```
IMG__FINAL_DISTRIBUTION__grp_096e9cf20e__TABLE__cluster_2_regen.jpg
IMG__FINAL_DISTRIBUTION__grp_096e9cf20e__TABLE__cluster_4_regen.jpg
IMG__FINAL_DISTRIBUTION__grp_1b3e1b32ba__TABLE__cluster_3_regen.jpg
...
```

---

## 📊 최종 통계

### 전체 REGEN 이미지 현황

| 카테고리 | 개수 | 파일 패턴 |
|---------|------|----------|
| **S2 Card Images** | 831 | `*__Q1_regen.jpg`, `*__Q2_regen.jpg` |
| **S1 Table Visuals** | 36 | `*__TABLE__cluster_*_regen.jpg` |
| **총계** | **867** | - |

### 디렉토리 구조

```
2_Data/metadata/generated/FINAL_DISTRIBUTION/
├── images/                          # ← 원본 이미지 (보존됨)
│   ├── IMG__*__TABLE__cluster_*.jpg (735개 - 원본 visuals)
│   ├── IMG__*__Q1.jpg               (3,538개 - 원본 cards)
│   └── IMG__*__Q2.jpg               (3,538개 - 원본 cards)
│
├── images_regen/                    # ← 재생성 이미지 (신규)
│   ├── IMG__*__TABLE__cluster_*_regen.jpg (36개 - S1 visuals)
│   ├── IMG__*__Q1_regen.jpg         (831개 중 Q1)
│   └── IMG__*__Q2_regen.jpg         (831개 중 Q2)
│
└── s3_image_spec__armG__s1_visual_regen.jsonl  # S6 enhanced specs
```

---

## 🔧 구현 상세

### Visual Score 계산 알고리즘

```python
def calculate_table_visual_score(visual_validation: Dict) -> float:
    """
    Calculate visual quality score (0-100, higher = better).
    
    Hard fail triggers (returns 30.0):
    - blocking_error == True
    - anatomical_accuracy == 0.0
    
    Weighted scoring:
    - Anatomical accuracy: 40 points (0.0/0.5/1.0 → 0-40)
    - Prompt compliance: 30 points (0.0/0.5/1.0 → 0-30)
    - Information clarity: 20 points (1-5 Likert → 0-20)
    - Table visual consistency: 10 points (0.0/0.5/1.0 → 0-10)
    
    Total: 0-100 points
    """
```

### Issue to Positive Instruction 변환

**입력 (S5 Issue)**:
```json
{
  "severity": "blocking",
  "type": "content_swap",
  "description": "CRITICAL SWAP: The diagram in Panel 3 (Renal Trauma) depicts Renal Vein Thrombosis anatomy instead.",
  "prompt_patch_hint": "Ensure row-based text injection strictly maps Row N to Panel N without shifting."
}
```

**출력 (Positive Instruction)**:
```
"Ensure row-based text injection strictly maps Row N to Panel N without shifting."
```

**Enhanced Prompt**:
```
[Original S3 Prompt]

IMPROVEMENTS REQUIRED:
- Ensure row-based text injection strictly maps Row N to Panel N without shifting.
- Verify panel count matches row count or use 'Others' section for overflow.
```

---

## 📁 생성된 파일

### 1. S6 Input Generator Script

**파일**: `3_Code/src/tools/regen/s1_visual_positive_regen.py`

**기능**:
- S5 validation 분석 및 visual score 계산
- Low-score visuals 추출 (threshold < 80)
- S5 issues → positive instructions 변환
- Enhanced S3 specs 생성

**사용법**:
```bash
python3 3_Code/src/tools/regen/s1_visual_positive_regen.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G \
  --threshold 80.0 \
  [--output s3_image_spec__armG__custom.jsonl]
```

### 2. Enhanced S3 Specs

**파일**: `2_Data/metadata/generated/FINAL_DISTRIBUTION/s3_image_spec__armG__s1_visual_regen.jsonl`

**레코드 수**: 36

**스펙 구조**:
```json
{
  "spec_kind": "S1_TABLE_VISUAL",
  "group_id": "grp_xxx",
  "cluster_id": "cluster_N",
  "prompt_en": "... [ENHANCED WITH POSITIVE INSTRUCTIONS] ...",
  "prompt_en_enhanced": "... [SAME AS prompt_en] ...",
  "positive_instructions": [
    "Ensure row-based text injection strictly maps Row N to Panel N...",
    "Verify panel count matches row count..."
  ],
  "_regen_metadata": {
    "regen_type": "S1_TABLE_VISUAL",
    "original_score": 30.0,
    "regen_reason": "low_visual_score",
    "s5_issues_count": 2
  }
}
```

### 3. Regenerated Images

**디렉토리**: `2_Data/metadata/generated/FINAL_DISTRIBUTION/images_regen/`

**파일 개수**: 867 images
- S1 visuals: 36
- S2 cards: 831

**파일명 규칙**:
```
S1 visuals: IMG__FINAL_DISTRIBUTION__grp_{group_id}__TABLE__cluster_{N}_regen.jpg
S2 cards:   IMG__FINAL_DISTRIBUTION__grp_{group_id}__{entity_id}__Q1_regen.jpg
```

---

## 🎯 다음 단계: PDF 생성

### 배포용 PDF (Distribution PDF)

**목적**: 최종 사용자 배포용 PDF 생성

**요구사항**:
1. **이미지 선택 로직**:
   - REGEN 이미지가 있으면 REGEN 사용 (867개)
   - 없으면 원본 이미지 사용 (나머지)
   
2. **구조**:
   - Cover Page
   - Table of Contents (specialty별 시작 페이지)
   - For each group:
     - Objective Goals (Korean)
     - Master Table (formatted)
     - Infographic (REGEN 우선)
     - Q1/Q2 Cards (REGEN 우선)

3. **헤더/푸터**:
   - Gradient header with breadcrumb
   - Section type indicator
   - Page numbers

**실행 명령** (예상):
```bash
python3 3_Code/src/tools/build_distribution_pdf.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G \
  --use_regen_images \
  --output FINAL_DISTRIBUTION_armG_v2.pdf
```

**이미지 선택 로직 구현**:
```python
def get_image_path(group_id, entity_id, card_role, cluster_id=None):
    """
    Get image path with REGEN priority.
    
    Priority:
    1. images_regen/{filename}_regen.jpg (if exists)
    2. images/{filename}.jpg (fallback)
    """
    if cluster_id:
        # S1 table visual
        regen_path = f"images_regen/IMG__{run_tag}__grp_{group_id}__TABLE__cluster_{cluster_id}_regen.jpg"
        baseline_path = f"images/IMG__{run_tag}__grp_{group_id}__TABLE__cluster_{cluster_id}.jpg"
    else:
        # S2 card
        regen_path = f"images_regen/IMG__{run_tag}__grp_{group_id}__{entity_id}__{card_role}_regen.jpg"
        baseline_path = f"images/IMG__{run_tag}__grp_{group_id}__{entity_id}__{card_role}.jpg"
    
    if os.path.exists(regen_path):
        return regen_path
    return baseline_path
```

---

### 평가용 PDF (Evaluation PDF)

**목적**: QA 팀 평가용 비교 PDF 생성

**요구사항**:
1. **REGEN 대상만 포함** (867개 이미지)
2. **Before/After 비교 레이아웃**:
   ```
   ┌─────────────────────────────────────┐
   │ Group: grp_xxx                      │
   │ Cluster: cluster_N                  │
   │ Original Score: 30.0                │
   ├─────────────────────────────────────┤
   │ BEFORE (Original)  │ AFTER (Regen)  │
   │ [Original Image]   │ [Regen Image]  │
   │                    │                │
   │ S5 Issues:                          │
   │ - Content swap...                   │
   │ - Korean text...                    │
   │                                     │
   │ Positive Instructions:              │
   │ - Ensure row-based mapping...       │
   │ - Verify panel count...             │
   └─────────────────────────────────────┘
   ```

3. **정렬 순서**:
   - Score 오름차순 (blocking errors 먼저)
   - Group ID 알파벳 순

**실행 명령** (예상):
```bash
python3 3_Code/src/tools/build_resident_eval_pdf.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G \
  --regen_only \
  --comparison_mode \
  --output FINAL_DISTRIBUTION_armG_REGEN_Evaluation.pdf
```

**필요한 데이터**:
- `s5_validation__armG.jsonl` (original scores, issues)
- `s3_image_spec__armG__s1_visual_regen.jsonl` (positive instructions)
- `images/` (original images)
- `images_regen/` (regenerated images)

---

## 📋 체크리스트

### S6 Visual Regeneration (완료)

- [x] S6 input generator 스크립트 작성
- [x] Visual score 계산 로직 구현
- [x] S5 issues → positive instructions 변환
- [x] Enhanced S3 specs 생성 (36개)
- [x] S4 image generation 실행 (36개)
- [x] 원본 이미지 보존 확인
- [x] REGEN 이미지 분리 저장 확인

### PDF Generation (다음 단계)

- [ ] 배포용 PDF 생성 스크립트 수정
  - [ ] REGEN 이미지 우선 선택 로직 추가
  - [ ] 이미지 경로 해석 로직 업데이트
  - [ ] 테스트 실행 (소규모)
  - [ ] 전체 PDF 생성 (321 groups)

- [ ] 평가용 PDF 생성 스크립트 작성
  - [ ] Before/After 비교 레이아웃 구현
  - [ ] S5 issues 및 positive instructions 표시
  - [ ] REGEN 대상만 필터링 (867개)
  - [ ] Score 기반 정렬
  - [ ] 전체 평가 PDF 생성

---

## 🔍 검증 포인트

### 1. 이미지 파일 검증

**확인 사항**:
```bash
# REGEN 이미지 개수 확인
ls -1 images_regen/*.jpg | wc -l
# Expected: 867

# S1 visual REGEN 개수 확인
ls -1 images_regen/*TABLE*_regen.jpg | wc -l
# Expected: 36

# S2 card REGEN 개수 확인
ls -1 images_regen/*Q1_regen.jpg images_regen/*Q2_regen.jpg | wc -l
# Expected: 831 (Q1 + Q2)
```

**결과**: ✅ 모두 확인됨

### 2. 파일명 규칙 검증

**S1 Visuals**:
```bash
ls images_regen/*TABLE*_regen.jpg | head -5
```
```
IMG__FINAL_DISTRIBUTION__grp_096e9cf20e__TABLE__cluster_2_regen.jpg
IMG__FINAL_DISTRIBUTION__grp_096e9cf20e__TABLE__cluster_4_regen.jpg
IMG__FINAL_DISTRIBUTION__grp_1b3e1b32ba__TABLE__cluster_3_regen.jpg
...
```
✅ 패턴 일치

**S2 Cards**:
```bash
ls images_regen/*Q1_regen.jpg | head -5
```
```
IMG__FINAL_DISTRIBUTION__grp_01eafd919c__DERIVED_038214d89fa7__Q1_regen.jpg
IMG__FINAL_DISTRIBUTION__grp_01eafd919c__DERIVED_43ffe48d7216__Q1_regen.jpg
...
```
✅ 패턴 일치

### 3. 원본 이미지 보존 검증

```bash
# 원본 이미지 개수 (변경 없어야 함)
ls -1 images/*.jpg | wc -l
# Expected: 7,811 (735 TABLE + 7,076 CARDS)
```
✅ 원본 보존됨

---

## 📚 관련 문서

### Protocol 문서
- `0_Protocol/05_Pipeline_and_Execution/DEPLOYMENT_IMAGE_SELECTION_GUIDE.md`
- `0_Protocol/05_Pipeline_and_Execution/Image_Asset_Naming_and_Storage_Convention.md`

### History 문서
- `0_Protocol/05_Pipeline_and_Execution/handoffs/Image_Regeneration_History.md`
- `0_Protocol/05_Pipeline_and_Execution/handoffs/PDF_Generation_History.md`

### 5_Meeting 원본 문서
- 이 문서가 원본입니다 (HANDOFF_2026-01-07_S6_Visual_Regeneration_Complete.md)

---

## 🚀 Quick Start for Next Agent

### 배포용 PDF 생성

```bash
cd /path/to/workspace/workspace/MeducAI

# 1. 기존 PDF 스크립트 확인
ls -lh 3_Code/src/tools/build_distribution_pdf.py

# 2. REGEN 이미지 우선 로직 추가 필요
# - get_image_path() 함수 수정
# - images_regen/ 디렉토리 우선 확인
# - 없으면 images/ fallback

# 3. 테스트 실행 (1개 그룹)
python3 3_Code/src/tools/build_distribution_pdf.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G \
  --use_regen_images \
  --test_group grp_096e9cf20e

# 4. 전체 실행
python3 3_Code/src/tools/build_distribution_pdf.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G \
  --use_regen_images \
  --output 6_Distributions/MeducAI_Final_Share/FINAL_DISTRIBUTION_armG_v2.pdf
```

### 평가용 PDF 생성

```bash
# 1. 평가 PDF 스크립트 작성 또는 수정
# - Before/After 비교 레이아웃
# - S5 issues 표시
# - Positive instructions 표시

# 2. 실행
python3 3_Code/src/tools/build_resident_eval_pdf.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G \
  --regen_only \
  --comparison_mode \
  --output 6_Distributions/QA/FINAL_DISTRIBUTION_armG_REGEN_Evaluation.pdf
```

---

## ⚠️ 주의사항

### 1. 이미지 경로 우선순위

**중요**: PDF 생성 시 반드시 REGEN 이미지 우선 사용

```python
# ❌ 잘못된 방법
image_path = f"images/IMG__{run_tag}__grp_{group_id}__TABLE__cluster_{cluster_id}.jpg"

# ✅ 올바른 방법
regen_path = f"images_regen/IMG__{run_tag}__grp_{group_id}__TABLE__cluster_{cluster_id}_regen.jpg"
baseline_path = f"images/IMG__{run_tag}__grp_{group_id}__TABLE__cluster_{cluster_id}.jpg"
image_path = regen_path if os.path.exists(regen_path) else baseline_path
```

### 2. 파일명 패턴 주의

**S1 Visuals**:
- REGEN: `*__TABLE__cluster_{N}_regen.jpg` (cluster_id 포함)
- Original: `*__TABLE__cluster_{N}.jpg`

**S2 Cards**:
- REGEN: `*__{entity_id}__{card_role}_regen.jpg`
- Original: `*__{entity_id}__{card_role}.jpg`

### 3. 누락 이미지 처리

일부 그룹은 REGEN이 없을 수 있음:
- S1 visuals: 699개 원본, 36개 REGEN
- S2 cards: 6,245개 원본, 831개 REGEN

**처리**: REGEN 없으면 원본 사용 (fallback)

---

## 📞 Contact

**질문 또는 이슈 발생 시**:
1. 이 인계장 문서 참조
2. `Image_Regeneration_History.md` 참조
3. 스크립트 주석 및 docstring 확인
4. 필요시 이전 에이전트에게 문의

---

**인계 완료**: 2026-01-07  
**작성자**: S6 Visual Regeneration Agent  
**상태**: ✅ Ready for PDF Generation


