# Multi-Infographic Clustering Design v2

**작성일**: 2025-12-23  
**버전**: 2.0  
**목적**: 관련 entity를 그룹화하여 여러 인포그래픽 생성 (스마트 클러스터링)

---

## 핵심 요구사항

### Clustering 조건
- **기존**: entity 개수가 8개 이상일 때만 clustering 시행
- **변경**: **같은 infographic으로 묶을 만한 entity가 3개 이상일 때** 하나의 group으로 묶기
- **Cluster 수**: 하나의 그룹당 **1개에서 4개까지**의 cluster

### 동작 원리
1. S1에서 모든 entity를 분석
2. 관련 있는 entity들을 찾아서 3개 이상이면 하나의 cluster로 묶음
3. Cluster가 1-4개 생성됨
4. 각 cluster별로 별도의 인포그래픽 생성

---

## 1. S1 확장: 스마트 Clustering

### 1.1 Clustering 로직

**조건**: 
- Entity가 3개 이상이고, 같은 infographic으로 묶을 만한 entity가 3개 이상일 때 clustering 수행
- 모든 entity가 관련이 없으면 clustering 없이 단일 인포그래픽 (기존 동작)

**방법**: S1 LLM (gemini-3-pro-preview)에서 직접 clustering 수행

**Clustering 프롬프트 구조**:
```
You are analyzing medical entities for infographic generation.

Given the master table and entity list, determine if entities can be grouped 
into semantically related clusters for separate infographics.

Rules:
- If 3 or more entities are semantically related enough to share one infographic, 
  group them into a cluster
- Each cluster should contain 3-8 related entities
- Maximum 4 clusters per group
- Minimum 1 cluster (if no clear grouping, use single cluster with all entities)
- Entities in the same cluster should be conceptually related 
  (same disease category, anatomical region, imaging pattern, etc.)

Output:
- If clustering is beneficial: return entity_clusters and infographic_clusters
- If all entities are best represented in one infographic: omit these fields (use default single infographic)
```

### 1.2 S1 출력 스키마 확장 (v1.4)

**기존 스키마 (v1.3)**:
```json
{
  "schema_version": "S1_STRUCT_v1.3",
  "group_id": "...",
  "group_path": "...",
  "objective_bullets": ["..."],
  "visual_type_category": "...",
  "master_table_markdown_kr": "...",
  "entity_list": [
    {
      "entity_id": "...",
      "entity_name": "..."
    }
  ],
  "integrity": {...}
}
```

**확장 스키마 (v1.4)** - Optional fields 추가:
```json
{
  "schema_version": "S1_STRUCT_v1.4",
  "group_id": "...",
  "group_path": "...",
  "objective_bullets": ["..."],
  "visual_type_category": "...",
  "master_table_markdown_kr": "...",
  "entity_list": [
    {
      "entity_id": "...",
      "entity_name": "..."
    }
  ],
  "integrity": {...},
  
  // Optional: Clustering fields (present only when clustering is beneficial)
  "entity_clusters": [
    {
      "cluster_id": "cluster_1",
      "entity_names": ["entity1", "entity2", "entity3", ...],
      "cluster_theme": "Brief theme description (e.g., 'Benign bone tumors')"
    },
    {
      "cluster_id": "cluster_2",
      "entity_names": ["entity4", "entity5", "entity6", ...],
      "cluster_theme": "Brief theme description"
    }
  ],
  "infographic_clusters": [
    {
      "cluster_id": "cluster_1",
      "infographic_style": "Anatomy_Map",
      "infographic_keywords_en": "10-25 words, comma-separated",
      "infographic_prompt_en": "Full English prompt for image generation"
    },
    {
      "cluster_id": "cluster_2",
      "infographic_style": "Pathology_Pattern",
      "infographic_keywords_en": "10-25 words, comma-separated",
      "infographic_prompt_en": "Full English prompt for image generation"
    }
  ]
}
```

### 1.3 필드 규칙

**Optional 필드**:
- `entity_clusters`: 배열, 길이 1-4
- `infographic_clusters`: 배열, 길이 1-4 (entity_clusters와 동일한 길이)

**조건부 동작**:
- `entity_clusters`가 **없으면**: 기존 동작 (단일 인포그래픽)
- `entity_clusters`가 **있으면**: 각 cluster별로 별도 인포그래픽 생성

**Validation 규칙**:
1. `entity_clusters`와 `infographic_clusters`는 둘 다 있거나 둘 다 없어야 함
2. 두 배열의 길이는 동일해야 함
3. `entity_clusters`의 각 cluster는 3-8개의 entity를 포함해야 함
4. 모든 entity는 정확히 하나의 cluster에 포함되어야 함
5. Cluster 수는 1-4개여야 함

### 1.4 Cluster ID 형식

**권장 형식**: `cluster_{index}` (1-based)
- `cluster_1`, `cluster_2`, `cluster_3`, `cluster_4`

**Entity 매핑**:
- 각 cluster의 `entity_names`는 `entity_list`의 `entity_name`과 정확히 일치해야 함

---

## 2. S3 수정: 여러 개의 S1_TABLE_VISUAL 스펙 생성

### 2.1 현재 동작

**파일**: `3_Code/src/03_s3_policy_resolver.py`

**함수**: `compile_table_visual_spec()`
- 입력: `s1_struct` (단일 그룹)
- 출력: 1개의 S1_TABLE_VISUAL 스펙

**호출 위치**: `process_s3()`
- 각 그룹당 1회 호출

### 2.2 수정 후 동작

**함수 수정**: `compile_table_visual_spec()`
- 입력: `s1_struct` (단일 그룹)
- 출력: 1개 또는 여러 개의 S1_TABLE_VISUAL 스펙

**로직**:
```python
def compile_table_visual_specs_for_group(
    *,
    run_tag: str,
    group_id: str,
    s1_struct: Dict[str, Any],
    prompt_bundle: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Compile S1 table visual specs for group-level image generation.
    Returns list of specs (1 if no clustering, 1-4 if clustering).
    """
    entity_clusters = s1_struct.get("entity_clusters", [])
    infographic_clusters = s1_struct.get("infographic_clusters", [])
    
    if not entity_clusters or not infographic_clusters:
        # No clustering: return single spec (existing behavior)
        return [compile_table_visual_spec(
            run_tag=run_tag,
            group_id=group_id,
            s1_struct=s1_struct,
            prompt_bundle=prompt_bundle,
            cluster_id=None,  # No cluster
        )]
    
    # Clustering: return one spec per cluster
    specs = []
    for cluster, infographic in zip(entity_clusters, infographic_clusters):
        cluster_id = cluster.get("cluster_id")
        
        # Extract cluster-specific table rows
        cluster_entity_names = cluster.get("entity_names", [])
        cluster_table = extract_cluster_table(
            master_table_markdown=s1_struct.get("master_table_markdown_kr", ""),
            entity_names=cluster_entity_names,
        )
        
        # Create cluster-specific s1_struct
        cluster_s1_struct = {
            **s1_struct,
            "master_table_markdown_kr": cluster_table,  # Override with cluster table
        }
        
        spec = compile_table_visual_spec(
            run_tag=run_tag,
            group_id=group_id,
            s1_struct=cluster_s1_struct,
            prompt_bundle=prompt_bundle,
            cluster_id=cluster_id,
            infographic_prompt=infographic.get("infographic_prompt_en"),  # Use cluster-specific prompt
        )
        specs.append(spec)
    
    return specs
```

### 2.3 스펙 식별자 변경

**기존**:
- `(S1_TABLE_VISUAL, None, None)`

**수정**:
- 단일 인포그래픽: `(S1_TABLE_VISUAL, None, None)` (기존과 동일)
- 클러스터 인포그래픽: `(S1_TABLE_VISUAL, cluster_id, None)`

**스펙 구조**:
```json
{
  "schema_version": "S3_IMAGE_SPEC_v1.0",
  "run_tag": "...",
  "group_id": "...",
  "entity_id": null,
  "entity_name": null,
  "card_role": null,
  "spec_kind": "S1_TABLE_VISUAL",
  "image_placement_final": "TABLE",
  "image_asset_required": true,
  "visual_type_category": "...",
  "template_id": "...",
  "prompt_en": "...",
  "cluster_id": "cluster_1"  // New: present only when clustering
}
```

### 2.4 파일명 형식

**기존**:
- `IMG__{run_tag}__{group_id}__TABLE.png`

**수정**:
- 단일 인포그래픽: `IMG__{run_tag}__{group_id}__TABLE.png` (기존과 동일)
- 클러스터 인포그래픽: `IMG__{run_tag}__{group_id}__TABLE__{cluster_id}.png`

**예시**:
- `IMG__RUN_20251223__G001__TABLE.png` (단일)
- `IMG__RUN_20251223__G001__TABLE__cluster_1.png` (클러스터 1)
- `IMG__RUN_20251223__G001__TABLE__cluster_2.png` (클러스터 2)

---

## 3. S4 수정: 여러 개의 인포그래픽 이미지 생성 지원

### 3.1 현재 동작

**파일**: `3_Code/src/04_s4_image_generator.py`

**동작**:
- S1_TABLE_VISUAL 스펙 1개 → 이미지 1개 생성
- 파일명: `IMG__{run_tag}__{group_id}__TABLE.png`

### 3.2 수정 후 동작

**동작**:
- S1_TABLE_VISUAL 스펙 N개 → 이미지 N개 생성
- 각 스펙의 `cluster_id`를 파일명에 포함

**로직 변경**:
- 기존: `spec_kind == "S1_TABLE_VISUAL"`인 스펙 1개 처리
- 수정: `spec_kind == "S1_TABLE_VISUAL"`인 모든 스펙 처리

**파일명 생성**:
```python
def generate_infographic_filename(
    run_tag: str,
    group_id: str,
    cluster_id: Optional[str] = None,
) -> str:
    """Generate infographic filename."""
    if cluster_id:
        return f"IMG__{run_tag}__{group_id}__TABLE__{cluster_id}.png"
    else:
        return f"IMG__{run_tag}__{group_id}__TABLE.png"
```

### 3.3 이미지 매니페스트 업데이트

**기존 매핑**:
```json
{
  "spec_kind": "S1_TABLE_VISUAL",
  "entity_id": null,
  "card_role": null
} -> "IMG__{run_tag}__{group_id}__TABLE.png"
```

**수정 매핑**:
```json
{
  "spec_kind": "S1_TABLE_VISUAL",
  "entity_id": null,
  "card_role": null,
  "cluster_id": null
} -> "IMG__{run_tag}__{group_id}__TABLE.png"

{
  "spec_kind": "S1_TABLE_VISUAL",
  "entity_id": null,
  "card_role": null,
  "cluster_id": "cluster_1"
} -> "IMG__{run_tag}__{group_id}__TABLE__cluster_1.png"
```

---

## 4. S5 수정: 여러 개의 인포그래픽을 PDF에 배치

### 4.1 현재 동작

**파일**: `3_Code/src/07_build_set_pdf.py`

**함수**: `build_infographic_section()`
- 입력: `image_path` (단일 이미지 경로)
- 동작: 인포그래픽 1개를 PDF에 배치

**호출 위치**: `build_set_pdf()`
- `image_mapping.get(("S1_TABLE_VISUAL", None, None))` → 단일 이미지 경로

### 4.2 수정 후 동작

**함수 수정**: `build_infographic_section()`
- 입력: `image_paths` (이미지 경로 리스트)
- 동작: 여러 개의 인포그래픽을 순차적으로 PDF에 배치

**로직**:
```python
def build_infographic_sections(
    story: List,
    image_mapping: Dict[Tuple[str, Optional[str], Optional[str]], str],
    custom_styles: Dict[str, ParagraphStyle],
    s1_record: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> None:
    """Build infographic sections - one per cluster."""
    
    entity_clusters = s1_record.get("entity_clusters", []) if s1_record else []
    
    if not entity_clusters:
        # Single infographic (existing behavior)
        image_path = image_mapping.get(("S1_TABLE_VISUAL", None, None))
        if image_path:
            build_infographic_section(
                story=story,
                image_path=image_path,
                custom_styles=custom_styles,
                s1_record=s1_record,
                cluster_info=None,
                **kwargs,
            )
    else:
        # Multiple infographics (one per cluster)
        for cluster in entity_clusters:
            cluster_id = cluster.get("cluster_id")
            cluster_theme = cluster.get("cluster_theme", "")
            
            image_path = image_mapping.get(("S1_TABLE_VISUAL", cluster_id, None))
            if image_path:
                build_infographic_section(
                    story=story,
                    image_path=image_path,
                    custom_styles=custom_styles,
                    s1_record=s1_record,
                    cluster_info={
                        "cluster_id": cluster_id,
                        "cluster_theme": cluster_theme,
                    },
                    **kwargs,
                )
```

### 4.3 Cluster 정보 표시 (선택적)

**옵션 1**: Cluster theme을 헤더에 표시
```python
def build_infographic_section(
    ...,
    cluster_info: Optional[Dict[str, str]] = None,
) -> None:
    """Build Infographic section with optional cluster theme."""
    
    # Header with cluster theme if available
    if cluster_info and cluster_info.get("cluster_theme"):
        theme_text = cluster_info["cluster_theme"]
        story.append(Paragraph(
            f"{header_text} | Infographic: {theme_text}",
            section_label_style
        ))
    else:
        story.append(Paragraph(
            f"{header_text} | Infographic",
            section_label_style
        ))
    
    # ... rest of the function
```

**옵션 2**: Cluster 정보를 별도 섹션으로 표시하지 않고 순차 배치만

---

## 5. 스키마 버전 관리

### 5.1 S1 스키마 버전

- **기존**: `S1_STRUCT_v1.3` (FROZEN)
- **확장**: `S1_STRUCT_v1.4` (optional fields 추가)

**하위 호환성**:
- v1.3 스키마는 v1.4에서도 유효 (optional fields 없음)
- v1.4 스키마는 v1.3에서도 처리 가능 (optional fields 무시)

### 5.2 S3 스펙 스키마 버전

- **기존**: `S3_IMAGE_SPEC_v1.0`
- **확장**: `S3_IMAGE_SPEC_v1.0` (기존 유지, `cluster_id` 필드 추가)

**하위 호환성**:
- `cluster_id` 필드는 optional
- 기존 스펙은 `cluster_id` 없이 동작

### 5.3 마이그레이션 전략

1. **기존 데이터**: `entity_clusters` 없음 → 단일 인포그래픽 (기존 동작)
2. **새 데이터**: `entity_clusters` 있음 → 여러 인포그래픽 (새 동작)
3. **혼합 환경**: 두 가지 모두 지원

---

## 6. 구현 체크리스트

### Phase 1: S1 확장
- [ ] S1 프롬프트에 clustering 지시사항 추가
- [ ] S1 출력 스키마에 `entity_clusters`, `infographic_clusters` 필드 추가 (optional)
- [ ] S1 validation 로직에 clustering 필드 검증 추가
- [ ] S1 Gate 체크리스트 업데이트

### Phase 2: S3 수정
- [ ] `compile_table_visual_spec()` 함수에 `cluster_id` 파라미터 추가
- [ ] `compile_table_visual_specs_for_group()` 함수 생성
- [ ] `process_s3()` 함수에서 여러 스펙 생성 로직 추가
- [ ] 스펙에 `cluster_id` 필드 추가

### Phase 3: S4 수정
- [ ] 여러 개의 S1_TABLE_VISUAL 스펙 처리 지원
- [ ] 파일명에 `cluster_id` 포함 로직 추가
- [ ] 이미지 매니페스트에 `cluster_id` 매핑 추가

### Phase 4: S5 수정
- [ ] `build_infographic_sections()` 함수 생성
- [ ] 여러 개의 인포그래픽 배치 로직 추가
- [ ] Cluster 정보 표시 옵션 추가 (선택적)

---

## 7. 테스트 시나리오

### 시나리오 1: Clustering 없음 (기존 동작)
- **Input**: entity_clusters 없음
- **Expected**: 단일 인포그래픽 생성
- **Output**: `IMG__{run_tag}__{group_id}__TABLE.png`

### 시나리오 2: 2개 Cluster
- **Input**: entity_clusters 2개
- **Expected**: 2개 인포그래픽 생성
- **Output**: 
  - `IMG__{run_tag}__{group_id}__TABLE__cluster_1.png`
  - `IMG__{run_tag}__{group_id}__TABLE__cluster_2.png`

### 시나리오 3: 4개 Cluster (최대)
- **Input**: entity_clusters 4개
- **Expected**: 4개 인포그래픽 생성
- **Output**: 4개 파일 (cluster_1 ~ cluster_4)

### 시나리오 4: Entity 3개 미만 (Clustering 불가)
- **Input**: entity_list 2개
- **Expected**: 단일 인포그래픽 (clustering 없음)
- **Output**: `IMG__{run_tag}__{group_id}__TABLE.png`

---

## 8. 비용 및 성능 고려사항

### LLM 호출 비용
- **Clustering**: S1 LLM에서 직접 수행 (추가 호출 없음)
- **비용 증가**: 없음 (기존 S1 호출에 포함)

### 이미지 생성 비용
- **기존**: 1개 인포그래픽
- **수정**: 1-4개 인포그래픽 (cluster 수에 따라)
- **예상 비용 증가**: 1-4배 (cluster 수에 따라)

### 성능 영향
- **S1**: 추가 처리 없음 (LLM이 clustering 포함)
- **S3**: 여러 스펙 생성 (N배 시간, N은 cluster 수)
- **S4**: 여러 이미지 생성 (N배 시간)
- **S5**: 여러 인포그래픽 배치 (N배 시간)

---

## 9. 하위 호환성

### 기존 데이터 호환
- `entity_clusters` 없음 → 기존 동작 (단일 인포그래픽)
- `entity_clusters` 있음 → 새로운 동작 (여러 인포그래픽)

### 스키마 버전
- **S1**: v1.3 → v1.4 (optional fields 추가)
- **S3**: v1.0 유지 (optional field 추가)
- **S4**: 변경 없음
- **S5**: 변경 없음 (로직만 수정)

---

## 10. 참고사항

- Clustering은 **선택적 기능** (LLM이 판단)
- 기존 동작은 그대로 유지 (하위 호환성)
- Cluster 수는 1-4개로 제한
- 각 cluster는 3-8개 entity 포함

