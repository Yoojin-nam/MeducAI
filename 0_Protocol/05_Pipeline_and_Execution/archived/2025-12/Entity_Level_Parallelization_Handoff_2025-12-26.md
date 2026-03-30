# Entity-Level 병렬화 Hang 이슈 인계 (2025-12-26)

## TL;DR

- **현상**: API 로그(Provider 콘솔)에서는 요청이 `200`으로 끝나는데, 로컬 `ThreadPoolExecutor` 기반 병렬 처리에서 **future가 완료되지 않고 멈춤**. 일부 entity만 끝나고 대부분 pending 상태로 정체.
- **핵심 원인**: Gemini(google-genai) SDK 호출이 로컬에서 응답 수신/파싱/내부 I/O 단계에서 **반환을 못 하고 블로킹**될 수 있으며, 기존 watchdog 구현은 구조적으로 **“타임아웃 raise 후에도 join(wait)에서 다시 멈출 수 있는”** 형태였다.
- **추가로 발견된 문제**: S1에서도 (1) 너무 짧은 watchdog 설정으로 **불필요한 hard-timeout**, (2) 모델이 `entity_list`를 `entity_clusters`에 누락해 **S1 스키마 검증 실패(coverage mismatch)**가 발생하며, (3) Gemini 호출을 subprocess로 격리한 경우 드물게 **IPC 결과 미수신(EmptyIPCResult)**가 발생할 수 있다.
- **해결 방향**:
  - Gemini 호출을 **subprocess로 격리한 hard-timeout**(S2 기본 ON)으로 “영구 hang”을 제거.
  - entity-level 병렬 루프를 단순화하고 **stall 진단 덤프(스레드 traceback)**를 추가.
  - S1 스키마의 “coverage mismatch”는 기본적으로 **자동 보정(repair)**하여 파이프라인을 진행 가능하게 함.
  - 운영 `.env`에 watchdog/heartbeat 및 디버깅 옵션을 추가.

---

## 1) 문제 현상(관측)

### 증상

- Provider 대시보드/로그에서는 요청이 정상 완료(`200`)로 보임.
- 로컬 파이썬에서는:
  - 일부 entity는 완료되지만 대부분이 처리되지 않음.
  - `as_completed()`가 끝나지 않거나, 진행률이 멈춘 채로 유지됨.
  - 타임아웃을 걸어도 “멈춘 듯” 보이는 상황이 존재.

### 재현/관측 포인트

- `01_generate_json.py`의 entity-level 병렬 처리 구간에서 pending future가 줄지 않음.
- `call_llm()`의 Gemini 호출이 반환되지 않아 해당 worker thread/future가 계속 `running()` 상태로 남는 케이스가 핵심.

---

## 2) 근본 원인 분석

### A. “API 200인데 로컬 future가 끝나지 않는” 이유

- **API 200 = 서버가 응답을 보냈다**는 의미이지, 로컬 SDK 호출이 “반환(return)까지 끝났다”는 보장이 아니다.
- 특히 google-genai SDK(또는 하부 gRPC/HTTP stack)에서
  - 응답 스트림 수신/디코딩,
  - 내부 connection/transport,
  - 파서 단계
  중 하나에서 블로킹이 걸리면 로컬은 멈출 수 있다.

### B. 기존 watchdog(스레드 기반)의 구조적 한계

- 실행 중인 `future.cancel()`은 대부분 효과가 없고(이미 실행 시작된 작업은 취소 불가),
- 더 치명적으로 `with ThreadPoolExecutor(...)` 컨텍스트를 빠져나갈 때 `shutdown(wait=True)`로 내부 스레드 종료를 기다리며 **타임아웃을 raise 하더라도 join에서 다시 멈출 수 있는 구조**가 된다.

### C. S1 “안 되던” 이유(후속 관측)

S1이 0바이트로 남았던 run들에서 원인은 대체로 아래 중 하나였다:

1. **watchdog가 너무 짧음** (`LLM_WATCHDOG_TIMEOUT_S=90` 등): S1이 보통 70~120초 걸리는 경우가 있어 첫 시도에서 hard-timeout으로 잘려 재시도 비용이 커짐.
2. **S1 스키마 검증 실패(coverage mismatch)**:
   - 모델이 `entity_list`에는 넣어놓고 `entity_clusters[*].entity_names`에는 누락하는 경우가 종종 발생.
   - 이 경우 Stage1 validation이 hard-fail 하면서 `stage1_raw__arm*.jsonl` / `stage1_struct__arm*.jsonl`이 **0B**로 남는다(“성공”이 한 번도 없으므로 writer가 append하지 못함).
3. **subprocess 격리 호출에서 EmptyIPCResult**:
   - subprocess worker가 큐에 결과를 남기지 못하고 종료하는 케이스가 관측됨(원인: subprocess 크래시/조기 종료/IPC 실패 등).
   - 이 케이스는 transient로 취급하여 call_llm retry 루프에서 재시도하도록 보강함.

---

## 3) 적용된 코드 변경(핵심)

### A. Gemini hard-timeout (subprocess 격리)

- Gemini `generate_content()`를 별도 프로세스에서 실행하고, watchdog 초과 시 `terminate/kill`로 반드시 복귀.
- 기본 정책:
  - **S2는 subprocess watchdog 기본 ON**(hang 위험 구간)
  - **S1은 기본 direct 호출**(subprocess IPC/오버헤드 리스크 회피)

설정 env:

- `LLM_GEMINI_SUBPROCESS_WATCHDOG=1`
- `LLM_GEMINI_SUBPROCESS_WATCHDOG_STAGE1=0`
- `LLM_GEMINI_SUBPROCESS_WATCHDOG_STAGE2=1`

### B. Entity-level 병렬 루프 단순화 + stall 진단

- 혼합된 `as_completed()`/수동 스캔 로직을 `wait(..., FIRST_COMPLETED)` 중심으로 단순화.
- 일정 시간 동안 완료가 없으면 `faulthandler.dump_traceback(all_threads=True)`로 **전체 스레드 스택 덤프**를 남김.

설정 env:

- `S2_ENTITY_STALL_DUMP_S=180` (기본 180초)

### C. 관측(로그) 강화

- `process_single_entity()` 시작/종료/예외에 대해 간결한 로그 추가:
  - entity name/id, thread id, elapsed seconds
- `call_llm()` 단계 로그:
  - watchdog 활성 로그
  - 응답 수신(raw chars) 로그(옵션)
  - schema validation 실패 로그(옵션)

설정 env(필요 시):

- `LLM_LOG_WATCHDOG=1`
- `LLM_LOG_PHASES=1`
- `S2_ENTITY_LOG=1`

### D. S1 coverage mismatch 자동 보정(repair)

- Stage1 validation에서 `entity_list`와 `entity_clusters`가 불일치할 때,
  - **extra는 제거**
  - **missing은 cluster의 최대 허용(8) 범위 내에서 가장 작은 cluster부터 채워 넣음**
  - cluster가 3 미만으로 떨어지면 큰 cluster에서 엔티티를 “빌려” 최소 3개를 유지
- 기본 ON:
  - `S1_CLUSTER_COVERAGE_REPAIR=1`

---

## 4) 운영 가이드(.env 권장)

```dotenv
TIMEOUT_S=600
LLM_WATCHDOG_TIMEOUT_S=600
LLM_HEARTBEAT_S=20

LLM_GEMINI_SUBPROCESS_WATCHDOG=1
LLM_GEMINI_SUBPROCESS_WATCHDOG_STAGE1=0
LLM_GEMINI_SUBPROCESS_WATCHDOG_STAGE2=1

S1_CLUSTER_COVERAGE_REPAIR=1
S2_ENTITY_STALL_DUMP_S=180

LLM_LOG_WATCHDOG=1
LLM_LOG_PHASES=0
S2_ENTITY_LOG=1
```

---

## 5) 테스트 커맨드(스모크)

### S1 단독 스모크(권장)

```bash
cd /path/to/workspace/workspace/MeducAI

python -u 3_Code/src/01_generate_json.py \
  --base_dir /path/to/workspace/workspace/MeducAI \
  --run_tag smoke_s1_fixed_$(date +%Y%m%d_%H%M%S) \
  --arm G \
  --mode FINAL \
  --stage 1 \
  --row_index 1
```

### S2/Entity 병렬 스모크(재현용)

```bash
cd /path/to/workspace/workspace/MeducAI

python -u 3_Code/src/01_generate_json.py \
  --base_dir /path/to/workspace/workspace/MeducAI \
  --run_tag smoke_s2_entity_$(date +%Y%m%d_%H%M%S) \
  --arm G \
  --mode FINAL \
  --stage 2 \
  --row_index 1 \
  --workers_s2_entity 4
```

---

## 6) 로그/아티팩트 위치(중요)

run_tag = `<RUN_TAG>` 기준:

- 출력(성공 시):
  - `2_Data/metadata/generated/<RUN_TAG>/stage1_raw__arm<ARM>.jsonl`
  - `2_Data/metadata/generated/<RUN_TAG>/stage1_struct__arm<ARM>.jsonl`
  - `2_Data/metadata/generated/<RUN_TAG>/s2_results__s1arm<S1ARM>__s2arm<S2ARM>.jsonl`
- 원문(LLM raw):
  - `2_Data/metadata/generated/<RUN_TAG>/raw_llm/stage1/<ARM>/<group_id>/attempt_XX.txt`
  - `2_Data/metadata/generated/<RUN_TAG>/raw_llm/stage2/<ARM>/<group_id>/<entity_id>/attempt_XX.txt`
- 진단 로그:
  - `2_Data/metadata/generated/<RUN_TAG>/logs/llm_metrics.jsonl`
  - `2_Data/metadata/generated/<RUN_TAG>/logs/llm_schema_retry_log.jsonl`
- 프롬프트 덤프:
  - `2_Data/metadata/generated/<RUN_TAG>/debug_raw/`

---

## 7) 향후 작업/주의점

- **S1 repair는 “파이프라인 진행”을 우선시하는 정책**이다.
  - 정확히 어떤 엔티티를 어떤 cluster로 넣을지는 모델이 결정해야 하는 의미가 있으므로,
  - repair가 자주 발생하면 프롬프트/스키마를 개선해 “처음부터 완전한 cluster coverage”를 유도하는 게 장기적으로 바람직하다.
- subprocess watchdog은 hang 해결에 매우 유효하지만, **IPC 미수신(EmptyIPCResult)** 같은 변종 케이스가 있을 수 있으니,
  - 기본값을 S2 중심으로 유지하고(S1은 direct),
  - 문제가 계속되면 subprocess worker의 exitcode/크래시 원인(환경/라이브러리/OS)을 별도 조사한다.


