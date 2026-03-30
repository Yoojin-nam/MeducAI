# User vs Non-user 비교용 최소 공변량 세트 (Prospective Observational)

**목적:** RCT가 아닌 전향적 관찰 연구에서 “사용자 vs 비사용자” 비교 시, **선택 편향/교란(confounding)**을 최소한으로 보정하기 위한 *최소* 공변량 세트를 정의한다.  
**권장 분석:** Baseline→Final 변화량(\(\Delta\)) 기반 비교 + (필요 시) 회귀 조정/가중치(IPW) 보강.

> **스코어/변수 정의(SSOT)**: `0_Protocol/06_QA_and_Study/Study_Design/Survey_Scoring_and_Variable_Dictionary_Paper3.md`

---

## 1) 최소 공변량 세트 (Baseline에서 확보)

> 아래 변수들은 “사용 여부”와 “결과(outcome)” 모두에 영향을 줄 가능성이 높은 핵심 교란 변수들입니다.

### 1.1 인구통계/훈련 맥락
- **연령** (Baseline: S0-3)
- **성별** (Baseline: S0-4)
- **병원 유형** (Baseline: S0-2)
- **로테이션** (Baseline: F2)

### 1.2 학습 강도/전략 (사용 가능성과 결과 모두에 영향)
- **최근 2주 주당 평균 공부 시간** (Baseline: F3)
- **기존 학습 도구 사용(복수 선택)** (Baseline: F5)
- **(선택) Anki 사용량/숙련도** (Baseline: F6)

### 1.3 AI/LLM 사전 노출 (도구 수용·신뢰·사용량에 영향)
- **LLM 사용 경험** (Baseline: F7)
- **임상 목적 LLM 사용 경험** (Baseline: F8)
- **LLM 기술 이해 수준** (Baseline: F9)
- **LLM 정보 신뢰도(전반)** (Baseline: F10)

### 1.4 Baseline 결과(Outcome) — 변화량 분석의 기준점
- **Extraneous cognitive load (baseline)**: C1-1~C1-3 (Baseline 문항 텍스트 기준)
- **자기효능감(선택적 단축 가능)**: D4(또는 D 전체 평균)
- **스트레스/수면/기분/운동**: Baseline E 섹션(행동·정서 요인)

---

## 2) Final에서 추가로 확보(공통 모듈) — 비교/해석을 위한 “동일 축”

> 사용자/비사용자 모두 응답하는 공통 모듈을 통해 \(\Delta\)를 만들 수 있습니다.

- **Extraneous cognitive load (final)**: Z1~Z3
- **행동·정서 요인 (final)**: Z4~Z8
- **자기효능감 단축(최소 1문항)**: Z9

---

## 3) 권장 비교 분석(요약)

- **1차(권장)**: 변화량 기반 비교  
  - \(\Delta Y = Y_{final} - Y_{baseline}\) 를 만들고, 사용자(=A1 예) vs 비사용자(=A1 아니오) 비교
- **2차(보강)**: 회귀 조정  
  - \(\Delta Y \sim \text{사용여부} + \) (위 1.1~1.3 + baseline outcome)
- **민감도(추천)**: 비사용자 중에서도 “접근/인지”가 달랐던 집단(N1)으로 층화  
  - 예: **받았는데 미사용** vs **아예 못 받음/모름**


