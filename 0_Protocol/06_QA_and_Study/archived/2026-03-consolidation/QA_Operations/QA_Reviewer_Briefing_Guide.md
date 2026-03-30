# QA 평가자 브리핑 가이드 (공저자용)

**Date:** 2025-12-20  
**Status:** 실행 가이드  
**Purpose:** 공저자 평가자에게 제공할 정보와 주의사항 가이드

---

## 📋 제공 가능한 정보 (블라인딩 준수)

### ✅ 제공해야 할 정보

#### 1. 연구 배경 및 목적 (일반적 정보)

```
MeducAI는 영상의학과 교육을 위한 Anki 카드 자동 생성 시스템입니다.

연구 목적:
- 교육용 콘텐츠의 품질을 평가하여 배포 가능 여부를 결정
- 다양한 생성 설정의 효과를 비교 (S0 단계)
- 대규모 생성 콘텐츠의 안전성을 검증 (S1 단계)

평가 목적:
- 생성된 카드의 의학적 정확성 확인
- 학습자 관점에서의 가독성 및 교육 효과 평가
- 배포 전 최종 품질 검증
```

#### 2. 평가 기준 및 방법론

- **QA Evaluation Rubric v2.0** 제공
- **S0_QA_Survey_Questions.md** 제공
- 평가 항목 설명:
  - Blocking Error (안전성 게이트)
  - Overall Card Quality (Primary Endpoint)
  - Clarity & Readability
  - Clinical/Exam Relevance
  - Editing Time

#### 3. 평가 역할 및 책임

**전문의 (Attending):**
- Safety-critical 판단 권한
- Blocking error 최종 판정
- 임상적 적합성 기준점 역할

**전공의 (Resident):**
- 학습자 관점 평가
- Overall card quality 평가 담당
- Clarity/usability 평가

#### 4. 평가 프로세스

- Set당 약 10분 목표
- 중간 저장 후 이어서 응답 가능
- Google Form을 통한 평가
- PDF 파일 확인 후 평가

---

## ❌ 제공하지 말아야 할 정보 (블라인딩 위반)

### 절대 금지 사항

다음 정보는 **평가 시작 전, 평가 중, 평가 완료 후** 모두 제공하면 안 됩니다:

1. **모델/Provider 정보**
   - ❌ "Gemini 3 Flash를 사용했습니다"
   - ❌ "GPT-5.2를 사용했습니다"
   - ❌ 어떤 LLM 모델을 사용했는지

2. **Arm/설정 정보**
   - ❌ "Arm A는 RAG 없이 생성했습니다"
   - ❌ "Arm E는 고성능 모델입니다"
   - ❌ "6개 arm을 비교합니다"
   - ❌ Thinking/RAG 사용 여부

3. **기술적 세부사항**
   - ❌ Prompt 설계
   - ❌ Generation 전략
   - ❌ Cost/latency 정보
   - ❌ 토큰 수, API 호출 정보

4. **실제 매핑 정보**
   - ❌ "Q01은 실제로 Arm C의 Set입니다"
   - ❌ "이 Set은 group_05입니다"
   - ❌ Surrogate ID와 실제 ID의 매핑

---

## 📝 권장 브리핑 내용

### 이메일/안내문 예시

```
안녕하세요 [평가자 이름]님,

MeducAI S0 QA 평가에 참여해 주셔서 감사합니다.

[연구 배경]
MeducAI는 영상의학과 교육을 위한 Anki 카드 자동 생성 시스템입니다.
본 평가는 생성된 콘텐츠의 품질을 검증하여 배포 가능 여부를 결정하기 위한 것입니다.

[평가 목적]
- 생성된 카드의 의학적 정확성 확인
- 학습자 관점에서의 가독성 및 교육 효과 평가
- 배포 전 최종 품질 검증

[평가 방법]
- 각 평가자에게 12개 Set (Q01~Q12)이 배정됩니다
- 각 Set은 Master Table, Anki 카드 12장, Infographic으로 구성됩니다
- Google Form을 통해 평가하시면 됩니다
- Set당 약 10분을 목표로 하며, 중간 저장 후 이어서 응답 가능합니다

[평가 기준]
- Blocking Error: 임상 판단을 잘못 유도할 수 있는 오류 여부
- Overall Card Quality: Set 전체의 종합적 품질 (1-5점)
- Clarity & Readability: 학습자 관점에서의 명확성
- Clinical/Exam Relevance: 전문의 시험 및 수련 목표 부합성

[중요: 블라인딩 원칙]
본 평가는 **블라인드 평가**로 진행됩니다.
평가는 오직 "콘텐츠 품질"에만 집중하시고, 다음을 추론하거나 고려하지 마세요:
- 어떤 모델을 사용했는지
- 어떤 생성 설정을 사용했는지
- 비용이나 기술적 세부사항

[제공 자료]
- Google Drive 폴더: [개인 폴더 링크]
- Google Form: [Form 링크]
- 평가 가이드: [QA Evaluation Rubric 링크]

[평가 기간]
[시작일] ~ [종료일]

문의사항이 있으시면 연락 주세요.

감사합니다.
MeducAI 연구팀
```

---

## ⚠️ 주의사항

### 1. 블라인딩 위반 시 대응

만약 평가자가 다음을 보고한 경우:
- "이건 GPT가 만든 것 같아요"
- "Arm C인 것 같습니다"
- "RAG를 사용한 것 같네요"

**대응:**
- 해당 평가를 즉시 flag
- 필요 시 해당 리뷰 제외 또는 재배정
- QA audit log에 기록

### 2. 공저자 특수 상황

공저자이므로 연구 전체 맥락을 이해하고 있을 수 있습니다. 하지만:

✅ **가능한 설명:**
- 연구 목적과 배경 (일반적)
- 평가의 중요성
- 논문에서의 역할

❌ **금지된 설명:**
- 구체적인 모델/arm 정보
- 기술적 세부사항
- 비교 대상 정보

### 3. 평가 완료 후

평가 완료 후에도 즉시 unblinding하지 않습니다.

**Unblinding 조건:**
- 모든 QA scoring 완료
- 데이터 lock
- IRR 분석 완료

이후 통계 분석 및 논문 작성 목적으로만 unblinding합니다.

---

## 📚 참고 문서

평가자에게 제공할 문서:
- `QA_Evaluation_Rubric.md` - 평가 기준표
- `S0_QA_Survey_Questions.md` - 설문 문항 설명
- `Google_Form_Creation_Guide.md` - Form 사용법 (필요시)

평가자에게 제공하지 말 문서:
- `QA_Blinding_Procedure.md` - 운영자 전용
- `QA_Assignment_Plan.md` - 운영자 전용
- `assignment_map.csv` - 운영자 전용
- `surrogate_map.csv` - 운영자 전용

---

## ✅ 체크리스트

평가자 브리핑 시 확인:

- [ ] 연구 배경 및 목적 설명 (일반적 정보)
- [ ] 평가 기준 및 방법론 설명
- [ ] 평가 역할 및 책임 설명
- [ ] 블라인딩 원칙 강조
- [ ] 금지 사항 명확히 안내
- [ ] 평가 가이드 문서 제공
- [ ] Google Form 및 Drive 링크 제공
- [ ] 평가 기간 및 일정 안내
- [ ] 문의 연락처 제공

---

**Last Updated:** 2025-12-20

