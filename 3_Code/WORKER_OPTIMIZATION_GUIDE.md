# Worker 수 최적화 가이드

## 개요

Worker 수를 늘리면 병렬 처리로 **더 빨라질 수 있지만**, API rate limit에 의해 제한됩니다. 각 스테이지별로 최적의 Worker 수가 다릅니다.

---

## 현재 설정된 API Rate Limits

### S1 (gemini-3-pro-preview)
- **RPM**: 25 (Requests Per Minute)
- **TPM**: 1,000,000 (Tokens Per Minute)
- **RPD**: 250 (Requests Per Day)
- **평균 응답 시간**: 60-90초 (thinking 모드)

### S2 (gemini-3-flash)
- **RPM**: 1,000 (Requests Per Minute)
- **TPM**: 1,000,000 (Tokens Per Minute)
- **RPD**: 10,000 (Requests Per Day)
- **평균 응답 시간**: 5-15초

### S4 (nano-banana-pro 이미지 생성)
- **RPM**: 20 (Requests Per Minute)
- **TPM**: 100,000 (Tokens Per Minute)
- **RPD**: 250 (Requests Per Day)
- **평균 응답 시간**: 10-30초 (이미지 생성)

---

## Worker 수 계산 공식

### 이론적 최대 Worker 수

```
최대 Worker 수 ≈ (RPM × 평균 응답 시간(초)) / 60
```

**주의**: 이는 이론적 최대값이며, 실제로는 안전 마진을 두어야 합니다.

### 실제 권장 Worker 수

```
권장 Worker 수 = 최대 Worker 수 × 0.7 (안전 마진 30%)
```

---

## 스테이지별 권장 Worker 수

### S1 (gemini-3-pro-preview)

**계산**:
- RPM: 25
- 평균 응답 시간: 75초 (thinking 모드)
- 이론적 최대: (25 × 75) / 60 = **31.25**
- 권장: 31 × 0.7 = **~22**

**권장 범위**: **2-5** (보수적)
- 이유: S1은 응답 시간이 길고, thinking 모드로 인해 변동성이 큼
- 실제 테스트 결과: 2-3개가 가장 안정적

**최대**: **10-15** (공격적)
- Rate limiter가 자동으로 제어하지만, 429 에러 위험 증가

---

### S2 (gemini-3-flash)

**계산**:
- RPM: 1,000
- 평균 응답 시간: 10초
- 이론적 최대: (1,000 × 10) / 60 = **166.7**
- 권장: 166 × 0.7 = **~116**

**권장 범위**: **10-20** (보수적)
- 이유: S2는 매우 빠르지만, S1 결과를 기다려야 하므로 파이프라인 병목 고려
- 실제 테스트 결과: 10-15개가 가장 효율적

**최대**: **50-100** (공격적)
- S2는 RPM이 매우 높아 많은 worker 가능
- 단, S1 완료 후 실행되므로 S1 worker 수와 균형 필요

---

### S4 (nano-banana-pro 이미지 생성)

**계산**:
- RPM: 20
- 평균 응답 시간: 20초
- 이론적 최대: (20 × 20) / 60 = **6.7**
- 권장: 6.7 × 0.7 = **~5**

**권장 범위**: **2-3** (보수적)
- 이유: 이미지 생성은 시간이 오래 걸리고, RPM이 낮음
- 실제 테스트 결과: 2개가 가장 안정적

**최대**: **4-5** (공격적)
- RPM이 낮아 worker 수를 많이 늘릴 수 없음
- Rate limiter가 자동으로 대기하지만, 대기 시간이 길어질 수 있음

---

## 실제 사용 예시

### 보수적 설정 (안정성 우선)

```bash
# S1 + S2 (병렬)
python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag test_parallel \
  --arm G \
  --stage both \
  --workers 3 \
  --mode FINAL

# S4 (이미지 생성)
python3 3_Code/src/04_s4_image_generator.py \
  --base_dir . \
  --run_tag test_parallel \
  --arm G \
  --workers 2 \
  --required_only
```

### 공격적 설정 (속도 우선, 429 위험 증가)

```bash
# S1 + S2
python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag test_parallel \
  --arm G \
  --stage both \
  --workers 10 \
  --mode FINAL

# S4
python3 3_Code/src/04_s4_image_generator.py \
  --base_dir . \
  --run_tag test_parallel \
  --arm G \
  --workers 4 \
  --required_only
```

---

## Worker 수 증가 시 고려사항

### ✅ 장점
1. **처리 속도 향상**: 병렬 처리로 전체 실행 시간 단축
2. **리소스 활용**: CPU/네트워크 대역폭 효율적 사용

### ⚠️ 단점
1. **429 에러 위험**: Rate limit 초과 시 에러 발생
2. **대기 시간 증가**: Worker가 많아도 rate limiter가 대기시킴
3. **메모리 사용량 증가**: 각 worker가 메모리 사용
4. **로그 혼잡**: 병렬 실행 시 로그가 섞일 수 있음

---

## Rate Limiter 동작 방식

현재 구현된 `QuotaLimiter`는:
- **RPM/TPM**: 60초 rolling window로 제어
- **RPD**: 일일 카운터로 제어
- **Thread-safe**: 여러 worker가 동시에 사용해도 안전
- **자동 대기**: Limit 초과 시 자동으로 대기 후 재시도

따라서 Worker 수를 늘려도 rate limiter가 자동으로 제어하지만, **너무 많으면 대기 시간만 늘어나고 실제 처리량은 증가하지 않습니다**.

---

## 모니터링 및 튜닝

### 실행 중 확인할 지표

1. **429 에러 발생 빈도**: `llm_metrics.jsonl`에서 확인
2. **실제 처리 속도**: 전체 실행 시간 / 처리된 항목 수
3. **Rate limiter 대기 시간**: 로그에서 `waiting` 메시지 확인

### 최적 Worker 수 찾기

1. **작은 샘플로 테스트**: `--sample 4` 등으로 작은 그룹으로 테스트
2. **Worker 수를 점진적으로 증가**: 2 → 4 → 6 → 8 ...
3. **실행 시간과 429 에러 발생 빈도 관찰**
4. **최적 지점 선택**: 속도 향상이 미미하고 429가 증가하기 시작하는 지점

---

## 결론

| 스테이지 | 보수적 권장 | 공격적 최대 | 비고 |
|---------|------------|------------|------|
| **S1** | 2-3 | 10-15 | 응답 시간이 길어 제한적 |
| **S2** | 10-15 | 50-100 | 매우 빠른 모델, 높은 RPM |
| **S4** | 2-3 | 4-5 | 낮은 RPM, 긴 응답 시간 |

**권장**: 처음에는 보수적 설정으로 시작하고, 점진적으로 증가시키면서 최적값을 찾으세요.

