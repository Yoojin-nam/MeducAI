# S0 QA 피드백 기반 지속적 개선 작업 인계서

**작성일**: 2025-12-29  
**인계 대상**: 개발 Agent / QA 개선 작업 담당자  
**기반 문서**: `S0_QA_final_time_Improvement_Recommendations.md`  
**관련 데이터**: `2_Data/metadata/generated/S0_QA_final_time/`

---

## 1. 작업 배경

### 1.1 문제 상황
S0 QA 설문조사에서 수집된 217개의 평가자 피드백을 분석한 결과, 다음과 같은 주요 문제점들이 식별되었습니다:

- **P0 (치명적 오류)**: 이미지-지문 불일치, 해부학적 오류, 모달리티 불일치 등 즉시 수정이 필요한 오류
- **P1 (높은 우선순위)**: 이미지/인포그래픽 품질 문제 (영상 소견 부정확, 모식도 부적절)
- **P2 (중간 우선순위)**: 답-해설 불일치, 중복 정답 가능성, 용어 정확성 문제
- **P3-P4 (낮은 우선순위)**: 표현/가독성, 테이블 구조 문제

### 1.2 현재 상태
- 프롬프트는 이미 v10-v13으로 업데이트되어 일부 개선 사항이 반영됨
- 하지만 **자동화된 검증 시스템**이 부재하여 피드백에서 지적된 문제들이 여전히 발생 가능
- 특히 **이미지-텍스트 일관성**, **모달리티 일치**, **답-해설 일관성** 등에 대한 자동 검증이 없음

### 1.3 작업 목표
피드백에서 지적된 문제점들을 **자동화된 검증 시스템**과 **프롬프트 개선**을 통해 지속적으로 개선하여, 향후 배포 자료의 품질을 향상시킵니다.

---

## 2. 작업 목록 (우선순위별)

### Phase 1: 즉시 적용 (P0 - 치명적 오류 방지)

#### 작업 1-1: S5 Validator 확장 - 이미지-텍스트 일관성 검증

**파일**: `3_Code/src/05_s5_validator.py`

**작업 내용**:
1. `validate_s2_card()` 함수에 이미지-텍스트 일관성 검증 로직 추가
2. S2 카드의 `front`/`back` 텍스트에서 모달리티 키워드 추출 (CT, MRI, XR, US 등)
3. S4 생성 이미지의 메타데이터 또는 VLM 분석을 통해 모달리티 확인
4. 불일치 시 `blocking_error=True` 플래그 및 상세 설명 추가

**입력**:
- S2 카드 JSON (front, back, image_hint)
- S4 이미지 파일 경로 또는 메타데이터

**출력**:
- `validation_result`에 `image_text_consistency` 필드 추가
- 불일치 시 `blocking_error=True`, `issues` 배열에 상세 설명 추가

**참고**:
- 피드백 사례: "지문은 CT 영상인데 제시된 사진은 US/초음파" (Arm A, group_07)
- 피드백 사례: "지문은 MRI 소견인데 제시된 사진은 CT" (Arm B, group_04)

**예상 작업 시간**: 2-3일

---

#### 작업 1-2: S5 Validator 확장 - 모달리티 일치 검증

**파일**: `3_Code/src/05_s5_validator.py`

**작업 내용**:
1. S2 `image_hint.modality_preferred`와 실제 생성된 이미지의 모달리티 비교
2. VLM 또는 이미지 메타데이터 분석을 통해 모달리티 확인
3. 불일치 시 경고 플래그

**입력**:
- S2 `image_hint.modality_preferred`
- S4 이미지 파일 또는 메타데이터

**출력**:
- `validation_result`에 `modality_match` 필드 추가 (boolean)
- 불일치 시 `issues` 배열에 경고 추가

**참고**:
- 피드백 사례: "CT 소견을 묻지만 첨부 이미지는 X선인 경우" (Boardexam_analysis.md 참고)

**예상 작업 시간**: 1-2일

---

#### 작업 1-3: S5 Validator 확장 - 해부학적 랜드마크 검증

**파일**: `3_Code/src/05_s5_validator.py`

**작업 내용**:
1. S2 `image_hint_v2.anatomy.key_landmarks_to_include`에 명시된 랜드마크가 이미지에 존재하는지 확인
2. VLM 기반 이미지 분석을 통해 랜드마크 존재 여부 검증
3. 누락 시 경고 플래그

**입력**:
- S2 `image_hint_v2.anatomy.key_landmarks_to_include` (배열)
- S4 이미지 파일

**출력**:
- `validation_result`에 `anatomy_landmarks_present` 필드 추가 (배열: present/missing)
- 누락 시 `issues` 배열에 경고 추가

**참고**:
- 피드백 사례: "해부학적 랜드마크 부족" (Arm F, group_01)

**예상 작업 시간**: 2-3일

---

#### 작업 1-4: Post-S4 검증 스크립트 개발

**파일**: `3_Code/src/tools/qa/validate_image_text_consistency.py` (신규)

**작업 내용**:
1. S2 결과물(`s2_results__arm*.jsonl`)과 S4 이미지 매니페스트(`s4_image_manifest__arm*.jsonl`)를 읽어서 매칭
2. 각 Q1 카드의 텍스트와 해당 이미지의 일관성 검증
3. 불일치 리포트 생성 (CSV 또는 Markdown)

**입력**:
- `2_Data/metadata/generated/{RUN_TAG}/s2_results__arm*.jsonl`
- `2_Data/metadata/generated/{RUN_TAG}/s4_image_manifest__arm*.jsonl`
- `2_Data/metadata/generated/{RUN_TAG}/images/` (이미지 파일)

**출력**:
- `2_Data/metadata/generated/{RUN_TAG}/validation_reports/image_text_consistency_report.md`
- 불일치 항목 리스트 (group_id, entity_id, card_role, issue_type, description)

**기능 요구사항**:
- 모달리티 키워드 추출 (정규표현식 또는 NLP)
- 이미지 메타데이터 또는 VLM 분석
- 불일치 감지 및 리포트 생성

**예상 작업 시간**: 2-3일

---

#### 작업 1-5: S2 프롬프트 개선 - 이미지-텍스트 일관성 자가 점검

**파일**: `3_Code/prompt/S2_SYSTEM__v11.md` (신규)

**작업 내용**:
1. S2_SYSTEM__v10.md를 기반으로 v11 생성
2. "IMAGE-TEXT CONSISTENCY SELF-CHECK" 섹션 추가
3. 카드 생성 후 자가 점검 체크리스트 추가:
   - 지문에서 언급한 모달리티와 `image_hint.modality_preferred` 일치 여부
   - 지문에서 언급한 영상 소견과 `image_hint.key_findings_keywords` 일치 여부
   - 해부학적 위치 일치 여부

**입력**:
- `3_Code/prompt/S2_SYSTEM__v10.md`

**출력**:
- `3_Code/prompt/S2_SYSTEM__v11.md`
- `3_Code/prompt/_registry.json` 업데이트 (S2_SYSTEM 버전 v11로 변경)

**참고**:
- 피드백 사례: "이미지-지문 불일치" 관련 모든 피드백

**예상 작업 시간**: 1일

---

### Phase 2: 단기 개선 (P1-P2)

#### 작업 2-1: S4 프롬프트 개선 - 특징적 소견 명시 강화

**파일**: `3_Code/prompt/S4_EXAM_SYSTEM__v9.md` (신규)

**작업 내용**:
1. S4_EXAM_SYSTEM__v8_REALISTIC_4x5_2K.md를 기반으로 v9 생성
2. "CHARACTERISTIC FINDINGS ENFORCEMENT" 섹션 추가
3. `key_findings_keywords`를 더 적극적으로 활용하도록 지시 강화
4. 교육 목표 부합성 확인 지시 추가

**입력**:
- `3_Code/prompt/S4_EXAM_SYSTEM__v8_REALISTIC_4x5_2K.md`

**출력**:
- `3_Code/prompt/S4_EXAM_SYSTEM__v9.md`
- `3_Code/prompt/_registry.json` 업데이트

**참고**:
- 피드백 사례: "영상 소견 부정확", "특징적 소견이 명확하지 않음" (Arm B, group_07)

**예상 작업 시간**: 2일

---

#### 작업 2-2: S4_CONCEPT 프롬프트 개선 - 해부학적 정확성

**파일**: `3_Code/prompt/S4_CONCEPT_USER__Anatomy_Map__v4.md` (신규)

**작업 내용**:
1. S4_CONCEPT_USER__Anatomy_Map__v3.md를 기반으로 v4 생성
2. 해부학적 정확성 검증 체크리스트 추가
3. 방향/위치 표시 명확화 지시 강화
4. 핵심 정보 포함 여부 확인 지시 추가

**입력**:
- `3_Code/prompt/S4_CONCEPT_USER__Anatomy_Map__v3.md`

**출력**:
- `3_Code/prompt/S4_CONCEPT_USER__Anatomy_Map__v4.md`
- `3_Code/prompt/_registry.json` 업데이트

**참고**:
- 피드백 사례: "해부학적 구조나 위치가 잘못 표시됨" (Arm A, group_02, group_09)

**예상 작업 시간**: 1-2일

---

#### 작업 2-3: S5 Validator 확장 - 답-해설 일관성 검증

**파일**: `3_Code/src/05_s5_validator.py`

**작업 내용**:
1. `validate_s2_card()` 함수에 답-해설 일관성 검증 로직 추가
2. MCQ 카드의 경우 `correct_index`와 `options[correct_index]`가 `back` 해설과 일치하는지 확인
3. BASIC 카드의 경우 `front` 질문과 `back` 답이 논리적으로 일치하는지 확인
4. 불일치 시 `blocking_error=True` 플래그

**입력**:
- S2 카드 JSON (front, back, options, correct_index)

**출력**:
- `validation_result`에 `answer_explanation_consistency` 필드 추가
- 불일치 시 `blocking_error=True`, `issues` 배열에 상세 설명 추가

**참고**:
- 피드백 사례: "답은 맞지만 해설과 불일치" (Arm A, group_04)

**예상 작업 시간**: 2-3일

---

#### 작업 2-4: S5 Validator 확장 - 중복 정답 가능성 검증

**파일**: `3_Code/src/05_s5_validator.py`

**작업 내용**:
1. MCQ 카드의 `options` 배열을 분석하여 여러 정답이 가능한지 LLM 기반 검증
2. 감별 진단을 고려하여 명확한 감별 포인트가 있는지 확인
3. 모호한 경우 경고 플래그

**입력**:
- S2 카드 JSON (front, back, options, correct_index)

**출력**:
- `validation_result`에 `multiple_answer_risk` 필드 추가 (boolean)
- 위험 시 `issues` 배열에 경고 추가

**참고**:
- 피드백 사례: "중복 정답의 가능성이 있음" (Arm A, group_07, group_14)

**예상 작업 시간**: 2-3일

---

#### 작업 2-5: 의학 용어 사전 통합

**파일**: `3_Code/src/tools/qa/medical_term_validator.py` (신규)

**작업 내용**:
1. 표준 의학 용어 사전 로드 (예: UMLS, MeSH, 또는 커스텀 사전)
2. Entity 이름 및 카드 텍스트에서 의학 용어 추출
3. 용어 정확성 검증 (오타, 번역 오류 감지)
4. 검증 결과 리포트 생성

**입력**:
- S1 `entity_list` (entity_name)
- S2 카드 텍스트 (front, back)

**출력**:
- 검증 리포트 (용어 오류 리스트)
- `validation_result`에 `term_accuracy` 필드 추가

**참고**:
- 피드백 사례: "진단 용어 오류", "Entity 이름 오류" (Arm A, group_14; Arm C, group_01)

**예상 작업 시간**: 3-4일

---

### Phase 3: 중장기 개선 (P3-P4)

#### 작업 3-1: 후처리 모듈 - 용어 표준화

**파일**: `3_Code/src/tools/postprocess/term_standardizer.py` (신규)

**작업 내용**:
1. 의학 용어 표준화 규칙 정의
2. 한글명 표준화 (예: "난소 염전" vs "난소 꼬임")
3. 용어 일관성 검사 및 자동 수정

**입력**:
- S1/S2 결과물 JSONL

**출력**:
- 표준화된 결과물 JSONL
- 변경 로그

**참고**:
- 피드백 사례: "Ovarian torsion의 한글명은 난소 염전 또는 꼬임이지 기형이 아님" (Arm B, group_04)

**예상 작업 시간**: 3-4일

---

#### 작업 3-2: 후처리 모듈 - 오타 검사

**파일**: `3_Code/src/tools/postprocess/typo_checker.py` (신규)

**작업 내용**:
1. 의학 용어 사전 기반 오타 검사
2. 일반적인 오타 패턴 감지 (예: "Gird/dector" → "Grid/detector")
3. 오타 수정 제안

**입력**:
- S1/S2 결과물 JSONL

**출력**:
- 오타 리포트
- 수정 제안

**참고**:
- 피드백 사례: "Gird/dector 옆에 박스 오타" (Arm B, group_02)

**예상 작업 시간**: 2-3일

---

#### 작업 3-3: PDF 빌더 개선 - Font 렌더링

**파일**: `3_Code/src/07_build_set_pdf.py`

**작업 내용**:
1. Font 깨짐 문제 해결
2. 한글 폰트 지원 강화
3. 폰트 폴백 메커니즘 개선

**입력**:
- 현재 PDF 빌더 코드

**출력**:
- 개선된 PDF 빌더

**참고**:
- 피드백 사례: "Page 3,7,8 font 깨짐" (Arm E, group_02)

**예상 작업 시간**: 3-4일

---

## 3. 작업 순서 및 의존성

### Phase 1 (즉시 적용)
```
작업 1-1 (S5 Validator - 이미지-텍스트 일관성)
  ↓
작업 1-2 (S5 Validator - 모달리티 일치)
  ↓
작업 1-3 (S5 Validator - 해부학적 랜드마크)
  ↓
작업 1-4 (Post-S4 검증 스크립트) [병렬 가능]
  ↓
작업 1-5 (S2 프롬프트 개선)
```

### Phase 2 (단기 개선)
```
작업 2-1 (S4 프롬프트 개선)
  ↓
작업 2-2 (S4_CONCEPT 프롬프트 개선)
  ↓
작업 2-3 (S5 Validator - 답-해설 일관성) [작업 1-1 이후]
  ↓
작업 2-4 (S5 Validator - 중복 정답) [작업 2-3 이후]
  ↓
작업 2-5 (의학 용어 사전) [병렬 가능]
```

### Phase 3 (중장기 개선)
```
작업 3-1 (용어 표준화)
  ↓
작업 3-2 (오타 검사) [작업 3-1 이후]
  ↓
작업 3-3 (PDF 빌더 개선) [병렬 가능]
```

---

## 4. 참고 자료

### 4.1 피드백 데이터
- **피드백 리포트**: `0_Protocol/06_QA_and_Study/QA_Operations/S0_QA_final_time_Reviewer_Feedback_Report.md`
- **개선 권장사항**: `0_Protocol/06_QA_and_Study/QA_Operations/S0_QA_final_time_Improvement_Recommendations.md`
- **피드백 CSV**: `0_Protocol/06_QA_and_Study/QA_Operations/S0_QA_final_time_Reviewer_Feedback.csv`

### 4.2 관련 코드
- **S5 Validator**: `3_Code/src/05_s5_validator.py`
- **S2 프롬프트**: `3_Code/prompt/S2_SYSTEM__v10.md`
- **S4 프롬프트**: `3_Code/prompt/S4_EXAM_SYSTEM__v8_REALISTIC_4x5_2K.md`
- **PDF 빌더**: `3_Code/src/07_build_set_pdf.py`

### 4.3 관련 프로토콜
- **S5 프로토콜**: `0_Protocol/05_Pipeline_and_Execution/archived/2025-12/S5_Prompt_Freeze_and_Experiment_Handoff.md`
- **QA 프레임워크**: `0_Protocol/06_QA_and_Study/QA_Framework.md`
- **S2 정책**: `0_Protocol/04_Step_Contracts/Step02_S2/S2_Cardset_Image_Placement_Policy_Canonical.md`

### 4.4 샘플 데이터
- **S0 배포 자료**: `2_Data/metadata/generated/S0_QA_final_time/`
  - `s2_results__arm*.jsonl`: S2 카드 결과물
  - `s4_image_manifest__arm*.jsonl`: S4 이미지 메타데이터
  - `images/`: 생성된 이미지 파일

---

## 5. 검증 및 테스트

### 5.1 단위 테스트
각 작업 완료 후 다음을 테스트:
- 새로운 검증 로직이 기존 정상 케이스에서 false positive를 발생시키지 않는지
- 새로운 검증 로직이 피드백에서 지적된 문제 케이스를 올바르게 감지하는지

### 5.2 통합 테스트
Phase 1 완료 후:
- S0_QA_final_time 데이터에 대해 Post-S4 검증 스크립트 실행
- 불일치 리포트 생성 및 검토
- S5 Validator 확장 기능이 실제 파이프라인에서 정상 작동하는지 확인

### 5.3 성공 지표
- **Phase 1**: 이미지-지문 불일치 감지율 > 90%, 모달리티 불일치 감지율 > 95%
- **Phase 2**: 답-해설 일관성 검증 정확도 > 85%, 중복 정답 감지율 > 70%
- **Phase 3**: 용어 표준화 적용률 > 95%, 오타 검사 정확도 > 95%

---

## 6. 작업 완료 체크리스트

### Phase 1
- [ ] 작업 1-1: S5 Validator - 이미지-텍스트 일관성 검증 구현 완료
- [ ] 작업 1-2: S5 Validator - 모달리티 일치 검증 구현 완료
- [ ] 작업 1-3: S5 Validator - 해부학적 랜드마크 검증 구현 완료
- [ ] 작업 1-4: Post-S4 검증 스크립트 개발 완료
- [ ] 작업 1-5: S2 프롬프트 v11 생성 및 등록 완료
- [ ] Phase 1 통합 테스트 완료

### Phase 2
- [ ] 작업 2-1: S4 프롬프트 v9 생성 및 등록 완료
- [ ] 작업 2-2: S4_CONCEPT 프롬프트 v4 생성 및 등록 완료
- [ ] 작업 2-3: S5 Validator - 답-해설 일관성 검증 구현 완료
- [ ] 작업 2-4: S5 Validator - 중복 정답 검증 구현 완료
- [ ] 작업 2-5: 의학 용어 사전 통합 완료
- [ ] Phase 2 통합 테스트 완료

### Phase 3
- [ ] 작업 3-1: 용어 표준화 모듈 개발 완료
- [ ] 작업 3-2: 오타 검사 모듈 개발 완료
- [ ] 작업 3-3: PDF 빌더 개선 완료
- [ ] Phase 3 통합 테스트 완료

---

## 7. 문의 사항

작업 중 문제가 발생하거나 명확하지 않은 사항이 있으면:
1. 관련 프로토콜 문서 재확인
2. 피드백 리포트에서 구체적 사례 확인
3. 기존 코드 구조 및 패턴 참고

---

**작성자**: MeducAI Research Team  
**최종 업데이트**: 2025-12-29

