"""
Shared S1 master table specification utilities.

Centralizes the canonical headers and column count for S1 master tables.
"""
from __future__ import annotations

import re
from typing import Dict, List

S1_EXPECTED_COLS = 6

S1_HEADERS_BY_CATEGORY: Dict[str, List[str]] = {
    "Anatomy_Map": [
        "Entity name",
        "해부학적 구조",
        "위치/인접 구조",
        "정상변이/함정",
        "임상 적용",
        "시험포인트",
    ],
    "Pathology_Pattern": [
        "Entity name",
        "질환 정의 및 분류",
        "모달리티별 핵심 영상 소견",
        "병리·기전/특징",
        "감별 질환",
        "시험포인트",
    ],
    "Pattern_Collection": [
        "Entity name",
        "패턴 정의 및 특징",
        "핵심 영상 단서(키워드+모달리티)",
        "유사/대조 및 함정",
        "임상 의미/대표 질환",
        "시험포인트",
    ],
    "Physiology_Process": [
        "Entity name",
        "생리 과정/단계 설명",
        "조건/원인/대상",
        "영상 표현",
        "시간축/순서",
        "시험포인트",
    ],
    "Equipment": [
        "Entity name",
        "장비/기기명 및 용도",
        "원리/기술",
        "프로토콜/적용",
        "아티팩트/제한",
        "시험포인트",
    ],
    "QC": [
        "Entity name",
        "품질 지표 정의",
        "허용 범위/기준",
        "측정 방법",
        "트러블슈팅(원인→조치)",
        "시험포인트",
    ],
    "General": [
        "Entity name",
        "핵심 개념 설명",
        "핵심 영상 단서(키워드+모달리티)",
        "병리·기전/특징",
        "감별 질환",
        "시험포인트",
    ],
}


def sanitize_cell_text(text: str) -> str:
    """
    Normalize cell text:
    - Replace <br>, <br/>, and embedded newlines with "; "
    - Collapse repeated delimiters/spaces
    - Trim whitespace
    """
    if text is None:
        return ""
    t = str(text)
    t = t.replace("<br/>", "; ").replace("<br>", "; ").replace("\\n", " ")
    t = t.replace("\n", "; ")
    t = re.sub(r"\s*;\s*", "; ", t)
    t = re.sub(r"\s{2,}", " ", t)
    t = re.sub(r"(; ){2,}", "; ", t)
    return t.strip()

