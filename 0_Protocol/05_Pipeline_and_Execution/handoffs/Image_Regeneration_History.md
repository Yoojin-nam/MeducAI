# Image Regeneration History

**Last Updated**: 2026-01-07  
**Purpose**: FINAL_DISTRIBUTION armG 이미지 생성 및 재생성 작업 전체 기록  
**Scope**: S4 이미지 생성, Realistic 이미지, REGEN 이미지, Anki 최적화

---

## 개요

본 문서는 MeducAI FINAL_DISTRIBUTION armG 파이프라인에서 수행된 모든 이미지 생성 및 재생성 작업을 시간순으로 정리합니다.

---

## Timeline

### 2026-01-07: REGEN 이미지 Anki 처리 완료

**문서**: `HANDOFF_2026-01-07_REGEN_Images_Anki_Processing.md`

#### 작업 요약

Successfully processed all 831 REGEN images for Anki distribution:
- ✅ Resized and optimized for Anki (1200px width, quality 85/90)
- ✅ Original high-res images archived in `images_regen_raw/`
- ✅ Anki-optimized images in `images_regen_anki/`

#### 처리 결과

**Image Counts**:
- **Total processed**: 831 images
- **Anki optimized**: 831 images (100%)
- **Raw archived**: 831 images (100%)
- **Status**: All OK, no errors

**Color Classification**:
- **GRAY**: 819 images (98.6%) - grayscale encoded
- **COLOR**: 12 images (1.4%) - RGB encoded

**Size Optimization**:
| Metric | Original | Optimized | Reduction |
|--------|----------|-----------|-----------|
| Median size | 342.4 KB | 150.7 KB | **56.0%** |
| Min size | - | 62.8 KB | - |
| P95 size | - | 234.8 KB | - |
| Max size | - | 436.9 KB | - |

**Total space saved**: ~159 MB (from 284 MB to 125 MB)

#### Directory Structure

```
2_Data/metadata/generated/FINAL_DISTRIBUTION/
└── images_regen/                   # ← REGEN images folder
    ├── raw/                        # ← Original high-res (archived)
    │   └── IMG__FINAL_DISTRIBUTION__grp_*__Q1_regen.jpg (831 files)
    ├── IMG__FINAL_DISTRIBUTION__grp_*__Q1_regen.jpg (831 files, Anki-optimized)
    └── manifest.csv                # Optimization details
```

#### Optimization Settings

**GRAY Images (98.6%)**:
- Width: 1200px (maintains aspect ratio)
- Quality: 85 (JPEG)
- Encoding: Grayscale (1-channel) for smaller file size
- Subsampling: 4:4:4 (no chroma subsampling)

**COLOR Images (1.4%)**:
- Width: 1200px (maintains aspect ratio)
- Quality: 90 (JPEG)
- Encoding: RGB (3-channel) to preserve color
- Subsampling: Default (4:2:0)

#### 스크립트

**Script**: `3_Code/Scripts/process_regen_images_for_anki.sh`

**Command**:
```bash
bash 3_Code/Scripts/process_regen_images_for_anki.sh
```

**Processing time**: ~1.5 minutes (831 images @ ~10 img/s)

#### Why 1200px Width?
- **Consistency**: Matches existing `images_anki/` dimensions
- **Anki compatibility**: Optimal for mobile + desktop viewing
- **File size**: Balances quality vs. size (median 150 KB)
- **Future-proof**: Sufficient for high-DPI displays

---

### 2026-01-07: 이미지 재생성 범위 정확한 계산

**문서**: `HANDOFF_2026-01-07_Image_Regen_Scope_Correction.md`

#### 발견된 문제

1. ❌ **Entity vs Card 단위 혼동**: 초기 예상 357개 card-regen은 entity가 아닌 card 단위 계산 오류
2. ❌ **S1 테이블 visual 누락**: 22개 테이블이 47개 visual을 가짐 (평균 2.1개/table)
3. ❌ **Card-only 수정 26 entities 간과**: 텍스트 변경 → 이미지도 필수 재생성
4. ❌ **Deduplication 영향 미반영**: 이전 작업에서 29 entities 제거됨

#### 수정된 최종 집계

```
예상 (초기 잘못된 계산): 580 images
실제 (정확한 계산): 1,036 images
차이: 456 images (약 79% 증가)
```

#### 정확한 집계

| 구분 | Entities | Cards/Images | 방법 |
|------|----------|--------------|------|
| **S1 Tables (text only)** | 22 tables | **0** | 텍스트만 수정 |
| **S2 Card-regen** | 310 entities | **620** | S4 direct |
| **S2 Image-only** | 208 entities | **416** | S6 → S4 |
| **TOTAL** | - | **1,036** | - |

#### 중요 발견

**Issue 1: Entity/Card 단위 혼동**

```
S2 파일: Entity 단위 (card_role = None)
S3/S5: Card 단위 (Q1, Q2)
이미지: Card별로 생성
```

**해결책**: Entity 개수 × 2 = Card 개수

**Issue 2: S1 표와 Visual 독립성**

- S1 표 텍스트와 visual(인포그래픽)은 독립적
- 표 텍스트 수정 → visual 재생성 불필요
- 22 tables (table_score < 80): 텍스트만 수정
- S1 visuals: 모두 score ≥ 80 → 재생성 불필요
- **S1 이미지 재생성: 0개**

**Issue 3: 텍스트 변경 → 이미지 필수 재생성**

```
구버전 텍스트 + 구버전 이미지 → S5 점수 80
     ↓ (텍스트 수정)
신버전 텍스트 + 구버전 이미지 → 불일치!
     ↓ (이미지 재생성 필수)
신버전 텍스트 + 신버전 이미지 → 일관성
```

**결론**: 텍스트 변경 시 이미지 점수와 관계없이 **무조건 재생성**

#### 실행 계획

**Step 9: Card-regen 이미지 생성 (620개)**

```bash
python3 3_Code/src/04_s4_image_generator.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G \
  --spec_path 2_Data/metadata/generated/FINAL_DISTRIBUTION/s3_image_spec__armG__regen.jsonl \
  --image_type regen \
  --workers 8
```

**예상 소요 시간**: 50-70분

**Step 10: Image-only Regen (416개)**

```bash
python3 3_Code/src/tools/regen/positive_regen_runner.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G \
  --threshold 80.0 \
  --workers 8
```

**예상 소요 시간**: 50-70분

---

### 2026-01-07: S1 Visual Validation 및 재생성

**문서**: `HANDOFF_2026-01-07_S1_Visual_Validation_and_Regen.md`

#### 작업 배경

**현재 상황**:
```
S5 Validation Mode: s2_only
  ✅ S1 table text: 검증됨 (22개 table_score < 80)
  ✅ S2 cards: 검증됨 (518 entities 이미지 재생성 중)
  ❌ S1 visuals: 검증 안됨 (table_visual_validation 없음)
```

**문제**: S5가 `s2_only` 모드로 실행되어 S1 visuals 검증 누락

#### S5 Visual Validation 실행

**목적**: S1 visuals의 정확한 점수 확인

```bash
python3 3_Code/src/05_s5_validation_agent.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G \
  --mode table_visual_only \
  --output_suffix visual_check
```

**예상 소요 시간**: 10-15분 (735 visuals)

#### 예상 시나리오

**Scenario A: Visuals 모두 양호 (가능성 높음)**
- 모든 visuals score ≥ 80
- 재생성 불필요
- 소요 시간: 15분

**Scenario B: 일부 Visuals 재생성 필요**
- N개 visuals score < 80 (예: N = 10~50)
- S6 + S4 재생성 필요
- 소요 시간: 30-60분

---

### 2026-01-06: S2 이미지 재생성 완료 및 할당

**문서**: `HANDOFF_2026-01-06_S2_Image_Regeneration_Complete_and_Allocation.md`

#### 작업 요약

S2 이미지 재생성 작업 완료 및 6000 카드 할당 생성:

1. ✅ 6000 card assignment generated (1,680 assignments)
2. ✅ Assignments.csv deployed to standard locations
3. ✅ Original S5 validation data restored for 8 missing groups (206 cards)
4. ✅ AppSheet export updated with restored S5 data

#### Assignment 통계

- **Residents**: 9 × 150 = 1,350 assignments
- **Specialists**: 11 × 30 = 330 assignments
- **Total**: 1,680 assignments
- **Calibration**: 33 unique items × 3 residents/item = 99 slots
- **REGEN**: 200 items (capped from 350)
- **Seed**: 20260101

#### S5 Data Recovery

**Problem**: 130 cards had empty S5 rows (no validation data)

**Affected Groups** (8 groups):
- grp_01eafd919c (28 cards)
- grp_0ea7736c3e (28 cards)
- grp_096e9cf20e (34 cards)
- grp_0a2b68b8e4 (11 cards in alloc, 22 in S5)
- grp_043427ea12 (26 cards)
- grp_023d60ba08 (22 cards)
- grp_0bddd64828 (11 cards in alloc, 22 in S5)
- grp_0a283963db (24 cards)

**Recovery Source**: `s5_validation__armG__backup_before_score_backfill.jsonl`

**Result**: All 206 cards restored successfully

---

### 2026-01-06: S5 Data Restoration Complete

**문서**: `HANDOFF_2026-01-06_S5_Restoration_Complete.md`

#### 작업 요약

S5 validation 데이터 8개 그룹 복원 완료:

- ✅ 8 groups (206 cards) 복원
- ✅ S5 validation scores backfilled
- ✅ Allocation 불일치 해결

---

### 2026-01-06: S1 Visual Data Restoration

**문서**: `HANDOFF_2026-01-06_S1_Visual_Data_Restoration_Complete.md`

#### 작업 요약

S1 visual 데이터 복원:

- ✅ 8 groups S1 table validation 복원
- ✅ S5 validation file 병합 완료
- ✅ 321 groups 전체 S5 validation 완성

---

### 2026-01-06: 이미지 재생성 에이전트 인계

**문서**: `HANDOFF_2026-01-06_To_Image_Regen_Agent.md`

#### 이미지 재생성 요구사항

**전체 규모**:
- S2 카드 이미지: ~357개 (card + image regen)
- S2 이미지만: ~223개 (image-only regen)
- **Total**: ~580개 이미지

**실행 명령**:

```bash
# Card-regen (S3 regen spec 사용)
python3 3_Code/src/04_s4_image_generator.py \
  --spec_path s3_image_spec__armG__regen.jsonl \
  --image_type regen

# Image-only (S6 positive instruction 사용)
python3 3_Code/src/tools/regen/positive_regen_runner.py \
  --threshold 80.0
```

---

### 2026-01-05: Realistic Image Generation Complete

**문서**: `HANDOFF_2026-01-05_Realistic_Image_Generation_Complete.md`

#### 작업 완료

Realistic 스타일 이미지 생성 완료:

- ✅ 7,810개 S3 spec realistic 변환
- ✅ Batch API 사용하여 이미지 생성
- ✅ 품질 검증 완료

#### Realistic vs Diagram

**Diagram** (기존):
- 단순화된 의학 다이어그램
- 명확한 라벨과 화살표
- 교육용 최적화

**Realistic** (새):
- 실제 의료 영상과 유사
- 해부학적 정확도 높음
- 임상 환경과 유사

---

### 2026-01-05: Realistic Image Issues

**문서**: `HANDOFF_2026-01-05_Realistic_Image_Issues.md`

#### 발견된 이슈

1. **Text Rendering**: 일부 realistic 이미지에서 텍스트 가독성 저하
2. **Anatomical Detail**: 과도한 디테일로 인한 핵심 포인트 흐림
3. **Color Contrast**: Grayscale 이미지에서 대비 부족

#### 해결 방안

- Prompt 조정으로 텍스트 명확성 개선
- Key findings에 집중하도록 프롬프트 강화
- Contrast 향상 후처리 적용

---

### 2026-01-04: S4 클러스터 인포그래픽 배치

**문서**: `HANDOFF_2026-01-04_S4_Cluster_Infographic_Batch.md`

#### 문제 발견

- 기존 TABLE 인포그래픽이 클러스터 단위로 생성되지 않고 그룹 단위(1개)로만 생성됨
- S1 struct에 308개 그룹의 `entity_clusters`/`infographic_clusters` 정의되어 있음
- S3 spec에는 722개 클러스터 단위 + 13개 비클러스터 = 735개 TABLE_VISUAL spec 존재

#### 원인

`batch_image_generator.py`의 `make_image_filename()` 함수가 `cluster_id`를 지원하지 않았음

#### 코드 수정

**수정 1: `make_image_filename()` 함수**

```python
def make_image_filename(
    run_tag: str,
    group_id: str,
    entity_id: Optional[str] = None,
    card_role: Optional[str] = None,
    spec_kind: Optional[str] = None,
    cluster_id: Optional[str] = None,  # 추가됨
) -> str:
    # ...
    if spec_kind == "S1_TABLE_VISUAL":
        if cluster_id:
            cluster_id_safe = sanitize(str(cluster_id))
            return f"IMG__{run_tag_safe}__{group_id_safe}__TABLE__{cluster_id_safe}.jpg"
        else:
            return f"IMG__{run_tag_safe}__{group_id_safe}__TABLE.jpg"
```

#### 배치 실행

```bash
python3 3_Code/src/tools/batch/batch_image_generator.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G \
  --only_spec_kind S1_TABLE_VISUAL \
  --model gemini-2.5-flash-image \
  --submit
```

**결과**:
- 735개 TABLE_VISUAL 배치 생성
- 722개 cluster + 13개 non-cluster
- 배치 ID: `bch-eesehfwb63fncvqwnwz664d0lqjj4vb7h`

---

### 2026-01-04: 클러스터 인포그래픽 개수 업데이트

**문서**: `HANDOFF_2026-01-04_Cluster_Infographic_Count_Update.md`

#### 인포그래픽 개수 정정

**이전 이해** (잘못됨):
- 321개 groups → 321개 TABLE images

**올바른 이해**:
- 321개 groups → 735개 TABLE images (cluster 단위)
- 308개 groups: 2-4개 clusters (평균 2.3개)
- 13개 groups: 1개 cluster (non-cluster)

#### 구조 예시

```
grp_4b36ed8159:
  - IMG__...__TABLE__cluster_1.jpg (Anatomy)
  - IMG__...__TABLE__cluster_2.jpg (Pathology)
  - IMG__...__TABLE__cluster_3.jpg (Imaging)

grp_38c815434e:
  - IMG__...__TABLE.jpg (single cluster, no suffix)
```

---

### 2026-01-04: 배치 다운로드 상태

**문서**: `HANDOFF_2026-01-04_Batch_Download_Status.md`

#### 배치 작업 상태

**Submitted Batches**:
- S1_TABLE_VISUAL: 735 images
- S2_CARD_IMAGE: ~6,175 images
- S2_CARD_CONCEPT: ~900 images

**Download Progress**:
- ✅ S1_TABLE_VISUAL: 735/735 (100%)
- 🔄 S2_CARD_IMAGE: In progress
- ⏳ S2_CARD_CONCEPT: Pending

---

## 파일 네이밍 규칙

### S2 Card Images

```
Q1: IMG__FINAL_DISTRIBUTION__grp_{group_id}__{entity_id}__Q1.jpg
Q2: IMG__FINAL_DISTRIBUTION__grp_{group_id}__{entity_id}__Q2.jpg

Regen:
Q1: IMG__FINAL_DISTRIBUTION__grp_{group_id}__{entity_id}__Q1_regen.jpg
Q2: IMG__FINAL_DISTRIBUTION__grp_{group_id}__{entity_id}__Q2_regen.jpg
```

### S1 Table Visual

```
Single cluster: IMG__FINAL_DISTRIBUTION__grp_{group_id}__TABLE.jpg
Multiple clusters: IMG__FINAL_DISTRIBUTION__grp_{group_id}__TABLE__cluster_{N}.jpg
```

---

## 이미지 디렉토리 구조

```
2_Data/metadata/generated/FINAL_DISTRIBUTION/
├── images/                          # Baseline images (7,811개)
│   ├── IMG__*__TABLE*.jpg          # S1 visuals (735개)
│   ├── IMG__*__Q1.jpg              # S2 Q1 cards (3,538개)
│   └── IMG__*__Q2.jpg              # S2 Q2 cards (3,538개)
│
├── images_anki/                     # Anki-optimized baseline
│   └── (same structure, 1200px width)
│
├── images_realistic/                # Realistic style images
│   └── (same structure, different style)
│
├── images_regen/                    # Regenerated images
│   ├── IMG__*_regen.jpg            # Anki-optimized regen (1,036개 예상)
│   └── raw/                        # Original high-res regen
│       └── IMG__*_regen.jpg        # Raw regen images
│
├── images_backup_pre_cluster/       # Backup before cluster fix
│   └── IMG__*__TABLE.jpg           # Old non-cluster images
│
└── manifest files
    ├── s4_image_manifest__armG.jsonl
    ├── s4_image_manifest__armG__regen.jsonl
    └── images_regen/manifest.csv
```

---

## Image Processing Pipeline

### 1. S3 Spec Generation
```
stage1_struct + s2_results → S3 policy resolver → s3_image_spec.jsonl
```

### 2. S4 Image Generation (Batch)
```
s3_image_spec.jsonl → Batch API → images/
```

### 3. Anki Optimization
```
images/ → optimize_images.py → images_anki/ (1200px, Q85)
```

### 4. Regeneration
```
S5 validation → trigger_score < 80 → regen pipeline
  ├─ Card-regen: S3 regen spec → S4
  └─ Image-only: S5 feedback → S6 → S4
```

### 5. Regen Anki Processing
```
images_regen_temp/ → process_regen_images_for_anki.sh → images_regen/
```

---

## Quality Metrics

### Image Resolution
- **Original**: 1024×1280 (4:5 aspect ratio)
- **Anki**: 1200×1500 (slightly upscaled for consistency)
- **Thumbnail**: 400×500 (for preview)

### Image Quality
- **GRAY images**: JPEG Q85, 1-channel
- **COLOR images**: JPEG Q90, 3-channel
- **Typical file size**: 150 KB (median)

### Image Counts
- **Baseline**: 7,811 images
- **Regen**: 1,036 images (estimated)
- **Total unique**: ~8,500 images

---

## 관련 스크립트

### Image Generation
```
3_Code/src/
  ├── 04_s4_image_generator.py        # Main image generator
  └── tools/batch/
      └── batch_image_generator.py    # Batch mode generator
```

### Image Processing
```
3_Code/
  ├── src/tools/
  │   └── optimize_images.py          # Anki optimization
  └── Scripts/
      └── process_regen_images_for_anki.sh  # Regen processing
```

### Regeneration
```
3_Code/src/tools/regen/
  ├── positive_regen_runner.py        # Orchestrator
  └── fast_s2_regen.py                # S2 text regen
```

---

## 참고 문서

### Protocol 문서
- `0_Protocol/04_Step_Contracts/Step04_S4/S4_Image_Cost_and_Resolution_Policy.md`
- `0_Protocol/05_Pipeline_and_Execution/Image_Asset_Naming_and_Storage_Convention.md`
- `0_Protocol/05_Pipeline_and_Execution/DEPLOYMENT_IMAGE_SELECTION_GUIDE.md`

### 5_Meeting 원본 문서
- `HANDOFF_2026-01-07_REGEN_Images_Anki_Processing.md`
- `HANDOFF_2026-01-07_Image_Regen_Scope_Correction.md`
- `HANDOFF_2026-01-07_S1_Visual_Validation_and_Regen.md`
- `HANDOFF_2026-01-06_S2_Image_Regeneration_Complete_and_Allocation.md`
- `HANDOFF_2026-01-06_S5_Restoration_Complete.md`
- `HANDOFF_2026-01-06_S1_Visual_Data_Restoration_Complete.md`
- `HANDOFF_2026-01-06_To_Image_Regen_Agent.md`
- `HANDOFF_2026-01-05_Realistic_Image_Generation_Complete.md`
- `HANDOFF_2026-01-05_Realistic_Image_Issues.md`
- `HANDOFF_2026-01-04_S4_Cluster_Infographic_Batch.md`
- `HANDOFF_2026-01-04_Cluster_Infographic_Count_Update.md`
- `HANDOFF_2026-01-04_Batch_Download_Status.md`

---

**문서 작성일**: 2026-01-07  
**최종 업데이트**: 2026-01-07  
**상태**: 통합 완료

