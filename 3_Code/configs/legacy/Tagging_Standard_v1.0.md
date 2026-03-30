==========================================
MeducAI Tagging Standard v1.0

Radiology Board Learning-Objective Modeling

==========================================

File Location:
MeducAI/3_Code/configs/MeducAI_Tagging_Standard_v1.0.md

Purpose:
본 문서는 MeducAI 파이프라인(테이블 → 슬라이드 → Anki → RAG) 전반에서
일관된 구조화를 위해 사용하는 표준 태그 규칙(Standard Tag Schema) 을 정의한다.

1. Tagging Overview

MeducAI 태그는 다음 4단계 계층으로 구성된다.

Level	Field	설명	예시
Level 1	part	전공 분야(서브스페셜티)	part_msk, part_thx
Level 2	region	해부학 영역	reg_shoulder, reg_liver
Level 3	category	학습 목표의 성격(Anatomy, Findings 등)	cat_ddx, cat_technique
Level 4	topic	세부 항목(Topic_Clean 기반)	topic_rotator_cuff_tear

Anki, RAG, Table 생성에서 태그는 다음 형식으로 조합한다:

part_msk; reg_shoulder; cat_diagnosis; topic_rotator_cuff_tear

2. Tag Naming Rules
2.1 공통 규칙

모든 태그는 snake_case
(소문자 + 숫자 + _)

공백 없음

가능한 20자 이내, 짧고 기억하기 좋게

영어 label과 무관하게 tag는 축약형 중심

3. Part Tag Definitions (전공 분야)
Korean	English Label	Tag (part_)
근골격계	Musculoskeletal radiology	part_msk
흉부	Thoracic radiology	part_thx
복부	Abdominal radiology	part_abd
비뇨생식기	Genitourinary radiology	part_gu
뇌신경	Neuroradiology	part_neuro
소아	Pediatric radiology	part_ped
유방	Breast radiology	part_breast
심장/혈관	Cardiovascular radiology	part_cv
인터벤션	Interventional radiology	part_ir
핵의학	Nuclear medicine	part_nm
4. Region Tag Guidelines

Region은 가능한 한 단일 명사형으로 유지한다.

English Label	Tag (reg_)
Shoulder joint	reg_shoulder
Spine	reg_spine
Lung	reg_lung
Mediastinum	reg_mediastinum
Liver	reg_liver
Kidney	reg_kidney
Pelvis	reg_pelvis
Elbow	reg_elbow
Wrist/Hand	reg_hand
Ankle/Foot	reg_foot
5. Category Tag Definitions

학습 목표의 성격을 나타내는 상위 범주이다.
카테고리는 다음 5개로 고정한다.

Category	Explanation	Tag (cat_)
Anatomy	영상 해부학	cat_anatomy
Imaging findings	영상 소견/패턴	cat_findings
Differential diagnosis	감별진단	cat_ddx
Modality / technique	영상 기법	cat_technique
Procedure / intervention	시술/인터벤션	cat_procedure
6. Topic Tag Guidelines

Topic_Clean 값을 기반으로 생성하며 다음 원칙을 따른다:

snake_case

필요 시 약간 축약 가능

지나치게 긴 경우 핵심 단어만 추출

예시:

Topic	Tag (topic_)
Rotator cuff tear	topic_rotator_cuff_tear
Emphysema	topic_emphysema
Renal cyst	topic_renal_cyst
Liver segment anatomy	topic_liver_segments
7. Full Tag Combination Example

아래는 테이블 1행이 슬라이드·Anki·RAG 등에서 사용되는 태그 조합 예시이다.

Example 1 (MSK / Shoulder / Diagnosis)
필드	값
Specialty_EN_LABEL	Musculoskeletal radiology
Anatomy_EN_LABEL	Shoulder joint
Category_EN_LABEL	Imaging diagnosis
Topic_Clean	rotator_cuff_tear

Anki/RAG 태그:

part_msk; reg_shoulder; cat_diagnosis; topic_rotator_cuff_tear

Example 2 (Thoracic / Lung / Anatomy)
part_thx; reg_lung; cat_anatomy; topic_lung_segments

Example 3 (Abdominal / Liver / DDX)
part_abd; reg_liver; cat_ddx; topic_focal_liver_lesion

8. Usage by Module
8.1 Table Generation

_EN_LABEL → 사람이 읽는 제목

_EN_TAG → Table ID 및 정렬 기준

8.2 Info Slide Generation

슬라이드 제목: _EN_LABEL

슬라이드 묶음: _EN_TAG

NotebookLM 자동 슬라이드 생성 시 안정적인 grouping 제공

8.3 Anki Deck Building

필터덱 예시:

견관절만 복습

tag:reg_shoulder


MSK + DDX만 복습

tag:part_msk tag:cat_ddx


폐 해부학만

tag:reg_lung tag:cat_anatomy

8.4 RAG Search

검색 텍스트: Objective_EN + _EN_LABEL

필터링/클러스터링: _EN_TAG

검색 정확도 향상 & LLM hallucination 감소

9. Versioning

본 문서는 tag schema의 공식 버전이다.

Version: v1.0

유지관리 위치: 3_Code/configs/

향후 변경 시 v1.1, v2.0 등으로 신규 파일 생성

10. Author & Maintainer

MeducAI Core Team
Radiology AI Research

END OF DOCUMENT

MeducAI_Tagging_Standard_v1.0.md