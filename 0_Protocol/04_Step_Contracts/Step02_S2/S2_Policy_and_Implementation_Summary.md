# S2 정책 및 구현 요약 (Policy and Implementation Summary)

**Status:** Canonical  
**Version:** 1.2  
**Last Updated:** 2025-12-20  
**Purpose:** S2의 입출력 스키마, 내부 처리 흐름, 프롬프트 정리

**Implementation Status:** ✅ **완료** (2025-12-20)
- S2 안정화 규칙 구현 완료
- 3 cards per entity 강제
- 5-option MCQ 검증
- Deictic image reference 검증
- Image hint compliance 검증

---

## 1. S2 정의 (One-Line Definition)

> **Step02 (S2) is a policy-agnostic execution stage that generates exactly N text-only Anki cards for a given entity, and nothing more.**

**핵심 원칙:**
- S2는 **정책 결정자(policy maker)가 아님**
- S2는 **실행 엔진(execution engine)**
- S2는 **엔티티 단위로 실행**됨
- S2는 **정확히 N개의 텍스트 전용 Anki 카드**를 생성

---

## 2. 입출력 스키마 (Input/Output Schema)

### 2.1 입력 (Input)

S2는 **S1 출력**을 소비합니다.

#### 입력 파일
- **경로:** `2_Data/metadata/generated/<RUN_TAG>/stage1_struct__arm{ARM}.jsonl`
- **스키마 버전:** `S1_STRUCT_v1.3` (FROZEN)
- **형식:** NDJSON (각 라인은 하나의 그룹 레코드)

#### 입력 스키마 (S1 출력에서 필요한 필드)

```json
{
  "schema_version": "S1_STRUCT_v1.3",
  "group_id": "G0123",                    // 필수: 그룹 식별자
  "group_path": "Chest/TB/Severity",       // 필수: 그룹 경로
  "visual_type_category": "Pathology_Pattern",  // 필수: 시각적 타입 카테고리
  "master_table_markdown_kr": "...",      // 필수: 마스터 테이블 (마크다운)
  "entity_list": [                         // 필수: 엔티티 리스트
    {
      "entity_id": "G0123__E01",           // 필수: 엔티티 식별자
      "entity_name": "Miliary pattern"     // 필수: 엔티티 이름
    }
  ],
  "objective_bullets": ["..."],            // 필수: 목표 불릿 리스트
  "integrity": {
    "entity_count": 2,
    "table_row_count": 2,
    "objective_count": 1
  }
}
```

#### S2 실행 타겟 생성

S2는 S1 출력의 `entity_list`를 기반으로 실행 타겟을 생성합니다:

```python
# S2 실행 타겟 구조
@dataclass(frozen=True)
class _S2Target:
    entity_id: str              # 엔티티 식별자
    entity_name: str            # 엔티티 이름
    cards_for_entity_exact: int # 정확히 생성할 카드 수
```

**카드 수 결정:**
- **S0 모드:** Allocation artifact에서 읽음 (`allocation/allocation_s0__group_{G}__arm_{A}.json`)
- **FINAL 모드:** `FINAL_CARDS_PER_ENTITY` 상수 사용 (기본값: 3)

---

### 2.2 출력 (Output)

#### 출력 파일
- **경로 (new format, 2025-12-23):** `2_Data/metadata/generated/<RUN_TAG>/s2_results__s1arm{S1_ARM}__s2arm{S2_ARM}.jsonl`
- **경로 (legacy format):** `2_Data/metadata/generated/<RUN_TAG>/s2_results__arm{ARM}.jsonl` (backward compatible)
- **스키마 버전:** `S2_RESULTS_v3.1`
- **형식:** NDJSON (각 라인은 하나의 엔티티 결과 레코드)
- **Note:** S1과 S2가 다른 arm을 사용할 수 있도록 파일명에 S1 arm과 S2 arm 정보를 모두 포함. Legacy 형식은 S0 결과와의 호환성을 위해 계속 지원.

#### 출력 스키마

```json
{
  "schema_version": "S2_RESULTS_v3.1",
  "run_tag": "TEST_20251219",
  "arm": "A",
  "group_id": "G0123",                    // 필수: 그룹 식별자
  "group_path": "Chest/TB/Severity",      // 필수: 그룹 경로
  "entity_id": "G0123__E01",              // 필수: 엔티티 식별자
  "entity_name": "Miliary pattern",       // 필수: 엔티티 이름 (S1에서 verbatim 복사)
  "cards_for_entity_exact": 3,            // 필수: 정확한 카드 수
  "anki_cards": [                         // 필수: Anki 카드 배열
    {
      "card_id": "G0123__E01__C01",       // 권장: 카드 식별자
      "card_role": "Q1",                  // 필수: 카드 역할 (Q1, Q2, Q3)
      "card_type": "BASIC",               // 필수: 카드 타입 (BASIC, MCQ)
      "front": "질문 텍스트",              // 필수: 앞면
      "back": "답변 텍스트",               // 필수: 뒷면
      "tags": ["tag1", "tag2"],           // 필수: 태그 배열
      "image_hint": {                     // 조건부: Q1 필수, Q2 권장, Q3 금지
        "modality_preferred": "CT",
        "anatomy_region": "Chest",
        "key_findings_keywords": ["miliary", "nodules"],
        "view_or_sequence": "axial",
        "exam_focus": "pattern"
      }
    }
  ],
  "integrity": {
    "card_count": 3                       // 필수: 카드 수 (len(anki_cards)와 일치)
  }
}
```

#### 출력 제약 조건 (Hard Constraints)

1. **정확한 카드 수:** `len(anki_cards) == cards_for_entity_exact`
2. **엔티티 불변성:** `entity_id`와 `entity_name`은 S1에서 verbatim 복사
3. **텍스트 전용:** 이미지 필드, 이미지 프롬프트, 시각적 메타데이터 없음 (단, `image_hint`는 구조화된 메타데이터로 허용)
4. **스키마 불변성:** 필수 필드만 포함, 추가 키 없음
5. **비중복성:** 동일한 `(card_type, front)` 쌍 없음
6. **카드 역할 (card_role):** 각 카드는 `Q1`, `Q2`, `Q3` 중 하나여야 함
7. **이미지 힌트 규칙:**
   - **Q1 카드:** `image_hint` 필수 (non-null 객체)
   - **Q2 카드:** `image_hint` 권장 (strongly preferred, null 허용)
   - **Q3 카드:** `image_hint` 금지 (null이거나 없어야 함)

---

## 3. 내부 처리 흐름 (Internal Processing Flow)

### 3.1 전체 실행 흐름

```
1. S1 출력 읽기
   └─> stage1_struct__arm{ARM}.jsonl 파일 로드
   
2. Allocation artifact 읽기 (S0 모드만)
   └─> allocation/allocation_s0__group_{G}__arm_{A}.json
   └─> 각 엔티티별 cards_for_entity_exact 결정
   
3. S2 실행 타겟 생성
   └─> entity_list를 순회하며 _S2Target 객체 생성
   
4. 각 엔티티별로 S2 실행
   ├─> 프롬프트 구성 (S2_SYSTEM + S2_USER_ENTITY)
   ├─> LLM 호출
   ├─> 응답 검증 (validate_stage2)
   ├─> 카드 수 검증 (len(anki_cards) == cards_for_entity_exact)
   └─> 결과 수집
   
5. 결과 출력
   └─> s2_results__arm{ARM}.jsonl 파일에 쓰기
```

### 3.2 코드 실행 위치

**메인 함수:** `process_single_group()` (라인 1397-2150)

**S2 실행 섹션:** 라인 1663-1822

```python
# -------- Stage 2 (S2) --------
entities_out: List[Dict[str, Any]] = []

for tgt in s2_targets:
    # 1. 엔티티 컨텍스트 구성
    entity_context = (
        f"Group ID: {gid}\n"
        f"Group Path: {group_path}\n"
        f"Visual Type: {s1_json.get('visual_type_category', 'General')}\n"
    )
    
    # 2. 사용자 프롬프트 포맷팅
    s2_user = safe_prompt_format(
        P_S2_USER_T,
        master_table=s1_json["master_table_markdown_kr"],
        group_id=gid,
        entity_name=ent_name,
        entity_context=entity_context,
        cards_for_entity_exact=expected_n,
        ...
    )
    
    # 3. LLM 호출
    s2_json, err2, rt_s2, raw_s2 = call_llm(
        provider=provider,
        system_prompt=P_S2_SYS,
        user_prompt=s2_user,
        model_name=model_stage2,
        temperature=temp_stage2,
        stage=2,
        ...
    )
    
    # 4. 응답 검증
    s2_json = validate_stage2(s2_json)
    
    # 5. 카드 수 검증
    got_n = len(s2_json.get("anki_cards") or [])
    if got_n != expected_n:
        raise RuntimeError(f"S0 exact-N violated: expected {expected_n}, got {got_n}")
    
    # 6. 메타데이터 추가
    s2_json["group_id"] = gid
    s2_json["group_path"] = group_path
    s2_json["entity_id"] = ent_id
    s2_json["cards_for_entity_exact"] = expected_n
    
    entities_out.append(s2_json)
```

### 3.3 검증 함수

**`validate_stage2()`** (라인 1456-1553)

```python
def validate_stage2(stage2: Dict[str, Any]) -> Dict[str, Any]:
    """
    S2 응답 검증 및 정규화 (v3.1)
    
    검증 항목:
    1. group_id, entity_id, entity_name 추출
    2. anki_cards 배열 정규화
    3. 각 카드의 필수 필드 검증 (card_role, card_type, front, back, tags)
    4. image_hint 검증 (Q1 필수, Q2 권장, Q3 금지)
    5. 빈 카드 제거
    """
```

**검증 규칙:**
- `anki_cards`는 배열이어야 함
- 각 카드는 `card_role` (Q1/Q2/Q3), `card_type`, `front`, `back`, `tags` 필수
- `card_role`이 없으면 인덱스로 추론 (backward compatibility)
- **Q1 카드:** `image_hint` 필수 (없으면 경고, 향후 fail-fast 가능)
- **Q3 카드:** `image_hint`가 있으면 제거
- `front`와 `back`이 비어있으면 제거

### 3.4 출력 함수

**`write_s2_results_jsonl()`** (라인 1308-1350)

```python
def write_s2_results_jsonl(
    entities: Optional[List[Dict[str, Any]]],
    fh: Optional[TextIO],
    *,
    run_tag: str,
    arm: str,
    group_path: str,
) -> None:
    """
    S2 결과를 canonical JSONL 형식으로 출력
    
    각 엔티티별로 하나의 레코드 생성:
    - schema_version: S2_RESULTS_v3.0
    - 필수 필드 모두 포함
    - integrity.card_count 검증
    """
```

---

## 4. 프롬프트 (Prompts)

### 4.1 시스템 프롬프트 (System Prompt)

**현재 프로덕션 버전:**
- `3_Code/prompt/S2_SYSTEM__S5R3__v12.md` (registry: `S2_SYSTEM__S5R3`)
- `3_Code/prompt/S2_USER_ENTITY__S5R2__v11.md` (registry: `S2_USER_ENTITY`)

**참고:**
- FINAL_DISTRIBUTION run_tag는 위 버전으로 생성됨
- 한글 사용이 다수 포함되어 있으나, 메타데이터 번역 도구로 후처리 가능
- 향후 업그레이드 계획: `S2_Language_Policy_Future_Upgrade.md` 참조

**역할:**
- S2의 역할과 경계 명확화
- 실행 규칙 및 제약 조건 정의
- 금지된 동작 명시

**주요 내용:**

```
ROLE BOUNDARY (NON-NEGOTIABLE):
- You are NOT a decision-maker.
- You are NOT a policy engine.
- You are NOT an image planner.
- You are NOT a QA or importance scorer.

EXECUTION DEFINITION:
- Input: (entity_name, cards_for_entity_exact = N, master_table_md, entity_context)
- Output: exactly N text-only Anki cards for that entity.

HARD CONSTRAINTS:
1) Exact cardinality: len(anki_cards) MUST equal cards_for_entity_exact.
2) Entity immutability: entity_name MUST be echoed verbatim.
3) Text-only: No image fields, no image prompts, no visual metadata.
4) Schema invariance: Output ONLY the canonical JSON object.
5) Non-redundancy: No exact duplicate (card_type, front) pairs.

FORBIDDEN ACTIONS:
- Deciding quotas, importance, weights, or policies.
- Generating or implying image necessity or prompts.
- Reclassifying visual domain.
- Introducing generation modes, experiment arms, or QA metadata.
```

### 4.2 사용자 프롬프트 (User Prompt)

**파일:** `3_Code/prompt/S2_USER_ENTITY__v5.md`

**역할:**
- 구체적인 실행 태스크 정의
- S1 출력 컨텍스트 제공
- 출력 형식 명시

**주요 내용:**

```
TASK:
Generate exactly N text-only Anki cards for the specified entity.

AUTHORITATIVE READ-ONLY CONTEXT:
[Master Table — S1 Output]
{master_table_md}

EXECUTION TARGET:
- Group ID: {group_id}
- Entity Name: {entity_name}
- Exact Card Count: {cards_for_entity_exact}

ENTITY CONTEXT (READ-ONLY):
{entity_context}

EXECUTION RULES (ABSOLUTE):
1) Interpret the entity strictly as defined by S1.
2) Generate exactly {cards_for_entity_exact} cards.
3) Card quality: Each card MUST have non-empty front and back.
4) Card types: Use only standard radiology board-appropriate card types.
5) Prohibitions: No image decisions or prompts.

OUTPUT REQUIREMENTS:
- Return ONLY one valid JSON object.
- No explanations, no markdown, no extra text.

CANONICAL OUTPUT SCHEMA:
{
  "group_id": "{group_id}",
  "entity_name": "{entity_name}",
  "anki_cards": [
    {
      "card_type": "string",
      "front": "string",
      "back": "string",
      "tags": ["string", "string"]
    }
  ]
}
```

### 4.3 프롬프트 로딩

프롬프트는 **프롬프트 번들(bundle)**로 로드됩니다:

```python
bundle = load_prompt_bundle(...)
P_S2_SYS = bundle["prompts"]["S2_SYSTEM"]
P_S2_USER_T = bundle["prompts"]["S2_USER_ENTITY"]
```

**프롬프트 번들 구조:**
- `S2_SYSTEM`: 시스템 프롬프트 텍스트
- `S2_USER_ENTITY`: 사용자 프롬프트 템플릿 (포맷팅 가능)

---

## 5. 실행 모드 (Execution Modes)

### 5.1 독립 실행 (Independent Execution)

S2는 `--stage 2` 옵션으로 독립 실행 가능:

```bash
python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag TEST_20251219 \
  --arm A \
  --mode S0 \
  --stage 2
```

**전제 조건:**
- S1 출력 파일 존재: `stage1_struct__arm{ARM}.jsonl`
- S0 모드인 경우: Allocation artifact 존재

### 5.2 통합 실행 (Integrated Execution)

S1과 S2를 함께 실행:

```bash
python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag TEST_20251219 \
  --arm A \
  --mode S0 \
  --stage both  # 기본값
```

---

## 6. 에러 처리 (Error Handling)

### 6.1 Fail-fast 규칙

S2는 다음 경우 즉시 실패:

1. **S1 입력 스키마 위반**
   - `schema_version != "S1_STRUCT_v1.3"`
   - 필수 필드 누락

2. **엔티티 해석 불가**
   - `entity_id`를 찾을 수 없음
   - `entity_name`이 비어있음

3. **출력 길이 제약 위반**
   - `len(anki_cards) != cards_for_entity_exact`

4. **필수 필드 누락 또는 타입 불일치**
   - `anki_cards`가 배열이 아님
   - 카드에 `front` 또는 `back`이 없음

### 6.2 S0 모드 특수 규칙

S0 모드에서는 **underfill/empty가 허용되지 않음**:

```python
if not s2_json:
    if str(mode).upper() == "S0":
        raise RuntimeError(f"S0 Stage2 failed: entity={ent_name} error={err2 or 'Unknown error'}")
    continue
```

---

## 7. 관련 문서 (Related Documents)

### 7.1 정책 문서
- `S2_Contract_and_Schema_Canonical.md` - S2 계약 및 스키마 정의
- `S2_Cardset_Image_Placement_Policy_Canonical.md` - 카드셋 및 이미지 배치 정책
- `S2_CARDSET_POLICY_V1.md` - 카드셋 정책

### 7.2 실행 문서
- `S1_S2_Independent_Execution_Design.md` - S1/S2 독립 실행 설계
- `Code_to_Protocol_Traceability.md` - 코드-프로토콜 추적성

### 7.3 입력 스키마
- `Step01_S1/S1_Stage1_Struct_JSON_Schema_Canonical.md` - S1 출력 스키마 (v1.3)

---

## 8. 구현 체크리스트 (Implementation Checklist)

### 8.1 입력 검증
- [ ] S1 출력 파일 존재 확인
- [ ] `schema_version == "S1_STRUCT_v1.3"` 확인
- [ ] 필수 필드 존재 확인 (`group_id`, `entity_list`, `master_table_markdown_kr`)
- [ ] Allocation artifact 읽기 (S0 모드)

### 8.2 실행
- [ ] 각 엔티티별로 S2 타겟 생성
- [ ] 프롬프트 번들 로드
- [ ] LLM 호출 (RAG, Thinking 옵션 지원)
- [ ] 응답 검증 (`validate_stage2`)
- [ ] 카드 수 검증 (`len(anki_cards) == cards_for_entity_exact`)

### 8.3 출력
- [ ] `s2_results__arm{ARM}.jsonl` 파일 생성
- [ ] 스키마 버전 `S2_RESULTS_v3.1` 설정
- [ ] 필수 필드 모두 포함 (card_role 포함)
- [ ] `integrity.card_count` 검증
- [ ] `image_hint` 규칙 준수 (Q1 필수, Q2 권장, Q3 금지)

---

## 9. 변경 이력 (Change History)

- **2025-12-19:** 초기 버전 작성
  - S2 입출력 스키마 정리
  - 내부 처리 흐름 문서화
  - 프롬프트 구조 정리

- **2025-12-19 (v1.1):** 스키마 v3.1 반영
  - `card_role` (Q1/Q2/Q3) 필드 추가
  - `image_hint` 조건부 필드 추가 및 규칙 명시
  - `validate_stage2()` 함수 업데이트 반영
  - 출력 제약 조건에 카드 역할 및 이미지 힌트 규칙 추가

- **2025-12-20 (v1.2):** S2 안정화 완료
  - 정확히 3 cards per entity 강제 구현
  - 5-option MCQ 검증 구현 (Q2/Q3)
  - Deictic image reference 검증 구현 (Q2/Q3 금지)
  - Image hint compliance 검증 구현
  - 6-arm 테스트 검증 완료

