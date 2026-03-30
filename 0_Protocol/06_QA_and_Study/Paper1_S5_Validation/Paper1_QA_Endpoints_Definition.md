# FINAL QA 설계 및 엔드포인트 정의 (최종 정리, 비판점 반영)

**Date:** 2025-12-26  
**Status:** Draft → Canonical 후보  
**Scope:** FINAL 배포 후보 6,000+ 문항에 대한 품질(오류, 교육목표 충실도) 검증 및 배포 승인 의사결정  
**Core principle:** “LLM 생성물의 자연상태 품질(v1)”과 “HITL(인간 개입) 후 최종 배포물 품질(v2)”을 혼동하지 않는다.

---

## 0. 목표와 주장(Claims)

### 0.1 연구/운영 목표
1) FINAL 배포본(v2)의 **치명 오류율(Critical error rate)**이 허용 가능한 수준 이하임을 보장한다.  
2) FINAL 배포본(v2)이 학습목표(Objective)에 **충실**하며 시험 학습에 적합함을 보장한다.  
3) 제한된 전문의 리소스(10명×30문항)를 활용하여 **안전성(치명 오류 탐지)**과 **대표성(무작위 표본)**을 동시에 확보한다.  
4) 추가 LLM은 “수정(editing)”이 아니라 **triage/flagging**으로 사람 검토를 효율화한다.

### 0.2 주장 범위의 경계(중요)
- 본 설계는 “모델의 자연상태 정확도(수정 전)”를 엄밀히 증명하기보다, **HITL 파이프라인을 거친 최종 배포본 품질(수정 후)**의 안전성과 충실도를 보장하는 것을 1차 목표로 한다.
- 필요 시 “수정 전(v1)” 지표를 별도 보고(탐색/부록)하되, **본결론의 근거는 v2(배포본) 지표**로 둔다.

---

## 0.3 Data Quality Warnings ⚠️

### Critical Issue: AppSheet Time Calculation Error

**분석 시작 전 필수 확인**: Ratings 시트의 시간 계산 컬럼(`post_duration_sec`, `s5_duration_sec`)에 데이터 무결성 문제가 있습니다.

- `post_duration_sec`: 대부분 s5 경과시간을 잘못 담고 있음 (98/107개 행)
- `s5_duration_sec`: 전부 비어있음

**필수 조치**: duration_sec 컬럼 사용 금지, 타임스탬프 차이로 재계산 필수

**상세 문서**: [`QA_Operations/handoffs/APPSHEET_TIME_CALCULATION_ISSUE_2026-01-09.md`](QA_Operations/handoffs/APPSHEET_TIME_CALCULATION_ISSUE_2026-01-09.md)

**Methods 작성 시 명시**:
> "AppSheet duration_sec 컬럼의 데이터 무결성 문제로 인해, 모든 경과 시간은 타임스탬프 차이(submitted_ts - started_ts)를 직접 계산하여 사용하였다."

---

## 1. 데이터와 버전 통제(Freeze rule)

### 1.1 버전 정의
- **v1 (Freeze 평가본):** 평가 시작 시점에 문항/정답/해설을 고정한 스냅샷
- **patch log:** 평가 중 발견된 오류 및 수정 제안(문항 ID 기준)만 기록
- **v2 (최종 배포본):** patch log를 반영하여 확정한 배포 버전

### 1.2 운영 원칙
- 평가 기간 동안 **v1은 변경하지 않는다**(평가 안정성, 재현성).
- 치명 오류가 발견된 문항은 patch log에 즉시 등록하며, 운영상 필요 시 “배포 후보 임시 제외” 표시를 하되 **v1 자체는 변경하지 않는다**.
- 평가 종료 후 v2를 생성하고, **최종 엔드포인트 판정은 v2에서 수행**한다.

### 1.3 v1→v2 연결 규칙(혼동 방지용 운영 정의)
- **v1 라벨**: “수정 전” 콘텐츠에 대한 관측치(자연상태 품질).  
- **v2 라벨**: patch log 반영 이후 “배포본” 콘텐츠에 대한 최종 판정치.
- **원칙(권장):** patch 적용된 문항은 v2 확정 전 **최소 1인(가능하면 adjudicator)의 재검토/검증**을 거쳐 v2 라벨을 확정한다. (미수정 문항은 v1 라벨을 v2로 승계 가능)

---

## 2. 엔드포인트(Outcomes) 및 운영적 정의

### 2.1 Primary Safety Endpoint: 치명 오류율(Critical error rate)

#### 치명 오류(Critical/Blocking error) 정의(요약)
- 정답이 임상적으로 명백히 틀리거나,
- 해설이 정답을 오도하며 환자/학습자에게 위해 가능성이 있거나,
- 핵심 영상소견/진단 논리가 반대로 서술되어 학습을 파괴하는 경우

#### 치명 오류율
- `(#치명 오류 문항) / (평가 대상 문항 수)`

> NOTE: “오류가 없다(0%)”는 절대 주장보다, CI 상한이 사전 기준 이하인지로 의사결정한다.

#### 용어 정합성(기존 문서와의 매핑)
- 본 문서의 **Critical/Blocking error**는 기존 Pipeline-1 문서에서 사용되는 **Blocking error(Accuracy=0.0)** 및/또는 **Major error**와 **동일 계열의 safety-critical 오류**를 의미한다.  
  - 실제 운영에서는 **단일 rubric(예/비예시 포함)으로 판정 기준을 고정**하고, 보고서에서 용어 매핑을 명시한다.

### 2.2 Primary Educational Endpoint: 교육목표 충실도(Objective alignment)

#### 권장 측정(최소 1개는 필수)
1) **Objective alignment (Binary):** Yes/No  
   - Yes: 해당 문항이 지정 Objective(또는 group bullet)에 **직접** 부합
   - No: 간접 관련/주제가 유사하나 핵심 학습목표와 불일치, 또는 목표 밖 내용 중심

2) (선택) **시험적합성(Likert 1–5):** 보드시험 스타일/핵심포인트 적합성

### 2.3 필수 동반 지표: 평가자 신뢰도(Agreement)
- 오류(치명/비치명), alignment(Yes/No)에 대해 평가자 간 합치 지표를 산출한다.
- 희귀 사건(치명 오류)이 매우 낮으면 Cohen’s kappa가 불안정할 수 있어, 상황에 따라 대체 지표(예: AC1 계열)를 사용하거나 해석을 보조한다(문서에 명시).

---

## 3. 샘플링 및 평가 구조(전공의 972 + 전문의 300)

### 3.1 전체 모집단
- FINAL 배포 후보 문항: 6,000+ (유한 모집단)

### 3.2 전공의 평가(대표성 추정의 중심): 972문항 × 2인 독립
- **표본:** 972문항(선정 규칙은 별도 문서로 고정)
- **평가:** 전공의 2인이 서로 독립적으로 평가(블라인드)
- **산출:** (a) 치명 오류 여부, (b) alignment(Yes/No), (c) 필요 시 시험적합성 점수
- **불일치 처리(adjudication):** 4장 SOP에 따라 최종 라벨 확정

> 역할: 972는 전체율(오류율/충실도)의 대표성 있는 추정과 CI 산출의 근간이다.

### 3.3 전문의 평가(검증·안전성 보강): 10명(분과별) × 30문항 = 300문항
- **원칙:** 전문의 평가는 “분과별 오류율의 정밀 추정”이 아니라,
  1) 전공의 라벨의 타당성/합치 확인,
  2) 치명 오류 탐지 강화(특히 위험층),
  3) 분과별 오류 유형/대표 사례 기술
  을 목표로 한다.

#### 3.3.1 분과별 30문항의 권장 구성(층화 추출)
- **Random stratum 20문항:** 분과 내 무작위(대표성)
- **High-risk stratum 10문항:** 아래 조건 중 하나라도 만족하면 포함(탐지 강화)
  - flagger LLM이 Critical/Major로 분류
  - 과거 오류가 잦았던 visual_type/주제
  - guideline/수치/분류체계가 포함된 문항
  - (가능 시) 전공의 2인 불일치(Discordant) 문항에서 일부 포함  
    - 단, 전공의 결과가 들어오기 시작하면 “추가 배정” 형태로 보강

#### 3.3.2 블라인드 및 병렬 진행(타임라인 단축 + 편향 억제)
- 전문의 평가는 전공의 평가 종료를 기다리지 않고 **동시에 시작**한다.
- 전문의에게는 전공의 평가 결과/코멘트/불일치 여부를 **절대 제공하지 않는다(블라인드)**.
- 사후에 매칭하여 합치도 및 불일치 패턴을 분석한다.

---

## 4. Adjudication SOP(최종 라벨 확정 절차)

### 4.1 트리거
- 전공의 2인이 (a) 치명 오류 여부 또는 (b) alignment(Yes/No)에서 불일치할 때
- 또는 flagger가 Critical로 올린 문항 중 사람이 “치명 오류 가능”으로 의심할 때

### 4.2 의사결정자
- 기본: 해당 분과 전문의(가능하면 1인) 또는 중앙 adjudication 위원(지정 1–2인)
- 운영상 어려우면: “합의회의(짧은 비동기 코멘트) → 최종 책임자 1인이 결정” 형태로 단순화

### 4.3 절차
1) 불일치 문항 목록 자동 집계(문항 ID, 쟁점 필드만)
2) adjudicator는 v1 문항을 보고 최종 라벨 확정(치명 오류 Yes/No, alignment Yes/No)
3) patch log에 수정 필요 여부를 기록(수정안은 v2에서 반영)
4) adjudication 로그는 문항 ID 기준으로 보관(감사 가능)

---

## 5. Flagger LLM(수정 금지) 설계: triage/flagging로 사람 검토 효율화

### 5.1 역할 경계(Strict)
- LLM은 문항/정답/해설을 **고치지 않는다**.
- 출력은 오직 “위험 신호”와 “근거 지점”이다.
- 목적은 (1) 고위험 문항 우선 검토, (2) 불일치 케이스 집중, (3) 전문의 high-risk strata 구성 지원이다.

### 5.2 출력 스키마(필수 필드)
- `risk_label`: Critical / Major / Minor / None
- `issue_type`(복수 가능): AnswerWrongSuspect, ExplanationLogicGap, GuidelineUncertain, ObjectiveMismatch, Ambiguity, etc.
- `span_hint`: 의심 근거가 되는 문장/선택지/해설의 위치 요약(짧게)
- `recommended_action`: “Needs attending adjudication”, “Needs fact-check”, 등

### 5.3 운영 규칙(verification bias 방지: 필수)
- **Flagged 문항:** 전량 또는 높은 비율로 심화 인간 검토(우선순위 상향)
- **Unflagged 문항:** 반드시 일정 비율(예: 10–20%) **무작위 감사 샘플**을 인간이 검토
- 목표 KPI는 precision보다 **치명 오류 recall(민감도)** 중심으로 둔다.

### 5.4 (추가) S1 Table 점검(테이블 특화 Flagger LLM; 수정 금지)

#### 5.4.1 목적
- FINAL 배포 후보에서 “문항(card)” 이전 단계의 **S1 master table**에 대해,
  - (a) **계약 위반(형식/정렬) FAIL-fast**를 조기에 탐지하고
  - (b) 사람 검토 리소스를 **row/col/cell 단위로 정확히 지목**하여
  - (c) 전문의 high-risk strata 구성 및 adjudication 우선순위를 지원한다.

#### 5.4.2 입력 범위(권장)
- 입력은 아래 필드만 사용(출처 추론/추가 지식 생성 금지):
  - `group_id`, `group_path`
  - `visual_type_category`
  - `objective_bullets`
  - `master_table_markdown_kr` (S1 master table)

> **AUTHORITATIVE SOURCE OF TRUTH:**  
> S1 master table은 downstream 단계(S2/S3/S4)의 범위와 정렬의 기준이며, flagger는 이를 “수정”하지 않는다.  
> (근거 계약: `0_Protocol/04_Step_Contracts/Step01_S1/S1_Stage1_Struct_JSON_Schema_Canonical.md` 의 Section 5–8)

#### 5.4.3 체크 항목(테이블 특화; 구조 vs 내용 분리)

**A) 구조(FAIL-fast 후보)**
- 정확히 1개 markdown table인지
- 헤더가 Canonical header set과 일치하는지(6 columns, 첫 열 `Entity name`, 마지막 열 `시험포인트`)
- 모든 data row가 6 cells인지, 빈 cell이 없는지
- cell 내부에 newline, raw `|`, placeholder("...", "etc")가 없는지
- row count ≤ 20인지
- `entity_list`와의 정렬(가능 시):
  - row 수 = entity 수
  - 1열 Entity name과 entity_name의 **문자 단위 exact match**

**B) 내용(위험 신호; triage 중심)**
- **Internal inconsistency**: 동일 용어/분류/핵심 소견이 행 간/열 간 모순
- **Safety-critical suspect**: 명백히 오도 가능(잘못된 진단 논리, 반대 소견 기술, 위험한 권고)
- **Objective mismatch**: objective_bullets 대비 핵심이 벗어나거나, 테이블이 objective를 직접 커버하지 못함
- **Overclaim / unverifiable**: 테이블에 없는 수치/가이드라인/분류체계를 단정적으로 기입(근거가 테이블 내부에 없는데 확정 서술)
- **Ambiguity / under-specification**: 시험포인트가 너무 추상적(“중요”, “자주 나옴”)이거나 학습을 오도

#### 5.4.4 권장 모델(고정; QA-only triage)
- **Primary(권장):** `gemini-3-pro-preview` (Arm E 계열)  
  - 이유: 테이블/목표/그룹 맥락을 한 번에 읽고, row/col 지목형 JSON을 안정적으로 생성하는 편
- **Fallback / 비용절감 1차 스캐너(선택):** `gemini-3-flash-preview` (Arm A–D 계열)  
  - Flash로 1차 구조/명백 오류를 스캔하고, `risk_label ∈ {Critical, Major}` 또는 구조 FAIL 의심 시 Pro로 재실행
- **대안(정교한 JSON 강제 필요 시):** `gpt-5.2-2025-12-11` (Arm F 계열)  
  - 이유: 엄격한 JSON-only 출력, 정형 스키마 준수 강점

> 운영 원칙: **모델은 “런타임 옵션”이 아니라 QA 설계 요소**로 사전 고정한다(Freeze).  
> (근거: `0_Protocol/02_Arms_and_Models/ARM_CONFIGS_Provider_Model_Resolution.md`)

#### 5.4.5 출력 스키마(테이블 특화; S2 점검과 유사한 라벨링)
- 출력은 **오직 JSON object**(추가 텍스트 금지)이며, 1 table(=1 group)당 1개를 생성한다.
- 최소 필드(권장):
  - `group_id`
  - `artifact_kind`: `"S1_MASTER_TABLE"`
  - `risk_label`: `Critical | Major | Minor | None`
  - `issue_type`: (복수 가능)  
    - `TableFormatViolation`, `HeaderMismatch`, `RowCellCountMismatch`, `EmptyCell`, `IllegalDelimiter`, `PlaceholderText`, `EntityAlignmentMismatch`  
    - `InternalInconsistency`, `SafetyCriticalSuspect`, `ObjectiveMismatch`, `OverclaimUnverifiable`, `Ambiguity`
  - `issues`: array
    - 각 issue는 아래를 포함:
      - `severity`: `Critical | Major | Minor`
      - `location`: `row_index`(1-based; header 제외), `col_name`, (가능하면) `entity_name`
      - `span_hint`: 문제 cell/문구의 짧은 지목(한 줄)
      - `evidence_quote`: 문제 근거(짧은 직접 인용; 1–2문장)
      - `recommended_action`: `Needs attending adjudication | Needs resident review | Needs format fix | Exclude pending patch`
  - `structural_validity`: `pass | warn | fail`
  - `fail_fast_reasons`: array (fail일 때만)

#### 5.4.6 운영 출력 포맷(사람 검토용)
- **NDJSON (권장):** `s1_table_flagger.ndjson` (group_id 당 1줄)
- **요약 CSV (권장):** `s1_table_flagger_issues.csv`
  - columns 예: `group_id, risk_label, severity, row_index, col_name, entity_name, issue_type, span_hint, recommended_action`
- 사람에게는 “근거 위치(row/col)”만 전달하고, LLM의 장문 해석/추론은 최소화한다.

---

## 6. 분석 및 보고(보고 실수 방지 가이드 포함)

### 6.1 전체 오류율/충실도 추정의 기준 표본
- “전체율”은 원칙적으로 **전공의 972(최종 라벨은 adjudication 포함)**을 기반으로 추정한다.
- 유한 모집단(6,000+) 특성을 고려할 경우 FPC 적용 가능(선택).

### 6.2 전문의 300의 보고 방식(중요)
- 전문의 300은 random/high-risk strata를 **구분하여** 보고한다.
- high-risk strata 결과를 섞어 전체율처럼 보고하지 않는다(통계적 공격 포인트 차단).
- 전문의 결과는
  - 전공의 라벨과의 합치/불일치,
  - 치명 오류 사례 유형,
  - 분과별 대표 수정 포인트
  중심으로 기술한다.

### 6.3 HITL 품질 주장 구조(권장)
- Primary: v2(최종 배포본)의 치명 오류율과 alignment가 기준을 만족
- Secondary: flagging 도입으로 검토 효율(시간/처리량) 개선(가능 시)
- Exploratory: v1→v2 변경 전후의 오류 감소(있다면 부록으로 기술)

---

## 7. 의사결정 규칙(Go/No-Go; 값은 프로젝트 상황에 맞게 확정)

### 7.1 Safety rule(필수)
- `Critical error rate`의 95% CI 상한이 사전 허용 기준 이하이면 통과
- 기준값은 파일럿 관측치와 교육적 허용 가능성을 근거로 사전 고정(추후 문서화)

### 7.2 Fidelity rule(필수)
- `Objective alignment(Yes)` 비율이 사전 기준 이상이면 통과

### 7.3 예외/보완 규칙(운영)
- 특정 분과에서 치명 오류가 반복적으로 발견되면 해당 분과 문항은 v2 배포 전 추가 검토/수정 필수
- “flagger Critical + attending Critical”이 일치한 유형은 패턴 분석 후 재발 방지 조치(프롬프트/게이트 개선) 수행

---

## 8. 주요 리스크와 대응(비판점 반영 체크리스트)

### 8.1 리스크: 치명 오류/충실도 정의가 애매함
- 대응: 1페이지 rubric(예/비예시) 배포, 평가 전 10문항 캘리브레이션

### 8.2 리스크: adjudication 부재로 최종 라벨이 흔들림
- 대응: 4장 SOP 고정, adjudicator 지정, 로그 보관

### 8.3 리스크: 전문의 30문항을 분과별 오류율 추정으로 과해석
- 대응: 전문의 300의 역할(검증/탐지/사례 기술) 명시, strata 분리 보고

### 8.4 리스크: flagger를 과신하여 unflagged를 안 봄(미검출 오류)
- 대응: unflagged 무작위 감사 샘플 규칙을 “필수”로 고정

### 8.5 리스크: 분과 태깅/문항 분류 오류로 샘플링 의미 저하
- 대응: 분과 태깅 규칙을 사전 고정(애매한 문항은 ‘공통/교차’ 풀로 분리)

---

## 9. 산출물(Artifacts)
- v1 freeze 패키지(문항/정답/해설 스냅샷)
- patch log(문항 ID별 수정 제안 및 확정 내역)
- 평가 원자료(전공의/전문의 개별 응답)
- adjudication 로그(최종 라벨 근거)
- 분석 리포트(전체율: 972 중심, 전문의: strata 분리 + 합치/사례)

---

## 10. 결정 사항(확정 필요 목록)
1) 치명 오류/충실도 rubric 1페이지 최종 확정
2) Safety/Fidelity 기준값(허용 한계) 사전 고정
3) adjudicator(또는 중앙 위원) 지정
4) 분과 태깅 규칙 확정(교차 주제 처리 포함)
5) unflagged 감사 샘플 비율(10–20% 권장) 확정
6) 전문의 strata 비율(20 random + 10 high-risk 권장) 확정

---

## 11. 관련 문서(현재 Canonical과의 연결점)
- Blinding: `0_Protocol/06_QA_and_Study/QA_Operations/QA_Blinding_Procedure.md`
- Rubric: `0_Protocol/06_QA_and_Study/QA_Operations/QA_Evaluation_Rubric.md`
- QA Framework(현재 SSOT): `0_Protocol/06_QA_and_Study/QA_Framework.md`
- (기존 S1 설계 문서): `0_Protocol/05_Pipeline_and_Execution/S1_QA_Design_Error_Rate_Validation.md`


