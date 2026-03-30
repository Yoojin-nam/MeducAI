# S5 시간 측정 및 비교 계획

**작성 일자**: 2025-12-29  
**목적**: Human Rater 시간 vs S5 멀티에이전트 시스템 시간 비교를 위한 로깅 스키마 정의

---

## 1. 비교 목표

### 1.1 비교 항목

| 항목 | Human Rater | S5 멀티에이전트 시스템 |
|------|-------------|----------------------|
| **검토 시간** | `time_pre_ms` (Pre-S5 검토) | `s5_validation_duration_ms` (S5 구동 시간) |
| **수정 시간** | `correction_time_ms` (Post-S5 수정) | `s5_repair_duration_ms` (S5R + S1R/S2R 재생성 시간) |
| **총 소요 시간** | `total_session_duration_ms` | `s5_total_duration_ms` (S5 + S5R + 재생성) |

### 1.2 비교 목적

1. **효율성 측정**: S5 멀티에이전트 시스템이 Human Rater보다 시간 효율적인지 측정
2. **비용-효과 분석**: 시간 절감 vs 품질 개선 trade-off 분석
3. **도구 효과 검증**: S5가 Human Rater의 검토/수정 시간을 얼마나 절감하는지 측정

---

## 2. 현재 상태

### 2.1 Human Rater 시간 측정 (이미 구현됨)

**FINAL_QA_Form_Design.md**에 정의된 필드:
- `time_pre_ms`: Pre-S5 검토 시간 (timestamp_submitted_ms - timestamp_viewed_ms)
- `correction_time_ms`: Post-S5 수정 시간 (timestamp_final_submitted_ms - s5_reveal_timestamp_ms)
- `total_session_duration_ms`: 총 세션 시간

**Time Measurement Protocol**:
- Active interaction time 기반 측정
- Idle time 제외 (30초 이상 비활성 시)

### 2.2 S5 시간 측정 (부분적 구현)

**현재 상태**:
- `validation_timestamp`: ISO 8601 타임스탬프만 있음
- 구동 시간(duration)은 명시적으로 로깅되지 않음

**S5_Multiagent_Repair_Plan**:
- MI-CLEAR-LLM compliance에 "Timing/counters: start/end timestamps, latency" 언급
- 하지만 구체적인 스키마 정의 없음

---

## 3. 제안: S5 시간 로깅 스키마

### 3.1 S5 Validation 시간 로깅

**S5_Validation_Schema에 추가할 필드**:

```json
{
  "s5_timing": {
    "validation_start_timestamp_ms": 1703587200000,
    "validation_end_timestamp_ms": 1703587250000,
    "validation_duration_ms": 50000,
    "s1_table_validation_duration_ms": 30000,
    "s2_cards_validation_duration_ms": 20000,
    "rag_query_duration_ms": 5000,
    "llm_call_count": 3,
    "llm_total_duration_ms": 45000
  }
}
```

**필드 설명**:
- `validation_start_timestamp_ms`: S5 검증 시작 시각 (Unix timestamp, milliseconds)
- `validation_end_timestamp_ms`: S5 검증 종료 시각
- `validation_duration_ms`: 총 검증 시간 (end - start)
- `s1_table_validation_duration_ms`: S1 테이블 검증 시간
- `s2_cards_validation_duration_ms`: S2 카드 검증 시간 (모든 카드 합계)
- `rag_query_duration_ms`: RAG 쿼리 총 시간
- `llm_call_count`: LLM 호출 횟수
- `llm_total_duration_ms`: LLM 호출 총 시간 (RAG 제외)

### 3.2 S5R Repair Plan 생성 시간 로깅

**S5_Repair_Plan_Schema에 추가할 필드**:

```json
{
  "s5r_timing": {
    "repair_plan_start_timestamp_ms": 1703587300000,
    "repair_plan_end_timestamp_ms": 1703587350000,
    "repair_plan_duration_ms": 50000,
    "llm_call_count": 1,
    "llm_duration_ms": 45000
  }
}
```

### 3.3 S1R/S2R 재생성 시간 로깅

**S1R/S2R 재생성 결과에 추가할 필드**:

```json
{
  "regeneration_timing": {
    "regeneration_start_timestamp_ms": 1703587400000,
    "regeneration_end_timestamp_ms": 1703587500000,
    "regeneration_duration_ms": 100000,
    "s1r_duration_ms": 40000,
    "s2r_duration_ms": 60000,
    "llm_call_count": 5,
    "llm_total_duration_ms": 95000
  }
}
```

### 3.4 S5' Post-Repair Validation 시간 로깅

**S5_Validation_Schema (post-repair)에 추가**:
- 동일한 `s5_timing` 구조 사용
- `is_post_repair: true` 플래그 추가

---

## 4. 통합 시간 비교 스키마

### 4.1 비교를 위한 통합 레코드

**파일**: `s5_vs_human_time_comparison__arm{arm}.jsonl`

**스키마**:
```json
{
  "schema_version": "TIME_COMPARISON_v1.0",
  "group_id": "grp_xxx",
  "card_id": "card_xxx",
  "arm": "G",
  "run_tag": "DEV_armG_s5loop_diverse_20251229_065718",
  
  "human_rater_timing": {
    "rater_id": "rater_001",
    "rater_role": "Resident",
    "time_pre_ms": 45000,
    "correction_time_ms": 5000,
    "total_session_duration_ms": 50000,
    "active_duration_ms": 48000,
    "idle_duration_ms": 2000
  },
  
  "s5_timing": {
    "validation_duration_ms": 50000,
    "s1_table_validation_duration_ms": 30000,
    "s2_cards_validation_duration_ms": 20000,
    "rag_query_duration_ms": 5000,
    "llm_call_count": 3
  },
  
  "s5_repair_timing": {
    "s5r_duration_ms": 50000,
    "s1r_duration_ms": 40000,
    "s2r_duration_ms": 60000,
    "s5_postrepair_duration_ms": 45000,
    "total_repair_duration_ms": 195000
  },
  
  "comparison_metrics": {
    "review_time_ratio": 0.9,  // s5_validation_duration_ms / time_pre_ms
    "correction_time_ratio": 39.0,  // total_repair_duration_ms / correction_time_ms
    "total_time_ratio": 4.9,  // (s5 + repair) / total_session_duration_ms
    "time_saved_ms": -145000,  // negative = slower
    "efficiency_gain": false
  }
}
```

### 4.2 비교 지표

1. **Review Time Ratio**: `s5_validation_duration_ms / time_pre_ms`
   - < 1.0: S5가 더 빠름
   - > 1.0: Human Rater가 더 빠름

2. **Correction Time Ratio**: `total_repair_duration_ms / correction_time_ms`
   - < 1.0: S5 재생성이 더 빠름
   - > 1.0: Human 수정이 더 빠름

3. **Total Time Ratio**: `(s5 + repair) / total_session_duration_ms`
   - 전체 프로세스 비교

4. **Time Saved**: `total_session_duration_ms - (s5 + repair)`
   - 절대 시간 절감량

---

## 5. 구현 계획

### 5.1 S5 Validator 수정

**파일**: `3_Code/src/05_s5_validator.py`

**추가할 코드**:
```python
# S5 검증 시작
s5_start_ms = int(time.time() * 1000)

# ... S5 검증 로직 ...

# S5 검증 종료
s5_end_ms = int(time.time() * 1000)
s5_duration_ms = s5_end_ms - s5_start_ms

# 결과에 timing 추가
validation_result["s5_timing"] = {
    "validation_start_timestamp_ms": s5_start_ms,
    "validation_end_timestamp_ms": s5_end_ms,
    "validation_duration_ms": s5_duration_ms,
    "s1_table_validation_duration_ms": s1_duration_ms,
    "s2_cards_validation_duration_ms": s2_duration_ms,
    "rag_query_duration_ms": rag_duration_ms,
    "llm_call_count": llm_call_count,
    "llm_total_duration_ms": llm_total_duration_ms
}
```

### 5.2 S5R Repair Planner 수정

**새 파일**: `3_Code/src/05r_s5_repair_planner.py` (미구현 시)

**추가할 코드**:
```python
# S5R 시작
s5r_start_ms = int(time.time() * 1000)

# ... S5R 로직 ...

# S5R 종료
s5r_end_ms = int(time.time() * 1000)
s5r_duration_ms = s5r_end_ms - s5r_start_ms

# 결과에 timing 추가
repair_plan["s5r_timing"] = {
    "repair_plan_start_timestamp_ms": s5r_start_ms,
    "repair_plan_end_timestamp_ms": s5r_end_ms,
    "repair_plan_duration_ms": s5r_duration_ms,
    "llm_call_count": llm_call_count,
    "llm_duration_ms": llm_duration_ms
}
```

### 5.3 S1R/S2R 재생성 수정

**파일**: `3_Code/src/01_generate_json.py` (재생성 모드)

**추가할 코드**:
```python
# 재생성 시작
regeneration_start_ms = int(time.time() * 1000)

# ... S1R/S2R 재생성 로직 ...

# 재생성 종료
regeneration_end_ms = int(time.time() * 1000)
regeneration_duration_ms = regeneration_end_ms - regeneration_start_ms

# 결과에 timing 추가
regeneration_result["regeneration_timing"] = {
    "regeneration_start_timestamp_ms": regeneration_start_ms,
    "regeneration_end_timestamp_ms": regeneration_end_ms,
    "regeneration_duration_ms": regeneration_duration_ms,
    "s1r_duration_ms": s1r_duration_ms,
    "s2r_duration_ms": s2r_duration_ms,
    "llm_call_count": llm_call_count,
    "llm_total_duration_ms": llm_total_duration_ms
}
```

### 5.4 비교 스크립트 생성

**새 파일**: `3_Code/scripts/compare_s5_vs_human_time.py`

**기능**:
1. Human Rater 시간 데이터 로드 (FINAL QA 결과)
2. S5 시간 데이터 로드 (S5 validation 결과)
3. S5 Repair 시간 데이터 로드 (S5R + S1R/S2R 결과)
4. 비교 지표 계산
5. 통계 요약 (mean, median, distribution)
6. 리포트 생성

---

## 6. 분석 계획

### 6.1 주요 분석 질문

1. **S5가 Human Rater보다 검토 시간이 빠른가?**
   - `review_time_ratio < 1.0` 비율
   - 평균 `review_time_ratio`

2. **S5 재생성이 Human 수정보다 빠른가?**
   - `correction_time_ratio < 1.0` 비율
   - 평균 `correction_time_ratio`

3. **전체 프로세스에서 시간 절감이 있는가?**
   - `total_time_ratio < 1.0` 비율
   - 평균 시간 절감량 (`time_saved_ms`)

4. **시간 절감과 품질 개선의 trade-off는?**
   - 시간 절감 vs 품질 개선 (blocking error reduction, quality score improvement)

### 6.2 통계 분석

**주요 지표**:
- Mean, Median, SD of time ratios
- Distribution plots (histogram, box plot)
- Correlation analysis (time vs quality)

**비교 테스트**:
- Paired t-test: Human time vs S5 time
- Wilcoxon signed-rank test (non-parametric)

---

## 7. 스키마 업데이트 필요 문서

### 7.1 업데이트할 문서

1. **S5_Validation_Schema_Canonical.md**
   - `s5_timing` 필드 추가

2. **S5_Multiagent_Repair_Plan_OptionC_Canonical.md**
   - 시간 로깅 스키마 명시

3. **S5_Repair_Plan_Schema** (새 문서)
   - `s5r_timing` 필드 정의

4. **S1R/S2R_Regeneration_Schema** (새 문서)
   - `regeneration_timing` 필드 정의

---

## 8. 예상 결과

### 8.1 예상 시나리오

**시나리오 1: S5가 더 빠름**
- Review Time Ratio: 0.5 (S5가 2배 빠름)
- Correction Time Ratio: 2.0 (재생성이 수정보다 느림)
- Total Time Ratio: 0.8 (전체적으로 20% 시간 절감)

**시나리오 2: Human이 더 빠름**
- Review Time Ratio: 2.0 (Human이 2배 빠름)
- Correction Time Ratio: 0.3 (재생성이 수정보다 빠름)
- Total Time Ratio: 1.5 (전체적으로 50% 더 느림)

### 8.2 해석

- **시간 절감**: S5 멀티에이전트 시스템이 Human Rater보다 빠르면 효율성 측면에서 유리
- **품질-시간 trade-off**: 시간이 더 걸리더라도 품질이 크게 개선되면 가치 있음
- **비용 분석**: 시간 절감 × 시간당 비용 vs API 비용 비교

---

## 9. 다음 단계

### 9.1 즉시 구현

1. **S5 Validator에 timing 로깅 추가**
   - `s5_timing` 필드 추가
   - 각 단계별 시간 측정

2. **S5R Repair Planner에 timing 로깅 추가**
   - `s5r_timing` 필드 추가

3. **S1R/S2R 재생성에 timing 로깅 추가**
   - `regeneration_timing` 필드 추가

### 9.2 비교 스크립트 개발

1. **비교 스크립트 작성**
   - Human Rater 시간 데이터 로드
   - S5 시간 데이터 로드
   - 비교 지표 계산
   - 리포트 생성

### 9.3 분석 수행

1. **데이터 수집**
   - Human Rater 시간 데이터 (FINAL QA)
   - S5 시간 데이터 (S5 validation)
   - S5 Repair 시간 데이터 (S5R + S1R/S2R)

2. **비교 분석**
   - 시간 비율 계산
   - 통계 분석
   - 시각화

---

## 10. 참고 문서

- **FINAL QA Form**: `0_Protocol/06_QA_and_Study/FINAL_QA_Form_Design.md`
- **Time Measurement Protocol**: `0_Protocol/06_QA_and_Study/Firebase QA/Time Measurement Protocol.md`
- **S5 Validation Schema**: `0_Protocol/04_Step_Contracts/Step05_S5/S5_Validation_Schema_Canonical.md`
- **S5 Multi-agent Plan**: `0_Protocol/05_Pipeline_and_Execution/S5_Multiagent_Repair_Plan_OptionC_Canonical.md`

---

**작성자**: MeducAI Research Team  
**검토 필요**: S5 Validator, S5R Repair Planner, S1R/S2R 재생성 코드 수정

