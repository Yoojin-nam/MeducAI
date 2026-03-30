# S1 QA 통계적 설계 - 통계학자 자문 요약

**목적**: FINAL 생성 6000문항에 대한 blocking error rate < 1% 통계적 보장

---

## 1. 연구 설계 개요

### 1.1 목표
- **모집단**: FINAL 생성 전체 Anki 카드 (N ≈ 6,000장)
- **목표**: 모집단의 **blocking error rate < 1%**임을 통계적으로 보장
- **통계적 보장 수준**: **one-sided 99% confidence**

### 1.2 Blocking Error 정의
- **Blocking error**: Accuracy = 0.0 (치명적 오류 또는 오개념 유발 가능)
- **판정 기준**: 전문의 최종 판정 (전공의 2인 독립 평가 후 불일치/blocking 발생 시)

---

## 2. 샘플링 설계

### 2.1 샘플 크기
- **n = 838 cards** (고정)

### 2.2 샘플링 방법
- **방식**: **PPS (Probability Proportional to Size) + 층화 샘플링**
  - 그룹 weight(또는 그룹별 카드 수)에 비례하여 추출
  - subspecialty / modality / tail group 최소 커버 하드 제약 유지
- **One-shot sampling**: 중간 배치 없이 단일 샘플로 종료

### 2.3 평가 구조
- **Primary Review**: 전공의 2인 독립 평가 (모든 838개)
- **IRR Anchor**: 300개 카드에 대해 전공의 2 + 전문의 1 (3인 교차평가)
- **Adjudication**: 전공의 간 불일치 또는 blocking 발생 시 전문의 최종 판정

---

## 3. Acceptance Sampling 규칙

### 3.1 Acceptance Criterion (고정)
- **n = 838, c = 2**
- **PASS**: 샘플에서 blocking error **≤ 2건**
- **FAIL**: 샘플에서 blocking error **≥ 3건**

### 3.2 통계 방법
- **Method**: **Clopper–Pearson upper bound** (Acceptance sampling)
- **해석**: PASS 시, 모집단 blocking error rate < 1%를 **one-sided 99% confidence**로 보장

---

## 4. 자문 요청 사항

### 4.1 샘플 크기 및 Acceptance Criterion 적정성
- **질문**: n=838, c=2 기준이 모집단 N=6000에서 blocking error rate < 1%를 one-sided 99% CI로 보장하기에 적절한가?
- **특히 확인 필요**:
  - PPS + 층화 샘플링이 단순 무작위 추출 가정과 다를 경우의 영향
  - Finite population correction 필요 여부

### 4.2 통계 방법 적절성
- **질문**: Clopper–Pearson upper bound가 이 맥락에 적절한가?
- **대안 검토**: 다른 acceptance sampling 방법론 고려 필요 여부

### 4.3 층화 샘플링 고려사항
- **질문**: PPS + 층화 샘플링 구조에서 통계적 추론 시 추가 고려사항이 있는가?
- **확인 필요**: 층화 가중치 적용, 층 간 차이 분석 필요 여부

### 4.4 평가자 간 신뢰도 (IRR) 해석
- **질문**: 전공의 2인 독립 평가 후 전문의 adjudication 구조에서 blocking error 판정의 신뢰도는 어떻게 해석해야 하는가?
- **확인 필요**: IRR anchor (m=300)에서 산출한 Fleiss' κ가 전체 평가의 신뢰도를 대표하는가?

---

## 5. 예상 결과 시나리오

### 시나리오 A: PASS
```
관찰된 blocking error: 0, 1, 또는 2건
결과: PASS
해석: 모집단 blocking error rate < 1%를 99% 신뢰로 보장
→ 배포 승인
```

### 시나리오 B: FAIL
```
관찰된 blocking error: 3건 이상
결과: FAIL
해석: blocking error rate ≥ 1%일 가능성이 높음
→ 배포 승인 보류, 수정 후 재검토
```

---

## 6. 참고 정보

- **관련 문서**: `0_Protocol/06_QA_and_Study/QA_Framework.md` (Section 3)
- **통계 분석 계획**: `0_Protocol/06_QA_and_Study/Study_Design/Statistical_Analysis_Plan.md`
- **목적**: 교육용 AI 생성 콘텐츠의 안전성 검증 (IRB 승인 연구)

---

**작성일**: 2025-12-20  
**작성자**: MeducAI 연구팀  
**목적**: 통계학자 자문 요청

