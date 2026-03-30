# Entity-Level 병렬화 구현 보고서 및 문제 해결

**Status:** Implementation Complete, Issue Investigation  
**Created:** 2025-12-26  
**Last Updated:** 2025-12-26

## 1. 구현 완료 사항

### 1.1 완료된 작업

#### Phase 1: 함수 분리 및 구조화 ✅
- **`process_single_entity()` 함수 생성** (line ~2760)
  - Entity 처리 로직을 독립 함수로 분리
  - 시그니처: `(entity_target, ..., quota_s2, P_S2_SYS, P_S2_USER_T) -> (s2_json, error_msg, runtime_meta)`
  - 반환값: 성공 시 `(s2_json, None, rt_s2_dict)`, 실패 시 `(None, error_msg, rt_s2_dict)`

- **기존 코드 리팩토링**
  - `process_single_group()` 내부의 entity 처리 루프를 `process_single_entity()` 호출로 변경
  - 순차 처리 모드 유지 (workers_s2_entity == 1)

#### Phase 2: Entity-level 병렬화 구현 ✅
- **ThreadPoolExecutor 추가** (line ~3509)
  - `workers_s2_entity > 1`일 때 ThreadPoolExecutor 사용
  - `as_completed()`로 결과 수집
  - 순차 처리 모드 유지 (workers_s2_entity == 1)

- **Worker 설정 추가**
  - CLI 인자: `--workers_s2_entity` 추가 (line ~3774)
  - 환경변수: `WORKERS_S2_ENTITY` 지원 (line ~3760)
  - 우선순위: CLI > 환경변수 > 기본값
  - 기본값: `min(8, len(s2_targets))` (자동 조정)

#### Phase 3: 진행 상황 추적 ✅
- Entity 처리 시작/완료 메시지 출력
- 병렬 모드에서도 진행 상황 추적
- 형식: `[S2] ✓ [completed/total] entity_name (cards)`

#### Phase 4: Thread-Safety 확인 ✅
- RAG metadata accumulation에 lock 추가 (`rag_lock`)
- `entities_out.append()`는 CPython GIL로 인해 thread-safe
- 결과 수집 후 메인 스레드에서 일괄 쓰기 (기존 구조 유지)

### 1.2 구현된 기능

1. **Entity-level 병렬화**
   - 그룹 내 entity들을 병렬로 처리
   - 최대 동시 요청: `workers_s2 × workers_s2_entity`
   - 예: 4 그룹 × 4 entity = 최대 16개 동시 요청

2. **자동 워커 조정**
   - `workers_s2_entity == 1`이고 `total_entities > 1`일 때
   - 자동으로 `min(8, total_entities)`로 조정

3. **진행 상황 표시**
   - 병렬 모드: `[S2] Starting parallel processing of N entities with M workers...`
   - 완료 메시지: `[S2] ✓ [completed/total] entity_name (cards)`

## 2. 발견된 문제

### 2.1 실행 중 멈춤 현상

**증상:**
- 11시 18분 이후 API 호출이 없음
- 진행률이 `0%|...| 0/4 [03:51<?, ?it/s]`에서 멈춤
- 일부 entity는 완료되었지만 (`[S2] ✓ [1/15]`, `[S2] ✓ [1/16]`)
- 대부분의 entity는 완료되지 않음

**관찰:**
- API 사이트 로그에서는 11시 18분에 성공적으로 완료된 요청들이 있음
- 로컬 프로세스는 결과를 기다리는 중인 것으로 보임
- `fut.result()`가 무한 대기 중

### 2.2 문제 분석

#### 가능한 원인 1: API 호출이 실제로 완료되지 않음
- `call_llm()` 함수가 타임아웃 없이 무한 대기
- HTTP 클라이언트 레벨에서 타임아웃이 제대로 작동하지 않음

#### 가능한 원인 2: 예외가 발생했지만 전파되지 않음
- `process_single_entity()` 내부에서 예외 발생
- ThreadPoolExecutor에서 예외가 제대로 전파되지 않음
- `fut.result()` 호출 시 예외가 발생하지만 처리되지 않음

#### 가능한 원인 3: 데드락 또는 블로킹
- 여러 스레드가 공유 리소스를 기다리는 중
- Lock이 제대로 해제되지 않음

#### 가능한 원인 4: API 응답 파싱 중 무한 대기
- `extract_json_object()` 또는 `validate_stage2()`에서 무한 루프
- 큰 응답을 처리하는 중 메모리 부족 또는 처리 지연

## 3. 근본 원인 조사 필요 사항

### 3.1 확인해야 할 코드 경로

1. **`call_llm()` 함수의 타임아웃 처리**
   - `timeout_s` 파라미터가 제대로 전달되는지
   - HTTP 클라이언트에 타임아웃이 설정되는지
   - 타임아웃 발생 시 예외가 제대로 발생하는지

2. **`call_llm_with_schema_retry()` 함수의 예외 처리**
   - 예외가 발생했을 때 제대로 반환하는지
   - `(None, error_msg, ...)` 형태로 반환하는지

3. **`process_single_entity()` 함수의 예외 처리**
   - 모든 예외 경로에서 반환값이 있는지
   - 예외가 발생해도 `(s2_json, err2, rt_s2_dict)` 형태로 반환하는지

4. **ThreadPoolExecutor의 예외 전파**
   - `fut.result()` 호출 시 예외가 제대로 전파되는지
   - 예외가 발생했을 때 `as_completed()`가 계속 진행하는지

### 3.2 디버깅 전략

1. **로깅 강화**
   - `process_single_entity()` 시작/종료 시점 로깅
   - `call_llm_with_schema_retry()` 시작/종료 시점 로깅
   - 예외 발생 시 상세한 스택 트레이스 로깅

2. **타임아웃 확인**
   - `timeout_s` 값이 실제로 전달되는지 확인
   - HTTP 클라이언트 타임아웃 설정 확인
   - API 호출 시작/종료 시간 로깅

3. **Future 상태 모니터링**
   - 주기적으로 future 상태 확인 (`fut.done()`, `fut.exception()`)
   - 완료되지 않은 future의 상태 로깅

## 4. 해결 방안 및 적용 사항

### 4.1 근본 원인 분석

**핵심 문제:**
- `process_single_entity()` 함수에서 예외가 발생했을 때 ThreadPoolExecutor의 future가 완료되지 않음
- `fut.result()` 호출 시 예외가 발생하면 무한 대기 가능
- `call_llm()` 함수는 watchdog timeout이 있지만, 예외가 제대로 전파되지 않을 수 있음

**근본 원인:**
1. **예외 처리 부족**: `process_single_entity()` 함수가 try-except로 완전히 감싸지지 않음
2. **Future 예외 미확인**: `fut.result()` 호출 전에 `fut.exception()`을 확인하지 않음
3. **예외 전파 문제**: ThreadPoolExecutor에서 예외가 발생해도 future가 완료되지 않을 수 있음

### 4.2 적용된 해결 방안

#### 4.2.1 예외 처리 강화 ✅ (적용 완료)
- `process_single_entity()` 함수를 try-except로 완전히 감쌈
- 모든 예외 경로에서 `(None, error_msg, {})` 형태로 반환 보장
- ThreadPoolExecutor에서 예외가 발생해도 future가 완료되도록 보장

```python
def process_single_entity(...):
    try:
        # ... 모든 처리 로직
        return s2_json, None, rt_s2_dict
    except Exception as e:
        # 모든 예외를 잡아서 반환값으로 변환
        return None, error_detail, {}
```

#### 4.2.2 Future 예외 사전 확인 ✅ (적용 완료)
- `fut.result()` 호출 전에 `fut.exception()` 확인
- 예외가 있는 future는 조기 감지하여 처리
- 무한 대기 방지

```python
# 예외가 있는 future는 조기 감지
if fut.exception() is not None:
    exc = fut.exception()
    # 예외 처리
    continue

# 예외가 없을 때만 result() 호출
s2_json, err2, rt_s2_dict = fut.result()
```

#### 4.2.3 Watchdog 타임아웃 활용
- `call_llm()` 함수에 이미 watchdog timeout 메커니즘 존재 (line 1417-1441)
- Heartbeat를 통한 진행 상황 표시
- `as_completed()`에 별도 타임아웃 불필요 (watchdog이 처리)

### 4.3 제거된 임시 방편

- ❌ `as_completed()`에 타임아웃 추가 (제거됨)
  - 이유: `call_llm()`의 watchdog이 이미 타임아웃 처리
  - `as_completed()` 타임아웃은 전체 루프를 중단시켜 다른 entity 처리 방해

- ❌ `fut.result(timeout=10)` (제거됨)
  - 이유: `fut.exception()` 사전 확인으로 불필요
  - 예외가 없으면 `result()`는 즉시 반환

### 4.4 최종 구현

**핵심 변경사항:**
1. `process_single_entity()`: 모든 예외를 잡아서 반환값으로 변환
2. Future 처리: `fut.exception()` 사전 확인 후 `fut.result()` 호출
3. 타임아웃: `call_llm()`의 watchdog에 의존 (별도 타임아웃 불필요)

## 5. 적용된 해결 방안 상세

### 5.1 예외 처리 강화 (적용 완료)

**변경 전:**
- `process_single_entity()` 함수에서 일부 예외만 처리
- 예외 발생 시 future가 완료되지 않을 수 있음

**변경 후:**
- 전체 함수를 try-except로 감쌈
- 모든 예외를 잡아서 반환값으로 변환
- ThreadPoolExecutor에서 예외가 발생해도 future가 완료됨

**코드:**
```python
def process_single_entity(...):
    try:
        # 모든 처리 로직
        return s2_json, None, rt_s2_dict
    except Exception as e:
        # 모든 예외를 잡아서 반환
        return None, error_detail, {}
```

### 5.2 Future 예외 사전 확인 (적용 완료)

**변경 전:**
- `fut.result()`를 직접 호출
- 예외가 있으면 무한 대기 가능

**변경 후:**
- `fut.exception()`을 먼저 확인
- 예외가 있으면 조기 처리
- 예외가 없을 때만 `fut.result()` 호출

**코드:**
```python
# 예외 사전 확인
if fut.exception() is not None:
    exc = fut.exception()
    # 예외 처리 후 continue
    continue

# 예외가 없을 때만 result() 호출
s2_json, err2, rt_s2_dict = fut.result()
```

### 5.3 Watchdog 타임아웃 활용

**기존 메커니즘:**
- `call_llm()` 함수에 watchdog timeout 존재 (line 1417-1441)
- Heartbeat를 통한 진행 상황 표시
- 타임아웃 발생 시 `TimeoutError` 예외 발생

**활용 방법:**
- `as_completed()`에 별도 타임아웃 불필요
- Watchdog이 API 호출 타임아웃 처리
- 예외는 `process_single_entity()`에서 처리되어 반환값으로 변환

## 6. 테스트 및 검증

### 6.1 테스트 시나리오

1. **정상 케이스**
   - 모든 entity가 성공적으로 처리되는지 확인
   - 진행 상황이 제대로 표시되는지 확인

2. **예외 케이스**
   - 일부 entity에서 예외 발생 시 다른 entity는 계속 처리되는지 확인
   - 예외 메시지가 제대로 로깅되는지 확인

3. **타임아웃 케이스**
   - API 호출이 타임아웃되면 예외가 제대로 처리되는지 확인
   - 다른 entity는 계속 처리되는지 확인

### 6.2 검증 체크리스트

- [ ] 작은 그룹(1-2개 entity)으로 테스트
- [ ] 대규모 그룹(10+ entity)으로 테스트
- [ ] 예외 발생 시나리오 테스트
- [ ] 타임아웃 발생 시나리오 테스트
- [ ] 진행 상황 표시 확인
- [ ] 파일 쓰기 정상 동작 확인

## 7. 다음 단계

### 7.1 즉시 테스트

1. **작은 그룹으로 테스트**
   - 1-2개 entity로 재현 시도
   - 예외 발생 시나리오 테스트

2. **로그 확인**
   - `[S2] [EXCEPTION]` 메시지 확인
   - Future exception 메시지 확인
   - 문제 발생 지점 정확히 파악

3. **전체 테스트**
   - 4개 그룹 전체 테스트
   - 모든 entity가 처리되는지 확인

### 7.2 추가 개선 사항 (필요 시)

1. **로깅 강화**
   - `process_single_entity()` 시작/종료 로깅
   - `call_llm_with_schema_retry()` 시작/종료 로깅

2. **모니터링**
   - 각 entity 처리 시간 추적
   - 느린 entity 조기 감지

3. **회복 메커니즘**
   - 실패한 entity 재시도 메커니즘
   - 부분 실패 허용 정책

## 8. 참고사항

### 8.1 핵심 개선사항

- ✅ **예외 처리 강화**: 모든 예외를 잡아서 반환값으로 변환
- ✅ **Future 예외 사전 확인**: `fut.exception()` 확인 후 `fut.result()` 호출
- ✅ **Watchdog 활용**: 기존 watchdog 타임아웃 메커니즘 활용

### 8.2 제거된 임시 방편

- ❌ `as_completed()` 타임아웃 제거 (watchdog이 처리)
- ❌ `fut.result(timeout=10)` 제거 (예외 사전 확인으로 불필요)

### 8.3 기대 효과

- 예외 발생 시에도 future가 완료되어 무한 대기 방지
- 예외가 있는 future는 조기 감지하여 처리
- 모든 entity가 처리되거나 명확한 에러 메시지와 함께 실패

## 9. 기술적 세부사항

### 9.1 ThreadPoolExecutor 예외 처리

**문제:**
- ThreadPoolExecutor에서 예외가 발생하면 future가 완료되지만
- `fut.result()` 호출 시 예외가 재발생
- 예외를 처리하지 않으면 무한 대기 가능

**해결:**
- `process_single_entity()`에서 모든 예외를 잡아서 반환값으로 변환
- `fut.exception()`을 먼저 확인하여 예외가 있는 future는 조기 처리
- 예외가 없을 때만 `fut.result()` 호출

### 9.2 Watchdog 타임아웃 메커니즘

**기존 구현:**
- `call_llm()` 함수에 watchdog timeout 존재
- Heartbeat를 통한 진행 상황 표시
- 타임아웃 발생 시 `TimeoutError` 예외 발생

**활용:**
- 별도 타임아웃 불필요
- Watchdog이 API 호출 타임아웃 처리
- 예외는 `process_single_entity()`에서 처리되어 반환값으로 변환

