# Schema Retry Policy (v1.0)

**Status:** Archived  
**Superseded by:** `0_Protocol/05_Pipeline_and_Execution/Schema_Retry_Policy.md`
**Do not use this file for new decisions or execution.**
**Version:** 1.0  
**Applies to:** S1, S2 (LLM 호출 단계)  
**Last Updated:** 2025-12-20  
**Purpose:** LLM 호출 결과의 스키마/구조 실패 시 동일 입력 조건으로 최대 2회 추가 재시도하여 성공률을 올리되, 스키마 불변/실험 공정성/재현성/추적 가능성을 보장한다.

---

## 0. 핵심 목표 (필수)

S1/S2에서 LLM 호출 결과가 **"스키마 실패(구조 불일치)"**로 판정되면:

- 동일한 base prompt(동일 컨텍스트/동일 파라미터)로 최대 2회 추가 시도한다.
- 총 시도 횟수는 **3회(1 + 2 retry)**로 고정한다.
- "스키마 실패" 재시도는 Transport/RateLimit 재시도와 분리하여 정의한다.
- Transport/429/timeout/5xx 등은 기존 정책이 있으면 유지하되, 이번 작업의 주된 추가사항은 Schema Retry(구조 실패)이다.
- 최종적으로 성공하면 PASS로 진행하되, 재시도 발생 여부 및 시도 횟수는 반드시 아티팩트/로그로 남긴다.
- 실험 비교(6arm×10 등)에서 편향이 생기지 않도록 모든 arm/provider에 동일하게 적용한다.
- 실패 시에는 fail-fast를 유지하되, "단일 attempt 내부에서 fail-fast" + "runner 레벨에서 고정 횟수 재시도 후 최종 실패"로 정책을 재정의한다.
- 최종 FAIL은 "왜 실패했는지(validator error 요약)"가 남아야 한다.

---

## 1. 비목표 (하지 말 것)

- S1/S2/S4 산출물 JSONL의 스키마(키/구조/타입)를 임의로 바꾸지 마라. (출력물에 retry 메타데이터를 끼워 넣지 않는다. 메타는 별도 아티팩트로 남긴다.)
- "품질이 마음에 안 들어서" 반복 생성하는 방식(quality escalation)으로 변질되지 않게 하라.
- 재시도마다 프롬프트를 재작성/증강하여 다른 분포를 만들지 마라. 단, 표준화된 '검증 오류 피드백' 메시지를 추가하는 방식은 허용하되, 반드시 "정책으로 고정"하고 코드로 일관되게 적용할 것.

---

## 2. Schema Retry 정책 (고정 상수)

### 2.1 최대 시도 횟수

- **MAX_SCHEMA_ATTEMPTS = 3** (고정)
- "추가 2회"를 명시적으로 보장해야 하므로 총 시도 횟수 3회로 하드 고정
- 환경변수/CLI 옵션으로 노출 가능하되 기본값은 3으로 고정
- 모든 arm/provider에 동일 적용

### 2.2 재시도 시 입력 불변 + 표준화된 오류 피드백

재시도는 **B 방식(표준화된 오류 피드백 추가)**으로 구현한다.

**2회차 이상부터는 아래 형식의 짧은 피드백을 고정 템플릿으로 추가:**

```
Your previous output failed schema validation. Fix the errors and re-output ONLY the valid JSON. Do not add extra keys.

Error details: {error_summary}
```

- `error_summary`는 validator가 반환한 에러 요약(최대 500자)을 첨부한다.
- 이 템플릿은 모든 stage/arm에 동일해야 한다.
- 원본 user_prompt는 변경하지 않고, 피드백만 추가한다.

---

## 3. "스키마 실패" 판정 기준 (엄격)

스키마 실패는 아래 중 하나라도 만족하면 true로 한다:

### 3.1 공통 실패 조건

- **JSON 파싱 실패** (`json.loads` 예외 등)
- **required key 누락** / **타입 불일치** / **리스트 길이 제약 위반**

### 3.2 S1 특화 실패 조건

- `visual_type_category` 누락 또는 enum 위반
- `master_table_markdown_kr` 누락 또는 비어있음
- `entity_list` 누락 또는 빈 리스트
- 마크다운 테이블 형식 위반 (| 또는 --- 누락)

### 3.3 S2 특화 실패 조건

- 엔티티당 카드 수 불일치 (예: 3장 고정 위반)
- 필수 필드 누락 (`card_role`, `card_type`, `front`, `back`, `tags`)
- `card_role` 값 불일치 (Q1/Q2/Q3 중 하나 누락)
- Q1 `image_hint` 필수 필드 누락 (`modality_preferred`, `anatomy_region`, `key_findings_keywords`)
- Q2/Q3에 deictic image reference 발견
- Q2/Q3 MCQ 형식 위반 (`options` 배열 5개, `correct_index` 0-4 범위)

이 판정은 "검증 함수(validate_fn)"로 통합하고, wrapper는 validate_fn이 예외를 던지거나 false를 반환하면 스키마 실패로 처리한다.

---

## 4. 아티팩트/로그 (필수)

### 4.1 Raw 응답 보존 (attempt별)

**경로:** `{RUN_DIR}/raw_llm/{stage}/{arm}/{group_id}/attempt_01.txt`  
**예시:**
- `raw_llm/stage1/armA/abc123def456/attempt_01.txt`
- `raw_llm/stage2/armA/abc123def456/entity_id_xyz/attempt_01.txt`
- `attempt_02.txt`, `attempt_03.txt`

**정책:**
- 최소한 최종 성공/실패와 관계없이, 시도한 모든 attempt raw를 남긴다.
- 파일명은 `attempt_{attempt_idx:02d}.txt` 형식으로 고정

### 4.2 Retry summary 로그 (머신리더블)

**경로:** `{RUN_DIR}/logs/llm_schema_retry_log.jsonl`

**각 라인 형식:**
```json
{
  "run_tag": "RUN_20251220",
  "stage": "S1",
  "arm": "A",
  "group_id": "abc123def456",
  "entity_id": "xyz789",
  "entity_name": "뇌경색",
  "row_index": null,
  "attempt_idx": 1,
  "success": true,
  "error_type": null,
  "error_summary": null,
  "raw_path": "raw_llm/stage1/armA/abc123def456/attempt_01.txt"
}
```

**필드 설명:**
- `run_tag`: 실행 태그
- `stage`: S1 또는 S2
- `arm`: Arm 식별자 (A-F)
- `group_id`: 그룹 식별자
- `entity_id`: 엔티티 식별자 (S2만, S1은 null)
- `entity_name`: 엔티티 이름 (S2만, S1은 null)
- `row_index`: 행 인덱스 (선택적)
- `attempt_idx`: 시도 번호 (1..MAX_SCHEMA_ATTEMPTS)
- `success`: 성공 여부 (boolean)
- `error_type`: 에러 타입 (`json_parse`, `schema_missing_key`, `type_mismatch`, `card_count_mismatch`, `s1_required_field`, `s2_required_field`, `s2_deictic_reference`, `s2_mcq_format`, `unknown`)
- `error_summary`: 에러 요약 (최대 200자)
- `raw_path`: Raw 응답 파일 경로 (상대 경로)

### 4.3 최종 요약 (옵션이지만 권장)

**경로:** `{RUN_DIR}/logs/llm_schema_retry_summary.json`

**형식:**
```json
{
  "run_tag": "RUN_20251220",
  "stage_summary": {
    "S1": {
      "total_groups": 10,
      "groups_with_retry": 2,
      "total_attempts": 12,
      "avg_attempts": 1.2,
      "max_attempts": 3,
      "success_rate": 1.0
    },
    "S2": {
      "total_entities": 30,
      "entities_with_retry": 5,
      "total_attempts": 40,
      "avg_attempts": 1.33,
      "max_attempts": 3,
      "success_rate": 1.0
    }
  },
  "error_type_distribution": {
    "json_parse": 1,
    "schema_missing_key": 2,
    "card_count_mismatch": 1
  }
}
```

---

## 5. Gate/Validator 출력 정책 (필수)

### 5.1 성공 시

최종 출력이 유효하면 PASS이되, schema retry가 발생한 경우:

- 콘솔에 **WARN**으로 `"schema retry occurred (attempt_used=2/3)"` 같은 요약을 남긴다.
- 예: `[WARN] Schema retry succeeded: stage=1, group_id=abc123, attempt_used=2/3`

### 5.2 실패 시

최종 3회 모두 실패하면:

- 기존처럼 **FAIL(비정상 종료)**하되,
- failure report에 "마지막 validator error 요약"과 "raw 경로"가 포함되어야 한다.
- 예: `Schema validation failed after 3 attempts. Last error: schema_missing_key - Stage1 visual_type_category is empty. Raw responses saved to: {raw_llm_dir}`

---

## 6. Transport/RateLimit 재시도와의 관계

### 6.1 분리 원칙

- **Transport/RateLimit 재시도**: `call_llm` 함수 내부에서 처리 (기존 정책 유지)
- **Schema Retry**: `call_llm_with_schema_retry` wrapper에서 처리 (새로 추가)

### 6.2 실행 순서

1. `call_llm_with_schema_retry` 호출
2. 내부에서 `call_llm` 호출 (Transport/RateLimit 재시도 포함)
3. `call_llm`이 성공하면 (JSON 파싱 성공), `validate_fn`으로 스키마 검증
4. 스키마 검증 실패 시, 동일 입력으로 재시도 (최대 MAX_SCHEMA_ATTEMPTS)

### 6.3 실패 처리

- **Transport/RateLimit 실패**: `call_llm`이 `None` 반환 → 즉시 실패 (Schema Retry 없음)
- **Schema 실패**: `call_llm`은 성공했으나 `validate_fn` 실패 → Schema Retry 수행

---

## 7. 실험 공정성 보장

### 7.1 모든 arm/provider에 동일 적용

- MAX_SCHEMA_ATTEMPTS는 모든 arm(A-F)에 동일하게 적용
- 재시도 피드백 템플릿은 모든 stage/arm에 동일
- 로깅 형식은 모든 arm에 동일

### 7.2 재현성 보장

- 재시도 발생 여부는 로그에 기록되므로, 재현성 분석 시 편향을 제어 가능
- Raw 응답 보존으로 모든 attempt를 추적 가능

---

## 8. 구현 위치

- **코드:** `3_Code/src/01_generate_json.py`
- **함수:** `call_llm_with_schema_retry()`
- **적용 지점:**
  - S1: `process_single_group()` 내부, `call_llm` 호출 대신 `call_llm_with_schema_retry` 사용
  - S2: `process_single_group()` 내부, `call_llm` 호출 대신 `call_llm_with_schema_retry` 사용

---

## 9. 변경 이력

- **2025-12-20**: v1.0 초기 작성 (Schema Retry Policy 구현)

---

## 10. 관련 문서

- `Pipeline_FailFast_and_Abort_Policy.md`: Fail-fast 정책 (Level 1)
- `S1_Stage1_Struct_JSON_Schema_Canonical.md`: S1 스키마 정의
- `S2_Policy_and_Implementation_Summary.md`: S2 스키마 정의
