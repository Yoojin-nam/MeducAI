"""
Entity Clustering Utility for Multi-Infographic Generation

When entity_list has more than 8 entities, this module clusters them
into semantically related groups (3-8 entities per cluster, max 3 clusters).
"""

from __future__ import annotations

import json
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path


def cluster_entities_with_llm(
    *,
    entity_list: List[str],
    master_table_markdown: str,
    visual_type_category: str,
    provider: str,
    clients: Any,
    model_name: str = "gpt-3.5-turbo",
    temperature: float = 0.3,
    timeout_s: int = 30,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Cluster entities into semantically related groups using a lightweight LLM.
    
    Args:
        entity_list: List of entity names
        master_table_markdown: Full master table markdown for context
        visual_type_category: Visual type category (e.g., "Pathology_Pattern")
        provider: LLM provider name
        clients: Provider clients object
        model_name: Model name (default: gpt-3.5-turbo for lightweight)
        temperature: Temperature for clustering (lower = more deterministic)
        timeout_s: Timeout in seconds
    
    Returns:
        (clusters, error_message): List of cluster dicts and optional error message
    """
    if len(entity_list) <= 8:
        # No clustering needed - return single cluster with all entities
        return [
            {
                "cluster_id": "cluster_1",
                "entity_names": entity_list,
                "cluster_theme": "All entities"
            }
        ], None
    
    # Build clustering prompt
    system_prompt = """You are a medical knowledge clustering assistant for radiology board exam content.

Your task is to group medical entities into semantically related clusters for infographic generation.

Rules:
- Each cluster should contain 3-8 related entities
- Entities in the same cluster should be conceptually related (same disease category, anatomical region, imaging pattern, etc.)
- Maximum 3 clusters total
- If entities are all closely related, use fewer clusters
- Cluster themes should be concise and descriptive

Output ONLY valid JSON matching the schema. No extra text."""

    user_prompt = f"""Given the following medical entities from a radiology board exam table, 
group them into semantically related clusters for infographic generation.

Visual Type Category: {visual_type_category}
Entity Count: {len(entity_list)}

Entity List:
{json.dumps(entity_list, ensure_ascii=False, indent=2)}

Master Table Context (first 3 columns of relevant rows):
{_extract_table_context(master_table_markdown, entity_list)}

Output JSON schema:
{{
  "clusters": [
    {{
      "cluster_id": "cluster_1",
      "entity_names": ["entity1", "entity2", ...],
      "cluster_theme": "Brief theme description (e.g., 'Benign bone tumors', 'Lung cancer staging')"
    }},
    ...
  ]
}}

Ensure:
- All entities are included in exactly one cluster
- Each cluster has 3-8 entities
- Maximum 3 clusters
- Cluster themes are concise and descriptive"""

    try:
        # Call LLM
        if provider.lower() == "openai":
            from openai import OpenAI
            client = clients.get("openai")
            if not client:
                return [], "OpenAI client not available"
            
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                response_format={"type": "json_object"},
                timeout=timeout_s,
            )
            result_text = response.choices[0].message.content
        elif provider.lower() == "anthropic":
            import anthropic
            client = clients.get("anthropic")
            if not client:
                return [], "Anthropic client not available"
            
            response = client.messages.create(
                model=model_name,
                max_tokens=2000,
                temperature=temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
                timeout=timeout_s,
            )
            result_text = response.content[0].text
        elif provider.lower() == "google":
            import google.generativeai as genai
            client = clients.get("google")
            if not client:
                return [], "Google client not available"
            
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(
                f"{system_prompt}\n\n{user_prompt}",
                generation_config={
                    "temperature": temperature,
                    "response_mime_type": "application/json",
                },
            )
            result_text = response.text
        else:
            return [], f"Unsupported provider: {provider}"
        
        # Parse JSON response
        result = json.loads(result_text)
        clusters = result.get("clusters", [])
        
        # Validate clusters
        all_entity_names = set(entity_list)
        clustered_entities = set()
        
        for cluster in clusters:
            cluster_entities = cluster.get("entity_names", [])
            clustered_entities.update(cluster_entities)
            
            # Validate cluster size
            if len(cluster_entities) < 3 or len(cluster_entities) > 8:
                return [], f"Invalid cluster size: {len(cluster_entities)} (must be 3-8)"
            
            # Ensure cluster_id exists
            if "cluster_id" not in cluster:
                cluster["cluster_id"] = f"cluster_{len(clusters)}"
        
        # Validate all entities are included
        if clustered_entities != all_entity_names:
            missing = all_entity_names - clustered_entities
            extra = clustered_entities - all_entity_names
            return [], f"Entity mismatch: missing={missing}, extra={extra}"
        
        # Validate cluster count
        if len(clusters) > 3:
            return [], f"Too many clusters: {len(clusters)} (max 3)"
        
        return clusters, None
        
    except json.JSONDecodeError as e:
        return [], f"Invalid JSON response: {e}"
    except Exception as e:
        return [], f"Clustering error: {e}"


def _extract_table_context(master_table_markdown: str, entity_list: List[str]) -> str:
    """Extract relevant rows from master table for context."""
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
    
    # Extract rows matching entities
    relevant_rows = []
    for line in lines[header_idx + 2:]:  # Skip header and separator
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]  # Remove empty first/last
        if cells and cells[0] in entity_list:
            # Include first 3 columns only
            relevant_rows.append(" | ".join(cells[:3]))
    
    return "\n".join(relevant_rows[:10])  # Limit to 10 rows


def generate_infographic_prompts_for_clusters(
    *,
    clusters: List[Dict[str, Any]],
    master_table_markdown: str,
    visual_type_category: str,
    group_id: str,
    group_path: str,
) -> List[Dict[str, Any]]:
    """
    Generate infographic prompts for each cluster.
    
    Args:
        clusters: List of cluster dicts from clustering
        master_table_markdown: Full master table markdown
        visual_type_category: Visual type category
        group_id: Group identifier
        group_path: Group path
    
    Returns:
        List of infographic cluster dicts with prompts
    """
    infographic_clusters = []
    
    for cluster in clusters:
        cluster_id = cluster.get("cluster_id", "cluster_1")
        entity_names = cluster.get("entity_names", [])
        cluster_theme = cluster.get("cluster_theme", "")
        
        # Extract relevant rows from master table for this cluster
        cluster_table = _extract_cluster_table(master_table_markdown, entity_names)
        
        # Generate keywords (simplified - can be enhanced with LLM)
        keywords = _generate_keywords_for_cluster(entity_names, cluster_theme, visual_type_category)
        
        # Generate prompt (simplified - can be enhanced with LLM)
        prompt = _generate_infographic_prompt(
            cluster_table=cluster_table,
            entity_names=entity_names,
            cluster_theme=cluster_theme,
            visual_type_category=visual_type_category,
            group_path=group_path,
        )
        
        infographic_clusters.append({
            "cluster_id": cluster_id,
            "infographic_style": _get_infographic_style(visual_type_category),
            "infographic_keywords_en": keywords,
            "infographic_prompt_en": prompt,
        })
    
    return infographic_clusters


def _extract_cluster_table(master_table_markdown: str, entity_names: List[str]) -> str:
    """Extract rows from master table matching cluster entities."""
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


def _generate_keywords_for_cluster(
    entity_names: List[str],
    cluster_theme: str,
    visual_type_category: str,
) -> str:
    """Generate keywords for cluster infographic."""
    keywords = [visual_type_category.replace("_", " ").lower()]
    keywords.extend(entity_names[:5])  # Limit to 5 entities
    if cluster_theme:
        keywords.append(cluster_theme)
    return ", ".join(keywords[:15])  # Limit to 15 keywords


def _generate_infographic_prompt(
    *,
    cluster_table: str,
    entity_names: List[str],
    cluster_theme: str,
    visual_type_category: str,
    group_path: str,
) -> str:
    """Generate infographic prompt for cluster."""
    return f"""Create a clean {visual_type_category.replace('_', ' ').lower()} infographic based on the following medical table data.

Visual type: {visual_type_category}
Cluster theme: {cluster_theme}
Entity count: {len(entity_names)}
Group path: {group_path}

Table data:
{cluster_table}

Style requirements: Single-page educational infographic, white background, high contrast, minimal text (labels only), no watermark, clinically accurate. Focus on the cluster theme: {cluster_theme}."""


def _get_infographic_style(visual_type_category: str) -> str:
    """Map visual_type_category to infographic style."""
    style_map = {
        "Anatomy_Map": "Anatomy",
        "Pathology_Pattern": "Pathology_Diagram",
        "Pattern_Collection": "Pattern_Diagram",
        "Physiology_Process": "Process_Diagram",
        "Equipment": "Equipment_Structure",
        "QC": "QC_Phantom",
        "General": "Default",
    }
    return style_map.get(visual_type_category, "Default")

