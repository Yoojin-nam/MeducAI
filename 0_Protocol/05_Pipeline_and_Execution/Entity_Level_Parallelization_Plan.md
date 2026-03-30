# Entity-Level 병렬화 구현 계획

**Status:** Planning  
**Priority:** P1 (Performance Critical)  
**Created:** 2025-12-26  
**Last Updated:** 2025-12-26

## 1. 문제 정의

### 1.1 현재 상황
- **현재 병렬화 수준**: Group-level만 지원
- **문제점**: 
  - 각 그룹 내 entity들이 순차적으로 처리됨
  - 63개 entity × 평균 10초 = 최소 10분 이상 소요
  - Schema retry 발생 시 추가 시간 소요
  - 워커 수 증가해도 그룹 수(4개)가 제한이 되어 효과 제한적

### 1.2 목표
- **Entity-level 병렬화**: 그룹 내 entity들을 병렬로 처리
- **성능 개선**: 63개 entity를 병렬 처리하여 전체 시간 단축
- **API Quota 최적 활용**: RPM 1K인 S2 모델의 성능을 최대한 활용

## 2. 현재 아키텍처 분석

### 2.1 현재 처리 흐름
```
main()
  └─ ThreadPoolExecutor (group-level)
       └─ process_single_group(row)
            └─ S1 처리 (if execute_s1)
            └─ S2 처리 (if execute_s2)
                 └─ for entity in s2_targets:  # 순차 처리
                      └─ call_llm_with_schema_retry()
                      └─ entities_out.append(s2_json)
            └─ return record (with entities_out)
       └─ write_s2_results_jsonl(entities)  # 메인 스레드에서 쓰기
```

### 2.2 주요 함수
- `process_single_group()`: 그룹 단위 처리 (line 2760)
- `call_llm_with_schema_retry()`: Entity별 LLM 호출 (line 1816)
- `write_s2_results_jsonl()`: S2 결과 파일 쓰기 (line 2449)

### 2.3 현재 병렬화 포인트
- **Group-level**: `ThreadPoolExecutor`로 여러 그룹 병렬 처리 (line 4064)
- **Entity-level**: 없음 (line 3351에서 순차 처리)

## 3. 설계 개요

### 3.1 새로운 아키텍처
```
main()
  └─ ThreadPoolExecutor (group-level)
       └─ process_single_group(row)
            └─ S1 처리 (if execute_s1)
            └─ S2 처리 (if execute_s2)
                 └─ ThreadPoolExecutor (entity-level)  # NEW
                      └─ process_single_entity()  # NEW
                           └─ call_llm_with_schema_retry()
                           └─ return s2_json
                 └─ collect results & aggregate
            └─ return record (with entities_out)
       └─ write_s2_results_jsonl(entities)  # 메인 스레드에서 쓰기
```

### 3.2 핵심 변경사항
1. **새 함수**: `process_single_entity()` 생성
2. **Entity-level ThreadPoolExecutor**: 그룹 내에서 entity 병렬 처리
3. **Thread-safe 파일 쓰기**: S2 결과 파일에 동시 쓰기 지원
4. **진행 상황 추적**: Entity-level 진행 상황 표시

## 4. 구현 단계

### Phase 1: 함수 분리 및 구조화

#### 4.1.1 `process_single_entity()` 함수 생성
**위치**: `01_generate_json.py`, `process_single_group()` 함수 내부

**시그니처**:
```python
def process_single_entity(
    *,
    entity_target: _S2Target,
    group_id: str,
    group_path: str,
    s1_json: Dict[str, Any],
    ent2id: Dict[str, str],
    provider: str,
    clients: ProviderClients,
    arm: str,
    arm_config: Dict[str, Any],
    bundle: Dict[str, Any],
    run_tag: str,
    mode: str,
    model_stage2: str,
    temp_stage2: float,
    timeout_s: int,
    thinking_enabled: bool,
    thinking_budget: Optional[int],
    thinking_level: Optional[str],
    rag_enabled: bool,
    out_dir: Path,
    quota_s2: Optional[Any],
) -> Tuple[Optional[Dict[str, Any]], Optional[str], Dict[str, Any]]
```

**책임**:
- 단일 entity의 S2 처리
- LLM 호출 및 schema validation
- Entity 결과 반환 (성공) 또는 에러 반환 (실패)

**반환값**:
- `(s2_json, error_msg, runtime_meta)` 또는 `(None, error_msg, runtime_meta)`

#### 4.1.2 기존 코드 리팩토링
- `process_single_group()` 내부의 entity 처리 루프 (line 3351-3465)를 `process_single_entity()` 호출로 변경
- Entity 처리 로직을 새 함수로 이동

### Phase 2: Entity-level 병렬화 구현

#### 4.2.1 ThreadPoolExecutor 추가
**위치**: `process_single_group()` 내부, S2 처리 섹션

**구현**:
```python
# Entity-level 병렬화
if workers_s2_entity > 1:
    with ThreadPoolExecutor(max_workers=workers_s2_entity) as entity_ex:
        entity_futures = {
            entity_ex.submit(
                process_single_entity,
                entity_target=tgt,
                group_id=gid,
                group_path=group_path,
                s1_json=s1_json,
                ent2id=ent2id,
                # ... other params
            ): tgt
            for tgt in s2_targets
        }
        
        for fut in as_completed(entity_futures):
            tgt = entity_futures[fut]
            try:
                s2_json, err2, rt_s2 = fut.result()
                if s2_json:
                    entities_out.append(s2_json)
                    # 진행 상황 출력
                else:
                    # 에러 처리
            except Exception as e:
                # 예외 처리
else:
    # 기존 순차 처리 (workers_s2_entity == 1)
    for tgt in s2_targets:
        s2_json, err2, rt_s2 = process_single_entity(...)
        # ...
```

#### 4.2.2 Worker 설정 분리
- **Group-level workers**: `WORKERS_S2_GROUP` (기존 `WORKERS_S2`)
- **Entity-level workers**: `WORKERS_S2_ENTITY` (새로운 설정)

**환경변수**:
```bash
WORKERS_S2_GROUP=4    # 그룹 간 병렬화 (기존)
WORKERS_S2_ENTITY=8   # 그룹 내 entity 병렬화 (새로운)
```

**우선순위**:
1. CLI 인자: `--workers_s2_entity`
2. 환경변수: `WORKERS_S2_ENTITY`
3. 기본값: `WORKERS_S2_ENTITY = min(8, len(s2_targets))` (entity 수에 맞춰 조정)

### Phase 3: Thread-Safe 파일 쓰기

#### 4.3.1 Lock 기반 쓰기
**현재**: `write_s2_results_jsonl()`은 메인 스레드에서만 호출됨

**변경 필요**: Entity-level 병렬화 시 여러 스레드에서 동시 쓰기 필요

**옵션 A: Lock 사용 (권장)**
```python
# process_single_group() 시작 부분
lock_s2 = threading.Lock()
s2_writer = _LockedWriter(f_s2, lock_s2) if (f_s2 and workers_s2_entity > 1) else f_s2

# process_single_entity()에서
if s2_json:
    write_s2_results_jsonl(
        [s2_json],
        s2_writer,
        run_tag=run_tag,
        arm=arm,
        group_path=group_path,
    )
```

**옵션 B: 결과 수집 후 일괄 쓰기 (대안)**
- Entity 처리 완료 후 `entities_out`에 수집
- 그룹 처리 완료 후 메인 스레드에서 일괄 쓰기
- 현재 구조와 유사하여 구현이 간단함

**선택**: 옵션 B (기존 구조 유지, 안정성 우선)

### Phase 4: 진행 상황 추적

#### 4.4.1 Entity-level 진행 상황 표시
- `tqdm` 사용하여 entity 진행 상황 표시
- 또는 간단한 카운터로 진행 상황 출력

**구현**:
```python
# Entity 처리 시작 전
total_entities = len(s2_targets)
completed = 0

for fut in as_completed(entity_futures):
    completed += 1
    print(f"[S2] Entity progress: {completed}/{total_entities} (group: {gid[:12]}...)", flush=True)
```

#### 4.4.2 에러 처리 및 로깅
- Entity별 에러는 그룹 전체를 실패시키지 않음 (FINAL mode)
- 에러 로그를 별도로 기록

## 5. API Quota 고려사항

### 5.1 RPM 제한
- **S2 모델**: gemini-3-flash-preview, RPM 1K
- **동시 요청**: Entity-level 병렬화 시 동시 요청 수 증가
- **권장 워커 수**: `WORKERS_S2_ENTITY = 8-16` (RPM 여유있음)

### 5.2 Quota Limiter 호환성
- 현재 `quota_s2`는 thread-safe하게 구현되어 있는지 확인 필요
- 필요시 추가 thread-safety 검토

## 6. 구현 체크리스트

### Phase 1: 함수 분리
- [ ] `process_single_entity()` 함수 생성
- [ ] Entity 처리 로직 이동
- [ ] 기존 코드 리팩토링
- [ ] 단위 테스트 작성

### Phase 2: 병렬화
- [ ] Entity-level ThreadPoolExecutor 구현
- [ ] Worker 설정 분리 (`WORKERS_S2_ENTITY`)
- [ ] 환경변수 및 CLI 인자 추가
- [ ] 순차 처리 모드 유지 (workers == 1)

### Phase 3: Thread-Safety
- [ ] 파일 쓰기 thread-safety 확인
- [ ] Lock 구현 (필요시)
- [ ] 결과 수집 로직 확인

### Phase 4: 진행 상황 및 에러 처리
- [ ] Entity-level 진행 상황 표시
- [ ] 에러 처리 로직
- [ ] 로깅 개선

### Phase 5: 테스트 및 검증
- [ ] 소규모 그룹으로 테스트 (2-3개 entity)
- [ ] 대규모 그룹으로 테스트 (10+ entity)
- [ ] 여러 그룹 동시 처리 테스트
- [ ] 성능 측정 (before/after)
- [ ] API quota 사용량 모니터링

## 7. 예상 효과

### 7.1 성능 개선
**현재 (Group-level만)**:
- 4개 그룹 병렬, 각 그룹 내 순차
- 63개 entity × 10초 = 최소 10분

**개선 후 (Entity-level 추가)**:
- 4개 그룹 병렬, 각 그룹 내 8개 entity 병렬
- 63개 entity / 8 = ~8 배치
- 각 배치 10초 = 약 1.25분 (이론적 최소)
- 실제: Schema retry 고려 시 약 2-3분 예상

### 7.2 API Quota 활용
- RPM 1K 기준으로 8-16개 entity 동시 처리 가능
- Quota 활용률 향상

## 8. 리스크 및 대응

### 8.1 Thread-Safety 이슈
**리스크**: 여러 스레드에서 파일 쓰기 시 race condition

**대응**: 
- Lock 사용 또는 결과 수집 후 일괄 쓰기
- 철저한 테스트

### 8.2 API Quota 초과
**리스크**: 동시 요청이 너무 많아 429 에러 발생

**대응**:
- Quota limiter가 thread-safe한지 확인
- Worker 수를 보수적으로 설정 (초기: 8개)
- 모니터링 후 점진적 증가

### 8.3 메모리 사용량 증가
**리스크**: 많은 entity를 동시에 처리하면 메모리 사용량 증가

**대응**:
- Worker 수 제한
- 결과를 즉시 파일에 쓰기 (옵션 B)

## 9. 후속 작업

### 9.1 S1에도 적용 (선택사항)
- S1도 entity-level 병렬화가 필요한지 검토
- S1은 그룹 단위 처리만 있어 적용 필요성 낮을 수 있음

### 9.2 S4에도 적용 (선택사항)
- S4는 이미 entity-level 병렬화 지원 (이미지별 처리)
- 추가 개선 필요 시 검토

## 10. 참고사항

- **기존 코드 호환성**: 순차 처리 모드 유지 (workers == 1)
- **점진적 적용**: 먼저 S2에만 적용, 안정화 후 다른 단계 검토
- **성능 모니터링**: 실제 사용량 및 성능 지표 수집

