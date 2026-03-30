# S0 QA 설문 응답 데이터 저장 가이드

**작성 일자**: 2025-12-29  
**목적**: S0 QA Google Form 설문 응답 데이터 저장 위치 및 관리 방법  
**상태**: 운영 가이드

---

## 1. 저장 위치

### 1.1 원시 데이터 (Raw Data) - 개인정보 포함

**위치**: `1_Secure_Participant_Info/QA_Operations/S0_QA_{RUN_TAG}/`

**파일명 규칙**:
- `S0_QA_{RUN_TAG}_raw_responses.xlsx` (또는 `.csv`)
- 예: `S0_QA_final_time_raw_responses.xlsx`

**포함 내용**:
- Google Form에서 다운로드한 원본 응답 데이터
- 평가자 이메일 주소 포함 (개인정보)
- 타임스탬프, 모든 응답 필드

**주의사항**:
- ⚠️ 이메일 주소 등 개인정보 포함
- `1_Secure_Participant_Info/` 폴더는 `.gitignore`에 포함되어 Git에 커밋되지 않음
- 접근 권한 제한 관리

---

### 1.2 비식별화 데이터 (De-identified Data)

**위치**: `2_Data/qa_responses/S0_QA_{RUN_TAG}/`

**파일명 규칙**:
- `S0_QA_{RUN_TAG}_deidentified.xlsx` (또는 `.csv`)
- 예: `S0_QA_final_time_deidentified.xlsx`

**포함 내용**:
- 이메일 주소를 `reviewer_id`로 변환
- `assignment_map.csv`와 결합하여 분석 가능한 형태
- 개인정보 제거

**생성 방법**:
```python
# assignment_map.csv와 결합하여 reviewer_id로 변환
# 이메일 주소는 reviewer_id로 매핑
```

---

### 1.3 분석용 데이터 (Analysis-Ready Data)

**위치**: `2_Data/qa_responses/S0_QA_{RUN_TAG}/`

**파일명 규칙**:
- `S0_QA_{RUN_TAG}_analysis_ready.xlsx` (또는 `.csv`)
- 예: `S0_QA_final_time_analysis_ready.xlsx`

**포함 내용**:
- `assignment_map.csv`와 결합 완료
- `surrogate_map.csv`와 결합 완료
- Arm 정보 포함 (블라인딩 해제 후)
- 통계 분석에 바로 사용 가능한 형태

---

## 2. 폴더 구조

```
1_Secure_Participant_Info/QA_Operations/
└── S0_QA_{RUN_TAG}/
    └── S0_QA_{RUN_TAG}_raw_responses.xlsx          # 원시 데이터 (개인정보 포함)

2_Data/qa_responses/
└── S0_QA_{RUN_TAG}/
    ├── S0_QA_{RUN_TAG}_deidentified.xlsx            # 비식별화 데이터
    ├── S0_QA_{RUN_TAG}_analysis_ready.xlsx         # 분석용 데이터
    └── README.md                                    # 데이터 설명 문서
```

---

## 3. 저장 절차

### 3.1 Google Form에서 다운로드

1. Google Form 편집 화면 접속
2. **응답** 탭 클릭
3. **스프레드시트에 연결** 또는 **다운로드** (CSV/Excel)
4. 파일 다운로드

### 3.2 원시 데이터 저장

```bash
# 폴더 생성
mkdir -p 1_Secure_Participant_Info/QA_Operations/S0_QA_final_time

# 파일 저장
# 다운로드한 파일을 다음 위치로 이동/복사
# 1_Secure_Participant_Info/QA_Operations/S0_QA_final_time/S0_QA_final_time_raw_responses.xlsx
```

### 3.3 비식별화 처리

```python
# 비식별화 스크립트 실행 (예시)
# assignment_map.csv와 결합하여 reviewer_id로 변환
python3 3_Code/Scripts/deidentify_qa_responses.py \
    --input 1_Secure_Participant_Info/QA_Operations/S0_QA_final_time/S0_QA_final_time_raw_responses.xlsx \
    --assignment_map 1_Secure_Participant_Info/QA_Operations/assignment_map.csv \
    --output 2_Data/qa_responses/S0_QA_final_time/S0_QA_final_time_deidentified.xlsx
```

### 3.4 분석용 데이터 생성

```python
# 분석용 데이터 생성 스크립트 실행 (예시)
# assignment_map.csv, surrogate_map.csv와 결합
python3 3_Code/Scripts/prepare_qa_analysis_data.py \
    --input 2_Data/qa_responses/S0_QA_final_time/S0_QA_final_time_deidentified.xlsx \
    --assignment_map 1_Secure_Participant_Info/QA_Operations/assignment_map.csv \
    --surrogate_map 1_Secure_Participant_Info/QA_Operations/surrogate_map_group_id.csv \
    --output 2_Data/qa_responses/S0_QA_final_time/S0_QA_final_time_analysis_ready.xlsx
```

---

## 4. 데이터 보안

### 4.1 개인정보 보호

- **원시 데이터**: 이메일 주소 등 개인정보 포함
  - Git에 커밋하지 않음
  - 접근 권한 제한
  - 필요 시 암호화 저장

- **비식별화 데이터**: 이메일 주소를 reviewer_id로 변환
  - Git에 커밋 가능 (개인정보 제거 확인 후)
  - 분석에 사용 가능

### 4.2 .gitignore 설정

**참고**: `1_Secure_Participant_Info/` 폴더 전체가 이미 `.gitignore`에 포함되어 있어 원시 데이터는 자동으로 제외됩니다.

```gitignore
# 1_Secure_Participant_Info/ 폴더 전체 제외 (이미 설정됨)
1_Secure_Participant_Info/
```

---

## 5. 데이터 메타데이터

각 폴더에 `README.md` 파일을 생성하여 다음 정보를 기록:

```markdown
# S0 QA 응답 데이터 - {RUN_TAG}

## 데이터 정보
- **RUN_TAG**: S0_QA_final_time
- **수집 일자**: 2025-12-22 ~ 2025-12-29
- **Form 링크**: [Google Form 링크]
- **총 응답 수**: XX개

## 파일 설명
- `raw_responses.xlsx`: 원시 응답 데이터 (개인정보 포함)
- `deidentified.xlsx`: 비식별화 데이터
- `analysis_ready.xlsx`: 분석용 데이터

## 데이터 처리 이력
- YYYY-MM-DD: 원시 데이터 저장
- YYYY-MM-DD: 비식별화 처리 완료
- YYYY-MM-DD: 분석용 데이터 생성 완료
```

---

## 6. 통계 분석

### 6.1 분석 스크립트

```python
# 분석용 데이터 사용
import pandas as pd

df = pd.read_excel('2_Data/qa_responses/S0_QA_final_time/S0_QA_final_time_analysis_ready.xlsx')

# 통계 분석 수행
# ...
```

### 6.2 분석 결과 저장

**위치**: `2_Data/qa_responses/S0_QA_{RUN_TAG}/analysis/`

**파일명 규칙**:
- `S0_QA_{RUN_TAG}_noninferiority_results.xlsx`
- `S0_QA_{RUN_TAG}_descriptive_stats.xlsx`
- `S0_QA_{RUN_TAG}_arm_comparison.xlsx`

---

## 7. 체크리스트

### 데이터 저장 시

- [ ] Google Form에서 원시 데이터 다운로드
- [ ] `2_Data/qa_responses/S0_QA_{RUN_TAG}/` 폴더 생성
- [ ] 원시 데이터 저장 (`*_raw_responses.xlsx`)
- [ ] 비식별화 처리 스크립트 실행
- [ ] 분석용 데이터 생성 스크립트 실행
- [ ] README.md 파일 생성 및 메타데이터 기록
- [ ] .gitignore 설정 확인 (원시 데이터 제외)

### 분석 전

- [ ] 분석용 데이터 파일 확인
- [ ] assignment_map.csv와 결합 확인
- [ ] surrogate_map.csv와 결합 확인
- [ ] 데이터 무결성 검증

---

## 8. 참고 문서

- `Google_Form_Creation_Guide.md`: Google Form 생성 가이드
- `S0_QA_Google_Form_Links.md`: Form 링크 관리
- `QA_Assignment_Summary.md`: Assignment 매핑 정보
- `S0_Noninferiority_Criteria_Canonical.md`: 통계 분석 기준

---

## 9. 문제 해결

### Q: 원시 데이터를 Git에 커밋해도 되나요?
A: 아니요. 이메일 주소 등 개인정보가 포함되어 있으므로 Git에 커밋하지 마세요. `.gitignore`에 추가하세요.

### Q: 분석용 데이터는 Git에 커밋해도 되나요?
A: 비식별화 처리가 완료되었고 개인정보가 제거되었다면 가능합니다. 다만 프로젝트 정책을 확인하세요.

### Q: 데이터를 어디서 찾을 수 있나요?
A: `2_Data/qa_responses/S0_QA_{RUN_TAG}/` 폴더에서 확인하세요.

---

**작성자**: MeducAI Research Team  
**업데이트**: 데이터 저장 시 메타데이터 업데이트 필요

