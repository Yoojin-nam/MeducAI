# S5R 문서 일관성 검토 및 정리 보고서

**작성일**: 2025-12-29  
**목적**: S5R 관련 문서들의 일관성 문제 및 중복 내용 정리 및 해결 방안 제시

---

## 1. 문서 역할 및 범위 명확화

### 1.1 Canonical 문서 (권위 있는 단일 소스)

#### 1.1.1 실험 설계 (Confirmatory Evaluation)

**`S5R_Experiment_Power_and_Significance_Plan.md`** (Canonical Prereg)
- **역할**: 논문에 기술할 confirmatory 실험 설계의 단일 소스
- **범위**: 
  - Primary endpoint: `S2_any_issue_rate_per_group` (단일)
  - Key secondary endpoints: ≤3개
  - 통계 분석 계획 (Wilcoxon, HL estimator, CI)
  - DEV vs HOLDOUT 분리
  - Target 1 (Generation) vs Target 2 (Judge) 인과 질문 분리
- **상태**: ✅ Canonical (prereg-ready)
- **Frozen**: No (DEV 단계), HOLDOUT 시작 시 Yes

#### 1.1.2 버전 네이밍 (Naming Convention)

**`S5_Version_Naming_S5R_Canonical.md`** (Canonical)
- **역할**: 모든 실험/문서/산출물에서 사용하는 버전 네이밍 규칙
- **핵심 규칙**:
  - S5R 라운드가 1차 식별자 (S5R0, S5R1, S5R2)
  - v버전과의 매핑 테이블 제공
  - 파일명 규칙: `{PROMPT_NAME}__S5R{k}__v{XX}.md`
  - Run tag 규칙: `DEV_armG_mm_S5R{k}_<condition>_YYYYMMDD_HHMMSS__repN`
- **상태**: ✅ Canonical

### 1.2 Development Process 문서 (개발 프로세스)

#### 1.2.1 프롬프트 개선 개발 엔드포인트

**`S5R_Prompt_Refinement_Development_Endpoint_Canonical.md`** (Canonical)
- **역할**: 내부 개발/개선 프로세스 정의 (confirmatory 아님)
- **범위**:
  - Development metric: `blocking_issue_rate_per_group` (development 전용)
  - 프롬프트 개선 절차 (S5 리포트 → Patch Backlog → 프롬프트 수정)
  - 반복 정책 (S5R0 → S5R1 → S5R2, 최대 2단계)
  - 데이터 누수 방지 (DEV set 사용, generalization claim 금지)
- **상태**: ✅ Canonical
- **주의**: 이 문서의 endpoint는 **confirmatory 실험과 분리됨**

#### 1.2.2 프롬프트 개선 방법론

**`S5_Prompt_Refinement_Methodology_Canonical.md`** (Canonical)
- **역할**: S5 리포트를 활용한 프롬프트 개선 방법론 (작업 프로세스)
- **범위**:
  - S5 리포트 구조 설명
  - Patch Backlog 생성 방법
  - 프롬프트 패치 작성 예시
  - 버전 관리 규칙
- **상태**: ✅ Canonical
- **관계**: `S5R_Prompt_Refinement_Development_Endpoint_Canonical.md`의 구체적 실행 방법

### 1.3 Supporting/Reference 문서 (참고용)

#### 1.3.1 정량적 평가 계획

**`S5_Prompt_Improvement_Quantitative_Evaluation_Plan.md`**
- **역할**: Canonical prereg 문서를 참조하는 실행 가이드
- **범위**:
  - Primary endpoint: `S2_any_issue_rate_per_group` (canonical과 일치)
  - 실험 실행 명령어
  - 비교 분석 스크립트 사용법
- **상태**: ⚠️ **Canonical 문서와 정렬 필요** (아래 2.1 참조)

#### 1.3.2 가설 및 방법

**`S5_Prompt_Improvement_Hypothesis_and_Methods.md`**
- **역할**: Canonical prereg 문서를 참조하는 가설 정리 및 논문 작성 가이드
- **범위**:
  - 연구 가설 (Target 1, Target 2)
  - 프롬프트 버전 히스토리
  - 논문 Methods/Results 섹션 예시
- **상태**: ⚠️ **Canonical 문서와 정렬 필요** (아래 2.1 참조)

#### 1.3.3 프로토콜 개정 요약

**`S5R_Protocol_Revision_Summary.md`**
- **역할**: 프로토콜 개정 내역 요약 (변경 이력)
- **상태**: ✅ 정상 (참고용)

#### 1.3.4 실험 인계 문서

**`0_Protocol/05_Pipeline_and_Execution/archived/2025-12/S5_Prompt_Freeze_and_Experiment_Handoff.md`**
- **역할**: 프롬프트 freeze 후 실험 실행을 위한 인계 문서
- **상태**: ✅ 정상 (작업 문서)

#### 1.3.5 레지스트리 상태 확인

**`S5R0_Registry_Status_Check.md`**
- **역할**: S5R0 실험 실행 전 레지스트리 상태 확인
- **상태**: ✅ 정상 (작업 문서)

#### 1.3.6 리포트 분석

**`S5_Report_Analysis_and_Improvements_DEV_armG_s5loop_diverse.md`**
- **역할**: 특정 run_tag의 S5 리포트 분석 결과 (역사적 기록)
- **상태**: ✅ 정상 (작업 문서)

### 1.4 Other Documents (다른 범위)

#### 1.4.1 FINAL QA Alignment

**`S5_vs_FINAL_QA_Alignment_Analysis.md`**
- **역할**: S5 LLM 검증과 FINAL QA 설문의 일치성 분석 (FINAL QA 평가용)
- **범위**: FINAL QA phase (S5R 실험과 별개)
- **상태**: ✅ 정상

#### 1.4.2 S5 Validation Plan (Option B)

**`S5_Validation_Plan_OptionB_Canonical.md`**
- **역할**: FINAL QA 단계에서의 S5 Validation 구현 계획 (FINAL QA 평가용)
- **범위**: FINAL QA phase (S5R 실험과 별개)
- **상태**: ✅ 정상

#### 1.4.3 시간 측정 계획

**`S5_Time_Measurement_and_Comparison_Plan.md`**
- **역할**: Human Rater vs S5 시스템 시간 비교 (독립 연구 질문)
- **범위**: S5R 실험과 별개
- **상태**: ✅ 정상

---

## 2. 일관성 문제 및 해결 방안

### 2.1 Primary Endpoint 불일치 (해결됨 - 역할 구분 필요)

**문제 인식**:
- `S5R_Experiment_Power_and_Significance_Plan.md`: `S2_any_issue_rate_per_group` (confirmatory)
- `S5R_Prompt_Refinement_Development_Endpoint_Canonical.md`: `blocking_issue_rate_per_group` (development)

**해결 방안**:
- ✅ **이것은 문제가 아님** - 역할이 다름
- Development endpoint는 **내부 개발 프로세스**용 지표
- Confirmatory endpoint는 **논문 보고**용 지표
- 두 문서 모두 명확히 범위를 구분하고 있음

**권장 조치**:
- 두 문서에 명시적으로 "역할 구분" 섹션 추가 (선택사항)

### 2.2 Supporting 문서들의 Canonical 정렬 필요

**문제**:
- `S5_Prompt_Improvement_Quantitative_Evaluation_Plan.md`와 `S5_Prompt_Improvement_Hypothesis_and_Methods.md`가 canonical prereg 문서와 대부분 일치하지만, 일부 세부사항에서 혼동 가능

**해결 방안**:
1. 두 문서에 명시적으로 canonical 문서 참조 추가
2. 중복된 endpoint 정의 제거하고 canonical 문서 참조로 대체
3. Canonical 문서와 다른 부분이 있다면 주석으로 명시

**구체적 수정 사항**:

#### 2.2.1 `S5_Prompt_Improvement_Quantitative_Evaluation_Plan.md` 수정

**현재 문제**:
- Section 2.4에 "Option A/B/C" 비교 옵션이 나열되어 있으나, canonical에서는 "contemporaneous before_rerun vs after"가 기본

**수정 방안**:
- Section 2.4에 canonical 문서 명시적 참조 추가
- "Option A (권장)"만 남기고 나머지는 참고로 이동

#### 2.2.2 `S5_Prompt_Improvement_Hypothesis_and_Methods.md` 수정

**현재 상태**:
- 이미 canonical 문서 참조가 있음 (line 11-12)
- 대부분 정렬되어 있음

**수정 방안**:
- 중복된 endpoint 정의 부분에 canonical 문서 참조 강화
- 논문 예시 템플릿에서 canonical의 보고 체크리스트와 일치 확인

### 2.3 Version Naming 일관성 (부분적 문제)

**문제**:
- 일부 문서에서 v12/v9, v13/v10, v14/v11 같은 숫자 버전을 직접 언급
- S5R0, S5R1, S5R2 라운드 표기를 혼용

**해결 방안**:
- ✅ `S5_Version_Naming_S5R_Canonical.md`에 매핑 테이블이 있음
- Supporting 문서에서 v버전을 언급할 때는 S5R 라운드도 함께 표기
- 예: "S5R2 (Text: v14/v11)" 또는 "v14/v11 (S5R2)"

**구체적 수정 사항**:

#### 2.3.1 `S5_Prompt_Improvement_Quantitative_Evaluation_Plan.md`
- v12/v9, v13/v10, v14/v11 언급 시 S5R 라운드 함께 표기

#### 2.3.2 `S5_Prompt_Improvement_Hypothesis_and_Methods.md`
- 이미 S5R 라운드 표기가 잘 되어 있음 (✅)

#### 2.3.3 `0_Protocol/05_Pipeline_and_Execution/archived/2025-12/S5_Prompt_Freeze_and_Experiment_Handoff.md`
- 이미 S5R 라운드 표기가 잘 되어 있음 (✅)

### 2.4 Development vs Confirmatory 혼동 방지

**문제**:
- `S5R_Prompt_Refinement_Development_Endpoint_Canonical.md`의 development metric과 confirmatory endpoint가 다른 문서에서 혼동될 수 있음

**해결 방안**:
- 두 문서 모두에 명시적 역할 구분 섹션 추가 (이미 있으나 강화 가능)
- Development endpoint 문서에 "이 지표는 confirmatory 실험과 별개" 경고 강화

### 2.5 중복 내용 정리

**문제**:
- 프롬프트 개선 방법론이 여러 문서에 중복
- 실험 설계 설명이 여러 문서에 분산

**해결 방안**:
- ✅ 이미 역할 구분이 잘 되어 있음:
  - `S5_Prompt_Refinement_Methodology_Canonical.md`: 방법론 (작업 프로세스)
  - `S5R_Prompt_Refinement_Development_Endpoint_Canonical.md`: 개발 엔드포인트 (지표/정책)
  - `S5R_Experiment_Power_and_Significance_Plan.md`: Confirmatory 실험 설계
- 각 문서에 다른 문서로의 명확한 링크 추가 (이미 대부분 있음)

---

## 3. 권장 문서 구조 (현재 상태 + 개선)

### 3.1 계층 구조

```
Level 1: Canonical (권위 있는 단일 소스)
├── S5R_Experiment_Power_and_Significance_Plan.md (Confirmatory 실험 설계)
├── S5_Version_Naming_S5R_Canonical.md (네이밍 규칙)
├── S5R_Prompt_Refinement_Development_Endpoint_Canonical.md (Development 프로세스)
└── S5_Prompt_Refinement_Methodology_Canonical.md (개선 방법론)

Level 2: Supporting (Canonical을 참조)
├── S5_Prompt_Improvement_Quantitative_Evaluation_Plan.md (실행 가이드)
├── S5_Prompt_Improvement_Hypothesis_and_Methods.md (가설/논문 가이드)
└── archived/2025-12/S5_Prompt_Freeze_and_Experiment_Handoff.md (작업 인계)

Level 3: Working Documents (작업 기록)
├── S5R0_Registry_Status_Check.md
├── S5_Report_Analysis_and_Improvements_DEV_armG_s5loop_diverse.md
└── S5R_Protocol_Revision_Summary.md

Level 4: Other Scope (별도 범위)
├── S5_vs_FINAL_QA_Alignment_Analysis.md (FINAL QA)
├── S5_Validation_Plan_OptionB_Canonical.md (FINAL QA)
└── S5_Time_Measurement_and_Comparison_Plan.md (시간 비교)
```

### 3.2 문서 간 참조 관계

**Canonical 문서들**:
- 독립적 (서로 참조 가능하나 의존성 최소화)

**Supporting 문서들**:
- 반드시 해당하는 Canonical 문서 참조
- Canonical과 다른 부분이 있으면 명시적으로 주석

**Working Documents**:
- 필요시 Canonical/Supporting 문서 참조

---

## 4. 즉시 조치 사항

### 4.1 필수 (즉시 수정)

#### 4.1.1 `S5_Prompt_Improvement_Quantitative_Evaluation_Plan.md`

**수정 사항**:
1. Section 2.4 "비교 옵션" 정리
   - "Option A (권장)"를 기본으로 명시
   - Option B/C는 참고 섹션으로 이동 또는 제거
   - Canonical 문서 명시적 참조 추가

2. Section 3.1.1에서 v버전 언급 시 S5R 라운드 함께 표기
   - 예: "S5R2 (Text: v14/v11)"

**수정 위치**:
- Line 38-81: Step 1-4 비교 옵션 정리
- Line 96-105: Primary endpoint 정의 부분

#### 4.1.2 `S5_Prompt_Improvement_Hypothesis_and_Methods.md`

**수정 사항**:
1. Section 2.2 "프롬프트 버전 히스토리"에서 v버전 언급 시 S5R 라운드 함께 표기 (이미 잘 되어 있으나 일관성 확인)

2. Section 3.1에서 canonical 문서 참조 강화

**수정 위치**:
- Line 58-87: 프롬프트 버전 히스토리 테이블

### 4.2 권장 (선택적 개선)

#### 4.2.1 역할 구분 명시 강화

**`S5R_Prompt_Refinement_Development_Endpoint_Canonical.md`**:
- Section 1.1에 "이 문서의 endpoint는 confirmatory 실험(`S5R_Experiment_Power_and_Significance_Plan.md`)과 별개" 경고 강화

**`S5R_Experiment_Power_and_Significance_Plan.md`**:
- Section "Endpoints"에 "이 endpoint는 development process(`S5R_Prompt_Refinement_Development_Endpoint_Canonical.md`)와 별개" 명시

#### 4.2.2 문서 간 링크 강화

모든 Supporting 문서의 시작 부분에 관련 Canonical 문서 링크 명시

---

## 5. 검증 체크리스트

### 5.1 일관성 검증

- [ ] 모든 Supporting 문서가 해당 Canonical 문서를 명시적으로 참조하는가?
- [ ] Primary endpoint 정의가 Canonical 문서와 일치하는가?
  - Confirmatory: `S2_any_issue_rate_per_group` (단일)
  - Development: `blocking_issue_rate_per_group` (개발 전용)
- [ ] Version naming이 일관되게 사용되는가? (v버전 언급 시 S5R 라운드도 함께)
- [ ] DEV vs HOLDOUT 구분이 명확한가?
- [ ] Target 1 vs Target 2 인과 질문 분리가 명확한가?

### 5.2 중복 검증

- [ ] 프롬프트 개선 방법론이 적절히 역할 구분되어 있는가?
  - 방법론: `S5_Prompt_Refinement_Methodology_Canonical.md`
  - 개발 엔드포인트: `S5R_Prompt_Refinement_Development_Endpoint_Canonical.md`
- [ ] 실험 설계 설명이 Canonical 문서에 집중되어 있는가?
- [ ] Supporting 문서는 실행 가이드/참고 역할만 하는가?

---

## 6. 결론

### 6.1 현재 상태

**✅ 잘 정리된 부분**:
- Canonical 문서들이 명확히 정의되어 있음
- 역할 구분이 대부분 명확함
- Version naming 규칙이 잘 정의되어 있음

**⚠️ 개선 필요 부분**:
- Supporting 문서들이 Canonical과 완전히 정렬되지 않음 (작은 차이)
- 일부 문서에서 v버전만 언급 (S5R 라운드 표기 부족)
- Development vs Confirmatory endpoint 혼동 가능성 (명시적 경고 강화 필요)

### 6.2 권장 조치 우선순위

1. **높음** (즉시): `S5_Prompt_Improvement_Quantitative_Evaluation_Plan.md`의 비교 옵션 정리
2. **중간** (선택): Version naming 일관성 강화 (v버전 언급 시 S5R 라운드 함께)
3. **낮음** (선택): 역할 구분 명시 강화 (이미 잘 되어 있음)

### 6.3 최종 평가

**전체적으로 문서 구조가 잘 정리되어 있으며**, 일부 Supporting 문서의 세부사항만 정렬하면 됩니다. 주요 Canonical 문서들은 명확하고 일관성 있습니다.

---

**작성자**: MeducAI Research Team  
**검토 필요**: 모든 Supporting 문서 작성자

