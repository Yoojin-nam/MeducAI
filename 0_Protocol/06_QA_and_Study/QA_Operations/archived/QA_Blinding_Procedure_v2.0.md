---

# QA Blinding Procedure – MeducAI (v2.0, Canonical)

**Aligned with:**

* QA Framework v2.0
* QA Evaluation Rubric v2.0

**Date:** 2025-12-15
**Status:** Archived (applies prospectively to S0 & S1)
**Superseded by:** `0_Protocol/06_QA_and_Study/QA_Operations/QA_Blinding_Procedure.md`
**Do not use this file for new decisions or execution.**

---

## 0. Purpose

본 문서는 **MeducAI Pipeline-1 QA(Step S0, Step S1)**에서
평가자의 **모델·arm·프롬프트·RAG 여부에 대한 추론을 원천 차단**하기 위한
**공식 Blinding 절차**를 정의한다.

본 절차의 목적은 다음과 같다.

* 평가 편향(bias) 최소화
* Arm 간 비교의 내적 타당성 확보 (S0)
* Release gate 판정의 신뢰성 확보 (S1)
* IRB 및 논문 심사에서의 **방법론적 방어 가능성 확보**

---

## 1. Scope & Blinding Level

### 1.1 Step S0 (Model Selection QA)

* **Blinding 대상**

  * Model / Provider
  * Arm ID
  * Thinking / RAG 여부
  * Prompt 전략
  * Cost / latency 정보
* **Blinding 강도**

  * **Full rater blinding**
  * 단, 운영자(QA manager)는 매핑 정보에 접근 가능

### 1.2 Step S1 (Release Gate QA)

* **Blinding 대상**

  * 생성 모델
  * 생성 시점
  * 그룹 weight
  * generation 설정
* **Blinding 강도**

  * **Full rater blinding**
  * S1에서는 arm 개념 자체가 노출되지 않음

---

## 2. Blinding Principles (Canonical)

1. **Content-only evaluation**

   * 평가는 오직 “콘텐츠 품질”에 근거한다.
2. **No provenance cues**

   * 생성 출처를 유추할 수 있는 모든 단서는 제거한다.
3. **Late unblinding**

   * 분석·보고 목적 외의 조기 unblinding 금지.

---

## 3. Metadata Stripping (Mandatory)

QA 배포 전, 모든 artifact는 아래 정보를 **완전히 제거**한다.

### 3.1 반드시 제거할 항목

* 모델명, provider명
* arm ID
* prompt 문구 및 system message 흔적
* generation timestamp, run tag
* 토큰 수, latency, cost
* 파일명에 포함된 generation 정보

### 3.2 허용되는 정보 (Minimum)

* 순수 교육 콘텐츠
* 구조적 포맷 (table, bullet, card layout)
* **Generic learning objective reference**

  * group_id는 **비식별화된 surrogate ID**로 대체

---

## 4. Grounding / Retrieval Neutrality (v2.0 NEW)

QA Framework v2.0에서는
**RAG_MODE = QA_ONLY** 설정이 허용된다.

이에 따라 다음 원칙을 고정한다.

* QA fact-checking 중 사용된:

  * URL
  * 검색 결과 제목
  * retrieval source metadata
    는 **평가자에게 절대 노출되지 않는다**.
* Retrieval evidence는:

  * QA audit metadata로 별도 저장
  * arm/모델 식별 정보로 사용되지 않음
  * S0/S1 분석 단계에서만 참조 가능

> **RAG 사용 여부는 평가 대상이 아니라 통제 변수**이며,
> blinding packet에는 어떤 형태로도 노출되어서는 안 된다.

---

## 5. Packaging for QA Distribution

QA 배포용 패키지는 다음 규칙을 따른다.

* **Tables / Cards**

  * Plain text, PDF, 또는 통일된 web form
* **Infographics**

  * Static image only
* **Formatting**

  * 모든 artifact는 **동일한 레이아웃**
  * 시각적 차이로 출처를 유추할 수 없도록 통일
* **File naming**

  * 무작위 surrogate ID 사용
  * generation 관련 문자열 포함 금지

---

## 6. Assignment & Mapping Control

* Artifact ID ↔ Reviewer 매핑은

  * 사전 정의된 assignment plan에 따라 수행
* 매핑 파일은:

  * QA 운영자만 접근 가능
  * reviewers에게 절대 공유되지 않음
* Reviewer에게 제공되는 자료는 다음으로 제한:

  * blinded artifacts
  * QA Evaluation Rubric v2.0
  * scoring form

---

## 7. Blinding Integrity Checks

Blinding 무결성을 보장하기 위해:

1. **사전 점검**

   * 최소 1인의 독립 운영자가
     metadata stripping 완료 여부 확인
2. **무작위 스팟 체크**

   * 배포 직전 random artifact 검사
3. **로그 기록**

   * 모든 점검 결과를 QA audit log에 기록

---

## 8. Handling of Blinding Breaches

다음 상황은 **blinding breach**로 간주한다.

* Reviewer가 모델/arm을 추론했다고 보고한 경우
* 운영 중 노출된 식별 단서가 발견된 경우

### 대응 절차

* 해당 artifact 즉시 flag
* 필요 시:

  * 해당 리뷰 제외
  * 새로운 reviewer로 재배정
* 모든 사건은 QA audit log에 기록

---

## 9. Post-QA Unblinding Policy

Unblinding은 **아래 조건을 모두 만족한 이후에만 허용**된다.

* 모든 QA scoring 완료
* 데이터 lock
* IRR 분석 완료

Unblinding 목적은 다음으로 제한된다.

* 통계 분석
* 결과 보고
* 논문 작성

---

## 10. Relationship to Other QA Documents (Updated)

본 문서는 다음 Canonical 문서들과 함께 작동한다.

* `QA_Framework_v2.0.md`
* `QA_Evaluation_Rubric_v2.0.md`
* `S0_S1_Completion_Checklist_and_Final_Freeze_v2.0.md`
* `QA_Assignment_Plan.md`

이들 문서는 **단일 QA 거버넌스 세트**를 구성한다.

---

## 11. Version Control & Freeze Policy

* 본 문서는 **QA Blinding Procedure v2.0 (Canonical)**이다.
* S0/S1 실행 중 수정 불가.
* 변경이 필요한 경우:

  * v2.1로 상향
  * 변경 사유 명시
  * **QA 시작 이전에만 적용 가능**

---

## Official Statement

> This blinding procedure ensures that MeducAI expert QA (S0/S1) is conducted under strict content-only evaluation, preventing rater bias from model provenance, retrieval strategies, or system configurations, and thereby supporting defensible deployment and release decisions.

---
