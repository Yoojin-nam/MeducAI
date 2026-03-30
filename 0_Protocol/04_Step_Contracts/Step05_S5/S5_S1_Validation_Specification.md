# S5 S1 평가 명세서 (프롬프트 개선 및 멀티에이전트용)

**목적:** S5가 S1을 어떻게 평가하는지에 대한 완전한 명세서  
**대상:** 프롬프트 개선, 멀티에이전트 시스템 설계, 평가 로직 수정  
**최종 업데이트:** 2025-12-30

---

## 1. 평가 아키텍처 개요

### 1.1 평가 단계

S5는 S1 테이블을 **2단계로 분리 평가**합니다:

```
┌─────────────────────────────────────────┐
│ Step 1: 테이블 평가 (항상 수행)         │
│ - 입력: master_table_markdown_kr        │
│ - 출력: blocking_error, technical_      │
│   accuracy, educational_quality, issues  │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ Step 2: 인포그래픽 평가 (선택적)         │
│ - 클러스터 없음: 1개 인포그래픽 평가     │
│ - 클러스터 있음: 최대 4개 인포그래픽 평가│
│ - 각각 독립적인 LLM 호출                │
└─────────────────────────────────────────┘
```

### 1.2 모델 설정

- **모델**: `gemini-3-pro-preview` (Pro 모델, 고정)
- **Temperature**: `0.2` (환경변수 `TEMPERATURE_STAGE5`로 오버라이드 가능)
- **Thinking**: `enabled=true`, `level="high"`
- **RAG**: `enabled=true` (blocking_error=true일 때 증거 필수)
- **Timeout**: 테이블 평가 300초, 인포그래픽 평가 300초

---

## 2. Step 1: 테이블 평가 (S5_USER_TABLE__v2.md)

### 2.1 입력 데이터

프롬프트 변수:
- `{group_id}`: 그룹 식별자
- `{group_path}`: 그룹 경로 (예: "Chest > Lung > CT")
- `{objective_bullets}`: 학습 목표 목록 (줄바꿈으로 연결)
- `{master_table_markdown_kr}`: 전체 마스터 테이블 (Markdown 형식)

### 2.2 평가 기준

#### 2.2.1 Technical Accuracy (기술적 정확성)
- **스케일**: `0.0 | 0.5 | 1.0`
- **0.0**: 안전성-중요 의학 오류 → **BLOCKING**
- **0.5**: 사소한 부정확성, 모호성, 수정 필요 (non-blocking)
- **1.0**: 명백한 오류 없음

#### 2.2.2 Educational Quality (교육적 품질)
- **스케일**: `1 | 2 | 3 | 4 | 5` (Likert)
- **5**: 매우 가치 있음, 핵심 시험 개념 직접 타겟
- **1**: 가치 낮음, 학습에 도움이 되지 않을 가능성

#### 2.2.3 Blocking Error (차단 오류)
- **의미**: 임상 안전성-중요 오류만 차단
- **규칙**:
  - `blocking_error=true` → 반드시 `technical_accuracy=0.0`
  - `blocking_error=true` → 반드시 RAG 증거 포함 (최소 1개, `relevance="high"`)
  - 구조/포맷/명확성 이슈는 단독으로는 blocking 아님

### 2.3 출력 형식

```json
{
  "blocking_error": boolean,
  "technical_accuracy": 0.0 | 0.5 | 1.0,
  "educational_quality": 1 | 2 | 3 | 4 | 5,
  "issues": [
    {
      "severity": "blocking" | "minor" | "warning",
      "type": string,
      "description": string,
      "row_index": integer (0-based, optional),
      "entity_name": string (optional),
      "suggested_fix": string,
      "issue_code": string (optional, 예: "S1_TERMINOLOGY_OUTDATED"),
      "affected_stage": "S1" | "S2" | "S3" | "S4" | "S5",
      "recommended_fix_target": string (optional, 예: "S1_SYSTEM", "S1_USER_GROUP"),
      "prompt_patch_hint": string (optional, 1-3줄),
      "confidence": number (0-1, optional),
      "evidence_ref": string (optional)
    }
  ],
  "rag_evidence": [
    {
      "source_id": string,
      "source_excerpt": string (최대 500자),
      "relevance": "high" | "medium" | "low"
    }
  ]
}
```

### 2.4 이슈 타입 예시

- `terminology_outdated`: 구식 용어 사용
- `factual_error`: 사실 오류
- `missing_entity`: 엔티티 누락
- `duplicate_entity`: 엔티티 중복
- `table_format_error`: 테이블 포맷 오류
- `exam_relevance_low`: 시험 관련성 낮음

---

## 3. Step 2: 인포그래픽 평가 (S5_USER_TABLE_VISUAL__v1.md)

### 3.1 클러스터 감지 및 처리

#### 3.1.1 클러스터 감지 로직
```python
entity_clusters = s1_table.get("entity_clusters", [])
infographic_clusters = s1_table.get("infographic_clusters", [])
has_clustering = bool(entity_clusters and infographic_clusters and len(entity_clusters) > 0)
```

#### 3.1.2 클러스터별 처리
- **클러스터가 있는 경우**:
  - 각 클러스터별로 `cluster_id` 추출
  - 클러스터별 테이블 서브셋 추출 (해당 엔티티만 포함)
  - 각 클러스터 인포그래픽 경로 해석: `IMG__{run_tag}__{group_id}__TABLE__{cluster_id}.jpg`
  - 각 클러스터별로 독립적인 LLM 호출 수행
- **클러스터가 없는 경우**:
  - 단일 인포그래픽 경로 해석: `IMG__{run_tag}__{group_id}__TABLE.jpg`
  - 전체 마스터 테이블 사용
  - 단일 LLM 호출 수행

### 3.2 입력 데이터

프롬프트 변수:
- `{group_id}`: 그룹 식별자
- `{group_path}`: 그룹 경로
- `{objective_bullets}`: 학습 목표 목록
- `{master_table_markdown_kr}`: 
  - 클러스터인 경우: 클러스터별 테이블 서브셋
  - 단일인 경우: 전체 마스터 테이블
- `{s3_infographic_prompt_en}`: S3에서 생성된 인포그래픽 프롬프트
- `{infographic_path}`: 인포그래픽 이미지 파일 경로

### 3.3 평가 기준 (인포그래픽별)

#### 3.3.1 Information Clarity (정보 명확성)
- **스케일**: `1 | 2 | 3 | 4 | 5` (Likert)
- **평가 내용**:
  - 테이블의 핵심 정보가 시각적으로 명확히 전달되는가?
  - 레이아웃이 체계적이고 읽기 쉬운가?
  - 정보 계층이 명확한가?
  - **OCR 검증**: 모든 텍스트 추출 및 정확성 검증
- **이슈 타입**:
  - `cluttered_layout`: 레이아웃 혼잡
  - `unclear_hierarchy`: 계층 불명확
  - `missing_text`: 텍스트 누락
  - `unreadable_text`: 텍스트 가독성 낮음
  - `text_error`: 텍스트 오류
  - `text_table_mismatch`: 텍스트-테이블 불일치

#### 3.3.2 Anatomical Accuracy (해부학적 정확성)
- **스케일**: `0.0 | 0.5 | 1.0`
- **평가 내용**: 해부학적 구조/관계가 정확한가?
- **이슈 타입**:
  - `anatomical_error`: 해부학적 오류
  - `relationship_misrepresentation`: 관계 오표현

#### 3.3.3 Prompt Compliance (프롬프트 준수도)
- **스케일**: `0.0 | 0.5 | 1.0`
- **평가 내용**:
  - S3 `infographic_prompt_en` 요구사항과 일치하는가?
  - 프롬프트의 필수 요소가 모두 포함되어 있는가?

#### 3.3.4 Table-Visual Consistency (테이블-비주얼 일관성)
- **스케일**: `0.0 | 0.5 | 1.0`
- **평가 내용**:
  - 인포그래픽 내용이 S1 테이블과 일치하는가?
  - 테이블의 모든 엔티티가 인포그래픽에 표현되어 있는가?
  - **OCR 검증**: 엔티티명 추출 및 테이블과 비교
- **이슈 타입**:
  - `content_mismatch`: 내용 불일치
  - `entity_missing`: 엔티티 누락
  - `entity_name_mismatch`: 엔티티명 불일치

### 3.4 출력 형식 (인포그래픽별)

```json
{
  "table_visual_validation": {
    "cluster_id": string (optional, 클러스터인 경우만),
    "blocking_error": boolean,
    "information_clarity": 1 | 2 | 3 | 4 | 5,
    "anatomical_accuracy": 0.0 | 0.5 | 1.0,
    "prompt_compliance": 0.0 | 0.5 | 1.0,
    "table_visual_consistency": 0.0 | 0.5 | 1.0,
    "extracted_text": string (optional, OCR로 추출한 텍스트),
    "entities_found_in_text": [string] (optional, OCR로 찾은 엔티티명 목록),
    "issues": [
      {
        "severity": "blocking" | "minor" | "warning",
        "type": string,
        "description": string,
        "issue_code": string (optional, 예: "TABLE_VISUAL_ENTITY_MISSING"),
        "recommended_fix_target": string (optional, 예: "S3_PROMPT"),
        "prompt_patch_hint": string (optional),
        "confidence": number (0-1, optional)
      }
    ],
    "image_path": string
  }
}
```

---

## 4. 최종 결과 구조

### 4.1 단일 인포그래픽 (클러스터 없음)

```json
{
  "blocking_error": false,
  "technical_accuracy": 1.0,
  "educational_quality": 4,
  "issues": [...],
  "rag_evidence": [...],
  "table_visual_validation": {
    // 인포그래픽 평가 결과 (단일 dict)
  }
}
```

### 4.2 클러스터 인포그래픽 (최대 4개)

```json
{
  "blocking_error": false,
  "technical_accuracy": 1.0,
  "educational_quality": 4,
  "issues": [...],
  "rag_evidence": [...],
  "table_visual_validations": [
    {
      "cluster_id": "C1",
      // 인포그래픽 평가 결과
    },
    {
      "cluster_id": "C2",
      // 인포그래픽 평가 결과
    },
    // ... 최대 4개
  ]
}
```

---

## 5. 프롬프트 개선을 위한 핵심 정보

### 5.1 프롬프트 파일 위치

- **System Prompt**: `3_Code/prompt/S5_SYSTEM__v2.md`
- **Table User Prompt**: `3_Code/prompt/S5_USER_TABLE__v2.md`
- **Table Visual User Prompt**: `3_Code/prompt/S5_USER_TABLE_VISUAL__v1.md`

### 5.2 프롬프트 변수 (템플릿 변수)

**S5_USER_TABLE__v2.md**:
- `{group_id}`
- `{group_path}`
- `{objective_bullets}`
- `{master_table_markdown_kr}`

**S5_USER_TABLE_VISUAL__v1.md**:
- `{group_id}`
- `{group_path}`
- `{objective_bullets}`
- `{master_table_markdown_kr}` (클러스터인 경우 서브셋)
- `{s3_infographic_prompt_en}`
- `{infographic_path}`

### 5.3 JSON 출력 스키마 (불변)

- 모든 JSON 키는 고정 (추가/삭제/변경 불가)
- 데이터 타입 고정
- `blocking_error=true`일 때 `rag_evidence` 필수
- `technical_accuracy`는 반드시 `0.0 | 0.5 | 1.0` 중 하나

### 5.4 평가 기준의 세부 규칙

#### 5.4.1 Blocking Error 판단 기준
- **차단해야 하는 경우**:
  - 안전성-중요 의학 오류 (예: 잘못된 용량, 금기사항 오류)
  - 임상 결정을 잘못 이끌 수 있는 오류
- **차단하지 않아야 하는 경우**:
  - 단순 용어 오류 (구식 용어 등)
  - 명확성 문제
  - 시험 관련성 문제
  - 포맷 오류

#### 5.4.2 Technical Accuracy 판단 기준
- **1.0**: 의학적으로 정확, 가이드라인 준수
- **0.5**: 사소한 부정확성, 모호성, 수정 권장
- **0.0**: 안전성-중요 오류, 반드시 blocking_error=true

#### 5.4.3 Educational Quality 판단 기준
- **5**: 시험에서 자주 묻는 핵심 개념, 직접 타겟
- **4**: 시험 관련성 높음
- **3**: 보통 수준
- **2**: 시험 관련성 낮음
- **1**: 학습 가치 낮음

---

## 6. 멀티에이전트 관점에서의 정보

### 6.1 에이전트 역할 분리

현재 S5는 단일 에이전트로 구현되어 있지만, 멀티에이전트로 분리 가능:

#### Agent 1: Table Validator
- **역할**: 테이블 평가 (Step 1)
- **입력**: `master_table_markdown_kr`, `objective_bullets`
- **출력**: `blocking_error`, `technical_accuracy`, `educational_quality`, `issues`, `rag_evidence`
- **프롬프트**: `S5_USER_TABLE__v2.md`

#### Agent 2: Infographic Validator (단일 또는 다중)
- **역할**: 인포그래픽 평가 (Step 2)
- **입력**: 테이블 + 인포그래픽 이미지 + S3 프롬프트
- **출력**: `table_visual_validation` 또는 `table_visual_validations`
- **프롬프트**: `S5_USER_TABLE_VISUAL__v1.md`
- **특징**: 클러스터가 있으면 각 클러스터별로 별도 에이전트 인스턴스 실행 가능

### 6.2 에이전트 간 통신

- **Table Validator → Infographic Validator**: 테이블 평가 결과 전달 (선택적)
- **Infographic Validator → Table Validator**: 인포그래픽 blocking_error가 테이블 blocking_error에 영향 (현재는 코드에서 처리)

### 6.3 병렬 처리 가능성

- **클러스터 인포그래픽 평가**: 각 클러스터별로 독립적이므로 완전 병렬 처리 가능
- **테이블 평가와 인포그래픽 평가**: 테이블 평가 완료 후 인포그래픽 평가 시작 (순차적)

---

## 7. 코드 레벨 구현 세부사항

### 7.1 함수 구조

```python
validate_s1_table(
    s1_table: Dict[str, Any],
    clients: ProviderClients,
    group_id: str,
    base_dir: Path,
    run_tag: str,
    arm: str,
    s4_manifest: Optional[Dict],
    s3_image_specs: Optional[Dict],
    prompt_bundle: Optional[Dict]
) -> Dict[str, Any]
```

### 7.2 내부 헬퍼 함수

```python
_validate_single_infographic(
    s1_table: Dict[str, Any],
    clients: ProviderClients,
    group_id: str,
    base_dir: Path,
    run_tag: str,
    arm: str,
    infographic_path: Optional[Path],
    s3_infographic_spec: Optional[Dict],
    cluster_id: Optional[str],
    prompt_bundle: Dict,
    cluster_table_markdown: Optional[str]
) -> Tuple[Optional[Dict], Optional[str]]
```

### 7.3 데이터 흐름

1. **S1 테이블 로드**: `load_s1_structure()`
2. **S4 매니페스트 로드**: `load_s4_manifest()` (cluster_id 포함 키 사용)
3. **S3 스펙 로드**: `load_s3_image_specs()` (cluster_id 포함 키 사용)
4. **클러스터 감지**: `entity_clusters`, `infographic_clusters` 확인
5. **테이블 평가**: LLM 호출 #1
6. **인포그래픽 평가**: LLM 호출 #2 ~ #5 (클러스터별)
7. **결과 통합**: 단일 또는 리스트로 반환

---

## 8. 프롬프트 개선 시 주의사항

### 8.1 스키마 불변성
- JSON 키 추가/삭제/변경 불가
- 데이터 타입 변경 불가
- 필수 필드 누락 불가

### 8.2 평가 기준 일관성
- `blocking_error=true` → 반드시 `technical_accuracy=0.0`
- `blocking_error=true` → 반드시 RAG 증거 포함
- 평가 스케일 고정 (0.0/0.5/1.0, 1-5 Likert)

### 8.3 클러스터 지원
- 프롬프트에서 클러스터를 명시적으로 언급할 필요 없음 (코드에서 처리)
- 단, 클러스터별 테이블 서브셋이 전달되므로 이를 고려한 평가 지침 필요

### 8.4 OCR 요구사항
- 인포그래픽 평가 시 OCR 사용 명시
- `extracted_text`, `entities_found_in_text` 필드 포함 권장

---

## 9. 멀티에이전트 설계 시 고려사항

### 9.1 에이전트 분리 전략
- **옵션 A**: Table Validator + Infographic Validator (2개 에이전트)
- **옵션 B**: Table Validator + Infographic Validator × N (N+1개 에이전트, N=클러스터 수)

### 9.2 상태 관리
- Table Validator 결과를 Infographic Validator에 전달할지 결정
- 현재는 독립적 평가 (테이블 평가 결과가 인포그래픽 평가에 직접 영향 없음)

### 9.3 오류 처리
- 한 에이전트 실패 시 다른 에이전트 계속 실행
- 부분 실패 허용 (fail-fast 아님)

### 9.4 결과 집계
- 각 에이전트 결과를 통합하는 집계 로직 필요
- 클러스터별 결과를 리스트로 관리

---

## 10. 참고 자료

- **프롬프트 파일**: `3_Code/prompt/S5_*.md`
- **구현 코드**: `3_Code/src/05_s5_validator.py`
- **프롬프트 개선 가이드**: `0_Protocol/00_Governance/supporting/Prompt_governance/S1_Prompt_Improvement_Guide.md`
- **S1 스키마**: `0_Protocol/04_Step_Contracts/Step01_S1/S1_Stage1_Struct_JSON_Schema_Canonical.md`

---

**버전**: 1.0  
**최종 업데이트**: 2025-12-30

