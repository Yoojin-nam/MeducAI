# Prompt 변경 이력 (Changelog)

**최종 업데이트:** 2026-01-07  
**작성 목적:** `3_Code/prompt/` 디렉토리의 모든 변경사항 기록

---

## 목차
0. [프롬프트 폴더 정리 (2026-01-07)](#프롬프트-폴더-정리-2026-01-07)
1. [S2 변경사항 (v12 → v13, S5R4)](#s2-변경사항-v12--v13-s5r4)
2. [전체 변경 개요](#전체-변경-개요)

---

## 프롬프트 폴더 정리 (2026-01-07)

### 변경 일시
- **2026-01-07**

### 목적
- 레포지토리 정리: 활성 버전만 루트에 유지, 비활성 버전은 archive로 이동
- 파일 탐색성 개선 및 `_registry.json`과의 일관성 확보

### 변경사항

#### 아카이브로 이동된 파일 (11개)
다음 파일들이 `archive/` 폴더로 이동되었습니다:

**S1R (재생성용 프롬프트)**:
- `S1R_SYSTEM__v1.md`
- `S1R_USER__v1.md`

**S2R (재생성용 프롬프트)**:
- `S2R_SYSTEM__v1.md`
- `S2R_USER__v1.md`

**S2 S5R4 버전 (registry에 없음)**:
- `S2_SYSTEM__S5R4__v13.md`
- `S2_USER_ENTITY__S5R4__v12.md`

**S4 구버전**:
- `S4_CONCEPT_USER__Anatomy_Map__S5R2__v6.md`
- `S4_CONCEPT_USER__Anatomy_Map__S5R2__v7.md`

**S5 구버전**:
- `S5_USER_CARD__S5R2__v5.md`
- `S5_USER_CARD_IMAGE__S5R2__v4.md`
- `S5_USER_TABLE_VISUAL__S5R2__v3.md`

#### 최종 상태
- **루트 프롬프트 파일**: 26개 (모두 `_registry.json`에 등록된 활성 버전)
- **Archive 파일**: 166개 (기존 158개 + 이동한 8개 + 추가 정리된 파일들)
- **Registry 항목 수**: 26개

#### 원칙
- `_registry.json`에 명시된 파일만 루트에 유지
- 나머지 모든 비활성 버전은 `archive/`로 이동
- 향후 롤백 필요 시 archive에서 복원 가능

### 참고
- S2 S5R4 버전은 registry에 등록되지 않았으므로 현재 사용되지 않음
- 실제 운영 중인 버전은 S2_SYSTEM__S5R3__v12.md 및 S2_SYSTEM__S5R2__v11.md
- S1R, S2R은 재생성용 프롬프트로 별도 관리 예정

---

## S2 변경사항 (v12 → v13, S5R4)

### 변경 일시
- **2026-01-05**

### 변경 파일
- `S2_SYSTEM__S5R4__v13.md` (신규)
- `S2_USER_ENTITY__S5R4__v12.md` (신규)

### 주요 변경사항

#### 1. Q2 Radiology Board Relevance (신규 섹션)
**배경**: 2024 영상의학과 전문의 시험 기출문제 692개 분석 결과 반영

**추가된 규칙**:
- Q2는 영상의학과 전문의 시험에 적합한 개념만 다루어야 함
- **Core Radiology Domains (허용)**:
  - 영상 소견을 설명하는 병태생리
  - 영상 패턴의 기전
  - 영상이 치료 결정을 guide하는 경우
  - QC/물리 원칙
  - 영상 프로토콜 선택 이유
- **Forbidden (금지)**:
  - 순수 임상 증후군/징후 (Gradenigo triad 등)
  - 순수 숫자 암기 (AAST Grade 크기 기준 등)
  - 영상과 무관한 약리학/치료 기전
  - 영상과 무관한 수술 기법

**예시**:
```
❌ WRONG: "Gradenigo triad에 포함되는 소견은?"
✅ CORRECT: "추체첨부염의 CT/MRI 영상 소견으로 적절한 것은?"

❌ WRONG: "AAST Grade III 간 혈종의 크기 기준은?"
✅ CORRECT: "간 외상에서 응급 수술을 시사하는 CT 소견은?"
```

#### 2. Q2 Difficulty Refinement (신규 섹션)
**목적**: 적절한 난이도 범위 설정

- **Appropriate (적절)**: 영상 소견 설명, 프로토콜 선택, 영상 기반 치료 결정
- **Too Easy (회피)**: 단순 용어 암기, 단순 숫자 암기
- **Too Difficult (회피)**: 세부분과 전문 지식, 희귀 예외 지식

**Reframing Strategies**:
- 숫자 암기 → 영상 해석 + 임상 판단
- 임상 증후군 → 영상 소견
- 순수 치료 → 영상 기반 치료 결정

#### 3. Q2 Verification 강화
기존 4개 항목에 2개 추가:
- **[S5R4 NEW]** 영상의학과 시험 적합성 검증
- **[S5R4 NEW]** 순수 숫자 암기 회피 검증

### 영향 범위
- 향후 S2 재생성 시 적용
- 기존 S2 카드에는 영향 없음 (S5 검증에서 해당 이슈 탐지 후 S5R로 수정)

### 관련 분석 데이터
- **Source**: `2_Data/raw/2024/*.pptx` (4개 파일, 692 슬라이드)
- **분석 결과**:
  | 문제 유형 | 비율 |
  |----------|------|
  | 영상 진단 | 53% |
  | 추가검사 선택 | 11% |
  | 해부구조 식별 | 10% |
  | 원인/병인 | 8% |
  | 영상 품질/물리 | 다수 |

---
3. [S1 변경사항 (v8 → v9)](#s1-변경사항-v8--v9)
4. [S2 변경사항 (v7 수정)](#s2-변경사항-v7-수정)
5. [S4_CONCEPT 변경사항 (v1 → v2)](#s4_concept-변경사항-v1--v2)
6. [S4_EXAM 변경사항 (v2 → v3)](#s4_exam-변경사항-v2--v3)
7. [파일 관리 변경사항](#파일-관리-변경사항)
8. [Registry 업데이트](#registry-업데이트)

---

## 전체 변경 개요

### 현재 활성 버전
- **S1_SYSTEM**: v9
- **S1_USER_GROUP**: v9
- **S2_SYSTEM**: v7
- **S2_USER_ENTITY**: v7
- **S4_CONCEPT_SYSTEM**: v2
- **S4_CONCEPT_USER_*** (11개 파일): v2
- **S4_EXAM_SYSTEM**: v3
- **S4_EXAM_USER**: v3

### 주요 변경 이벤트
1. **S1 v9 업그레이드**: 볼드 강조 정책 및 시험포인트 마이크로 템플릿 추가
2. **S2 v7 수정**: Q2 카드의 image_hint 규칙 명확화
3. **S4_CONCEPT v2 대규모 개편**: 결정적 패널 제한, 도식 우선 요구사항 강화
4. **S4_EXAM v3 개선**: 현저성(conspicuity) 제어 및 카드 컨텍스트 통합
5. **Archive 폴더 생성**: 이전 버전 파일 정리 및 보관

---

## S1 변경사항 (v8 → v9)

### 변경 일시
- 최근 커밋: `5805bbf Full pipe line`

### 주요 변경사항

#### 1. Bold Emphasis Policy 추가 (9.1)
- **목적**: 보드 시험 핵심 판별자 강조
- **규칙**:
  - 각 행의 '시험포인트' 셀에 **≥1개 볼드 구문 필수**
  - '영상 소견 키워드' 또는 '결정 소견'에 **≥1개 볼드 구문 권장**
  - 셀당 **≤2개 볼드 구문** (시각적 노이즈 방지)
  - 볼드 구문은 짧게 (2–8 단어), 전체 문장 볼드 금지

#### 2. 시험포인트 마이크로 템플릿 추가 (9.2)
- **목적**: Neuro-table 스타일의 컴팩트하고 기억하기 쉬운 시험 지향형 포맷
- **패턴**:
  - `Trigger → **Answer**` (예: "string of pearls → **Deep watershed**")
  - `If/Then: If X, then **Y**`
  - `Pitfall: **A** vs B (discriminator: ...)`
  - `Classic: triad/association → **key label**`
- **형식**: `<br>`로 2–4개 마이크로 라인 분리 가능 (단일 라인 텍스트 유지)

#### 3. Neuro-Style High-Density Content 업데이트 (9)
- **변경 전 (v8)**: 비-'시험포인트' 셀당 2–4개 원자적 사실
- **변경 후 (v9)**: 
  - 비-'시험포인트' 셀: **3–6개 원자적 사실**
  - '시험포인트' 셀: **4–8개 원자적 사실** (시험 지향 구조)

#### 4. 최소 내용 체크리스트 추가 (9.3)
각 엔티티 행에 대해 다음을 포함해야 함:
- 정의/범위 (컬럼 2): 하위유형/스펙트럼 또는 전형적 맥락
- 영상 키워드 (컬럼 3): 위치 + 형태 + 분포 (최소 3개)
- 모달리티별 (컬럼 4): 2+ 모달리티/시퀀스/뷰 또는 2+ 필수 지식 사인
- 병태생리학 (컬럼 5): 기전 + 1개 고수율 앵커
- 감별진단 (컬럼 6): 2–4개 감별진단 + 최소 1개 판별자 구문

### 파일
- `S1_SYSTEM__v9.md` (신규)
- `S1_USER_GROUP__v9.md` (신규)
- 이전 버전들 (v1–v8) → `archive/` 폴더로 이동

---

## S2 변경사항 (v7 수정)

### 변경 일시
- 최근 커밋: `5805bbf Full pipe line`

### 주요 변경사항

#### Q2 카드의 image_hint 규칙 명확화
- **변경 전**: `Q2 (MCQ, image-on-back): image_hint is STRONGLY RECOMMENDED.`
- **변경 후**: `Q2 (MCQ, image-on-back): image_hint is OPTIONAL (Q2 reuses Q1 image, so image_hint is not used for image generation but may be provided for consistency).`

**이유**: Q2는 Q1 이미지를 재사용하므로 image_hint가 실제 이미지 생성에 사용되지 않음. 일관성을 위해 제공 가능하지만 필수 아님.

### 파일
- `S2_SYSTEM__v7.md` (수정)
- `S2_USER_ENTITY__v7.md` (미세 수정)

---

## S4_CONCEPT 변경사항 (v1 → v2)

### 변경 일시
- 커밋: `85d402a Fix temperature to 0.2 for all stages and add RAG toggle to S4`

### 상세 문서
- 자세한 변경사항은 `S4_CONCEPT_v2_Summary.md` 참조

### 주요 변경사항 요약

#### 1. 결정적 패널 제한 (Deterministic Panel Limit)
- **MAX 6개 확장 패널** (권장 4개)
- 테이블 행이 6개 초과 시: 처음 6개 행만 테이블 순서대로 확장
- 나머지 엔티티 → 컴팩트한 "Others" 섹션 (키워드만)
- 주관적 "중요한" 엔티티 선택 금지

#### 2. 패널당 단어 예산 (Word Budget per Panel)
- 엔티티명 (영문, 볼드)
- **≤3개 키워드** (짧은 구문, 문장 금지)
- 1개 박스형 "시험포인트" (한국어, 정확히 1줄)
- 단락 전역 금지

#### 3. 마크다운 테이블 렌더링 금지
- 명시적 지시: "마크다운 테이블을 테이블로 렌더링하지 말 것"
- 다이어그램/그리드/플로우로 변환 필수

#### 4. 도식 우선 요구사항 (Schematic-First Requirement)
- **QC/Physiology_Process/Equipment/Algorithm 필수 포함**:
  - 플로우차트, 블록 다이어그램, 루프 다이어그램, 또는 축 차트
- "텍스트 전용 슬라이드"는 실패 조건

#### 5. 엄격한 경계
- 마스터 테이블 내용만 사용
- 환각된 파라미터/값/범위 금지
- 추가 소견, 분류체계, 단계 금지

### Visual-Type별 개선사항

#### General
- 4–6개 엔티티 패널 + Others 리스트
- 각 패널에 선택적 작은 도식 아이콘

#### Pathology_Pattern
- 패턴 중심 일러스트레이션 (분포/외관 강조)
- 그리드 레이아웃 (2×2 또는 3×2)

#### Pattern_Collection
- 3–5개 버킷 허용
- 총 확장 항목은 top-N 규칙 제한 (최대 6개)
- 버킷 헤더 짧게; 미니 항목: 이름 + 1개 키워드

#### Physiology_Process
- **필수** 4–7단계 화살표 플로우 다이어그램
- 각 단계: 영상 표현 ≤2 토큰
- 컴팩트한 "시험 함정" 박스 (≤3줄)

#### QC
- **필수** QC 루프 다이어그램: Acquire → Measure → Compare → Action
- 컴팩트한 메트릭 패널 (키워드만; 범위는 제공된 경우만)
- "실패 → 수정" 미니맵
- 불릿 전용 대시보드 금지

#### Sign_Collection
- 균일한 그리드 (최대 6개)
- 각 셀: 사인명 + 작은 의사 이미지 + ≤2 키워드 + 1줄 시험포인트

#### Anatomy_Map
- 중앙 도식 맵 + 최대 6개 콜아웃
- 추가 영역은 Others 리스트

#### Comparison
- 하나의 일관된 레이아웃 선택; 확장 항목 제한 (최대 4–6개)
- 차별화 축 강조

#### Classification
- **필수** 의사결정 트리/분류체계 다이어그램
- 최대 6개 리프 노드 표시; 나머지는 Others

#### Algorithm
- **필수** 파이프라인: Input → Steps(3–6) → Output
- 각 단계 ≤2 토큰
- "일반적인 함정" 시험 박스 (한국어 1줄)

#### Equipment
- **필수** 컴포넌트 레이블 블록 다이어그램
- "아티팩트/제한 → 완화" 미니맵
- 숫자 설정 환각 금지

### 파일
- `S4_CONCEPT_SYSTEM__v2.md` (신규)
- `S4_CONCEPT_USER__General__v2.md` (신규)
- `S4_CONCEPT_USER__Pathology_Pattern__v2.md` (신규)
- `S4_CONCEPT_USER__Pattern_Collection__v2.md` (신규)
- `S4_CONCEPT_USER__Physiology_Process__v2.md` (신규)
- `S4_CONCEPT_USER__QC__v2.md` (신규)
- `S4_CONCEPT_USER__Sign_Collection__v2.md` (신규)
- `S4_CONCEPT_USER__Anatomy_Map__v2.md` (신규)
- `S4_CONCEPT_USER__Comparison__v2.md` (신규)
- `S4_CONCEPT_USER__Classification__v2.md` (신규)
- `S4_CONCEPT_USER__Algorithm__v2.md` (신규)
- `S4_CONCEPT_USER__Equipment__v2.md` (신규)
- `S4_CONCEPT_PREAMBLE__v1.txt` (신규)
- `S4_CONCEPT_v2_Summary.md` (신규, 변경사항 요약 문서)
- v1 파일들 유지 (폴백용)

---

## S4_EXAM 변경사항 (v2 → v3)

### 변경 일시
- 최근 커밋: `5805bbf Full pipe line`

### 주요 변경사항

#### 1. 현저성 및 심각도 제어 추가 (CONSPICUITY & SEVERITY CONTROL)
- **위치**: `S4_EXAM_SYSTEM__v3.md`에 새 섹션 추가
- **규칙**:
  - 이상 소견을 전형적인 임상 심각도로 묘사 (기본: 경증–중등도)
  - IMAGE_HINT가 명시적으로 심각/광범위를 요구하지 않는 한, 병변 확대, 대비 부스팅, 노이즈 제거 금지
  - 모호한 경우, 더 미묘하지만 여전히 감지 가능한 묘사 선호 (과장된 교수용 과장 금지)
  - 완벽한 대칭/기하학적 형태 및 "포스터화된" 강도 단계 방지

#### 2. 카드 컨텍스트 통합
- **위치**: `S4_EXAM_USER__v3.md`에 새 섹션 추가
- **추가된 필드**:
  ```
  CARD CONTEXT (for specificity):
  - Question (front): {card_front_short}
  - Correct answer: {card_answer_short}
  - Explanation keywords: {card_back_keywords}
  ```
- **목적**: 이미지가 카드의 질문과 답변을 직접 지원하도록 보장

#### 3. 필수 이미지 구성 규칙 강화
- 이미지가 질문을 직접 지원해야 함: `"{card_front_short}"` with answer: `"{card_answer_short}"`
- 묘사된 소견이 설명 컨텍스트와 일관되어야 함: `{card_back_keywords}`
- 현저성 제어 (HARD): 경증–중등도 심각도 기본값; 명확성을 위해 소견 확대/강화 금지; 현실적인 노이즈/질감 보존; 포화된 "빛나는" 하이라이트 또는 그래픽 엣지 방지

#### 4. MRI 특화 규칙 추가
- 신호: 포화 방지 ("순백색 페인트" 없음); key_findings_keywords에 명시적으로 암시되지 않는 한 빛나는 림 방지
- 미묘한 소견을 두꺼운 원주형 링으로 바꾸지 않음 (명시적으로 요구되지 않는 한)

#### 5. 시스템 프롬프트 정리
- `image_hint` → `IMAGE_HINT` (대문자로 통일)
- 실패 조건에 현저성 관련 항목 추가: "과도하게 명확한/만화 같은/예술적 렌더링 또는 과장된 병변 현저성 (예: 빛나는 림, 포화된 강화, 비현실적으로 높은 대비)"

### 파일
- `S4_EXAM_SYSTEM__v3.md` (신규)
- `S4_EXAM_USER__v3.md` (신규)
- v2 파일들 → `archive/` 폴더로 이동

---

## 파일 관리 변경사항

### Archive 폴더 생성
- **위치**: `3_Code/prompt/archive/`
- **목적**: 이전 버전 프롬프트 파일 보관
- **보관된 파일**:
  - S1_SYSTEM__v1.md ~ v8.md (8개)
  - S1_USER_GROUP__v1.md ~ v8.md (8개)
  - S2_SYSTEM__v1.md ~ v6.md (6개)
  - S2_USER_ENTITY__v1.md ~ v6.md (6개)
  - S4_EXAM_SYSTEM__v1.md, v2.md (2개)
  - S4_EXAM_USER__v1.md, v2.md (2개)
  - **총 32개 파일**

### 파일 정리 상태
- Git 상태에서 많은 이전 버전 파일들이 삭제됨 (아직 스테이징 안 됨)
- 이 파일들은 `archive/` 폴더로 이동됨 (untracked 상태)

---

## Registry 업데이트

### `_registry.json` 현재 상태

```json
{
  "S1_SYSTEM": "S1_SYSTEM__v9.md",
  "S1_USER_GROUP": "S1_USER_GROUP__v9.md",
  "S2_SYSTEM": "S2_SYSTEM__v7.md",
  "S2_USER_ENTITY": "S2_USER_ENTITY__v7.md",
  "S4_CONCEPT_SYSTEM": "S4_CONCEPT_SYSTEM__v2.md",
  "S4_CONCEPT_USER__General": "S4_CONCEPT_USER__General__v2.md",
  "S4_CONCEPT_USER__Comparison": "S4_CONCEPT_USER__Comparison__v2.md",
  "S4_CONCEPT_USER__Algorithm": "S4_CONCEPT_USER__Algorithm__v2.md",
  "S4_CONCEPT_USER__Classification": "S4_CONCEPT_USER__Classification__v2.md",
  "S4_CONCEPT_USER__Sign_Collection": "S4_CONCEPT_USER__Sign_Collection__v2.md",
  "S4_CONCEPT_USER__Pathology_Pattern": "S4_CONCEPT_USER__Pathology_Pattern__v2.md",
  "S4_CONCEPT_USER__Pattern_Collection": "S4_CONCEPT_USER__Pattern_Collection__v2.md",
  "S4_CONCEPT_USER__Physiology_Process": "S4_CONCEPT_USER__Physiology_Process__v2.md",
  "S4_CONCEPT_USER__Anatomy_Map": "S4_CONCEPT_USER__Anatomy_Map__v2.md",
  "S4_CONCEPT_USER__Equipment": "S4_CONCEPT_USER__Equipment__v2.md",
  "S4_CONCEPT_USER__QC": "S4_CONCEPT_USER__QC__v2.md",
  "S4_EXAM_SYSTEM": "S4_EXAM_SYSTEM__v3.md",
  "S4_EXAM_USER": "S4_EXAM_USER__v3.md"
}
```

### 변경 이력
- S1: v8 → v9
- S2: v7 유지 (수정만)
- S4_CONCEPT: v1 → v2 (모든 서브타입)
- S4_EXAM: v2 → v3

---

## 호환성 및 통합

### 보존된 요소
- ✅ 모든 플레이스홀더 동일: `{group_id}`, `{group_path}`, `{visual_type_category}`, `{master_table_markdown_kr}`
- ✅ 출력 계약 동일: "Return IMAGE ONLY." (S4), JSON 스키마 (S1, S2)
- ✅ 스키마 필드 변경 없음
- ✅ S1/S2 계약 수정 없음

### 코드 통합
- ✅ `_registry.json`이 모든 최신 버전을 가리킴
- ✅ `03_s3_policy_resolver.py`가 자동으로 레지스트리에서 로드
- ✅ 이전 버전 파일들 보관됨 (필요시 폴백 가능)

---

## 테스트 권장사항

### S1 v9
1. 볼드 강조가 '시험포인트' 셀에 필수로 포함되는지 확인
2. 시험포인트 마이크로 템플릿 패턴이 올바르게 사용되는지 확인
3. Neuro-style 고밀도 내용 (3–6개/4–8개 원자적 사실) 확인

### S2 v7
1. Q2 카드의 image_hint가 Optional로 처리되는지 확인
2. Q1, Q3 규칙은 그대로 유지되는지 확인

### S4_CONCEPT v2
1. QC/Physics 중심 그룹: 최소 하나의 다이어그램 존재, 텍스트 전용이 아닌지 확인
2. Pathology/Neuro 그룹: 4–6개 패널, 큰 읽기 가능한 텍스트, 행이 6개 초과 시 "Others" 동작 확인
3. 출력이 여전히 "IMAGE ONLY"를 반환하고 플레이스홀더가 올바르게 렌더링되는지 확인

### S4_EXAM v3
1. 이미지가 카드 질문/답변과 직접적으로 관련되는지 확인
2. 현저성이 적절히 제어되어 과장되지 않는지 확인 (경증–중등도 기본값)
3. MRI 신호가 포화되지 않고 현실적인지 확인

---

## 롤백 방법

### v1로 복귀 (S4_CONCEPT만)
`_registry.json`의 해당 항목을 `*__v1.md`로 변경하면 됨. 코드 변경 불필요.

### v8로 복귀 (S1)
`_registry.json`의 S1 항목을 `*__v8.md`로 변경. `archive/` 폴더에서 파일 복원 필요.

### v2로 복귀 (S4_EXAM)
`_registry.json`의 S4_EXAM 항목을 `*__v2.md`로 변경. `archive/` 폴더에서 파일 복원 필요.

---

## 관련 커밋

```
5805bbf Full pipe line
85d402a Fix temperature to 0.2 for all stages and add RAG toggle to S4
7b9d9c6 feat: S3/S4 파이프라인 구현 완료 및 프로토콜 문서 업데이트
e8dfb88 Refactor documentation: Consolidated and updated references
c501d1d protocol
c3226f3 smoke
```

---

## 참고 문서
- `S4_CONCEPT_v2_Summary.md`: S4_CONCEPT v2 변경사항 상세 요약
- `_registry.json`: 현재 활성 프롬프트 버전 레지스트리
- `archive/`: 이전 버전 파일 보관소

