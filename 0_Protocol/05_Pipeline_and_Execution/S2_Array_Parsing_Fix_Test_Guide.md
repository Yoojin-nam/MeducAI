# S2 배열 파싱 수정 사항 테스트 가이드

**작성일**: 2025-12-26  
**목적**: S2 배열 파싱 로직 강화 및 관련 수정 사항 검증

---

## 수정 사항 요약

### 1. 배열 파싱 로직 강화
- `_extract_valid_object_from_array()` 헬퍼 함수 추가
- 배열에서 `anki_cards` 필드를 가진 객체를 우선 선택
- 모든 파싱 경로(Try 1-5)에 강화된 배열 처리 적용

### 2. 진단 로깅 추가
- `validate_stage2()` 호출 전 파싱된 JSON 구조 로깅
- `anki_cards` 필드 존재 여부, 타입, 개수 확인
- 누락/빈 배열/타입 불일치 경고

### 3. 프롬프트 개선
- S2 시스템 프롬프트에 단일 JSON 객체 반환 명시
- 배열 반환 금지 및 올바른 형식 예시 제공

### 4. 에러 복구 메커니즘
- `card_count_mismatch` 발생 시 재시도 프롬프트에 배열 반환 금지 명시

---

## 테스트 절차

### Step 1: 단일 그룹 테스트 (grp_f073599bec)

이전에 0/19 완료 상태였던 그룹을 재실행하여 수정 사항이 제대로 작동하는지 확인합니다.

```bash
cd /path/to/workspace/workspace/MeducAI
./3_Code/Scripts/test_s2_array_parsing_fix.sh
```

또는 수동 실행:

```bash
cd /path/to/workspace/workspace/MeducAI

RUN_TAG="smoke_4groups_20251226_123809"
ARM="G"
TEST_GROUP="grp_f073599bec"

export LLM_GEMINI_SUBPROCESS_WATCHDOG=1
export LLM_GEMINI_SUBPROCESS_WATCHDOG_STAGE2=1
export LLM_GEMINI_IPC_METHOD="file"
export TIMEOUT_S=300
export LLM_WATCHDOG_TIMEOUT_S=300
export LLM_HEARTBEAT_S=10
export S2_ENTITY_STALL_DUMP_S=60
export GEMINI3_STAGE2_FORCE_64K=0
export MAX_OUTPUT_TOKENS_STAGE2=8192

python3 -u 3_Code/src/01_generate_json.py \
  --base_dir /path/to/workspace/workspace/MeducAI \
  --run_tag "${RUN_TAG}" \
  --arm "${ARM}" \
  --s1_arm "${ARM}" \
  --mode FINAL \
  --stage 2 \
  --sample 4 \
  --workers_s2 4 \
  --workers_s2_entity 4 \
  --only_group_id "${TEST_GROUP}" \
  2>&1 | tee /tmp/s2_test_${RUN_TAG}_${ARM}_${TEST_GROUP}.log
```

#### 확인 사항

1. **card_count_mismatch 에러 확인**:
   ```bash
   grep -c "card_count_mismatch" /tmp/s2_test_${RUN_TAG}_${ARM}_${TEST_GROUP}.log
   ```
   - **기대값**: 0 (에러 없음)

2. **배열 파싱 경고 확인**:
   ```bash
   grep "LLM returned array" /tmp/s2_test_${RUN_TAG}_${ARM}_${TEST_GROUP}.log
   ```
   - 배열이 반환된 경우 경고가 나타나야 함
   - 경고가 있어도 파싱은 정상적으로 처리되어야 함

3. **진단 로그 확인**:
   ```bash
   grep "\[DIAG\] Before validation" /tmp/s2_test_${RUN_TAG}_${ARM}_${TEST_GROUP}.log
   ```
   - 각 엔티티에 대해 진단 정보가 출력되어야 함
   - `has_anki_cards=true`, `cards_count=2` 여야 함

4. **결과 파일 확인**:
   ```bash
   RESULT_FILE="2_Data/metadata/generated/${RUN_TAG}/s2_results__s1arm${ARM}__s2arm${ARM}.jsonl"
   grep -c "\"group_id\":\"${TEST_GROUP}\"" "${RESULT_FILE}"
   ```
   - **기대값**: 19 (모든 엔티티 완료)

### Step 2: 전체 그룹 검증

모든 그룹에서 `card_count_mismatch` 에러가 0개인지 확인합니다.

```bash
cd /path/to/workspace/workspace/MeducAI
./3_Code/Scripts/verify_all_groups_s2.sh
```

#### 확인 사항

1. **card_count_mismatch 에러**: 0개
2. **전체 엔티티 수**: 68개 (grp_2155b4f5c3: 14, grp_cbcba66e24: 16, grp_f073599bec: 19, grp_fb292cfd1d: 19)
3. **각 그룹별 완료 상태**: 모든 그룹이 예상 엔티티 수만큼 완료

---

## 예상 결과

### 성공 시나리오

1. ✅ `card_count_mismatch` 에러 0개
2. ✅ 모든 그룹의 엔티티가 정상적으로 처리됨
3. ✅ 배열이 반환된 경우에도 정상적으로 파싱됨 (경고만 출력)
4. ✅ 진단 로그에서 모든 엔티티의 `anki_cards` 필드가 정상적으로 확인됨

### 실패 시나리오 (추가 디버깅 필요)

1. ❌ `card_count_mismatch` 에러가 여전히 발생
   - Raw LLM response 확인 필요
   - `2_Data/metadata/generated/${RUN_TAG}/raw_llm/stage2/${ARM}/${GROUP_ID}/${ENTITY_ID}/attempt_*.txt` 파일 확인
   - 배열 파싱이 제대로 작동하지 않는 경우 추가 수정 필요

2. ❌ 일부 엔티티만 처리됨
   - 로그에서 실패한 엔티티 확인
   - Schema validation 에러 타입 확인
   - 재시도 로그 확인: `2_Data/metadata/generated/${RUN_TAG}/logs/llm_schema_retry_log.jsonl`

---

## 로그 분석 명령어

### 기본 확인

```bash
RUN_TAG="smoke_4groups_20251226_123809"
ARM="G"
LOG_FILE="/tmp/s2_test_${RUN_TAG}_${ARM}_grp_f073599bec.log"

# card_count_mismatch 에러 수
grep -c "card_count_mismatch" "${LOG_FILE}"

# 배열 파싱 경고
grep "LLM returned array" "${LOG_FILE}"

# 진단 로그
grep "\[DIAG\] Before validation" "${LOG_FILE}"

# Missing anki_cards 경고
grep "Missing 'anki_cards' field" "${LOG_FILE}"

# Empty anki_cards 경고
grep "'anki_cards' is empty array" "${LOG_FILE}"
```

### 상세 분석

```bash
# 실패한 엔티티 목록
grep "card_count_mismatch" "${LOG_FILE}" | grep -o "Entity: [^,]*" | sort | uniq

# 에러 발생 패턴
grep -A 5 "card_count_mismatch" "${LOG_FILE}" | head -20

# 재시도 발생 여부
grep "Schema retry succeeded" "${LOG_FILE}"
```

---

## 관련 파일

- **테스트 스크립트**: `3_Code/Scripts/test_s2_array_parsing_fix.sh`
- **검증 스크립트**: `3_Code/Scripts/verify_all_groups_s2.sh`
- **수정된 코드**: `3_Code/src/01_generate_json.py`
- **수정된 프롬프트**: `3_Code/prompt/S2_SYSTEM__v8.md`
- **인계 문서**: `0_Protocol/05_Pipeline_and_Execution/archived/2025-12/S2_Debugging_Session_2025-12-26_Handoff.md`

---

## 다음 단계

1. ✅ 코드 수정 완료
2. ✅ 테스트 스크립트 작성 완료
3. ⏳ **사용자 실행 필요**: 단일 그룹 테스트 실행
4. ⏳ **사용자 실행 필요**: 전체 그룹 검증 실행
5. ⏳ 결과 확인 및 추가 수정 (필요 시)

---

**참고**: 실제 테스트 실행은 사용자가 직접 수행해야 합니다. 스크립트는 준비되어 있으며, 위의 명령어를 실행하면 자동으로 결과를 분석합니다.

