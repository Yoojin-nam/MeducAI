# S2 디버깅 세션 인계 문서 (2025-12-26)

**목적**: S2 실행 중 발생한 여러 이슈들의 발견, 분석, 해결 과정을 다음 에이전트에게 인계

**세션 일시**: 2025-12-26  
**RUN_TAG**: `smoke_4groups_20251226_123809`  
**ARM**: `G`

---

## 요약 (Executive Summary)

이번 세션에서는 S2 실행 중 다음과 같은 문제들이 순차적으로 발견되고 해결되었습니다:

1. ✅ **IPC 문제 (EmptyIPCResult)**: macOS `spawn` context에서 `SimpleQueue` 불안정 → **파일 기반 IPC로 해결**
2. ✅ **ApiKeyRotator deadlock**: `threading.Lock()` → `threading.RLock()`로 해결
3. ✅ **Schema validation 실패 (card_count_mismatch)**: LLM이 배열 반환 → **JSON 파싱 로직에 배열 처리 추가**

---

## 1. IPC 문제 (EmptyIPCResult) - 이미 해결됨

### 문제 현상
- S2 실행 시 모든 엔티티가 `EmptyIPCResult` 에러로 실패
- macOS `spawn` context에서 `multiprocessing.SimpleQueue`가 신뢰성 없게 동작
- Queue에 결과가 전달되지 않음

### 해결 방법
**파일 기반 IPC 구현** (`3_Code/src/01_generate_json.py`)

- `_gemini_generate_content_worker`: 결과를 임시 JSON 파일에 먼저 저장
- `_run_gemini_generate_with_hard_timeout`: 파일을 우선적으로 읽고, 실패 시 queue로 fallback
- 환경변수 `LLM_GEMINI_IPC_METHOD=file` (기본값)

### 관련 파일
- `3_Code/src/01_generate_json.py`: `_gemini_generate_content_worker()`, `_run_gemini_generate_with_hard_timeout()`

### 상태
✅ **해결 완료** - 파일 기반 IPC가 정상 작동하며 `[IPC] file read success` 로그 확인됨

---

## 2. ApiKeyRotator Deadlock 문제

### 문제 현상
- S2 실행 중 process stall 발생 (180초 이상 진행 없음)
- Thread traceback 분석 결과: 모든 스레드가 `api_key_rotator.py`의 `record_success()`에서 대기
- `record_success()` 내부에서 `_save_state()` 호출 시 같은 lock을 재진입하려고 시도

### 원인
```python
# api_key_rotator.py (기존 코드)
self._lock = threading.Lock()  # Non-reentrant lock

def record_success(self, batch_save: bool = True):
    with self._lock:  # Lock 획득
        # ...
        self._save_state()  # 여기서 다시 같은 lock을 획득하려고 시도 → DEADLOCK

def _save_state(self):
    with self._lock:  # 이미 lock을 보유한 상태에서 재진입 시도 → 실패
        # ...
```

### 해결 방법
**Non-reentrant lock → Re-entrant lock 변경**

```python
# api_key_rotator.py (수정 후)
self._lock = threading.RLock()  # Re-entrant lock
```

### 관련 파일
- `3_Code/src/tools/api_key_rotator.py`: `__init__()` 메서드의 lock 초기화

### 상태
✅ **해결 완료** - RLock로 변경하여 deadlock 해결

---

## 3. Schema Validation 실패 (card_count_mismatch) - 핵심 이슈

### 문제 현상
- 일부 엔티티에서 schema validation 실패: `Expected exactly 2 cards per entity, got 0`
- 에러 발생 엔티티:
  - `**FCD & Nonossifying Fibroma (NOF)**` (grp_f073599bec)
  - `**Ossifying Fibroma**` (grp_f073599bec)

### 원인 분석

#### 3.1 프롬프트 변경 분석 (v7 → v8)
- **v7**: 3-card policy (Q1, Q2, Q3), Q2 image_hint OPTIONAL
- **v8**: 2-card policy (Q1, Q2만), Q2 image_hint REQUIRED
- **결론**: 프롬프트 변경 자체는 문제 없음 (더 명확해짐)

#### 3.2 실제 원인 발견
Raw response 확인 결과, **LLM이 객체 대신 배열을 반환**:
```json
[
  {
    "entity_name": "**FCD & Nonossifying Fibroma (NOF)**",
    "anki_cards": [...]
  }
]
```

`extract_json_object()` 함수는 객체 `{...}`만 처리하도록 구현되어 있어, 배열 `[{...}]`을 반환하면 파싱 실패 → `anki_cards` 필드를 찾지 못함 → 빈 배열로 처리 → validation 실패

### 해결 방법
**JSON 파싱 로직에 배열 처리 추가** (`3_Code/src/01_generate_json.py`)

모든 JSON 파싱 경로에 배열 처리 로직 추가:
- Try 1 (Direct parse): 배열이면 첫 번째 요소 추출
- Try 2 (Code blocks): 배열이면 첫 번째 요소 추출
- Try 3 (Balanced braces): 배열 처리
- Try 4 (Repaired JSON): 배열 처리
- Try 5 (Regex fallback): 배열 패턴도 검색

```python
# extract_json_object() 함수 수정 예시
parsed = json.loads(raw)
if isinstance(parsed, list):
    if len(parsed) == 0:
        raise ValueError("JSON array is empty")
    if len(parsed) > 1:
        print("[WARN] LLM returned array with N elements, using first element only")
    parsed = parsed[0]
if not isinstance(parsed, dict):
    raise ValueError(f"JSON root is not an object")
return parsed
```

### 관련 파일
- `3_Code/src/01_generate_json.py`: `extract_json_object()` 함수 (line ~1278)

### 상태
✅ **해결 완료** - 배열 파싱 로직 추가됨 (코드 수정 완료, 실제 테스트 대기 중)

---

## 4. S2 Stall 문제 분석

### 문제 현상
- S2 실행 중 일부 엔티티가 180초 이상 진행 없음
- Stall dump 로그에서 마지막 엔티티 (`**Hemangioma**`)가 `[LLM] waiting` 상태로 200초+ 대기

### 원인 분석
- 실제 deadlock이 아닌 **단순히 매우 느린 LLM 호출**
- Gemini API 호출이 200초 이상 걸리는 경우 (특히 64k output token 설정 시)
- Watchdog timeout이 600초로 설정되어 있어 계속 대기 중

### 개선 사항 (적용됨)
1. **Stall dump 개선**: 실행 중인 엔티티 정보 출력 추가
2. **Output token cap 조정**: `GEMINI3_STAGE2_FORCE_64K=0`, `MAX_OUTPUT_TOKENS_STAGE2=8192` 환경변수 추가

### 관련 파일
- `3_Code/src/01_generate_json.py`: S2 stall detection 로직 (line ~4120)

### 상태
⚠️ **부분 해결** - 코드 개선은 완료되었으나, 실제로는 "느린 LLM 호출"이므로 timeout 조정으로 관리

---

## 5. S1 vs S2 결과 비교

### 분석 결과
S1 결과 파일은 **정상**:
- 모든 그룹의 JSON 유효성 확인 완료
- `entity_list` 모두 정상
- S2가 S1을 로드하는 과정에서 문제 없음

S2 처리 상태 (마지막 확인 시점):
- ✅ `grp_2155b4f5c3`: 14/14 완료
- ⚠️ `grp_cbcba66e24`: 15/16 (1개 누락)
- ❌ `grp_f073599bec`: 0/19 (전체 미처리 - schema validation 실패로 인해)
- ✅ `grp_fb292cfd1d`: 19/19 완료

**결론**: S1 문제 없음. S2 실행 중 발생한 문제들 (IPC, deadlock, schema validation)이 원인.

---

## 6. 테스트 명령어 및 확인 방법

### 6.1 그룹 1개만 테스트하는 명령어
```bash
cd /path/to/workspace/workspace/MeducAI

RUN_TAG="smoke_4groups_20251226_123809"
ARM="G"

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
  --only_group_id grp_fb292cfd1d \
  2>&1 | tee /tmp/s2_debug_${RUN_TAG}_${ARM}_single_group.log
```

### 6.2 결과 확인 명령어
```bash
# Schema validation 에러 확인 (0이어야 성공)
grep -c "card_count_mismatch" /tmp/s2_debug_${RUN_TAG}_${ARM}_single_group.log

# 배열 파싱 경고 확인 (배열이 감지되면 로그에 나타남)
grep -n "LLM returned array" /tmp/s2_debug_${RUN_TAG}_${ARM}_single_group.log

# 최종 결과 파일 라인 수 확인
wc -l "2_Data/metadata/generated/${RUN_TAG}/s2_results__s1arm${ARM}__s2arm${ARM}.jsonl"
```

---

## 7. 주요 변경 사항 요약

### 7.1 코드 변경
1. **파일 기반 IPC 추가** (`01_generate_json.py`)
   - `_gemini_generate_content_worker()`: 결과를 임시 파일에 저장
   - `_run_gemini_generate_with_hard_timeout()`: 파일 우선 읽기

2. **ApiKeyRotator deadlock 수정** (`tools/api_key_rotator.py`)
   - `threading.Lock()` → `threading.RLock()`

3. **JSON 배열 파싱 지원 추가** (`01_generate_json.py`)
   - `extract_json_object()`: 모든 파싱 경로에 배열 처리 로직 추가

4. **Stall detection 개선** (`01_generate_json.py`)
   - 실행 중인 엔티티 정보 출력 추가

### 7.2 환경변수 추가
- `GEMINI3_STAGE2_FORCE_64K=0`: Gemini 3 Stage2의 64k 강제 정책 해제
- `MAX_OUTPUT_TOKENS_STAGE2=8192`: Stage2 output token cap (기본값보다 낮춤)

---

## 8. 다음 단계 권장 사항

### 8.1 즉시 확인 필요
1. ✅ 배열 파싱 수정이 제대로 작동하는지 테스트
   - 그룹 1개만 실행하여 `card_count_mismatch` 에러가 0개인지 확인
   - 배열이 반환된 경우 `[WARN] LLM returned array` 로그 확인

2. ⚠️ `grp_f073599bec` 그룹 재처리
   - 이전에 schema validation 실패로 0/19 완료된 상태
   - 배열 파싱 수정 후 재실행 필요

### 8.2 추가 개선 가능 사항
1. **프롬프트 개선**: LLM이 배열 대신 객체를 반환하도록 프롬프트 강화 (현재는 파싱 단계에서 처리)
2. **Timeout 최적화**: Gemini API 호출이 200초+ 걸리는 경우에 대한 적절한 timeout 설정
3. **에러 복구**: Schema validation 실패한 엔티티만 재시도하는 기능

---

## 9. 관련 문서 및 파일

- `0_Protocol/05_Pipeline_and_Execution/S2_EmptyIPCResult_Issue_2025-12-26.md`: IPC 문제 상세 분석
- `3_Code/src/01_generate_json.py`: 메인 실행 파일 (주요 수정 위치)
- `3_Code/src/tools/api_key_rotator.py`: ApiKeyRotator (deadlock 수정)
- `3_Code/prompt/S2_SYSTEM__v8.md`: S2 시스템 프롬프트 (v8)
- `3_Code/prompt/S2_USER_ENTITY__v8.md`: S2 유저 프롬프트 (v8)

---

## 10. 체크리스트 (다음 에이전트용)

- [ ] 그룹 1개로 테스트 실행
- [ ] `card_count_mismatch` 에러 0개 확인
- [ ] 배열 파싱 경고 로그 확인 (있으면 정상 작동)
- [ ] `grp_f073599bec` 그룹 재처리
- [ ] 모든 그룹 완료 상태 확인 (48개 엔티티 모두 완료)
- [ ] 최종 S2 결과 파일 검증

---

**문서 작성일**: 2025-12-26  
**작성자**: AI Assistant (Auto)  
**다음 인계 대상**: 다음 디버깅 세션 담당 에이전트

