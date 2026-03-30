---
marp: true
theme: gaia
paginate: true
backgroundColor: #fff
---

# MeducAI 연구 개요 및 발전 가능성 분석
<br>
<br>

<div style="font-size: 18px;">
2026년 1월 12일<br>
GLM-4.7 연구 분석 기반
</div>

---

# 목차

1. 연구 개요
2. 파이프라인 구조
3. 3편 논문 포트폴리오
4. 현재 상태 및 일정
5. 발전 가능성 분석
6. 우선순위 및 향후 계획

---

# 1. 연구 개요

## MeducAI란?

**AI 기반 의료 교육 플랫폼**
- **목표**: 영상의학과 전문의 시험 준비
- **핵심**: AI가 생성한 플래시카드 + 이미지
- **프로세스**: 교육 목표 → AI 파이프라인 → 학습자

```
Curriculum Objectives → AI Pipeline → Flashcards → Learners
```

---

# 2. 파이프라인 구조

## S1 → S6 6단계 파이프라인

```
S1: 구조화 (Entity 추출)
    ↓
S2: 카드 생성 (Q1/Q2 질문-답변)
    ↓
S3: 정책 해결 (이미지 스펙 컴파일)
    ↓
S4: 이미지 생성 (Illustration + Realistic)
    ↓
S5: 검증 & 재작성 (PASS/REGEN 판정)
    ↓
S6: 패키징 (PDF, Anki 덱)
```

### 핵심 특징
- **2-card 정책**: 각 엔티티당 정확히 2개 카드
- **Back-only 인포그래픽**: 모든 Q1/Q2 카드
- **Q1/Q2 독립 이미지**: 각각 별도 이미지 생성

---

# 3. 3편 논문 포트폴리오

## 연구 로직 흐름

```
Paper 1: S5 시스템 신뢰도
    "AI 검증 시스템이 정확한가?"
          ↓
Paper 2: 이미지 신뢰도
    "AI 생성 이미지가 임상적으로 정확한가?"
          ↓
Paper 3: 교육 효과
    "최종 교육자료가 시험에 도움이 되는가?"
```

---

# Paper 1: S5 Multi-agent 신뢰도 연구

| 항목 | 내용 |
|------|------|
| **연구 유형** | 진단 정확도 연구 (Validation) |
| **핵심 질문** | "S5 multi-agent 시스템이 인간 전문가 수준의 품질 검증을 수행할 수 있는가?" |
| **Primary Claim** | "S5-PASS는 안전하다 (FN < 0.3%)" |
| **데이터** | FINAL QA (1,350 전공의 + 330 전문의 평가) |

### 핵심 메트릭
- False Negative Rate (PASS의 안전성): < 0.3% (95% CI)
- Accept-as-is Rate (REGEN의 완전성)
- Pre-S5 → Post-S5 변화율

---

# Paper 2: MLLM 이미지 신뢰도 연구

| 항목 | 내용 |
|------|------|
| **연구 유형** | 기술적 검증 연구 (Technical Validation) |
| **핵심 질문** | "MLLM이 생성한 의료 교육 이미지가 임상적으로 정확하고 교육적으로 유용한가?" |

### Sub-studies

#### 2.1 Visual Modality Sub-study
| 평가자 | Illustration | Realistic |
|--------|--------------|-----------|
| Resident | 1,350개 | 330개 |
| Specialist | 330개 | 330개 |

#### 2.2 Table Infographic Evaluation
- 전체 833개 인포그래픽 중 **100개 (12%)** 샘플링
- 9명 전공의 평가

---

# Paper 3: 교육효과 전향적 연구

| 항목 | 내용 |
|------|------|
| **연구 유형** | 전향적 관찰연구 (Prospective Observational) |
| **대상** | 영상의학과 4년차 전공의 (전문의 시험 응시자) |
| **핵심 질문** | "MeducAI FINAL 산출물이 전문의 시험 대비에 실질적으로 도움이 되는가?" |

### 타임라인
```
1/7 배포          ~6주 사용           2월 시험         시험 후
┌────┐           ┌───────────┐       ┌────────┐      ┌────────┐
│동의서│ ────────▶│ MeducAI  │──────▶│ 전문의 │─────▶│ FINAL  │
│+    │           │ 자율 사용│       │ 시험   │      │ 설문   │
│Base-│           │          │       │        │      │        │
│line │           │          │       │        │      │        │
└────┘           └───────────┘       └────────┘      └────────┘
```

### Primary Outcomes
- Extraneous Cognitive Load (인지 부하)
- Learning Efficiency (학습 효율성)
- Perceived Exam Readiness (시험 준비 자신감)
- Knowledge Retention (지식 유지)

---

# 4. 현재 상태 및 일정

## 연구 규모

- **총 카드**: 6,000개
- **평가자**: 9명 전공의 + 11명 전문의
- **평가량**: 1,680건 (Resident) + 660건 (Specialist)

## 현재 상태

| 논문 | 상태 |
|------|------|
| **Paper 1** | 데이터 수집 준비 완료 |
| **Paper 2 - Visual** | 데이터 수집 준비 완료 |
| **Paper 2 - Table** | 카드 평가와 병행 실행 |
| **Paper 3** | IRB 진행 중, 1/7 배포 예정 |

## 일정

```
1월         2월         3월         4월         5월         6월
├───────────┼───────────┼───────────┼───────────┼───────────┤

Paper 1: QA 완료 → 분석 → 작성 → 투고      → 투고 (3-4월)

Paper 2: QA 완료 → 분석 → 작성 → 투고      → 투고 (4-5월)

Paper 3: 시험(2월) → 설문 → 분석 → 작성 → 투고 → 투고 (5-6월)
```

---

# 5. 발전 가능성 분석

## 1. 연구 설계 차원

### Turing Test 연구 확장 (Paper 2.5)

**현재 상태**: 아직 실행되지 않은 제안된 연구

**발전 가능성**:
```
Paper 2 (이미지 신뢰도) + Paper 2.5 (Turing Test)
    "품질 평가" + "구분 가능성" + "AI Reject/Accept 분석"
```

**권장 설계**: 독립 논문 전략
- **Primary**: "AI 생성 이미지가 실제 이미지와 구분 가능한가?"
- **Secondary**: "AI 평가 시스템의 calibration은 적절한가?"

---

## 2. 통계 분석 차원

### Sample Size 계산 강화

**현재 상태**: 추정치 기반

**발전 가능성**:
- **Pilot Study 선행**: 10-20개 이미지로 실제 구분 난이도 측정
- **Adaptive Design**: 초기 2개 → 정답률 >90%면 4개로 전환

### AI Reject/Accept 분석 프레임워크

```
┌─────────────────────────────────────────────────────────────┐
│              AI Reject/Accept 분석 매트릭스                  │
├───────────────────────┬─────────────────────────────────────┤
│                       │  Turing Test 결과                   │
│  Paper 2 평가 점수    ├──────────────┬──────────────────────┤
│                       │  실제 이미지 │  AI 이미지            │
├───────────────────────┼──────────────┼──────────────────────┤
│  낮은 점수 (1-2점)    │  AI Reject  │  AI Accept (적절)    │
│  (Reject)             │  (False     │  (True Negative)      │
│                       │   Negative) │                       │
├───────────────────────┼──────────────┼──────────────────────┤
│  높은 점수 (4-5점)    │  AI Accept  │  AI Reject (과도)     │
│  (Accept)             │  (True      │  (False Positive)     │
│                       │   Positive) │                       │
└───────────────────────┴──────────────┴──────────────────────┘
```

---

## 3. 언어 정책 차원

### S2 프롬프트 언어 정책 개선

**현재 상태**: 한글 과도 사용 문제

**발전 가능성**:
```
────────────────────────
LANGUAGE POLICY (CRITICAL)
────────────────────────
- **Minimize Korean text usage**: Prefer English for question stems
- **Korean usage is LIMITED to**:
  - Essential medical terminology that is standard in Korean radiology practice
  - Back format labels: "정답:", "근거:", "오답 포인트:"
- **Use English for**:
  - Question stems when possible
  - Explanations and reasoning text
  - General descriptive text
```

---

## 4. 파이프라인 차원

### S3-S4 Code-Protocol 일관성

**현재 문제점**:

| 이슈 | 코드 실제 | 문서 명시 | 필요한 조치 |
|------|-----------|-----------|-----------|
| **M-04** | S3 deterministic inference | "no inference" 금지 | 계약 업데이트 또는 코드 변경 |
| **M-05** | JPG, 2K/4K | PNG, 1K/2K | 프로토콜 또는 코드 일관화 |

---

## 5. 데이터 품질 차원

### AppSheet 시간 계산 이슈 해결 (CRITICAL)

**현재 상태**:
- `post_duration_sec`: 대부분의 행에서 s5 경과시간을 잘못 담고 있음 (98/107개 행)
- `s5_duration_sec`: 전부 비어있음 (계산 로직 누락)

**필수 조치**:
```python
# 안전한 시간 계산 방법
pre_time = (pre_submitted_ts - pre_started_ts).dt.total_seconds()
post_time = (post_submitted_ts - post_started_ts).dt.total_seconds()
s5_time = (s5_submitted_ts - s5_started_ts).dt.total_seconds()
```

---

## 6. 새로운 연구 방향

### Paper 2.5: Turing Test 독립 연구

**권장 구조**:

```
┌─────────────────────────────────────────────────────────────┐
│                  Adaptive Publication Strategy               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Phase 1: 독립 논문으로 Submission                         │
│    Title: "Discriminability Assessment of AI-Generated      │
│           Medical Images: A Turing Test Study with           │
│           AI Reject/Accept Analysis"                       │
│                                                             │
│  Phase 2: 결과에 따른 전략                                 │
│    Case A: Accept → 독립 논문으로 출판 (4-Paper)           │
│    Case B: Reject → Paper 2에 Sub-study 2로 포함 (3-Paper)  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

# 6. 우선순위 및 향후 계획

## 발전 가능성 우선순위

| 우선순위 | 분야 | 구체적 발전 방안 | 시기 |
|---------|------|----------------|------|
| **P0** | **데이터 품질** | AppSheet 시간 계산 이슈 해결 | 즉시 |
| **P1** | **연구 설계** | Turing Test Pilot Study 실행 | 1-2월 |
| **P1** | **연구 설계** | Turing Test 독립 논문 전략 | 1-2월 |
| **P2** | **통계 분석** | Sample Size 계산 강화 | 1-2월 |
| **P2** | **언어 정책** | S2 프롬프트 업그레이드 | 3월 이후 |
| **P3** | **파이프라인** | S3-S4 일관성 해결 | 2-3월 |
| **P3** | **논문 출판** | 3-Paper vs 4-Paper 전략 결정 | 1월 |
| **P4** | **기술적** | 다국어 확장 | 2026 H2 |

---

## 향후 6개월 로드맵

```
1월              2월              3월              4월              5월              6월
├────────────────┼────────────────┼────────────────┼────────────────┼────────────────┼───────────────┤

P0: AppSheet 이슈 해결
P1: Turing Test Pilot Study
P1: 독립 논문 전략 결정
P2: Sample Size 계산

┌────────────────────────────────────────────────────────────────────────────────────────┐
│  Paper 1: QA 완료 → 분석 → 작성 → 투고 (3-4월)                                │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  Paper 2: QA 완료 → 분석 → 작성 → 투고 (4-5월)                                │
│           Turing Test: Pilot → Main Study → 분석 → 작성 (독립 논문)                 │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  Paper 3: 시험(2월) → 설문 → 분석 → 작성 → 투고 (5-6월)                        │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

# 7. 결론

## 핵심 요약

**MeducAI는 현재 3편 논문 기반에서 다음과 같은 발전 가능성이 있습니다:**

1. **연구 설계**: Turing Test 연구 확장 (AI Reject/Accept 분석)
2. **데이터 품질**: AppSheet 시간 계산 이슈 즉시 해결
3. **통계 분석**: Sample size 계산 및 Pilot study 선행
4. **언어 정책**: S2 프롬프트 영어 우선 정책 적용
5. **파이프라인**: Code-Protocol 일관성 강화
6. **논문 출판**: Adaptive Publication Strategy (3-Paper ↔ 4-Paper)

---

## 가장 큰 발전 가능성

**Turing Test 연구**
- AI 생성 이미지의 구분 가능성 평가
- AI 평가 시스템의 calibration 검증
- Paper 1의 FN 검증과 연결

**권장 전략**: 독립 논문으로 먼저 Submission
- Accept 시: 독립 논문으로 출판 (4-Paper 체계)
- Reject 시: Paper 2에 Sub-study 2로 포함 (3-Paper 체계)

---

## 질의응답

<br>
<br>
<br>
**감사합니다!**

<br>
<br>

<div style="font-size: 16px;">
연구팀 문의: [email-redacted]<br>
문서: 0_Protocol/06_QA_and_Study/
</div>
