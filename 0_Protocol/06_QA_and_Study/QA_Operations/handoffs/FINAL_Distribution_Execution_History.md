# FINAL Distribution Execution History

**Last Updated**: 2026-01-15  
**Purpose**: FINAL_DISTRIBUTION armG 실행 및 QA 배포 작업 기록  
**Scope**: 6000 카드 할당 생성, AppSheet 배포, 최종 QA 준비

---

## 개요

본 문서는 MeducAI FINAL_DISTRIBUTION armG의 최종 배포 및 QA 작업을 시간순으로 정리합니다.

---

## Timeline

### 2026-01-15: FINAL_DISTRIBUTION Execution Guide

**문서**: `HANDOFF_2026-01-15_FINAL_DISTRIBUTION_Execution_Guide.md`

#### 현재 상태

**준비 완료 항목**:

| 항목 | 상태 | 비고 |
|------|------|------|
| Allocation | ✅ 완료 | 321개 그룹 |
| 인포그래픽 | ✅ 완료 | 735개 (클러스터 단위) |
| S2 결과 | ✅ 완료 | `s2_results__s1armG__s2armG.jsonl` |
| S4 이미지 | ✅ 완료 | `images/` 및 `images_anki/` |
| Assignment 스크립트 | ✅ 업데이트 완료 | Calibration 33개/3명 로직 반영 |

**진행 중 / 대기 중 항목**:

| 항목 | 상태 | 다음 액션 |
|------|------|-----------|
| S5 S1 평가 | 🔄 진행 중 | 완료 대기 (예상 1.5시간) |
| S5 S2 평가 | ⏳ 대기 | S1 완료 후 실행 |
| S5 리포트 | ⏳ 대기 | S2 완료 후 생성 |
| AppSheet Export | ⏳ 대기 | S5 리포트 후 실행 |
| Assignments 생성 | ⏳ 대기 | AppSheet 업로드 후 |
| 최종 배포물 | ⏳ 대기 | Assignments 생성 후 |

#### Phase 0: 사전 준비 (Preflight) ✅

**0-1. 인포그래픽 다운로드 완료 확인**

**중요**: 인포그래픽은 클러스터 단위로 생성됨 (그룹당 1개 아님)

```bash
# 현재 상태 확인
ls -1 2_Data/metadata/generated/FINAL_DISTRIBUTION/images/*__TABLE* | wc -l
# 목표: 735개 (722개 클러스터 + 13개 비클러스터)
```

**파일명 패턴**:
- 클러스터: `IMG__FINAL_DISTRIBUTION__grp_{group_id}__TABLE__cluster_N.jpg`
- 비클러스터: `IMG__FINAL_DISTRIBUTION__grp_{group_id}__TABLE.jpg`

#### Phase 1: S5 검증 실행 (Mode Split)

**1-1. S1 평가 (Pro 모델)** 🔄 진행 중

```bash
python3 3_Code/src/05_s5_validator.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G \
  --s5_mode s1_only \
  --workers_s5 3
```

**예상 소요 시간**: 1.5시간 (321 groups × Pro model)

**1-2. S2 평가 (Flash 모델)** ⏳ 대기

```bash
python3 3_Code/src/05_s5_validator.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G \
  --s5_mode s2_only \
  --workers_s5 8
```

**예상 소요 시간**: 1-1.5시간 (3,509 entities × Flash model)

#### Phase 2: S5 리포트 생성

```bash
python3 3_Code/src/tools/analysis/generate_s5_report.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G
```

**출력**:
- `s5_report__armG.md` - Markdown 요약
- `s5_statistics__armG.json` - 통계 JSON

#### Phase 3: AppSheet Export

```bash
python3 3_Code/src/tools/final_qa/export_appsheet_tables.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G
```

**출력**:
```
6_Distributions/Final_QA/AppSheet_Export/
  ├── Cards.csv (7,018 cards)
  ├── Groups.csv (321 groups)
  └── Images.csv (7,811 images)
```

#### Phase 4: Assignment 생성

```bash
python3 3_Code/src/tools/qa/generate_final_qa_assignments.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G \
  --seed 20260101
```

**출력**:
```
6_Distributions/Final_QA/AppSheet_Export/
  └── Assignments.csv (1,680 assignments)
```

**통계**:
- **Residents**: 9 × 150 = 1,350 assignments
- **Specialists**: 11 × 30 = 330 assignments
- **Calibration**: 33 unique items × 3 residents = 99 slots
- **REGEN**: 200 items (capped from 350)

---

### 2026-01-15: Current Work Status

**문서**: `HANDOFF_2026-01-15_Current_Work_Status.md`

#### 작업 진행 상황

**완료된 작업**:
- ✅ S1/S2 baseline 생성
- ✅ S3 image spec 생성
- ✅ S4 이미지 배치 생성 (7,811개)
- ✅ 인포그래픽 클러스터 생성 (735개)

**현재 작업**:
- 🔄 S5 validation 실행 중
- 🔄 이미지 재생성 (REGEN) 준비 중

**다음 작업**:
- ⏳ S5 리포트 생성
- ⏳ AppSheet export
- ⏳ Assignment 생성
- ⏳ 최종 배포

---

### 2026-01-04: S5 Execution Ready

**문서**: `HANDOFF_2026-01-04_S5_Execution_Ready.md`

#### S5 실행 준비 완료

**Preflight Checks**:
- ✅ S1 struct 파일 확인 (321 groups)
- ✅ S2 results 파일 확인 (3,509 entities)
- ✅ S3 image spec 파일 확인 (7,810 specs)
- ✅ S4 images 확인 (7,811 images)
- ✅ S5 validator 코드 업데이트 완료

**Model Configuration**:
- S1: gemini-3-pro-preview
- S2: gemini-3-flash-preview

**Worker Configuration**:
- S1: 3 workers (Pro model, expensive)
- S2: 8 workers (Flash model, cheap)

---

### 2026-01-04: FINAL QA Design Update

**문서**: `HANDOFF_2026-01-04_FINAL_QA_Design_Update.md`

#### QA 설계 업데이트

**변경 사항**:

1. **Calibration 증가**: 30개 → 33개
   - 각 specialty에서 1개씩 추가
   - 더 robust한 inter-rater agreement 측정

2. **REGEN 샘플링**:
   - 350개 REGEN cards 생성 예상
   - Assignment는 200개로 cap (균형 유지)

3. **Stratification**:
   - Score-based: Low (< 70), Medium (70-80), High (80-90)
   - Specialty-based: 11개 specialty 비례 할당

**QA Form**:
- Google Form 또는 AppSheet
- 4-point Likert scale:
  1. Poor
  2. Fair
  3. Good
  4. Excellent

---

## AppSheet 구조

### Tables

**1. Groups.csv**:
- group_id
- specialty
- region
- modality
- category
- objective_list_kr (Korean objectives)

**2. Cards.csv**:
- card_uid (unique ID)
- group_id (FK to Groups)
- entity_id
- card_role (Q1/Q2)
- card_front
- card_back
- s5_decision (PASS/CARD_REGEN/IMAGE_REGEN)
- s5_card_score
- s5_image_score

**3. Images.csv**:
- image_uid (unique ID)
- card_uid (FK to Cards)
- group_id
- entity_id
- card_role
- image_filename
- image_path
- image_type (baseline/regen)

**4. Assignments.csv**:
- assignment_id (PK)
- reviewer_email
- card_uid (FK to Cards)
- batch (calibration/main/regen)
- status (To do/In progress/Complete)
- due_date

### Relationships

```
Groups (1) ─────< Cards (N)
Cards (1) ──────< Images (N)
Cards (1) ──────< Assignments (N)
```

---

## Assignment Generation Logic

### Calibration Items (33개)

**Selection**:
- 11 specialties × 3 items = 33 items
- High-quality cards (S5 score ≥ 90)
- Representative of specialty

**Distribution**:
- Each calibration item → 3 residents
- Total: 33 × 3 = 99 assignments

### Main Items

**Residents** (9명 × 150개 = 1,350 assignments):
- Random stratified sampling
- Balanced across specialties
- No duplicates within reviewer

**Specialists** (11명 × 30개 = 330 assignments):
- Specialty-matched sampling
- Each specialist reviews own specialty only

### REGEN Items (200개, capped)

**Selection**:
- Cards with S5 decision = CARD_REGEN or IMAGE_REGEN
- Prioritize by lowest S5 score
- Cap at 200 to balance workload

**Distribution**:
- Mixed into main assignments
- No separate batch for REGEN

---

## Deployment Checklist

### Pre-deployment

- [ ] S5 validation 완료 (S1 + S2)
- [ ] S5 리포트 생성
- [ ] AppSheet export 완료
- [ ] Assignment CSV 생성
- [ ] PDF 생성 (distribution document)

### Deployment

- [ ] AppSheet 업로드 (4 CSV files)
- [ ] AppSheet 앱 테스트
- [ ] Reviewer 이메일 발송
- [ ] 접근 권한 확인

### Post-deployment

- [ ] 응답 수집 모니터링
- [ ] Inter-rater agreement 계산
- [ ] 최종 분석 및 리포트

---

## Timeline Estimate

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| S5 Validation | 2.5-3시간 | S1+S2 complete |
| S5 Report | 5분 | S5 validation |
| AppSheet Export | 10분 | S5 report |
| Assignment Gen | 5분 | AppSheet export |
| PDF Generation | 20분 | All data ready |
| AppSheet Upload | 10분 | CSV files ready |
| **Total** | **3-4시간** | Sequential |

---

## 관련 스크립트

### S5 Validation
```
3_Code/src/
  └── 05_s5_validation_agent.py
```

### S5 Report
```
3_Code/src/tools/analysis/
  └── generate_s5_report.py
```

### AppSheet Export
```
3_Code/src/tools/final_qa/
  └── export_appsheet_tables.py
```

### Assignment Generation
```
3_Code/src/tools/qa/
  └── generate_final_qa_assignments.py
```

### PDF Generation
```
3_Code/src/tools/
  └── build_distribution_pdf.py
```

---

## 참고 문서

### Protocol 문서
- `0_Protocol/06_QA_and_Study/QA_Framework.md`
- `0_Protocol/06_QA_and_Study/Paper1_S5_Validation/Paper1_QA_Endpoints_Definition.md`
- `0_Protocol/06_QA_and_Study/QA_Operations/FINAL_QA_Assignment_Guide.md`
- `0_Protocol/05_Pipeline_and_Execution/S1_QA_Design_Error_Rate_Validation.md`

### 5_Meeting 원본 문서
- `HANDOFF_2026-01-15_FINAL_DISTRIBUTION_Execution_Guide.md`
- `HANDOFF_2026-01-15_Current_Work_Status.md`
- `HANDOFF_2026-01-04_S5_Execution_Ready.md`
- `HANDOFF_2026-01-04_FINAL_QA_Design_Update.md`

---

**문서 작성일**: 2026-01-15  
**최종 업데이트**: 2026-01-15  
**상태**: 통합 완료

