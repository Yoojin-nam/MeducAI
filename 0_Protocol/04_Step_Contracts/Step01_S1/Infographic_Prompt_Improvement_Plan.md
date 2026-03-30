# 인포그래픽 프롬프트 개선 계획

**작성일**: 2025-12-23  
**목적**: 인포그래픽 텍스트 불안정 문제 해결 및 간결한 텍스트 출력

---

## 문제 분석

### 현재 문제점

1. **텍스트 불안정성**
   - 프롬프트에서 "Up to 3 keywords"라고 명시되어 있지만, 실제로는 더 많은 텍스트가 생성됨
   - 다양한 형식의 텍스트가 혼재 (문장, 키워드, 설명 등)
   - 일관성 없는 텍스트 배치

2. **과도한 정보 포함**
   - Entity name 외에도 질환 정의, 병리 기전, 감별 질환 등 다양한 정보가 포함됨
   - 시각적 요소보다 텍스트에 집중되는 경향

3. **Modality 정보 부족**
   - Modality 키워드가 명확히 추출되지 않음
   - 영상 소견과 Modality의 연결이 약함

---

## 개선 목표

### 목표 텍스트 구성

각 Entity Panel에 포함될 텍스트:

1. **Entity name** (필수)
   - 영어, 볼드
   - 테이블의 첫 번째 컬럼에서 추출

2. **Modality 키워드** (필수)
   - CT, MRI, X-ray, US 등
   - 테이블의 "모달리티별 핵심 영상 소견" 컬럼에서 추출
   - 형식: "CT / MRI" 또는 "CT, MRI"

3. **시험포인트 키워드** (선택적)
   - 테이블의 "시험포인트" 컬럼에서 추출
   - 핵심 키워드만 (1-3개 단어)
   - 한국어 또는 영어

### 제외할 정보

- 질환 정의 및 분류
- 병리·기전/특징
- 감별 질환
- 기타 설명 텍스트

---

## 프롬프트 개선 방안

### 1. S4_CONCEPT_SYSTEM__v3.md 개선

**현재**:
```
PER-PANEL CONTENT (READABILITY):
Each expanded panel SHOULD contain:
- Entity name (English, bold)
- Up to 3 short keywords/tokens (English; short phrases; no sentences)
- "시험포인트" box (Korean, EXACTLY one short line) ONLY IF the table provides a clear pitfall/pearl.
```

**개선안**:
```
PER-PANEL CONTENT (STRICT TEXT LIMIT):
Each expanded panel MUST contain ONLY the following text elements:

1. Entity name (English, bold) - REQUIRED
   - Extract from table "Entity name" column
   - Display as-is, no modification

2. Modality keywords (English) - REQUIRED
   - Extract from table "모달리티별 핵심 영상 소견" column
   - Format: "CT / MRI" or "CT, MRI" (use "/" or "," separator)
   - Include ONLY modality names (CT, MRI, X-ray, US, PET, etc.)
   - Maximum 3 modalities per entity
   - Example: "CT / MRI" or "X-ray"

3. 시험포인트 keywords (Korean or English) - OPTIONAL
   - Extract from table "시험포인트" column
   - Display ONLY key trigger words (1-3 words maximum)
   - Format: single line, no sentences
   - If table "시험포인트" is empty or unclear, OMIT this element

TEXT PROHIBITIONS (STRICT):
- DO NOT include disease definitions
- DO NOT include pathology mechanisms
- DO NOT include differential diagnoses
- DO NOT include clinical features
- DO NOT include any explanatory text
- DO NOT create sentences or phrases
- DO NOT add information not present in the table

TEXT FORMATTING:
- Entity name: Bold, English
- Modality: Regular, English, separated by "/" or ","
- 시험포인트: Regular, Korean or English, single line
- Maximum total text per panel: Entity name + Modality + 시험포인트 (if present)
```

### 2. S4_CONCEPT_USER__Pathology_Pattern__v3.md 개선

**현재**:
```
PATTERN CARD TEMPLATE (each expanded panel):
- Entity name (English, bold)
- Visual anchor (MANDATORY):
  ...
- ≤ 3 keywords/tokens total (English; NO sentences), preferably in labeled fields:
  - Distribution: <token>
  - Appearance/Signal: <token>
  - Key sign / DDx pitfall: <token>
- "시험포인트" box (Korean, EXACTLY one short line) ONLY if grounded in the table.
```

**개선안**:
```
PATTERN CARD TEMPLATE (each expanded panel):
- Entity name (English, bold) - REQUIRED
  - Extract from table "Entity name" column

- Modality keywords (English) - REQUIRED
  - Extract from table "모달리티별 핵심 영상 소견" column
  - Format: "CT / MRI" or "CT, MRI"
  - Include ONLY modality names (CT, MRI, X-ray, US, PET, etc.)
  - Maximum 3 modalities per entity

- Visual anchor (MANDATORY):
  - At least one grayscale radiology-like thumbnail OR a simplified schematic
  - The thumbnail/schematic must express distribution, appearance, key sign
  - Use subtle highlights (outline/overlay) only

- 시험포인트 keywords (Korean or English) - OPTIONAL
  - Extract from table "시험포인트" column
  - Display ONLY key trigger words (1-3 words maximum)
  - Format: single line, no sentences
  - If table "시험포인트" is empty or unclear, OMIT this element

TEXT PROHIBITIONS:
- DO NOT include "Distribution:", "Appearance:", "Key sign:" labels
- DO NOT include disease definitions or explanations
- DO NOT include differential diagnoses
- DO NOT create sentences or phrases
- DO NOT add information not present in the table

WORD BUDGET (STRICT):
- Entity name: As-is from table
- Modality: 1-3 modality names only (e.g., "CT / MRI")
- 시험포인트: 1-3 words maximum (if present)
- Total text per panel: Entity name + Modality + 시험포인트 (if present)
```

### 3. S4_CONCEPT_USER__General__v3.md 개선

**현재**:
```
PANEL TEMPLATE:
- Entity name (English, bold)
- Visual anchor (thumbnail/schematic) with minimal highlight
- ≤ 3 tokens total (English; no sentences), labeled if helpful:
  - Key finding: <token>
  - Location/Distribution: <token>
  - Pitfall/DDx: <token>
- Optional "시험포인트" (Korean, EXACTLY one short line) ONLY if table-supported.
```

**개선안**:
```
PANEL TEMPLATE:
- Entity name (English, bold) - REQUIRED
  - Extract from table "Entity name" column

- Modality keywords (English) - REQUIRED
  - Extract from table "핵심 영상 단서(키워드+모달리티)" or "모달리티별 핵심 영상 소견" column
  - Format: "CT / MRI" or "CT, MRI"
  - Include ONLY modality names (CT, MRI, X-ray, US, PET, etc.)
  - Maximum 3 modalities per entity

- Visual anchor (thumbnail/schematic) with minimal highlight - REQUIRED

- 시험포인트 keywords (Korean or English) - OPTIONAL
  - Extract from table "시험포인트" column
  - Display ONLY key trigger words (1-3 words maximum)
  - Format: single line, no sentences
  - If table "시험포인트" is empty or unclear, OMIT this element

TEXT PROHIBITIONS:
- DO NOT include "Key finding:", "Location:", "Pitfall:" labels
- DO NOT include disease definitions or explanations
- DO NOT include differential diagnoses
- DO NOT create sentences or phrases
- DO NOT add information not present in the table
```

### 4. S4_CONCEPT_USER__Anatomy_Map__v3.md 개선

**현재**:
```
CALLOUT TEMPLATE (each expanded row):
- Entity name (English, bold)
- Up to 2 labeled tokens (English; no sentences), e.g.:
  - Region: <token>
  - Landmark / Pitfall: <token>
- Optional "시험포인트" (Korean, EXACTLY one short line) ONLY if clearly supported by the table content.
```

**개선안**:
```
CALLOUT TEMPLATE (each expanded row):
- Entity name (English, bold) - REQUIRED
  - Extract from table "Entity name" column

- Modality keywords (English) - REQUIRED (if applicable)
  - Extract from table "위치/인접 구조" or "임상 적용" column if modality mentioned
  - Format: "CT / MRI" or "CT, MRI"
  - Include ONLY modality names (CT, MRI, X-ray, US, PET, etc.)
  - Maximum 3 modalities per entity
  - If no modality information in table, OMIT this element

- 시험포인트 keywords (Korean or English) - OPTIONAL
  - Extract from table "시험포인트" column
  - Display ONLY key trigger words (1-3 words maximum)
  - Format: single line, no sentences
  - If table "시험포인트" is empty or unclear, OMIT this element

TEXT PROHIBITIONS:
- DO NOT include "Region:", "Landmark:" labels
- DO NOT include anatomical descriptions
- DO NOT include clinical applications
- DO NOT create sentences or phrases
- DO NOT add information not present in the table
```

---

## Modality 추출 로직

### 테이블 컬럼별 Modality 추출 방법

1. **Pathology_Pattern**: "모달리티별 핵심 영상 소견" 컬럼
   - 형식: "CT: [findings]; MRI: [findings]; X-ray: [findings]"
   - 추출: "CT", "MRI", "X-ray" 키워드만 추출

2. **Pattern_Collection**: "핵심 영상 단서(키워드+모달리티)" 컬럼
   - 형식: "CT/MRI: [findings]" 또는 "CT, MRI"
   - 추출: Modality 키워드만 추출

3. **General**: "핵심 영상 단서(키워드+모달리티)" 컬럼
   - 형식: "CT/MRI: [findings]" 또는 "CT, MRI"
   - 추출: Modality 키워드만 추출

4. **Anatomy_Map**: Modality 정보가 없을 수 있음
   - "위치/인접 구조" 또는 "임상 적용" 컬럼에서 추출 시도
   - 없으면 생략

### Modality 키워드 정규화

**인식할 Modality**:
- CT, MRI, X-ray, US, PET, SPECT, Mammography, Fluoroscopy, DSA, etc.

**추출 규칙**:
- "CT:", "MRI:", "X-ray:" 등의 패턴에서 추출
- "CT/MRI", "CT, MRI" 등의 패턴에서 추출
- 대소문자 구분 없이 인식

---

## 시험포인트 키워드 추출 로직

### 추출 규칙

1. **테이블 "시험포인트" 컬럼에서 추출**
2. **핵심 키워드만 선택** (1-3개 단어)
3. **형식**: 
   - "If X, then Y" → "X" 또는 "Y" 키워드만
   - "Pitfall: A vs B" → "A", "B" 키워드만
   - "숫자/기준/컷오프" → 숫자와 기준만

### 예시

**원본 시험포인트**:
- "If nidus > 1cm, then consider osteoblastoma"
- **추출 키워드**: "nidus > 1cm" 또는 "osteoblastoma"

**원본 시험포인트**:
- "Pitfall: Osteoid osteoma vs Osteoblastoma; distinguishing feature = nidus"
- **추출 키워드**: "nidus" 또는 "Osteoid osteoma vs Osteoblastoma"

---

## 구현 단계

### Phase 1: 프롬프트 템플릿 수정

1. **S4_CONCEPT_SYSTEM__v3.md** 수정
   - PER-PANEL CONTENT 섹션 개선
   - TEXT PROHIBITIONS 섹션 추가

2. **S4_CONCEPT_USER__*.md** 수정
   - 각 카테고리별 템플릿 수정
   - Modality 추출 지시사항 추가
   - 시험포인트 키워드 추출 지시사항 추가

### Phase 2: S3 프롬프트 생성 로직 개선 (선택적)

**현재**: 전체 master_table_markdown_kr을 프롬프트에 포함

**개선안**: Entity별로 필요한 정보만 추출하여 포함

```python
def extract_entity_text_for_infographic(
    master_table_markdown: str,
    entity_name: str,
) -> Dict[str, str]:
    """
    Extract only necessary text for infographic:
    - Entity name
    - Modality keywords
    - 시험포인트 keywords
    """
    # Parse table
    # Extract row for entity_name
    # Extract Entity name (column 1)
    # Extract Modality from appropriate column
    # Extract 시험포인트 keywords (column 6)
    
    return {
        "entity_name": "...",
        "modality_keywords": "CT / MRI",
        "exam_point_keywords": "nidus > 1cm",  # Optional
    }
```

### Phase 3: 테스트 및 검증

1. **단위 테스트**: Modality 추출 로직 테스트
2. **통합 테스트**: S3 → S4 프롬프트 생성 테스트
3. **이미지 생성 테스트**: 실제 인포그래픽 생성 및 텍스트 검증

---

## 예상 효과

### 개선 전
```
Entity: Osteoid osteoma
Distribution: Epiphysis
Appearance: Nidus formation
Key sign: Night pain
시험포인트: If nidus > 1cm, then consider osteoblastoma
```

### 개선 후
```
Entity: Osteoid osteoma
CT / MRI
nidus > 1cm
```

**효과**:
- 텍스트 간결성 향상
- 일관성 있는 형식
- 시각적 요소에 집중 가능
- Modality 정보 명확화

---

## 주의사항

1. **하위 호환성**: 기존 프롬프트와의 호환성 유지
2. **테이블 구조**: 테이블 컬럼 구조에 따라 Modality 추출 방법이 다를 수 있음
3. **시험포인트**: 테이블에 시험포인트가 없거나 불명확한 경우 생략
4. **Modality**: 테이블에 Modality 정보가 없는 경우 생략 (Anatomy_Map 등)

---

## 다음 단계

1. 프롬프트 템플릿 수정 (Phase 1)
2. 테스트 및 검증 (Phase 3)
3. 필요시 S3 로직 개선 (Phase 2)

