# 4_Instruments

Status: Working
Purpose: Study instruments, operational templates, and measurement documentation for MeducAI S0/S1 QA and subsequent study phases.

## 1. What belongs here

`4_Instruments`는 “연구에서 측정(measurement)과 운영(operation)을 표준화하기 위한 도구 모음”이다.
코드(3_Code)나 실행 산출물(2_Data/metadata/generated), 배포 패키지(6_Distributions)와 달리, 여기의 파일들은 다음을 목표로 한다.

* 동일한 절차를 반복 가능하게 한다(재현성).
* QA/설문/채점 입력을 표준화한다(데이터 품질).
* IRB 및 감사(Audit) 상황에서 “문항/변수/운영 변경 이력”을 설명 가능하게 한다(추적성).

## 2. Folder map

### 2.1 Logs_and_Metadata/

운영 문서(메타데이터)와 변경 이력을 관리한다. 분석자/PI가 가장 먼저 확인해야 하는 문서들이 포함된다.

* `Data_Dictionary.md`
  설문/로그/평가 데이터의 변수 정의서.
  분석(SAP)과 결과 해석의 기준이 되는 “변수 사전” 역할.

* `Survey_Change_Log.md`
  설문/평가 문항 변경 이력(버전, 변경 이유, 적용 시점).
  IRB/Methods 작성 시 “사후 변경” 논쟁을 방지하는 문서.

* `Survey_Timeline.md`
  배포/수집/마감 등 설문 운영 타임라인 기록.
  실제 수집 기간과 버전 적용 시점을 나중에 재구성할 수 있게 한다.

### 2.2 Post_Exam_Survey/

설문 문항 및 운영 설계를 보관한다(“무엇을 어떻게 물었는가”).

* `Post_Exam_Survey_v1.0.md`
  설문 문항 본문(최종 문항 세트). 실제 배포본의 기준 문서.

* `Scale_Mapping_Table.md`
  리커트/척도 매핑 규칙(점수 방향, 역문항 여부 등).
  분석 시 점수화 오류를 방지한다.

* `Survey_Administration_Plan.md`
  설문 배포·회수·리마인더·익명화 등 운영 계획.
  (누가, 언제, 어떤 채널로, 어떤 안내문으로 수행했는지)

* `Survey_Overview.md`
  설문의 목적, 구성, 수집 항목, 주요 endpoint 요약(1–2페이지).

### 2.3 templates/

현장 운영 시 “직접 입력하는 표준 양식”이다.
원본 템플릿은 수정하지 않고, 실행(run) 또는 배포 시에는 복사본을 생성하여 사용한다.

* `S0_score_sheet_v2.0_template.csv`
  S0 QA 채점표 템플릿.

* `S1_score_sheet_v2.0_template.csv`
  S1 QA 채점표 템플릿.

* `S1_adjudication_log_v2.0_template.csv`
  S1 불일치/조정(adjudication) 기록 템플릿.

## 3. Rules of use

1. 템플릿은 “원본 보존”이 원칙이다.

* `templates/`의 파일은 직접 채우지 않는다.
* 실제 사용 시에는 `6_Distributions/` 또는 `1_Secure_Participant_Info/QA Raw/`에 “복사본”을 만들어 사용한다.

2. 문항/척도 변경이 발생하면 반드시 로그를 남긴다.

* 설문 문항이나 점수화 규칙이 바뀌면 `Logs_and_Metadata/Survey_Change_Log.md`에 기록한다.

3. 이 폴더의 문서는 코드 실행에 의존하지 않는다.

* 파이프라인이 동작하지 않아도, 연구 운영과 해석 기준은 여기 문서만으로 설명 가능해야 한다.

## 4. Common workflows

* “분석을 시작한다”
  → `Data_Dictionary.md` + `Scale_Mapping_Table.md` 확인 후 분석 코드 작성

* “설문을 배포한다”
  → `Survey_Administration_Plan.md` 확인 후 배포, 변경 사항은 `Survey_Change_Log.md`에 기록

* “채점/조정을 진행한다”
  → `templates/`에서 복사본 생성 후 사용, 원본 템플릿은 유지

## 5. Non-goals

다음은 `4_Instruments`에 두지 않는다.

* 개인식별정보(PII) 및 키 매핑: `1_Secure_Participant_Info/`
* 실행 산출물(RUN_TAG 결과, generated): `2_Data/metadata/generated/`
* 배포 패키지(apkg, pdf, slides): `6_Distributions/`
* Canonical 정책/계약 문서: `0_Protocol/`