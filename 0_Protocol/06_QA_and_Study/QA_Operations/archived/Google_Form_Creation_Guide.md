# Google Form 생성 가이드 (S0 QA)

**Date:** 2025-12-20  
**Purpose:** MeducAI S0 QA 평가를 위한 Google Form 수동 생성 가이드

---

## 방법 1: Google Apps Script 사용 (권장)

### 1.1 준비

1. Google Drive 접속
2. 새 Google 스프레드시트 생성 (이름: "MeducAI_QA_Form_Creator")
3. **확장 프로그램** > **Apps Script** 클릭

### 1.2 스크립트 실행

1. `3_Code/Scripts/create_google_form_qa.js` 파일의 내용을 복사
2. Apps Script 편집기에 붙여넣기
3. 상단 메뉴에서 `createQAForm` 함수 선택
4. **실행** 버튼 클릭
5. 권한 승인 (처음 실행 시)
6. 로그에서 Form URL 확인

### 1.3 생성된 Form 확인

- Form URL: 로그에 출력된 URL로 접속
- Form 편집 URL: 필요시 수정 가능

---

## 방법 2: 수동 생성 (상세 가이드)

### 2.1 기본 설정

1. **Google Forms 접속**: https://forms.google.com
2. **새 양식 만들기**
3. **제목**: "MeducAI S0 QA 평가 설문"
4. **설명**: "MeducAI S0 QA 평가를 위한 설문입니다. 각 Set(Q01~Q12)에 대해 평가해주세요."

### 2.2 Form 설정

**설정 아이콘 (톱니바퀴) 클릭:**

- ✅ **이메일 주소 수집**: 켜기
- ✅ **1인당 1회만 응답**: 켜기
- ✅ **응답 수정 허용**: 켜기 (중간 저장 후 이어서 응답)
- ❌ **응답 후 링크 표시**: 끄기

### 2.3 Section 1: 평가자 정보

1. **페이지 구분 추가** (오른쪽 메뉴)
   - 제목: "Section 1: 평가자 정보"
   - 설명: "평가자 정보를 입력해주세요."

2. **객관식 질문 추가**
   - 질문: "평가자 구분"
   - 필수: ✅
   - 옵션:
     - 전문의 (Attending)
     - 전공의 (Resident)
   - 도움말: "평가자 역할을 선택해주세요."

> **참고**: 이메일은 자동으로 수집되므로 별도 입력 항목 불필요

---

### 2.4 Section 2~13: Q01~Q12 평가 섹션

각 Q (Q01~Q12)마다 동일한 구조로 섹션을 생성합니다.

#### 예시: Q01 섹션 생성

1. **페이지 구분 추가**
   - 제목: "Section 2: Q01 평가"
   - 설명: "Q01 Set에 대한 평가입니다. PDF 파일을 확인한 후 평가해주세요."

#### Part B: 카드 평가 (Primary Endpoint)

2. **B1. Blocking Error (객관식)**
   - 질문: "[Q01] B1. Blocking Error"
   - 필수: ✅
   - 옵션:
     - No (blocking error 없음)
     - Yes (blocking error 있음)
   - 도움말: "Blocking Error란: 임상 판단 또는 시험 정답을 직접적으로 잘못 유도할 가능성이 큰 오류입니다."

3. **B1-1. Blocking Error 설명 (단락 텍스트)**
   - 질문: "[Q01] B1-1. Blocking Error 설명 (Yes 선택 시 필수)"
   - 필수: ❌ (조건부 필수는 Google Form에서 직접 구현 불가, 안내 문구로 대체)
   - 도움말: "Blocking Error가 있는 경우, 구체적인 설명을 1줄 이내로 입력해주세요."

4. **B2. Overall Card Quality (척도)**
   - 질문: "[Q01] B2. Overall Card Quality (필수, Primary Endpoint)"
   - 필수: ✅
   - 척도: 1~5
   - 왼쪽 레이블: "매우 나쁨"
   - 오른쪽 레이블: "매우 좋음"
   - 도움말: "이 Set의 카드 전반적 품질을 평가하세요. 정확성, 가독성, 교육 목표 부합성을 종합적으로 고려합니다. (1=매우 나쁨, 5=매우 좋음)"

5. **B3. Evidence Comment (단락 텍스트)**
   - 질문: "[Q01] B3. Evidence Comment (조건부)"
   - 필수: ❌
   - 도움말: "B1=Yes 또는 B2≤2인 경우에만 작성해주세요. 문제가 있는 카드에 대한 구체적 근거를 1-2줄 이내로 입력하세요."

#### Part C: 테이블 및 인포그래픽 안전성 게이트

6. **C1. Critical Error (객관식)**
   - 질문: "[Q01] C1. Critical Error (테이블/인포그래픽)"
   - 필수: ✅
   - 옵션:
     - No (치명 오류 없음)
     - Yes (치명 오류 있음)
   - 도움말: "테이블 또는 인포그래픽에 치명 오류가 있는지 평가하세요."

7. **C1-1. Critical Error 설명 (단락 텍스트)**
   - 질문: "[Q01] C1-1. Critical Error 설명 (Yes 선택 시 필수)"
   - 필수: ❌
   - 도움말: "Critical Error가 있는 경우, 구체적인 설명을 1줄 이내로 입력해주세요."

8. **C2. Scope Failure (객관식)**
   - 질문: "[Q01] C2. Scope Failure (테이블/인포그래픽)"
   - 필수: ✅
   - 옵션:
     - No (불일치 없음)
     - Yes (불일치 있음)
   - 도움말: "테이블 또는 인포그래픽이 Group Path/objectives와 명백히 불일치하는지 평가하세요."

9. **C2-1. Scope Failure 설명 (단락 텍스트)**
   - 질문: "[Q01] C2-1. Scope Failure 설명 (Yes 선택 시 필수)"
   - 필수: ❌
   - 도움말: "Scope Failure가 있는 경우, 구체적인 설명을 1줄 이내로 입력해주세요."

#### Part D: 보조 평가 항목 (Secondary Outcomes)

10. **D1. Clarity & Readability (척도)**
    - 질문: "[Q01] D1. Clarity & Readability (선택)"
    - 필수: ❌
    - 척도: 1~5
    - 왼쪽 레이블: "혼란·오해 가능성 높음"
    - 오른쪽 레이블: "매우 명확, 학습 친화적"
    - 도움말: "이 Set의 카드가 학습자 관점에서 얼마나 명확하고 읽기 쉬운가? (1=혼란, 5=매우 명확)"

11. **D2. Clinical/Exam Relevance (척도)**
    - 질문: "[Q01] D2. Clinical/Exam Relevance (선택)"
    - 필수: ❌
    - 척도: 1~5
    - 왼쪽 레이블: "시험과 거의 무관"
    - 오른쪽 레이블: "핵심 고빈도 시험 주제"
    - 도움말: "이 Set의 카드가 영상의학과 전문의 시험 및 수련 목표에 얼마나 부합하는가? (1=무관, 5=핵심 주제)"

12. **D3. Editing Time (단답형 텍스트)**
    - 질문: "[Q01] D3. Editing Time (필수, 분 단위)"
    - 필수: ✅
    - 도움말: "이 Set을 '배포 가능한 수준'으로 만드는 데 필요한 편집 시간을 분 단위로 입력하세요. (예: 0, 1, 2.5, 3, 5, 10)"

#### Part E: 평가 시간 (선택)

13. **E. 실제 평가 시간 (객관식)**
    - 질문: "[Q01] E. 실제 평가 시간 (선택)"
    - 필수: ❌
    - 옵션:
      - 5분 미만
      - 5-7분
      - 7-10분
      - 10분 초과
    - 도움말: "본 Set 평가에 실제로 소요된 시간을 선택해주세요. (운영 검증용)"

14. **자유 의견 (단락 텍스트)**
    - 질문: "[Q01] 자유 의견 (선택)"
    - 필수: ❌
    - 도움말: "추가 의견이나 제안사항이 있으시면 입력해주세요."

---

### 2.5 Q02~Q12 반복

위의 Q01 섹션 구조를 Q02~Q12까지 반복합니다.

**팁**: 
- Q01 섹션을 복사하여 Q02~Q12로 수정하는 것이 빠릅니다.
- 질문 제목의 "[Q01]" 부분만 "[Q02]", "[Q03]", ... "[Q12]"로 변경하면 됩니다.

---

### 2.6 완료 메시지 설정

1. **설정 아이콘** 클릭
2. **표시** 탭
3. **커스텀 확인 메시지**: "평가에 참여해주셔서 감사합니다!"

---

## 방법 3: Python 스크립트 사용 (고급)

Google Forms API는 제한적이지만, Google Apps Script를 Python에서 호출하거나, 직접 HTML/JavaScript로 폼을 만들 수 있습니다.

> **참고**: Google Forms API는 공식적으로 제공되지 않으므로, 방법 1 (Google Apps Script)을 권장합니다.

---

## 체크리스트

### 생성 후 확인 사항

- [ ] Section 1: 평가자 정보 섹션 생성됨
- [ ] Section 2~13: Q01~Q12 평가 섹션 모두 생성됨 (총 12개)
- [ ] 각 Q 섹션에 필수 문항 포함:
  - [ ] B1. Blocking Error (객관식, 필수)
  - [ ] B2. Overall Card Quality (척도 1-5, 필수)
  - [ ] C1. Critical Error (객관식, 필수)
  - [ ] C2. Scope Failure (객관식, 필수)
  - [ ] D3. Editing Time (텍스트, 필수)
- [ ] Form 설정 확인:
  - [ ] 이메일 수집 활성화
  - [ ] 1인당 1회 응답 제한 활성화
  - [ ] 응답 수정 허용 활성화
- [ ] Form URL 확인 및 저장
- [ ] 테스트 응답 제출하여 동작 확인

---

## 데이터 수집 및 분석

### 응답 다운로드

1. Form 편집 화면에서 **응답** 탭 클릭
2. **스프레드시트에 연결** 또는 **다운로드** (CSV)

### 데이터 결합

Google Form 응답 CSV와 `assignment_map.csv`를 결합하여 분석합니다.

**Join key:**
- `reviewer_email` (Form 응답) + `reviewer_email` (assignment_map)
- `section` (Q01~Q12) + `local_qid` (assignment_map)

---

## 참고 문서

- `Google_Form_Design_Specification.md`
- `S0_QA_Survey_Questions.md`
- `QA_Framework.md`
- `QA_Evaluation_Rubric.md`

---

## 문제 해결

### Q: Google Apps Script 실행 시 권한 오류가 발생합니다.
A: 처음 실행 시 Google 계정 권한 승인이 필요합니다. "고급" > "안전하지 않은 페이지로 이동"을 클릭하여 승인하세요.

### Q: Form이 생성되지 않습니다.
A: Apps Script 로그를 확인하세요. **보기** > **로그** 메뉴에서 오류 메시지를 확인할 수 있습니다.

### Q: 조건부 필수 항목을 설정할 수 없습니다.
A: Google Form은 조건부 필수를 직접 지원하지 않습니다. 도움말 텍스트에 조건을 명시하고, 데이터 분석 단계에서 검증하세요.

### Q: Form 응답을 실시간으로 확인하고 싶습니다.
A: Form 편집 화면에서 **응답** 탭을 클릭하면 실시간으로 응답을 확인할 수 있습니다. 또는 **스프레드시트에 연결**하여 자동으로 응답이 저장되도록 설정할 수 있습니다.

---

**Last Updated:** 2025-12-20

