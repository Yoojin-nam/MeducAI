# Multi-Infographic Clustering Implementation Plan

**작성일**: 2025-12-23  
**목적**: 각 단계별 구현 상세 계획

---

## 개요

이 문서는 Multi-Infographic Clustering 기능의 단계별 구현 계획을 정리합니다.

**참고 문서**:
- `Multi_Infographic_Clustering_Design_v2.md` - 전체 설계
- `S1_Stage1_Struct_JSON_Schema_v1.4_Extension.md` - 스키마 확장

---

## Phase 1: S1 확장

### 1.1 목표

S1에서 관련 entity를 자동으로 클러스터링하고, 각 cluster별로 인포그래픽 프롬프트를 생성합니다.

### 1.2 변경 사항

#### 1.2.1 S1 프롬프트 수정

**파일**: `3_Code/prompt/S1_SYSTEM__v12.md`

**추가 내용**:
```
────────────────────────
INFographic Clustering (Optional)
────────────────────────

13) Entity Clustering for Multi-Infographic (**OPTIONAL**)
- Analyze all entities in the master table.
- If 3 or more entities are semantically related enough to share one infographic, 
  group them into a cluster.
- Create 1-4 clusters, each containing 3-8 related entities.
- If all entities are best represented in a single infographic, omit clustering fields.

Clustering Rules:
- Each cluster should contain 3-8 related entities
- Maximum 4 clusters per group
- Minimum 1 cluster (if no clear grouping, use single infographic)
- Entities in the same cluster should be conceptually related 
  (same disease category, anatomical region, imaging pattern, etc.)

Output (if clustering is beneficial):
- entity_clusters: Array of cluster objects with cluster_id, entity_names, cluster_theme
- infographic_clusters: Array of infographic objects with cluster_id, infographic_style, 
  infographic_keywords_en, infographic_prompt_en

Output (if single infographic is best):
- Omit entity_clusters and infographic_clusters fields (default behavior)
```

**파일**: `3_Code/prompt/S1_USER_GROUP__v11.md`

**추가 내용** (Output 섹션):
```
**Output**:
Return **ONLY** the single JSON object required by **S1_SYSTEM**.

If clustering is beneficial (3+ related entities can share one infographic):
- Include entity_clusters and infographic_clusters fields
- Each cluster should have a distinct theme and infographic prompt

If single infographic is best:
- Omit entity_clusters and infographic_clusters fields (default behavior)
```

#### 1.2.2 S1 출력 스키마 확장

**파일**: `3_Code/src/01_generate_json.py`

**함수**: `validate_stage1()`

**추가 검증 로직**:
```python
def validate_stage1_clustering(s1_json: Dict[str, Any]) -> None:
    """Validate clustering fields if present."""
    entity_clusters = s1_json.get("entity_clusters")
    infographic_clusters = s1_json.get("infographic_clusters")
    
    # Both present or both absent
    if (entity_clusters is None) != (infographic_clusters is None):
        raise ValueError(
            "entity_clusters and infographic_clusters must both be present or both absent"
        )
    
    if entity_clusters is None:
        return  # No clustering, valid
    
    # Validate clustering structure
    if not isinstance(entity_clusters, list):
        raise ValueError("entity_clusters must be an array")
    
    if not isinstance(infographic_clusters, list):
        raise ValueError("infographic_clusters must be an array")
    
    if len(entity_clusters) != len(infographic_clusters):
        raise ValueError(
            f"entity_clusters and infographic_clusters must have same length "
            f"(got {len(entity_clusters)} vs {len(infographic_clusters)})"
        )
    
    if len(entity_clusters) < 1 or len(entity_clusters) > 4:
        raise ValueError(
            f"entity_clusters must have 1-4 clusters (got {len(entity_clusters)})"
        )
    
    # Validate each cluster
    all_entity_names = set()
    for i, cluster in enumerate(entity_clusters):
        cluster_id = cluster.get("cluster_id")
        entity_names = cluster.get("entity_names", [])
        cluster_theme = cluster.get("cluster_theme", "")
        
        if not cluster_id:
            raise ValueError(f"cluster {i+1} missing cluster_id")
        
        if not entity_names:
            raise ValueError(f"cluster {cluster_id} missing entity_names")
        
        if len(entity_names) < 3 or len(entity_names) > 8:
            raise ValueError(
                f"cluster {cluster_id} must have 3-8 entities (got {len(entity_names)})"
            )
        
        if not cluster_theme:
            raise ValueError(f"cluster {cluster_id} missing cluster_theme")
        
        # Check for duplicates
        for name in entity_names:
            if name in all_entity_names:
                raise ValueError(f"Entity '{name}' appears in multiple clusters")
            all_entity_names.add(name)
        
        # Validate corresponding infographic cluster
        infographic = infographic_clusters[i]
        if infographic.get("cluster_id") != cluster_id:
            raise ValueError(
                f"infographic_clusters[{i}].cluster_id mismatch "
                f"(expected {cluster_id}, got {infographic.get('cluster_id')})"
            )
        
        if not infographic.get("infographic_prompt_en"):
            raise ValueError(f"infographic_clusters[{i}] missing infographic_prompt_en")
    
    # Validate all entities are covered
    entity_list = s1_json.get("entity_list", [])
    entity_list_names = set()
    for entity in entity_list:
        if isinstance(entity, dict):
            name = entity.get("entity_name") or entity.get("name", "")
        else:
            name = str(entity)
        if name:
            entity_list_names.add(name.strip())
    
    if all_entity_names != entity_list_names:
        missing = entity_list_names - all_entity_names
        extra = all_entity_names - entity_list_names
        raise ValueError(
            f"Entity coverage mismatch: missing={missing}, extra={extra}"
        )
```

#### 1.2.3 S1 Gate 체크리스트 업데이트

**파일**: `0_Protocol/01_Execution_Safety/stabilization/s_1_gate_checklist_canonical.md`

**추가 검증 항목**:
- Level 3.5: Clustering validation (if present)
  - entity_clusters와 infographic_clusters co-presence 확인
  - Cluster 수 1-4개 확인
  - 각 cluster의 entity 수 3-8개 확인
  - 모든 entity가 정확히 하나의 cluster에 포함되는지 확인

### 1.3 테스트 계획

1. **단위 테스트**:
   - Clustering 없음 (기존 동작)
   - 1개 cluster
   - 2개 clusters
   - 4개 clusters (최대)
   - Invalid clustering (validation 실패)

2. **통합 테스트**:
   - S1 → S2 (clustering 필드 무시 확인)
   - S1 → S3 (clustering 필드 전달 확인)

---

## Phase 2: S3 수정

### 2.1 목표

S3에서 `entity_clusters`가 있으면 각 cluster별로 별도의 `S1_TABLE_VISUAL` 스펙을 생성합니다.

### 2.2 변경 사항

#### 2.2.1 함수 수정

**파일**: `3_Code/src/03_s3_policy_resolver.py`

**함수**: `compile_table_visual_spec()`

**시그니처 변경**:
```python
def compile_table_visual_spec(
    *,
    run_tag: str,
    group_id: str,
    s1_struct: Dict[str, Any],
    prompt_bundle: Optional[Dict[str, Any]] = None,
    cluster_id: Optional[str] = None,  # New parameter
    infographic_prompt: Optional[str] = None,  # New parameter (cluster-specific prompt)
) -> Dict[str, Any]:
```

**로직 변경**:
- `cluster_id`가 있으면 cluster-specific 처리
- `infographic_prompt`가 있으면 이를 사용 (기존 프롬프트 생성 로직 대신)

**새 함수 추가**: `compile_table_visual_specs_for_group()`
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
            cluster_id=None,
            infographic_prompt=None,
        )]
    
    # Clustering: return one spec per cluster
    specs = []
    master_table = s1_struct.get("master_table_markdown_kr", "")
    
    for cluster, infographic in zip(entity_clusters, infographic_clusters):
        cluster_id = cluster.get("cluster_id")
        cluster_entity_names = cluster.get("entity_names", [])
        
        # Extract cluster-specific table rows
        cluster_table = extract_cluster_table(
            master_table_markdown=master_table,
            entity_names=cluster_entity_names,
        )
        
        # Create cluster-specific s1_struct
        cluster_s1_struct = {
            **s1_struct,
            "master_table_markdown_kr": cluster_table,
        }
        
        # Use cluster-specific infographic prompt
        infographic_prompt = infographic.get("infographic_prompt_en")
        
        spec = compile_table_visual_spec(
            run_tag=run_tag,
            group_id=group_id,
            s1_struct=cluster_s1_struct,
            prompt_bundle=prompt_bundle,
            cluster_id=cluster_id,
            infographic_prompt=infographic_prompt,
        )
        specs.append(spec)
    
    return specs
```

**유틸리티 함수 추가**: `extract_cluster_table()`
```python
def extract_cluster_table(
    master_table_markdown: str,
    entity_names: List[str],
) -> str:
    """
    Extract rows from master table matching cluster entities.
    Returns markdown table with header, separator, and matching rows only.
    """
    lines = master_table_markdown.strip().split("\n")
    if not lines:
        return ""
    
    # Find header row
    header_idx = None
    for i, line in enumerate(lines):
        if "|" in line and "Entity name" in line:
            header_idx = i
            break
    
    if header_idx is None:
        return ""
    
    # Extract header and separator
    result_lines = [lines[header_idx], lines[header_idx + 1]]
    
    # Extract matching rows
    for line in lines[header_idx + 2:]:
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if cells and cells[0] in entity_names:
            result_lines.append(line)
    
    return "\n".join(result_lines)
```

#### 2.2.2 process_s3() 수정

**파일**: `3_Code/src/03_s3_policy_resolver.py`

**함수**: `process_s3()`

**변경 위치**: Table visual spec 생성 부분

**기존 코드**:
```python
# Generate table visual spec (once per group)
table_spec = compile_table_visual_spec(
    run_tag=run_tag,
    group_id=group_id,
    s1_struct=s1_struct,
    prompt_bundle=prompt_bundle,
)
f_spec.write(json.dumps(table_spec, ensure_ascii=False) + "\n")
```

**수정 코드**:
```python
# Generate table visual spec(s) (one per cluster if clustering, else one)
table_specs = compile_table_visual_specs_for_group(
    run_tag=run_tag,
    group_id=group_id,
    s1_struct=s1_struct,
    prompt_bundle=prompt_bundle,
)

for spec in table_specs:
    f_spec.write(json.dumps(spec, ensure_ascii=False) + "\n")
```

#### 2.2.3 스펙에 cluster_id 추가

**함수**: `compile_table_visual_spec()`

**추가 필드**:
```python
spec = {
    "schema_version": "S3_IMAGE_SPEC_v1.0",
    "run_tag": run_tag,
    "group_id": group_id,
    "entity_id": None,
    "entity_name": None,
    "card_role": None,
    "spec_kind": "S1_TABLE_VISUAL",
    "image_placement_final": "TABLE",
    "image_asset_required": True,
    "visual_type_category": visual_type,
    "template_id": f"TABLE_VISUAL_v1__{visual_type}",
    "prompt_en": prompt_en,
    "cluster_id": cluster_id,  # New: None for single, "cluster_1" etc for clusters
}
```

### 2.3 테스트 계획

1. **단위 테스트**:
   - `extract_cluster_table()` 함수 테스트
   - `compile_table_visual_specs_for_group()` 함수 테스트
   - Clustering 없음 → 1개 스펙
   - Clustering 있음 → N개 스펙

2. **통합 테스트**:
   - S1 → S3 → S4 전체 파이프라인
   - 여러 스펙 생성 확인

---

## Phase 3: S4 수정

### 3.1 목표

S4에서 여러 개의 `S1_TABLE_VISUAL` 스펙을 처리하여 각각에 대해 이미지를 생성합니다.

### 3.2 변경 사항

#### 3.2.1 파일명 생성 로직

**파일**: `3_Code/src/04_s4_image_generator.py`

**함수 추가/수정**: 이미지 파일명 생성

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

#### 3.2.2 이미지 생성 로직

**기존**: `spec_kind == "S1_TABLE_VISUAL"`인 스펙 1개만 처리

**수정**: 모든 `S1_TABLE_VISUAL` 스펙 처리

**변경 위치**: `process_s4()` 또는 이미지 생성 루프

**로직**:
```python
# Process all S1_TABLE_VISUAL specs (not just one)
for spec in image_specs:
    if spec.get("spec_kind") == "S1_TABLE_VISUAL":
        cluster_id = spec.get("cluster_id")
        
        # Generate filename
        filename = generate_infographic_filename(
            run_tag=spec.get("run_tag"),
            group_id=spec.get("group_id"),
            cluster_id=cluster_id,
        )
        
        output_path = images_dir / filename
        
        # Generate image
        generate_image(
            image_spec=spec,
            output_path=output_path,
            ...
        )
```

#### 3.2.3 이미지 매니페스트 업데이트

**매니페스트 키 형식**:
- 단일: `(S1_TABLE_VISUAL, None, None)`
- 클러스터: `(S1_TABLE_VISUAL, cluster_id, None)`

### 3.3 테스트 계획

1. **단위 테스트**:
   - 파일명 생성 테스트
   - 여러 스펙 처리 테스트

2. **통합 테스트**:
   - S3 → S4 → S5 전체 파이프라인
   - 여러 이미지 생성 확인

---

## Phase 4: S5 수정

### 4.1 목표

S5에서 여러 개의 인포그래픽을 PDF에 순차적으로 배치합니다.

### 4.2 변경 사항

#### 4.2.1 함수 수정

**파일**: `3_Code/src/07_build_set_pdf.py`

**함수**: `build_infographic_section()`

**시그니처 변경**:
```python
def build_infographic_section(
    story: List,
    image_path: Optional[str],
    custom_styles: Dict[str, ParagraphStyle],
    allow_missing: bool = False,
    page_width: Optional[float] = None,
    page_height: Optional[float] = None,
    optimize_images: bool = True,
    image_max_dpi: float = 150.0,
    image_jpeg_quality: int = 90,
    s1_record: Optional[Dict[str, Any]] = None,
    korean_font_bold: Optional[str] = None,
    cluster_info: Optional[Dict[str, str]] = None,  # New parameter
) -> None:
```

**로직 변경**: Cluster theme 표시 (선택적)

#### 4.2.2 여러 인포그래픽 배치 로직

**함수**: `build_set_pdf()`

**변경 위치**: Infographic 섹션 생성 부분

**기존 코드**:
```python
# Section 2: Infographic (with header, full page)
infographic_path = image_mapping.get(("S1_TABLE_VISUAL", None, None))
if infographic_path:
    build_infographic_section(
        story, infographic_path, custom_styles, ...
    )
```

**수정 코드**:
```python
# Section 2: Infographic(s) (with header, full page)
entity_clusters = s1_record.get("entity_clusters", []) if s1_record else []

if not entity_clusters:
    # Single infographic (existing behavior)
    infographic_path = image_mapping.get(("S1_TABLE_VISUAL", None, None))
    if infographic_path:
        build_infographic_section(
            story, infographic_path, custom_styles, ...,
            cluster_info=None,
        )
else:
    # Multiple infographics (one per cluster)
    for cluster in entity_clusters:
        cluster_id = cluster.get("cluster_id")
        cluster_theme = cluster.get("cluster_theme", "")
        
        infographic_path = image_mapping.get(("S1_TABLE_VISUAL", cluster_id, None))
        if infographic_path:
            build_infographic_section(
                story, infographic_path, custom_styles, ...,
                cluster_info={
                    "cluster_id": cluster_id,
                    "cluster_theme": cluster_theme,
                },
            )
```

### 4.3 테스트 계획

1. **단위 테스트**:
   - 여러 인포그래픽 배치 테스트
   - Cluster 정보 표시 테스트

2. **통합 테스트**:
   - S1 → S5 전체 파이프라인
   - PDF에 여러 인포그래픽 포함 확인

---

## 전체 테스트 시나리오

### 시나리오 1: Clustering 없음
1. S1: entity_clusters 없음
2. S3: 1개 스펙 생성
3. S4: 1개 이미지 생성
4. S5: 1개 인포그래픽 배치

### 시나리오 2: 2개 Cluster
1. S1: entity_clusters 2개
2. S3: 2개 스펙 생성
3. S4: 2개 이미지 생성
4. S5: 2개 인포그래픽 배치

### 시나리오 3: 4개 Cluster (최대)
1. S1: entity_clusters 4개
2. S3: 4개 스펙 생성
3. S4: 4개 이미지 생성
4. S5: 4개 인포그래픽 배치

---

## 롤아웃 계획

1. **Phase 1**: S1 확장 (프롬프트 + validation)
2. **Phase 2**: S3 수정 (여러 스펙 생성)
3. **Phase 3**: S4 수정 (여러 이미지 생성)
4. **Phase 4**: S5 수정 (여러 인포그래픽 배치)

각 Phase는 독립적으로 테스트 가능하며, 이전 Phase가 완료되어야 다음 Phase 진행 가능.

