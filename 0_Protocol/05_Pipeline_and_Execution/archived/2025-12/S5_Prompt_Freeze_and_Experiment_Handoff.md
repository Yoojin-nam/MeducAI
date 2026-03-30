# S5 프롬프트 Freeze 및 실험 인계 문서

**작성 일자**: 2025-12-29  
**상태**: 프롬프트 **S5R2**(Text: v14/v11) Freeze 완료, 실험 실행 대기  
**목적**: 프롬프트 freeze 확인 및 실험 실행을 위한 인계 문서

> **네이밍 업데이트(S5R 라운드)**: 앞으로 실험/리포트에서는 `v14/v11` 같은 숫자 대신 **`S5R<k>`**를 1차 표기로 사용합니다.  
> Canonical: `0_Protocol/05_Pipeline_and_Execution/S5_Version_Naming_S5R_Canonical.md`
>
> **S4 정렬 원칙(멀티모달 실험 시)**: 이미지(S4) 프롬프트를 수정하는 경우에도, 가능하면 S1/S2와 동일한 **S5R 라운드**로 정렬합니다.

---

## 1. 프롬프트 Freeze 상태

### 1.1 Freeze된 프롬프트 버전

**S1 프롬프트**:
- **파일**: `3_Code/prompt/S1_SYSTEM__v14.md`
- **레지스트리**: `3_Code/prompt/_registry.json` → `"S1_SYSTEM": "S1_SYSTEM__v14.md"`
- **상태**: ✅ **FROZEN** (2025-12-29)
- **반영된 피드백**: 
  - 1차: 용어 혼동 방지, 용어 현대화 (v12 → v13)
  - 2차: 임상적 뉘앙스, 수치 일관성, 진단 기준 업데이트 (v13 → v14)
  - **라운드 표기**: **S5R2** (Text)

**S2 프롬프트**:
- **파일**: 
  - `3_Code/prompt/S2_SYSTEM__v11.md`
  - `3_Code/prompt/S2_USER_ENTITY__v11.md`
- **레지스트리**: `3_Code/prompt/_registry.json` → 
  - `"S2_SYSTEM": "S2_SYSTEM__v11.md"`
  - `"S2_USER_ENTITY": "S2_USER_ENTITY__v11.md"`
- **상태**: ✅ **FROZEN** (2025-12-29)
- **반영된 피드백**:
  - 1차: QC/행정 용어 구분, MCQ 형식, 오답 설명 완전성, 한국어 의학 용어 (v9 → v10)
  - 2차: Back 설명 완전성, Distractor 일치성, 질문 명확성, 용어 선택 정밀도 (v10 → v11)
  - **라운드 표기**: **S5R2** (Text)

### 1.2 Freeze 확인 사항

- [x] 프롬프트 파일 생성 완료 (v14/v11)
- [x] 프롬프트 레지스트리 업데이트 완료
- [x] S5 피드백 반영 완료
- [x] 프롬프트 버전 히스토리 문서화 완료
- [x] 가설 및 실험 방법 문서화 완료

**Freeze 일자**: 2025-12-29  
**Freeze 담당**: S5 피드백 반영 Agent  
**다음 단계**: 실험 실행 (다른 Agent)

---

## 2. 실험 실행 인계

### 2.1 실험 목적

**가설**: LLM-as-a-judge 검증(S5) 피드백을 기반으로 한 체계적 프롬프트 개선은 생성 콘텐츠의 품질 이슈 발생률을 유의미하게 감소시킬 것이다.

**비교(권장 표기)**: **S5R0(수정 전; baseline rerun)** vs **S5R2(수정 후; after)**  
**참고(기술 통계)**: Historical S5R1 (Text: v13/v10) = `DEV_armG_s5loop_diverse_20251229_065718`

### 2.2 실험 실행 절차

#### Step 1: 동일한 11개 그룹 재생성 (**S5R2**, rep1/rep2)

**명령어**:
```bash
python3 3_Code/src/01_generate_json.py \
  --base_dir /path/to/workspace/workspace/MeducAI \
  --run_tag DEV_armG_mm_S5R2_after_postFix_YYYYMMDD_HHMMSS__rep1 \
  --arm G \
  --only_group_id grp_f073599bec \
  --only_group_id grp_cbcba66e24 \
  --only_group_id grp_fb292cfd1d \
  --only_group_id grp_6ae1e80a49 \
  --only_group_id grp_92ab25064f \
  --only_group_id grp_afe6e9c0b9 \
  --only_group_id grp_baa12e0b6e \
  --only_group_id grp_c63d9a24cf \
  --only_group_id grp_929cf68679 \
  --only_group_id grp_2c6fda981d \
  --only_group_id grp_1c64967efa \
  --seed 101 \
  --workers 4
```

**주의사항**:
- `YYYYMMDD_HHMMSS`는 실제 실행 시각으로 대체
- 프롬프트 레지스트리가 S5R2(Text: v14/v11)를 가리키는지 확인: `3_Code/prompt/_registry.json`
- Replicate는 `__rep2` + 다른 seed(예: 202)로 1회 더 실행
- 동일한 11개 group_id 사용 (Before/After 동일)

#### Step 2: S5 검증 실행

**명령어**:
```bash
python3 3_Code/src/05_s5_validator.py \
  --base_dir /path/to/workspace/workspace/MeducAI \
  --run_tag DEV_armG_mm_S5R2_after_postFix_YYYYMMDD_HHMMSS__rep1 \
  --arm G \
  --workers_s5 4
```

**출력 위치**: `2_Data/metadata/generated/DEV_armG_mm_S5R2_after_postFix_YYYYMMDD_HHMMSS__rep1/s5_validation__armG.jsonl`

#### Step 3: S5 리포트 생성

**명령어**:
```bash
python3 -m tools.s5.s5_report \
  --base_dir /path/to/workspace/workspace/MeducAI \
  --run_tag DEV_armG_mm_S5R2_after_postFix_YYYYMMDD_HHMMSS__rep1 \
  --arm G
```

**출력 위치**: `2_Data/metadata/generated/DEV_armG_mm_S5R2_after_postFix_YYYYMMDD_HHMMSS__rep1/reports/s5_report__armG.md`

#### Step 4: Before/After 비교 분석

**Historical (descriptive only)**:
- **Run Tag**: `DEV_armG_s5loop_diverse_20251229_065718` (**S5R1**, Text: v13/v10)
- **리포트**: `2_Data/metadata/generated/DEV_armG_s5loop_diverse_20251229_065718/reports/s5_report__armG.md`

**Primary comparator (권장)**:
- **Before_rerun (S5R0; 수정 전, 동시기 baseline)**: `DEV_armG_mm_S5R0_before_rerun_preFix_YYYYMMDD_HHMMSS__rep1` (+ `__rep2`)
- **After (S5R2; 수정 후, 동시기 after)**: `DEV_armG_mm_S5R2_after_postFix_YYYYMMDD_HHMMSS__rep1` (+ `__rep2`)
**결과 리포트 위치(예시)**:
- `2_Data/metadata/generated/<RUN_TAG>/reports/s5_report__armG.md`

**비교 항목**:
1. Overall issue rate (issues per group, issues per card)
2. Targeted issue code reduction (10개 이슈 코드)
3. Quality metrics (Technical Accuracy, Educational Quality)
4. Blocking error rate
5. Issue category distribution

### 2.3 비교 분석 스크립트 (선택적)

**파일**: `3_Code/src/tools/s5/s5_compare_mm.py` (멀티모달: Text+Image, replicates 지원)

**기능**:
- Before/After(run_tag 리스트)에서 `s5_validation__armG.jsonl`을 로드
- group_id 기준으로 집계(클러스터 구조 보호)
- Text(S1/S2) + Image(S4) endpoint 비교 테이블 생성
- Difficulty(난이도)가 S5 출력에 포함된 경우 자동 요약 포함
- CSV/MD 산출물 생성

**실행 예시(권장; S5R0 vs S5R2, rep1/rep2)**:

```bash
python3 -m tools.s5.s5_compare_mm \
  --base_dir /path/to/workspace/workspace/MeducAI \
  --arm G \
  --before_run_tag DEV_armG_mm_S5R0_before_rerun_preFix_YYYYMMDD_HHMMSS__rep1 \
  --before_run_tag DEV_armG_mm_S5R0_before_rerun_preFix_YYYYMMDD_HHMMSS__rep2 \
  --after_run_tag DEV_armG_mm_S5R2_after_postFix_YYYYMMDD_HHMMSS__rep1 \
  --after_run_tag DEV_armG_mm_S5R2_after_postFix_YYYYMMDD_HHMMSS__rep2
```

**기본 출력 폴더**:
- `2_Data/metadata/generated/COMPARE__<before_tag0>__VS__<after_tag0>/`
  - `overall_endpoints__mm.csv`
  - `group_level__mm.csv`
  - `summary__mm.md`

---

## 3. 측정 지표 및 예상 결과

### 3.1 주요 지표 (Primary Endpoints)

**S1 Table**:
- **Before**: 1.55 issues/group (17 issues / 11 groups)
- **After**: 측정 필요
- **목표**: 47% reduction (1.55 → 0.82)

**S2 Cards**:
- **Before**: 0.054 issues/card (18 issues / 334 cards)
- **After**: 측정 필요
- **목표**: 61% reduction (0.054 → 0.021)

**Total Issues**:
- **Before**: 35개
- **After**: 측정 필요
- **목표**: 60% reduction (35 → 14)

**Targeted Issue Codes** (10개):
- **Before**: 10개
- **After**: 측정 필요
- **목표**: 100% reduction (10 → 0)

### 3.2 보조 지표 (Secondary Endpoints)

**Quality Metrics**:
- **Technical Accuracy**: Before 1.00 → After 유지 목표 (≥1.00)
- **Educational Quality**: Before 4.99 → After 유지/개선 목표 (≥4.99)
- **Blocking Error Rate**: Before 0.0% → After 유지 목표 (0.0%)

### 3.3 예상 시나리오

**시나리오 1 (Optimistic)**: 60% reduction
- Total Issues: 35 → 14
- Targeted Issues: 10 → 0 (100%)

**시나리오 2 (Realistic)**: 40% reduction
- Total Issues: 35 → 21
- Targeted Issues: 10 → 3 (70%)

**시나리오 3 (Pessimistic)**: 14% reduction
- Total Issues: 35 → 30
- Targeted Issues: 10 → 7 (30%)

---

## 4. 참고 문서

### 4.1 실험 설계 문서

- **가설 및 실험 방법**: `S5_Prompt_Improvement_Hypothesis_and_Methods.md`
- **정량적 평가 계획**: `S5_Prompt_Improvement_Quantitative_Evaluation_Plan.md`

### 4.2 프롬프트 개선 문서

- **1차 피드백 반영**: `0_Protocol/05_Pipeline_and_Execution/archived/2025-12/S5_Feedback_Implementation_Report_DEV_armG_s5loop_diverse.md`
- **2차 피드백 반영**: `S5_Feedback_Implementation_Update_Report_v2.md`

### 4.3 Before 데이터

- **Run Tag**: `DEV_armG_s5loop_diverse_20251229_065718`
- **S5 리포트**: `2_Data/metadata/generated/DEV_armG_s5loop_diverse_20251229_065718/reports/s5_report__armG.md`
- **S5 Validation**: `2_Data/metadata/generated/DEV_armG_s5loop_diverse_20251229_065718/s5_validation__armG.jsonl`

### 4.4 프롬프트 파일

- **S1**: `3_Code/prompt/S1_SYSTEM__v14.md` (FROZEN)
- **S2**: `3_Code/prompt/S2_SYSTEM__v11.md` (FROZEN)
- **S2**: `3_Code/prompt/S2_USER_ENTITY__v11.md` (FROZEN)
- **레지스트리**: `3_Code/prompt/_registry.json`

---

## 5. 체크리스트

### 5.1 실험 실행 전 확인

- [ ] 프롬프트 레지스트리가 v14/v11을 가리키는지 확인
- [ ] Before 데이터 위치 확인 (`DEV_armG_s5loop_diverse_20251229_065718`)
- [ ] 11개 그룹 ID 목록 확인
- [ ] 실행 환경 준비 (API keys, workers 설정 등)

### 5.2 실험 실행

- [ ] Step 1: S1/S2 재생성 (v14/v11)
- [ ] Step 2: S5 검증 실행
- [ ] Step 3: S5 리포트 생성
- [ ] Step 4: Before/After 비교 분석

### 5.3 결과 보고

- [ ] Overall issue rate 계산
- [ ] Targeted issue code reduction 계산
- [ ] Quality metrics 비교
- [ ] Improvement rate 계산
- [ ] 결과 리포트 생성
- [ ] 논문 Methods/Results 섹션 작성

---

## 6. 인계 요약

### 6.1 완료된 작업

✅ **프롬프트 개선 완료**:
- S1: v12 → v13 → v14 (2단계 S5 피드백 반영)
- S2: v9 → v10 → v11 (2단계 S5 피드백 반영)

✅ **프롬프트 Freeze 완료**:
- v14/v11 프롬프트 파일 생성 및 레지스트리 업데이트
- Freeze 상태 확인 완료

✅ **실험 설계 문서화 완료**:
- 가설, 실험 방법, 예상 결론 문서 작성
- 정량적 평가 계획 수립

### 6.2 다음 단계 (실험 Agent)

1. **실험 실행**: 동일한 11개 그룹에 대해 **S5R2**(Text: v14/v11)로 재생성
2. **S5 검증**: 재생성된 콘텐츠에 대해 S5 검증 실행
3. **비교 분석(권장)**: **S5R0(동시기 before_rerun)** vs **S5R2(동시기 after)** 비교 (참고: Historical S5R1(v13/v10)은 descriptive only)
4. **결과 보고**: Improvement rate 계산 및 논문 작성

### 6.3 핵심 정보

**Before Run Tag**: `DEV_armG_s5loop_diverse_20251229_065718`  
**After Run Tag**: `DEV_armG_mm_S5R2_after_postFix_YYYYMMDD_HHMMSS__rep1` (+ `__rep2`)  
**프롬프트 버전**: **S5R2** (Text: v14/v11; FROZEN)  
**그룹 수**: 11개 (동일한 group_id 사용)  
**예상 개선율**: 40-60% reduction

---

## 7. 문의 사항

실험 실행 중 문제가 발생하거나 추가 정보가 필요한 경우:

1. **프롬프트 관련**: `S5_Feedback_Implementation_Update_Report_v2.md` 참조
2. **실험 설계 관련**: `S5_Prompt_Improvement_Hypothesis_and_Methods.md` 참조
3. **Before 데이터**: `DEV_armG_s5loop_diverse_20251229_065718` run tag 참조

---

**인계 일자**: 2025-12-29  
**인계 담당**: S5 피드백 반영 Agent  
**수신 담당**: 실험 실행 Agent  
**상태**: ✅ Ready for Experiment

