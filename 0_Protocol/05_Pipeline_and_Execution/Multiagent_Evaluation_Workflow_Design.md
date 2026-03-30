# 멀티에이전트 수정 결과 평가 워크플로우 설계

**작성 일자**: 2025-12-29  
**목적**: QA 리뷰어가 멀티에이전트 수정 결과를 평가하는 3-pass 워크플로우 정의  
**인계 대상**: 새로운 Agent (멀티에이전트 평가 시스템 구현)  
**상태**: 미래 계획 (멀티에이전트 시스템 구축 후 적용)

---

## 1. 개요

### 1.1 목적

QA 리뷰어가 멀티에이전트 시스템의 수정 결과를 평가하고, 평가 agent(S5)의 정확도를 검증하는 3-pass 워크플로우를 설계합니다.

**중요**: 이 문서는 **미래 계획 문서**입니다. 현재는 2-pass workflow (Pre-S5 → S5 Reveal → Post-S5)가 사용되고 있으며, 이 3-pass workflow는 멀티에이전트 시스템 (S5R/S1R/S2R)이 구축된 후에 적용됩니다. 현재 2-pass workflow는 `Human_Rating_Schema_Canonical.md`와 `FINAL_QA_Form_Design.md`에 정의되어 있으며, 이 문서와는 별개의 평가 시스템입니다.

### 1.2 현재 워크플로우와의 관계

**현재 워크플로우 (2-pass)**:
- `Human_Rating_Schema_Canonical.md`: 2-pass workflow (Pre-S5 → S5 Reveal → Post-S5)
- `FINAL_QA_Form_Design.md`: 2-pass workflow 구현 가이드
- **목적**: S5 validation 결과를 참고하여 Human Rater가 평가 수정
- **Primary Endpoint**: Pre-S5 ratings (arm comparison용)

**미래 워크플로우 (3-pass, 이 문서)**:
- 멀티에이전트 수정 결과 평가 전용
- **목적**: 멀티에이전트 수정 결과의 효과 측정 및 S5 agent 정확도 검증
- **Primary Endpoint**: Pre-Multiagent ratings (멀티에이전트 수정 전 원본 평가)
- **Secondary Endpoint**: Post-Multiagent ratings (멀티에이전트 수정 후 평가)

**통합 방식**:
- 현재 2-pass workflow는 멀티에이전트 시스템이 구축되기 전까지 계속 사용됩니다.
- 멀티에이전트 시스템이 구축된 후에는:
  - 멀티에이전트 수정이 적용된 콘텐츠: 3-pass workflow (이 문서)
  - 멀티에이전트 수정이 적용되지 않은 콘텐츠: 2-pass workflow 유지

### 1.2 핵심 원칙

1. **원본 평가 우선**: 멀티에이전트 수정 결과를 보기 전에 원본을 평가 (primary endpoint)
2. **수정 결과 평가**: 멀티에이전트 수정 결과를 본 후 평가 (secondary endpoint)
3. **Agent 정확도 검증**: 평가 agent(S5)의 판단이 올바른지 평가 (tool effect measurement)

---

## 2. 3-Pass 워크플로우

### 2.1 전체 흐름

```
┌─────────────────────────────────────────────────────────┐
│ Pass 1: Pre-Multiagent Evaluation (Primary Endpoint)    │
│ - 원본 콘텐츠만 보여줌                                     │
│ - 멀티에이전트 수정 결과 숨김                              │
│ - 평가: Blocking Error, Technical Accuracy, Quality      │
│ - 결과: pre_multiagent_rating                            │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ Pass 2: Multiagent Results Reveal                       │
│ - 멀티에이전트 수정 결과 공개                              │
│ - 원본 vs 수정본 비교 표시                                │
│ - S5 평가 결과 표시                                       │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ Pass 3: Post-Multiagent Evaluation (Secondary Endpoint)  │
│ - 수정본 평가                                             │
│ - S5 평가 동의/비동의 평가                                 │
│ - Agent 정확도 평가                                       │
│ - 결과: post_multiagent_rating                           │
└─────────────────────────────────────────────────────────┘
```

### 2.2 Pass 1: Pre-Multiagent Evaluation

**목적**: 멀티에이전트 수정 결과의 영향을 받지 않은 원본 평가 (Primary Endpoint)

**평가 항목**:
- **B1. Blocking Error** (Yes/No)
- **B1.5. Technical Accuracy** (0.0 / 0.5 / 1.0)
- **B2. Overall Card Quality** (1-5 Likert)
- **B3. Evidence Comment** (조건부: B1=Yes 또는 B2≤2)

**제약 조건**:
- 멀티에이전트 수정 결과는 **완전히 숨김**
- S5 평가 결과도 **숨김** (원본만 평가)
- 평가 제출 후 **immutable** (수정 불가)

**데이터 구조**:
```json
{
  "pre_multiagent_rating": {
    "timestamp_submitted_ms": 1703587200000,
    "time_pre_ms": 45000,
    "blocking_error": false,
    "technical_accuracy": 1.0,
    "overall_quality": 4,
    "evidence_comment": null
  }
}
```

### 2.3 Pass 2: Multiagent Results Reveal

**목적**: 멀티에이전트 수정 결과와 S5 평가 결과 공개

**표시 내용**:
1. **원본 콘텐츠** (읽기 전용, 회색 배경)
2. **수정본 콘텐츠** (강조 표시, 변경 부분 하이라이트)
3. **변경 사항 요약**:
   - 변경된 필드 (Front, Back, Options, etc.)
   - 변경 이유 (S5 이슈 설명)
   - S5 평가 결과 (blocking_error, technical_accuracy, educational_quality)
4. **S5 이슈 목록**:
   - 테이블 평가 이슈: `issues[]` (테이블 레벨)
   - 인포그래픽 평가 이슈: `table_visual_validation.issues[]` (단일) 또는 `table_visual_validations[].issues[]` (클러스터별, 최대 4개)
   - 각 이슈의 severity, type, description
   - RAG evidence (있는 경우)
   - 클러스터별 인포그래픽 이슈는 각 클러스터 ID와 함께 표시

**UI 디자인**:
- Side-by-side 비교 또는 Diff 뷰
- 변경 부분 하이라이트 (추가: 녹색, 삭제: 빨간색, 수정: 노란색)
- S5 평가 결과 패널 (참고용)

### 2.4 Pass 3: Post-Multiagent Evaluation

**목적**: 수정본 평가 및 S5 평가 정확도 검증

**평가 항목**:

#### 3.1 수정본 평가 (Post-Multiagent Rating)

- **B1. Blocking Error** (Yes/No) - 수정본 기준
- **B1.5. Technical Accuracy** (0.0 / 0.5 / 1.0) - 수정본 기준
- **B2. Overall Card Quality** (1-5 Likert) - 수정본 기준
- **B3. Evidence Comment** (조건부)

**데이터 구조**:
```json
{
  "post_multiagent_rating": {
    "timestamp_submitted_ms": 1703587300000,
    "correction_time_ms": 5000,
    "blocking_error": false,
    "technical_accuracy": 1.0,
    "overall_quality": 5,
    "evidence_comment": null
  }
}
```

#### 3.2 S5 평가 동의/비동의 평가 (NEW)

**C1. S5 Blocking Error 판단 동의 여부** (Required)

- **질문**: "S5가 원본에 blocking error가 있다고 판단한 것에 동의하시나요?"
- **타입**: Radio button
- **옵션**:
  - `AGREE`: "동의함 (S5 판단이 맞음)"
  - `DISAGREE_FALSE_POSITIVE`: "비동의 - False Positive (원본에 blocking error 없음)"
  - `DISAGREE_FALSE_NEGATIVE`: "비동의 - False Negative (원본에 blocking error 있지만 S5가 놓침)"
  - `NOT_APPLICABLE`: "해당 없음 (S5가 blocking error를 판단하지 않음)"
- **필드명**: `s5_blocking_error_agreement`

**C2. S5 Technical Accuracy 평가 동의 여부** (Required)

- **질문**: "S5가 평가한 Technical Accuracy (0/0.5/1)에 동의하시나요?"
- **타입**: Radio button
- **옵션**:
  - `AGREE`: "동의함"
  - `DISAGREE_OVERESTIMATED`: "비동의 - S5가 과대평가 (실제보다 높게 평가)"
  - `DISAGREE_UNDERESTIMATED`: "비동의 - S5가 과소평가 (실제보다 낮게 평가)"
  - `NOT_APPLICABLE`: "해당 없음"
- **필드명**: `s5_technical_accuracy_agreement`

**C3. S5 Educational Quality 평가 동의 여부** (Required)

- **질문**: "S5가 평가한 Educational Quality (1-5)에 동의하시나요?"
- **타입**: Radio button
- **옵션**:
  - `AGREE`: "동의함"
  - `DISAGREE_OVERESTIMATED`: "비동의 - S5가 과대평가"
  - `DISAGREE_UNDERESTIMATED`: "비동의 - S5가 과소평가"
  - `NOT_APPLICABLE`: "해당 없음"
- **필드명**: `s5_educational_quality_agreement`

**C4. S5 이슈 판단 동의 여부** (Required if S5 has issues)

- **질문**: "S5가 식별한 이슈들에 동의하시나요?"
- **타입**: Checkbox (multiple selection)
- **옵션**: 각 S5 이슈에 대해
  - `AGREE`: "동의함"
  - `DISAGREE_FALSE_POSITIVE`: "False Positive (이슈가 아님)"
  - `DISAGREE_MISSED`: "False Negative (S5가 놓친 이슈)"
- **필드명**: `s5_issues_agreement[]` (array of objects)

#### 3.3 수정본 수용 여부 평가 (NEW)

**D1. 수정본 수용 여부** (Required)

- **질문**: "멀티에이전트 수정본을 수용하시겠습니까?"
- **타입**: Radio button
- **옵션**:
  - `ACCEPT`: "수용함 (수정본이 원본보다 나음)"
  - `REJECT`: "거부함 (원본이 더 나음)"
  - `PARTIAL`: "부분 수용 (일부만 수용)"
- **필드명**: `multiagent_repair_acceptance`

**D2. 수용/거부 이유** (Required if D1 != ACCEPT)

- **타입**: Text area (1-3 lines, max 500 chars)
- **필드명**: `acceptance_reason`

**D3. 수정본 품질 개선 여부** (Required)

- **질문**: "수정본이 원본보다 품질이 개선되었나요?"
- **타입**: Radio button
- **옵션**:
  - `IMPROVED`: "개선됨"
  - `SAME`: "동일함"
  - `DEGRADED`: "악화됨"
- **필드명**: `quality_change`

---

## 3. 데이터 스키마

### 3.1 통합 평가 레코드

**파일**: `human_rating_with_multiagent__arm{arm}.jsonl`

**스키마**:
```json
{
  "schema_version": "HUMAN_RATING_MULTIAGENT_v1.0",
  "group_id": "grp_xxx",
  "card_id": "card_xxx",
  "arm": "G",
  "run_tag": "DEV_armG_s5loop_diverse_20251229_065718",
  "rater_id": "rater_001",
  "rater_role": "Resident",
  
  "pre_multiagent_rating": {
    "timestamp_submitted_ms": 1703587200000,
    "time_pre_ms": 45000,
    "blocking_error": false,
    "technical_accuracy": 1.0,
    "overall_quality": 4,
    "evidence_comment": null
  },
  
  "multiagent_reveal": {
    "timestamp_revealed_ms": 1703587250000,
    "s5_snapshot_id": "s5_xxx",
    "multiagent_repair_snapshot_id": "repair_xxx"
  },
  
  "post_multiagent_rating": {
    "timestamp_submitted_ms": 1703587300000,
    "correction_time_ms": 5000,
    "blocking_error": false,
    "technical_accuracy": 1.0,
    "overall_quality": 5,
    "evidence_comment": null
  },
  
  "s5_agreement": {
    "s5_blocking_error_agreement": "AGREE",
    "s5_technical_accuracy_agreement": "AGREE",
    "s5_educational_quality_agreement": "DISAGREE_UNDERESTIMATED",
    "s5_issues_agreement": [
      {
        "issue_id": "issue_001",
        "agreement": "AGREE"
      },
      {
        "issue_id": "issue_002",
        "agreement": "DISAGREE_FALSE_POSITIVE"
      }
    ]
  },
  
  "multiagent_repair_evaluation": {
    "multiagent_repair_acceptance": "ACCEPT",
    "acceptance_reason": null,
    "quality_change": "IMPROVED"
  },
  
  "session_metadata": {
    "total_session_duration_ms": 100000,
    "active_duration_ms": 95000,
    "idle_duration_ms": 5000
  }
}
```

---

## 4. UI/UX 설계

### 4.1 Pass 1: Pre-Multiagent Form

**레이아웃**:
```
┌─────────────────────────────────────────────────┐
│ 원본 콘텐츠 (Card Front/Back)                     │
│ - 멀티에이전트 수정 결과 숨김                      │
│ - S5 평가 결과 숨김                                │
└─────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────┐
│ Pre-Multiagent Rating Section                   │
│ - B1. Blocking Error (Yes/No)                   │
│ - B1.5. Technical Accuracy (0/0.5/1)            │
│ - B2. Overall Quality (1-5)                     │
│ - B3. Evidence Comment (조건부)                   │
│ [Submit Pre-Multiagent Rating]                  │
└─────────────────────────────────────────────────┘
```

### 4.2 Pass 2: Reveal Section

**레이아웃**:
```
┌─────────────────────────────────────────────────┐
│ [Reveal Multiagent Results] 버튼                  │
│ (Pre-Multiagent 제출 후 활성화)                   │
└─────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────┐
│ 원본 vs 수정본 비교                               │
│ - Side-by-side 또는 Diff 뷰                       │
│ - 변경 부분 하이라이트                            │
└─────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────┐
│ S5 평가 결과 패널                                 │
│ - S5 Blocking Error Flag                         │
│ - S5 Technical Accuracy                          │
│ - S5 Educational Quality                        │
│ - S5 Issues List                                 │
│   * 테이블 평가 이슈                              │
│   * 인포그래픽 평가 이슈 (클러스터별, 최대 4개)    │
│ - RAG Evidence (있는 경우)                        │
└─────────────────────────────────────────────────┘
```

### 4.3 Pass 3: Post-Multiagent Form

**레이아웃**:
```
┌─────────────────────────────────────────────────┐
│ 수정본 콘텐츠 (Card Front/Back)                   │
└─────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────┐
│ Post-Multiagent Rating Section                  │
│ - B1. Blocking Error (Yes/No) - 수정본 기준      │
│ - B1.5. Technical Accuracy (0/0.5/1) - 수정본 기준│
│ - B2. Overall Quality (1-5) - 수정본 기준        │
│ - B3. Evidence Comment (조건부)                  │
└─────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────┐
│ S5 평가 동의/비동의 평가                          │
│ - C1. S5 Blocking Error 판단 동의 여부           │
│ - C2. S5 Technical Accuracy 평가 동의 여부      │
│ - C3. S5 Educational Quality 평가 동의 여부      │
│ - C4. S5 이슈 판단 동의 여부 (각 이슈별)         │
└─────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────┐
│ 수정본 수용 여부 평가                             │
│ - D1. 수정본 수용 여부                           │
│ - D2. 수용/거부 이유 (조건부)                     │
│ - D3. 수정본 품질 개선 여부                      │
└─────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────┐
│ [Submit Final Rating] 버튼                       │
└─────────────────────────────────────────────────┘
```

---

## 5. 분석 계획

### 5.1 Primary Endpoints (Pre-Multiagent)

**Arm Comparison**:
- `blocking_error_rate_pre`: `mean(blocking_error_pre)` per arm
- `technical_accuracy_mean_pre`: `mean(technical_accuracy_pre)` per arm (0.0/0.5/1.0 스케일)
- `overall_quality_mean_pre`: `mean(overall_quality_pre)` per arm (1-5 Likert 스케일)

**사용**: 모든 arm 비교 분석은 Pre-Multiagent 평가만 사용

**Technical Accuracy 정의**: `QA_Metric_Definitions.md` Section 3 참조
- 1.0: Core concept and explanation are fully correct
- 0.5: Core concept is correct, but explanation contains minor omissions
- 0.0: Core concept is incorrect, misleading, or likely to cause misunderstanding

### 5.2 Secondary Endpoints (Post-Multiagent)

**Tool Effect Measurement**:
- `blocking_error_change`: `blocking_error_post - blocking_error_pre`
- `technical_accuracy_change`: `technical_accuracy_post - technical_accuracy_pre`
- `overall_quality_change`: `overall_quality_post - overall_quality_pre`
- `repair_acceptance_rate`: `mean(multiagent_repair_acceptance == "ACCEPT")`
- `quality_improvement_rate`: `mean(quality_change == "IMPROVED")`

### 5.3 S5 Agent Accuracy Metrics

**S5 평가 정확도**:
- `s5_blocking_error_agreement_rate`: `mean(s5_blocking_error_agreement == "AGREE")`
- `s5_technical_accuracy_agreement_rate`: `mean(s5_technical_accuracy_agreement == "AGREE")`
- `s5_educational_quality_agreement_rate`: `mean(s5_educational_quality_agreement == "AGREE")`
- `s5_false_positive_rate`: `mean(s5_blocking_error_agreement == "DISAGREE_FALSE_POSITIVE")`
- `s5_false_negative_rate`: `mean(s5_blocking_error_agreement == "DISAGREE_FALSE_NEGATIVE")`

**S5 이슈 정확도**:
- `s5_issue_agreement_rate`: `mean(s5_issues_agreement[].agreement == "AGREE")`
- `s5_issue_false_positive_rate`: `mean(s5_issues_agreement[].agreement == "DISAGREE_FALSE_POSITIVE")`
- `s5_issue_false_negative_rate`: `mean(s5_issues_agreement[].agreement == "DISAGREE_MISSED")`

---

## 6. 구현 체크리스트

### 6.1 Frontend Components

- [ ] `PreMultiagentRatingForm` component
- [ ] `MultiagentResultsReveal` component
- [ ] `PostMultiagentRatingForm` component
- [ ] `S5AgreementEvaluation` component
- [ ] `MultiagentRepairEvaluation` component
- [ ] `OriginalVsRepairedComparison` component (Diff view)
- [ ] Time measurement hooks

### 6.2 Backend API Integration

- [ ] Pre-Multiagent submission endpoint
- [ ] Multiagent results reveal endpoint
- [ ] Post-Multiagent submission endpoint
- [ ] S5 validation data fetch
- [ ] Multiagent repair data fetch
- [ ] Error handling and retry logic

### 6.3 Validation Logic

- [ ] Pre-Multiagent field validation
- [ ] Post-Multiagent field validation
- [ ] S5 agreement validation
- [ ] Multiagent repair evaluation validation
- [ ] Time calculation logic

### 6.4 Data Schema

- [ ] Human rating schema 업데이트 (multiagent fields 추가)
- [ ] S5 validation schema 확인 (필요 시 업데이트)
- [ ] Multiagent repair schema 확인 (필요 시 업데이트)

---

## 7. 관련 문서

### 7.1 현재 워크플로우 (2-pass)

- **Human Rating Schema (2-pass)**: `0_Protocol/04_Step_Contracts/Step05_S5/Human_Rating_Schema_Canonical.md`
  - 현재 사용 중인 2-pass workflow 스키마 정의
  - Pre-S5 → S5 Reveal → Post-S5 구조
- **FINAL QA Form Design (2-pass)**: `0_Protocol/06_QA_and_Study/FINAL_QA_Form_Design.md`
  - 현재 2-pass workflow 구현 가이드
  - Technical Accuracy 필드 포함 (v1.1)

### 7.2 멀티에이전트 시스템

- **S5 Multi-agent Repair Plan**: `0_Protocol/05_Pipeline_and_Execution/S5_Multiagent_Repair_Plan_OptionC_Canonical.md`
  - 멀티에이전트 수정 시스템 (S5R/S1R/S2R) 설계
  - 이 3-pass workflow의 전제 조건

### 7.3 S5 Validation

- **S5 Validation Schema**: `0_Protocol/04_Step_Contracts/Step05_S5/S5_Validation_Schema_Canonical.md`
  - S5 validation 결과 스키마
  - Technical Accuracy (0.0/0.5/1.0), Educational Quality (1-5) 평가 포함
- **S5 S1 평가 명세서**: `0_Protocol/04_Step_Contracts/Step05_S5/S5_S1_Validation_Specification.md`
  - S5의 2단계 평가 구조 (테이블 평가 + 인포그래픽 평가) 상세 설명
  - 클러스터 처리 로직, 출력 스키마 (`table_visual_validation` vs `table_visual_validations[]`)
  - 인포그래픽 평가 항목 (Information Clarity, Anatomical Accuracy, Prompt Compliance, Table-Visual Consistency)

### 7.4 QA Metrics

- **QA Metric Definitions**: `0_Protocol/05_Pipeline_and_Execution/QA_Metric_Definitions.md`
  - Technical Accuracy 정의 (0.0/0.5/1.0 스케일)
  - Educational Quality 정의 (1-5 Likert 스케일)
- **S5 vs FINAL QA Alignment Analysis**: `0_Protocol/05_Pipeline_and_Execution/S5_vs_FINAL_QA_Alignment_Analysis.md`
  - S5와 Human Rater 평가 항목 정렬 분석

---

## 8. 인계 사항

### 8.1 핵심 요구사항

1. **3-Pass Workflow 구현**:
   - Pass 1: Pre-Multiagent (원본만 평가)
   - Pass 2: Reveal (멀티에이전트 결과 공개)
   - Pass 3: Post-Multiagent (수정본 평가 + S5 동의 평가)

2. **평가 항목**:
   - 원본/수정본 평가 (Blocking Error, Technical Accuracy, Quality)
   - S5 평가 동의/비동의 평가
   - 수정본 수용 여부 평가

3. **데이터 스키마**:
   - Pre-Multiagent rating
   - Post-Multiagent rating
   - S5 agreement evaluation
   - Multiagent repair evaluation

### 8.2 구현 우선순위

1. **Phase 1**: 기본 3-pass workflow 구현
   - Pre-Multiagent 평가
   - Multiagent 결과 reveal
   - Post-Multiagent 평가

2. **Phase 2**: S5 동의 평가 추가
   - S5 평가 동의/비동의 필드
   - S5 이슈별 동의 평가

3. **Phase 3**: 수정본 수용 평가 추가
   - 수정본 수용 여부
   - 품질 개선 여부

### 8.3 주의사항

1. **Primary Endpoint 보호**:
   - Pre-Multiagent 평가는 멀티에이전트 결과의 영향을 받지 않아야 함
   - 평가 제출 후 immutable

2. **UI/UX**:
   - 원본 vs 수정본 비교 뷰가 명확해야 함
   - S5 평가 결과가 참고용임을 명시

3. **데이터 무결성**:
   - 모든 필드가 필수 조건에 따라 검증되어야 함
   - 타임스탬프가 올바르게 기록되어야 함

---

**작성자**: MeducAI Research Team  
**인계 대상**: 새로운 Agent (멀티에이전트 평가 시스템 구현)  
**상태**: 미래 계획 (멀티에이전트 시스템 구축 후 적용)

---

## 9. Version History

- **v1.0** (2025-12-29): 초기 문서 작성
- **v1.1** (2025-12-29): 관계 명확화 섹션 추가 (현재 2-pass workflow와의 관계), Technical Accuracy 필드 명시, 관련 문서 링크 업데이트
- **v1.2** (2025-12-30): S5 평가 구조 명세 추가 (테이블 평가 + 인포그래픽 평가), 클러스터별 인포그래픽 이슈 처리 명시, s5_s1_validation_specification.md 참조 추가

