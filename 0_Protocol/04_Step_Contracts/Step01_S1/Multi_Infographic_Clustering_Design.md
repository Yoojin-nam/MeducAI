# Multi-Infographic Clustering Design

**작성일**: 2025-12-23  
**목적**: 테이블 entity가 많을 때 (8개 초과) 관련 entity를 그룹화하여 여러 인포그래픽 생성

---

## 문제 상황

- 테이블에 entity가 많을 때 (15-20개) 하나의 인포그래픽으로 표현하기 어려움
- LLM 없이 단순히 나누면 상관 없는 entity들이 묶일 우려
- 관련 있는 entity들을 최대 8개까지 묶어서 1~3개의 인포그래픽 생성 필요

---

## 해결 방안

### 1. Entity Clustering (S1 단계)

**조건**: `entity_list`가 8개 초과일 때만 실행

**방법**: 가벼운 LLM을 사용하여 semantic clustering 수행

**LLM 선택**:
- GPT-3.5-turbo (가벼움, 저렴, 빠름)
- Claude Haiku (가벼움, 저렴)
- Gemini Flash (가벼움, 저렴)

**Clustering 프롬프트 구조**:
```
You are a medical knowledge clustering assistant.

Given a list of medical entities from a radiology board exam table, 
group them into semantically related clusters.

Rules:
- Each cluster should contain 3-8 related entities
- Entities in the same cluster should be conceptually related
- Maximum 3 clusters total
- If entity count <= 8, return single cluster with all entities

Input:
- Entity list: [entity names]
- Master table context: [relevant rows from table]
- Visual type category: [category]

Output JSON:
{
  "clusters": [
    {
      "cluster_id": "cluster_1",
      "entity_names": ["entity1", "entity2", ...],
      "cluster_theme": "Brief theme description"
    },
    ...
  ]
}
```

### 2. S1 출력 스키마 확장

**기존 스키마**:
```json
{
  "visual_type_category": "...",
  "master_table_markdown_kr": "...",
  "entity_list": ["..."]
}
```

**확장 스키마** (entity_list > 8일 때):
```json
{
  "visual_type_category": "...",
  "master_table_markdown_kr": "...",
  "entity_list": ["..."],
  "entity_clusters": [
    {
      "cluster_id": "cluster_1",
      "entity_names": ["entity1", "entity2", ...],
      "cluster_theme": "Brief theme description"
    },
    ...
  ],
  "infographic_clusters": [
    {
      "cluster_id": "cluster_1",
      "infographic_style": "Anatomy_Map",
      "infographic_keywords_en": "10-25 words",
      "infographic_prompt_en": "Full prompt for this cluster"
    },
    ...
  ]
}
```

**조건부 필드**:
- `entity_list` <= 8: `entity_clusters`와 `infographic_clusters` 생략 가능 (기존 동작)
- `entity_list` > 8: `entity_clusters`와 `infographic_clusters` 필수

### 3. S3 수정: 여러 개의 S1_TABLE_VISUAL 스펙 생성

**현재 동작**:
- `compile_table_visual_spec()` 호출 → 1개의 S1_TABLE_VISUAL 스펙 생성

**수정 후 동작**:
- `entity_clusters`가 있으면: 각 cluster별로 `compile_table_visual_spec()` 호출
- `entity_clusters`가 없으면: 기존 동작 (1개 스펙 생성)

**스펙 식별자**:
- 기존: `(S1_TABLE_VISUAL, None, None)`
- 수정: `(S1_TABLE_VISUAL, cluster_id, None)`

**파일명 형식**:
- 기존: `IMG__{run_tag}__{group_id}__TABLE.png`
- 수정: `IMG__{run_tag}__{group_id}__TABLE__{cluster_id}.png`

### 4. S4 수정: 여러 개의 인포그래픽 이미지 생성

**현재 동작**:
- S1_TABLE_VISUAL 스펙 1개 → 이미지 1개 생성

**수정 후 동작**:
- S1_TABLE_VISUAL 스펙 N개 → 이미지 N개 생성
- 각 스펙의 `cluster_id`를 파일명에 포함

### 5. S5 수정: 여러 개의 인포그래픽을 PDF에 배치

**현재 동작**:
- `build_infographic_section()` 호출 → 인포그래픽 1개 배치

**수정 후 동작**:
- `infographic_clusters`가 있으면: 각 cluster별로 `build_infographic_section()` 호출
- 각 인포그래픽에 cluster_theme 표시 (선택적)

---

## 구현 단계

### Phase 1: S1 Clustering 로직 추가
1. S1에서 `entity_list` 길이 확인
2. 8개 초과일 때 clustering LLM 호출
3. 각 cluster별로 인포그래픽 프롬프트 생성
4. 출력 스키마에 `entity_clusters`와 `infographic_clusters` 추가

### Phase 2: S3 수정
1. `compile_table_visual_spec()` 수정: cluster별 스펙 생성 지원
2. `process_s3()` 수정: 여러 개의 S1_TABLE_VISUAL 스펙 생성

### Phase 3: S4 수정
1. 여러 개의 S1_TABLE_VISUAL 스펙 처리 지원
2. 파일명에 `cluster_id` 포함

### Phase 4: S5 수정
1. `build_infographic_section()` 수정: 여러 개의 인포그래픽 배치 지원
2. 각 인포그래픽에 cluster 정보 표시 (선택적)

---

## 비용 및 성능 고려사항

### LLM 호출 비용
- Clustering: entity_list > 8일 때만 1회 호출
- 가벼운 모델 사용 (GPT-3.5-turbo 등)
- 예상 비용: $0.001-0.01 per group (entity 수에 따라)

### 이미지 생성 비용
- 기존: 1개 인포그래픽
- 수정: 1-3개 인포그래픽 (cluster 수에 따라)
- 예상 비용 증가: 1-3배 (cluster 수에 따라)

### 성능 영향
- Clustering LLM 호출: +1-2초 per group (entity > 8일 때만)
- 이미지 생성: cluster 수만큼 증가
- 전체 파이프라인 영향: 미미 (entity > 8인 그룹이 적을 경우)

---

## 하위 호환성

### 기존 데이터 호환
- `entity_clusters`가 없으면: 기존 동작 (1개 인포그래픽)
- `entity_clusters`가 있으면: 새로운 동작 (여러 인포그래픽)

### 스키마 버전
- 기존: `S1_STRUCT_v1.3`
- 수정: `S1_STRUCT_v1.4` (optional fields 추가)

---

## 테스트 계획

1. **단위 테스트**:
   - Clustering 로직 테스트 (entity_list > 8)
   - 기존 동작 테스트 (entity_list <= 8)

2. **통합 테스트**:
   - S1 → S3 → S4 → S5 전체 파이프라인 테스트
   - 여러 인포그래픽 생성 및 PDF 배치 확인

3. **성능 테스트**:
   - Clustering LLM 호출 시간 측정
   - 이미지 생성 시간 측정

---

## 참고사항

- Clustering은 선택적 기능 (entity_list > 8일 때만)
- 기존 동작은 그대로 유지 (하위 호환성)
- 가벼운 LLM 사용으로 비용 최소화
- Cluster 수는 최대 3개로 제한 (인포그래픽 수 관리)

