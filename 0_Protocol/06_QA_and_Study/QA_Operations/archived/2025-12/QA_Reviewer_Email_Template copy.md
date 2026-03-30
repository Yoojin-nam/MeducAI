[MeducAI] S0 QA 평가 자료 배포 및 평가 요청 - [이름] 선생님께


안녕하세요 [       ] 선생님,

바쁘신 일정 중에도 MeducAI S0 QA 평가에 도움을 주시기로 해주셔서 진심으로 감사드립니다.
본 메일은 **선생님께 배정된 S0 QA 평가 자료(PDF)와 설문 링크 그리고 Kick off meeting 일정**을 전달드리기 위한 안내입니다.

* 이번 S0 평가는 **최종 배포 모델 선정의 핵심 근거**가 됩니다.
* 선생님의 **[전문 분야/교육 경험/이전 도움]**을 고려할 때, **임상적 적합성/시험 적합성** 평가에 중요한 기준점이 될 것으로 기대합니다.
* 지난 [미팅/이전 검토/자문]에서 주신 피드백 덕분에 QA 구조를 안정적으로 설계할 수 있었습니다. 다시 한번 감사드립니다.

**주요 링크**

* 영상 통화 링크(Google Meet): [https://meet.google.com/fkp-eskz-twp](https://meet.google.com/fkp-eskz-twp)
* Google Form: [https://forms.gle/MjPjbh11TeezyMTs7](https://forms.gle/MjPjbh11TeezyMTs7)
* [Google Drive 백업]()

---

## Kick-off meeting 안내(중요)

Doodle 투표 결과를 반영하여 Kick-off meeting 시간을 아래와 같이 확정하였습니다.
미팅에 참석이 어려우시더라도, 메일로 연구 방향에 대해 한마디 조언 주시면 큰 도움이 됩니다.

* 일시(한국시간, KST): **2025-12-23(화) 20:00–21:00**
* 영상 통화 링크(Google Meet): [https://meet.google.com/fkp-eskz-twp](https://meet.google.com/fkp-eskz-twp)

---

## 참여 관련 안내(중요)

본 평가는 공저자 참여를 전제로 안내드리지만, **참여 여부 및 공저자 참여 지속 여부는 전적으로 선생님 판단**에 따릅니다.
아래 상황 모두 전혀 부담 갖지 않으셔도 되며, 편하게 회신 주시면 연구팀에서 즉시 조정하겠습니다.

1. **연구 목적/품질이 기대와 다르다고 판단되시는 경우** : S0 결과 또는 자료를 보신 뒤 연구 방향이나 품질 수준이 다르다고 판단되시면 **공저자 참여를 중단/철회하셔도 괜찮습니다.**

2. **이번 S0 QA를 기한 내 완료하기 어려우신 경우** : 일정상 어려우시면 **가능한 한 빨리 알려주시면** 연구팀에서 **대체 평가자 확보 및 배정 조정**을 진행하겠습니다.

---

## 개인별 안내(중요)

* 선생님께 배정된 평가 분량: **총 12개 Set**
* 본 메일 첨부: **개인 전용 ZIP 1개** (내부: **Q01.pdf ~ Q12.pdf**)
* Google Drive 백업(재다운로드용)

중요: 이번 평가는 **개인별로 배정된 PDF 구성이 서로 다릅니다.**
블라인딩 및 배정 무결성 유지를 위해 **타 평가자와 PDF/ZIP 공유(전달·재업로드 포함)는 삼가** 부탁드립니다.

---

## 1) 연구 배경 및 S0 QA 목적(요약)

MeducAI는 영상의학과 교육을 위한 **Anki 카드 자동 생성 시스템**입니다.
본 S0 QA는 **6개 Arm(A–F)**을 비교하여 **최종 배포 모델을 선정**하기 위한 단계입니다.

* 각 Arm은 **S1→S2→S3→S4** 파이프라인으로 콘텐츠를 생성합니다.
* S0에서는 **고정 payload(각 Set당 12 cards)**로 Arm 간 공정한 비교를 수행합니다.
* 본 평가는 **배포 전 최종 품질 검증(안전성/정확성/가독성/교육목표 부합성)**을 목표로 합니다.

또한 본 연구는 두 개의 독립 Pipeline으로 구성됩니다.

* **Pipeline-1 (Paper-1):** Expert QA 기반 모델 선택 및 배포 승인
* **Pipeline-2 (Paper-2):** 실제 사용자 연구(별도 진행)
  이번에 배포드리는 자료는 **Pipeline-1의 S0 단계 평가 자료**입니다.

---

## 2) S0 QA 구조(이번 배포 범위)

* 총 **108 sets** (18 groups × 6 arms)
* 각 Set 구성: **Master Table + Anki 카드 12장 + Infographic(해당 시)**
* 분석 단위: **Set-level evaluation**

의사결정 프레임워크(2-layer):

* **Safety Gate(Primary):** Blocking error rate ≤ 1%
* **Secondary:** Overall Card Quality (Non-inferiority 분석)

---

## 3) 평가자 역할(선생님 역할: [Attending / Resident])

본 S0 QA는 Set당 **2인 교차평가(Resident 1명 + Attending 1명)**로 진행됩니다.

* **Attending:** Blocking error 최종 판정, 임상/시험 적합성 기준점
* **Resident:** 가독성·명확성 등 사용자 관점(Usability) 평가

---

## 4) 배포 파일 구성(첨부 + Drive)

첨부 및 Drive의 각 PDF는 **Set 1개**이며, 구성 순서는 다음과 같습니다.

1. Master Table → 2) Anki 카드 12장 → 3) Infographic(해당 시)

---

## 5) 평가 방법(설문)

* Google Form: [https://forms.gle/MjPjbh11TeezyMTs7](https://forms.gle/MjPjbh11TeezyMTs7)
* **중요: 설문 응답을 “중간에 멈추어도 저장/재개”할 수 있도록, Gmail(구글) 계정 로그인이 필수입니다.**
* 권장: 설문에서 제시되는 문항번호와 같은 **PDF 파일(Q01~Q12)**을 보고 평가해주세요(집계 및 매핑 정확도 향상).

각 Set에 대해 아래 항목을 평가해 주세요.

1. **Blocking Error 여부(필수)**: 임상 판단을 잘못 유도할 수 있는 오류 여부(Yes/No)
2. **Overall Card Quality(필수)**: Set 전체 종합 품질(1–5점)
3. **Table/Infographic Critical Error(필수)**: 치명 오류 여부(Yes/No)
4. **Scope Failure(해당 시)**: 교육 목표와의 불일치 여부
5. **Editing Time(필수)**: 배포 가능 수준으로 만드는 데 필요한 편집 시간
6. **Clarity & Readability(필수)**: 학습자 관점의 명확성
7. **Clinical/Exam Relevance(필수)**: 시험/수련 목표 부합성

---

## 6) 블라인딩 원칙(중요)

본 평가는 **블라인드 평가**로 진행됩니다. 아래 사항은 **추론하거나 고려하지 말아 주세요**.

* 어떤 모델/arm인지, 생성 설정(thinking/RAG 등)
* 비용 및 기술적 세부사항

평가는 오직 **콘텐츠 품질(정확성, 안전성, 가독성, 교육목표 부합성)**에만 집중 부탁드립니다.

---

## 7) 평가 기간

* 평가 시작: **2025-12-22(월)**
* 평가 마감: **2025-12-28(일)**
* 예상 소요: Set당 **약 5–10분**, 총 **약 1시간 내외**

---

## 문의

평가 중 기술적 문제(Drive 접근/파일 손상/설문 오류) 또는 내용 관련 문의가 있으시면 언제든지 연락 부탁드립니다.

* 이메일: [[email-redacted]](mailto:[email-redacted])
* 전화: [phone-redacted] (평일 07:00–23:00)

선생님께서 남겨주실 평가는 S0 단계의 **Safety Gate 및 모델 선택(Non-inferiority 판단)**에 직접 반영되며,
향후 배포 승인 및 논문 Methods/Results 정리에도 중요한 근거로 활용될 예정입니다.
바쁘신 가운데 시간을 내어주셔서 다시 한번 감사드립니다.

감사합니다.

[Study Coordinator] 올림
삼성창원병원 영상의학과