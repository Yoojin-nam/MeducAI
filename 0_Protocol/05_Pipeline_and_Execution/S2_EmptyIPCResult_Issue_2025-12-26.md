# S2 EmptyIPCResult 이슈 및 해결 방안 (2025-12-26)

> **📋 관련 문서**: `0_Protocol/05_Pipeline_and_Execution/archived/2025-12/S2_Debugging_Session_2025-12-26_Handoff.md` - 전체 디버깅 세션 인계 문서 참고

## TL;DR

- **현상**: S2 실행 시 모든 entity가 `EmptyIPCResult` 에러로 실패 (204개 에러 발생)
- **원인**: macOS의 multiprocessing spawn context에서 SimpleQueue가 제대로 작동하지 않음
- **해결 방안**: 
  1. 큐 타임아웃 증가 (2초 → 10초) - **부분적 개선**
  2. S2에서 subprocess watchdog 비활성화 (임시 해결책) - **권장**
- **S1/S2 같은 코드**: 문제 없음 (stage별 분기 처리, 독립적 설정 가능)

---

## 1) 문제 현상

### 증상
- S2 실행 시 모든 entity가 `EmptyIPCResult` 에러로 실패
- `s2_results__s1armG__s2armG.jsonl` = 0바이트 (결과 없음)
- 로그에서 204개의 `EmptyIPCResult` 에러 발생
- 모든 entity가 `attempt=2/3`, `attempt=3/3`로 재시도 후 실패

### 에러 메시지
```
GeminiSubprocessError: EmptyIPCResult: Gemini subprocess returned no result 
(exitcode=0, alive=False, queue_timeout=10.0s, error=Empty)
```

### 재현 조건
- macOS (darwin 25.2.0)
- Python 3.13.2
- multiprocessing spawn context 사용
- S2 stage에서 subprocess watchdog 활성화 (`LLM_GEMINI_SUBPROCESS_WATCHDOG_STAGE2=1`)

---

## 2) 근본 원인 분석

### A. EmptyIPCResult 발생 메커니즘

1. **Subprocess watchdog 동작**:
   - Gemini SDK 호출을 별도 프로세스에서 실행
   - `multiprocessing.SimpleQueue`를 통해 결과 전달
   - subprocess가 정상 종료(exitcode=0)하지만 큐에 결과가 없음

2. **macOS multiprocessing spawn context 문제**:
   - macOS는 기본적으로 `spawn` context 사용
   - `spawn` context에서 SimpleQueue flush가 느리거나 실패할 수 있음
   - subprocess 종료 후 큐에서 결과를 받는 데 실패

### B. 코드 위치

**파일**: `3_Code/src/01_generate_json.py`

- **Subprocess worker**: `_gemini_generate_content_worker()` (line 896)
- **Watchdog wrapper**: `_run_gemini_generate_with_hard_timeout()` (line 1029)
- **큐 타임아웃**: line 1096에서 `q.get(timeout=10.0)` 호출

### C. S1과 S2가 같은 코드에 있는 것의 영향

**문제 없음**. 이유:
- S1과 S2는 같은 파일이지만 **stage별로 분기 처리**됨
- Subprocess watchdog 설정은 **stage별로 독립적으로 제어** 가능:
  - `LLM_GEMINI_SUBPROCESS_WATCHDOG_STAGE1=0` (S1 비활성화)
  - `LLM_GEMINI_SUBPROCESS_WATCHDOG_STAGE2=1` (S2 활성화)
- 각 stage는 독립적인 함수 호출 경로를 가짐

---

## 3) 적용된 해결 방안

### A. 큐 타임아웃 증가 (부분적 개선)

**변경 사항**:
- 큐 타임아웃: 2.0초 → **10.0초**
- subprocess 종료 후 대기: 0.1초 → **0.5초**
- subprocess worker에서 stdout/stderr flush 추가

**결과**: 여전히 `EmptyIPCResult` 발생 (개선되지 않음)

**코드 위치**: `3_Code/src/01_generate_json.py` line 1091-1107

### B. S2에서 subprocess watchdog 비활성화 (권장 해결책)

**임시 해결책**: macOS에서 SimpleQueue 문제를 우회하기 위해 S2에서 watchdog 비활성화

**설정**:
```bash
export LLM_GEMINI_SUBPROCESS_WATCHDOG=1
export LLM_GEMINI_SUBPROCESS_WATCHDOG_STAGE2=0  # S2 watchdog 비활성화
```

**주의사항**:
- Watchdog 비활성화 시 hang 위험이 있음
- 하지만 현재는 EmptyIPCResult로 진행이 막혀 있어 watchdog 없이 테스트 필요
- S1은 watchdog 비활성화 상태로 정상 작동했음 (참고)

---

## 4) 테스트 결과 요약

### 성공한 단계
- ✅ **S1**: 4개 그룹 모두 성공 (병렬화 정상 작동, 약 1.8배 속도 개선)
- ✅ **S3**: 정상 완료
- ✅ **S4**: 이미지 11개 생성 완료 (병렬화 정상 작동)

### 실패한 단계
- ❌ **S2**: 모든 entity가 EmptyIPCResult로 실패 (204개 에러)

---

## 5) 다음 단계 (다른 Agent 인계)

### 즉시 테스트할 사항

1. **S2 watchdog 비활성화 테스트**:
```bash
cd /path/to/workspace/workspace/MeducAI

RUN_TAG="smoke_4groups_20251226_123809"
ARM="G"

export LLM_GEMINI_SUBPROCESS_WATCHDOG=1
export LLM_GEMINI_SUBPROCESS_WATCHDOG_STAGE2=0  # S2 watchdog 비활성화
export TIMEOUT_S=600
export LLM_WATCHDOG_TIMEOUT_S=600

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
  --resume
```

2. **결과 확인**:
```bash
# S2 결과 파일 확인
wc -l 2_Data/metadata/generated/${RUN_TAG}/s2_results__s1armG__s2armG.jsonl

# 에러 로그 확인
grep -c "EmptyIPCResult" 2_Data/metadata/generated/${RUN_TAG}/logs/llm_metrics.jsonl
```

### 장기적 해결 방안 (향후 작업)

1. **IPC 메커니즘 개선**:
   - SimpleQueue 대신 다른 IPC 방법 고려 (파일 기반, socket 등)
   - 또는 subprocess 대신 thread 기반 watchdog 고려

2. **플랫폼별 처리**:
   - macOS에서만 watchdog 비활성화 또는 다른 IPC 사용
   - Linux/Windows에서는 기존 방식 유지

3. **에러 복구 강화**:
   - EmptyIPCResult 발생 시 자동으로 direct 호출로 fallback
   - 또는 재시도 시 다른 IPC 메커니즘 사용

---

## 6) 관련 파일 및 설정

### 코드 파일
- `3_Code/src/01_generate_json.py`:
  - `_gemini_generate_content_worker()` (line 896): subprocess worker
  - `_run_gemini_generate_with_hard_timeout()` (line 1029): watchdog wrapper
  - `call_llm()` (line 1407): LLM 호출 메인 함수

### 환경변수 설정
```bash
# Subprocess watchdog 제어
LLM_GEMINI_SUBPROCESS_WATCHDOG=1              # 전체 활성화
LLM_GEMINI_SUBPROCESS_WATCHDOG_STAGE1=0       # S1 비활성화 (기본)
LLM_GEMINI_SUBPROCESS_WATCHDOG_STAGE2=1       # S2 활성화 (기본, 문제 발생)
LLM_GEMINI_SUBPROCESS_WATCHDOG_STAGE2=0       # S2 비활성화 (임시 해결책)

# 타임아웃 설정
TIMEOUT_S=600
LLM_WATCHDOG_TIMEOUT_S=600
```

### 로그 파일 위치
- `2_Data/metadata/generated/${RUN_TAG}/logs/llm_metrics.jsonl`: 에러 로그
- `2_Data/metadata/generated/${RUN_TAG}/logs/llm_schema_retry_log.jsonl`: 재시도 로그

---

## 7) 참고 문서

- `0_Protocol/05_Pipeline_and_Execution/archived/2025-12/Entity_Level_Parallelization_Handoff_2025-12-26.md`: 원본 인계 문서
- Handoff 문서에서 언급: "subprocess watchdog은 hang 해결에 매우 유효하지만, **IPC 미수신(EmptyIPCResult)** 같은 변종 케이스가 있을 수 있으니..."

---

## 8) 현재 상태 요약

| 단계 | 상태 | 비고 |
|------|------|------|
| S1 | ✅ 성공 | 4개 그룹, 병렬화 정상, 약 1.8배 속도 개선 |
| S2 | ❌ 실패 | EmptyIPCResult 204개, watchdog 비활성화 테스트 필요 |
| S3 | ✅ 성공 | 정상 완료 |
| S4 | ✅ 성공 | 이미지 11개 생성, 병렬화 정상 |

**다음 작업**: S2 watchdog 비활성화로 재테스트 필요

