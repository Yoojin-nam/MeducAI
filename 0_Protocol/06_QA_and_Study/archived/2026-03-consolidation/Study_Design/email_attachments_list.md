# 박선영 교수님께 보낼 메일 첨부 파일 목록

**작성일:** 2025-12-20  
**목적:** 통계 분석 설계 검토를 위한 자료 정리

---

## 첨부 파일 구성

### 1. 필수 첨부 파일 (Core Documents)

#### 1.1 연구 설계 문서
- [ ] **Study Design v4.0** (`Study_Design.md`)
  - 전체 연구 설계, Two-Pipeline 구조
  - Pipeline-1/Pipeline-2 상세 설명
  - Group-first Architecture 설명

- [ ] **QA Framework v2.0** (`QA_Framework.md`)
  - S0/S1 QA 프레임워크
  - 평가 구조, 의사결정 규칙
  - Safety gate 및 Non-inferiority framework

#### 1.2 통계 분석 계획 문서
- [ ] **Statistical Analysis Plan v2.0** (`Statistical_Analysis_Plan.md`)
  - Pipeline-1/Pipeline-2 통계 분석 계획
  - Endpoints, covariates, 분석 방법
  - Missing data handling, reliability checks

- [ ] **S0 Non-Inferiority Criteria (Canonical)** (`S0_Noninferiority_Criteria_Canonical.md`)
  - S0 non-inferiority 분석의 canonical 규칙
  - Margin (Δ = 0.5), statistical method
  - Decision rules, multiple comparisons correction

### 2. 보조 자료 (Supporting Documents)

#### 2.1 데이터 구조 및 평가 구조
- [ ] **S0 QA Survey Questions v2.0** (`S0_QA_Survey_Questions.md`)
  - 평가 설문 문항, 답변 형식
  - 평가 항목 정의 (Blocking error, Overall Card Quality 등)

- [ ] **S0 QA Form One-Screen Layout** (`S0_QA_Form_One-Screen_Layout.md`)
  - 평가 폼 레이아웃
  - 필수/선택 항목, 평가 방법

#### 2.2 프로젝트 개요
- [ ] **Meeting Agenda (QA Deployment)** (`Meeting_Agenda_QA_Deployment.md`)
  - 프로젝트 목표 및 배경
  - 파이프라인 구조, QA 과정
  - 향후 일정 및 로드맵

- [ ] **Reference Arm Recommendation** (`Reference_Arm_Recommendation.md`)
  - Baseline arm 선택 근거
  - Arm A vs Arm E 비교

### 3. 선택적 첨부 파일 (Optional)

#### 3.1 미팅 자료
- [ ] **PPT Structure (QA Deployment Meeting)** (`PPT_Structure_QA_Deployment_Meeting.md`)
  - 미팅 PPT 구성 및 내용
  - 프로젝트 개요, S0 QA 구조, 분석 계획
  - **참고:** 실제 PPT 파일(.pptx)이 있다면 함께 첨부

- [ ] **실제 PPT 파일** (있는 경우)
  - 파일명: `MeducAI_QA_Deployment_Meeting.pptx` (또는 해당 파일명)
  - 미팅에서 사용한 실제 발표 자료

#### 3.2 기타 참고 자료
- [ ] **QA Plan Review Report** (`QA_Plan_Review_Report.md`)
  - QA 계획 검토 보고서
  - 주요 강점 및 개선 사항

- [ ] **S0 18-Group Selection Rule** (`S0_18Group_Selection_Rule_Canonical.md`)
  - 18개 그룹 선택 규칙 상세 설명
  - Sampling strategy 근거

---

## 파일 경로 정리

### 절대 경로 (Workspace 기준)
```
0_Protocol/06_QA_and_Study/
├── Study_Design/
│   ├── Study_Design.md
│   └── Statistical_Analysis_Plan.md
├── QA_Framework.md
├── QA_Operations/
│   ├── S0_Noninferiority_Criteria_Canonical.md
│   ├── S0_QA_Survey_Questions.md
│   ├── S0_QA_Form_One-Screen_Layout.md
│   ├── Meeting_Agenda_QA_Deployment.md
│   └── PPT_Structure_QA_Deployment_Meeting.md
└── Reference_Arm_Recommendation.md
```

---

## 첨부 파일 준비 체크리스트

### Step 1: 필수 파일 확인
- [ ] 모든 필수 첨부 파일 존재 확인
- [ ] 파일 경로 및 이름 확인
- [ ] 파일 내용 최신 버전 확인

### Step 2: 파일 포맷 변환 (필요 시)
- [ ] Markdown 파일을 PDF로 변환 (선택적)
- [ ] PPT 파일(.pptx) 확인 및 첨부 준비

### Step 3: 파일 압축 (선택적)
- [ ] ZIP 파일로 압축하여 첨부 (파일이 많을 경우)
- [ ] 또는 Google Drive 링크 제공

### Step 4: 메일 작성
- [ ] 메일 본문에 첨부 파일 목록 명시
- [ ] 각 파일의 목적 및 내용 간단히 설명
- [ ] 파일 크기 확인 (메일 첨부 제한 고려)

---

## 메일 첨부 권장 사항

### 옵션 1: 직접 첨부 (파일 수가 적을 경우)
- 필수 파일만 직접 첨부
- 파일 크기 제한 확인 (일반적으로 25MB)

### 옵션 2: Google Drive 링크 (파일이 많거나 클 경우)
- 모든 파일을 Google Drive에 업로드
- 공유 링크 생성 (읽기 전용)
- 메일 본문에 링크 제공

### 옵션 3: ZIP 파일 + Drive (혼합)
- 필수 파일은 ZIP으로 압축하여 첨부
- 보조 자료는 Drive 링크로 제공

---

## 파일 설명 (메일 본문용)

메일 본문에 포함할 파일 설명 예시:

```
첨부 파일 목록:

1. [필수] 연구 설계 문서
   - Study_Design.md: 전체 연구 설계 및 Two-Pipeline 구조
   - QA_Framework.md: S0/S1 QA 프레임워크 및 평가 구조

2. [필수] 통계 분석 계획
   - Statistical_Analysis_Plan.md: Pipeline-1/Pipeline-2 통계 분석 계획
   - S0_Noninferiority_Criteria_Canonical.md: S0 non-inferiority 분석 규칙

3. [보조] 데이터 구조 및 평가 구조
   - S0_QA_Survey_Questions.md: 평가 설문 문항 및 형식
   - S0_QA_Form_One-Screen_Layout.md: 평가 폼 레이아웃

4. [보조] 프로젝트 개요
   - Meeting_Agenda_QA_Deployment.md: 프로젝트 목표 및 파이프라인 구조
   - Reference_Arm_Recommendation.md: Baseline arm 선택 근거

5. [선택] 미팅 자료
   - PPT_Structure_QA_Deployment_Meeting.md: 미팅 PPT 구성
   - MeducAI_QA_Deployment_Meeting.pptx: 실제 PPT 파일 (있는 경우)
```

---

**참고:** 
- 모든 파일은 Markdown 형식이므로, 필요하시면 PDF로 변환하여 첨부하실 수 있습니다.
- 파일이 많거나 크기가 클 경우, Google Drive 링크를 제공하는 것을 권장합니다.

