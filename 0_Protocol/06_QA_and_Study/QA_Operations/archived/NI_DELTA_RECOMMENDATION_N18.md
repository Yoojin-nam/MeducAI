# n=18에서 비열등성 검정 Delta 설정 권장사항

**Date:** 2025-12-23  
**Context:** n=18 groups로 이미 배포 완료, 비열등성 검정을 "최적화 도구"로 사용  
**Status:** Recommendation Document

---

## 1. 상황 요약

- **n = 18 groups** (이미 배포 완료, 변경 불가)
- **Endpoint:** Set-level Overall Card Quality (1–5 Likert scale)
- **Baseline:** Arm E (High-End)
- **목적:** 비열등성 검정은 "필수"가 아니라 "cost optimization 도구"
- **Fallback Policy:** 비열등성 검정 실패 시 High-End 모델 사용 가능

---

## 2. 현재 Canonical 설정

**S0_Noninferiority_Criteria_Canonical.md (v2.0):**
- Δ = 0.5 (Likert scale, half of one step)
- CI = 95% two-sided (one-sided α = 0.025)

**문제점:**
- n=18은 작은 샘플 크기 → 검정력(power) 낮음
- Δ=0.5, 95% CI는 "필수 검증" 수준의 엄격함
- 비열등성 검정 실패 시에도 High-End 사용 가능하므로, 더 관대한 기준 고려 가능

---

## 3. Delta 설정 옵션 (n=18 고정)

### Option 1: Delta 증가 (권장)

**Δ = 0.6 (Likert scale)**

**근거:**
- 0.5 (half step)에서 0.6으로 약간 완화
- Likert scale에서 0.6은 여전히 "교육적으로 타당한 범위"
- 예: Baseline E가 4.0일 때, candidate가 3.4 이상이면 비열등
- n=18에서 검정력이 낮으므로, 약간의 완화가 타당

**장점:**
- CI는 95% 유지 (통계적 엄격함 보존)
- Delta만 완화하므로 해석이 단순
- 논문에서도 "half step에서 약간 완화된 기준"으로 설명 가능

**단점:**
- "half step"이라는 명확한 기준에서 벗어남

---

### Option 2: Delta + CI 완화 (더 관대)

**Δ = 0.6, CI = 90% (one-sided α = 0.05)**

**근거:**
- Delta와 CI를 모두 완화하여 검정력 보완
- Early-phase pilot로서 90% CI도 통계적으로 방어 가능
- Statistical_Analysis_Plan.md에서도 "90% CI for operational selection" 옵션 제시

**장점:**
- 검정력 향상 (비열등성 검정 통과 가능성 증가)
- n=18에 더 적합한 설계

**단점:**
- 90% CI는 95% CI보다 덜 엄격 (논문에서 비열등성 주장 시 약점 가능)

---

### Option 3: Delta 대폭 증가 (가장 관대)

**Δ = 0.7 (Likert scale), CI = 95%**

**근거:**
- 비열등성이 "최적화 도구"라면 더 관대한 기준도 타당
- 0.7은 여전히 "1.0 (full step)"보다는 엄격
- Fallback policy 존재하므로, 비열등성 검정 실패 시 High-End 사용

**장점:**
- 검정력 향상
- Cost optimization 목적에 부합

**단점:**
- 0.7은 "half step"보다 크게 완화됨
- 논문에서 delta justification이 필요

---

## 4. 권장 설정 (Recommendation)

### Primary Recommendation: **Δ = 0.6, CI = 95%**

**이유:**
1. **n=18에 적합:** 작은 샘플 크기에서 검정력을 보완하면서도 통계적 엄격함 유지
2. **교육적 타당성:** 0.6은 여전히 Likert scale에서 "교육적으로 의미 있는 범위"
3. **명확한 해석:** "half step에서 약간 완화"로 설명 가능
4. **논문 방어 가능:** 95% CI 유지로 통계적 엄격함 보존

### Alternative Recommendation (더 관대한 기준 원할 경우): **Δ = 0.6, CI = 90%**

**이유:**
1. **Early-phase pilot:** n=18은 early-phase pilot로서 90% CI도 타당
2. **Operational selection:** 비열등성 검정이 "operational decision" 목적이라면 90% CI 적절
3. **검정력 향상:** Delta와 CI를 모두 완화하여 검정력 보완

---

## 5. 구현 방법

### 스크립트 실행 예시

**Option 1 (권장):**
```bash
python 3_Code/src/tools/qa/s0_noninferiority_setlevel.py \
  --input_csv <path> \
  --baseline_arm E \
  --delta 0.6 \
  --n_boot 10000 \
  --seed 123 \
  --out_json <path> \
  --out_csv <path>
```

**Option 2 (더 관대):**
- CI를 90%로 설정하려면 스크립트 수정 필요 (현재는 95% 고정으로 보임)
- 또는 bootstrap percentile을 5th percentile로 변경 (현재는 2.5th percentile)

---

## 6. 문서 업데이트 필요사항

Delta를 0.5에서 0.6으로 변경할 경우:

1. **S0_Noninferiority_Criteria_Canonical.md 업데이트:**
   - Section 1.2: "Why Δ = 0.6 is Appropriate for n=18"
   - Section 2.2: Delta = 0.6으로 변경
   - Version bump (v2.0 → v2.1)

2. **Justification 추가:**
   - n=18로 인한 검정력 제약
   - 비열등성 검정이 "최적화 도구"라는 목적
   - Fallback policy 존재

3. **논문 Methods 섹션:**
   - Delta = 0.6 선택 근거 명시
   - "n=18 early-phase pilot에서 검정력을 고려하여 Δ=0.6으로 설정" 등

---

## 7. 결론

**n=18로 이미 배포된 상황에서 비열등성 검정을 "최적화 도구"로 사용한다면:**

**권장: Δ = 0.6 (Likert scale), CI = 95%**

이 설정은:
- n=18의 검정력 제약을 고려
- 통계적 엄격함(95% CI) 유지
- 교육적 타당성 유지 (0.6은 여전히 "의미 있는 범위")
- 논문에서도 방어 가능

**더 관대한 기준을 원할 경우:** Δ = 0.6, CI = 90%도 고려 가능

