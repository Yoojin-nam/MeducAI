# Deployment Image Selection Guide (Card-Level)

**작성일**: 2026-01-07  
**목적**: AppSheet Export 및 Anki Export 시 regen vs baseline 이미지를 **카드별로** 선택적으로 사용하기 위한 가이드  
**적용 대상**: FINAL_DISTRIBUTION Arm G

---

## 📋 요약

### 이미지 생성 vs 실제 사용

| 구분 | 생성 개수 | 실제 사용 권장 | 차이 (예비) |
|------|-----------|---------------|-------------|
| **S1 Visuals** | 45 | 45 | 0 |
| **S2 Card-regen** | 620 (310 entities × 2) | **334** | 286 |
| **S2 Image-only** | 416 (208 entities × 2) | **212** | 204 |
| **합계** | **1,081** | **591** | **490 (45%)** |

### 왜 차이가 나는가?

**이미지 생성 단계 (S3/S4)**:
- Entity 단위로 동작 (Q1, Q2 항상 쌍으로 생성)
- 안전성: 한쪽만 필요해도 양쪽 모두 생성
- S3 spec 구조상 entity 단위로 작성됨

**배포 단계 (AppSheet/Anki Export)**:
- **Card 단위**로 선택 가능
- Q1만 변경 → Q1만 regen 이미지 사용, Q2는 baseline 사용
- Q2만 변경 → Q2만 regen 이미지 사용, Q1은 baseline 사용
- 양쪽 모두 변경 → 둘 다 regen 이미지 사용

---

## 🎯 배포 전략

### 전략 A: 최소 변경 (권장, 546장)

**실제로 변경이 필요한 카드만 regen 이미지 사용**

#### A-1. S2 Card-regen (334장)
- 배치 repair로 텍스트가 **실제로 변경된 카드만** 사용
- Q1만 변경된 경우: Q1은 regen, Q2는 baseline
- Q2만 변경된 경우: Q2는 regen, Q1은 baseline
- 양쪽 모두 변경: 둘 다 regen

#### A-2. S2 Image-only (212장)
- S5 validation에서 `image_regeneration_trigger_score < 80`인 카드만
- 이미 카드별로 판단되었으므로 그대로 사용

#### A-3. S1 Visuals (45개)
- 모두 사용

**총 591장 regen 이미지 사용**

### 전략 B: Entity 단위 사용 (832장)

**Entity에 변경이 있으면 Q1, Q2 모두 regen 이미지 사용**

- 구현이 간단 (entity 단위 판단만)
- 하지만 286장의 불필요한 이미지 교체 발생

### 전략 C: 전체 재생성 사용 (1,081장)

**생성한 모든 regen 이미지 사용**

- 가장 간단한 구현
- 하지만 490장의 불필요한 이미지 교체
- QA 부담 증가

---

## 📊 카드별 선택 로직 (전략 A 구현)

### 1. Card-regen 이미지 선택 함수

```python
def get_card_image_path(group_id, entity_id, card_role, baseline_s2, regen_s2):
    """
    카드별로 baseline vs regen 이미지 경로 결정
    
    Args:
        group_id: 그룹 ID
        entity_id: 엔티티 ID
        card_role: 'Q1' or 'Q2'
        baseline_s2: baseline S2 results dict (keyed by (group_id, entity_id))
        regen_s2: regen S2 results dict (keyed by (group_id, entity_id))
    
    Returns:
        str: 'baseline' or 'regen'
    """
    key = (group_id, entity_id)
    
    # Entity가 regen에 없으면 baseline 사용
    if key not in regen_s2:
        return 'baseline'
    
    baseline_entity = baseline_s2.get(key)
    regen_entity = regen_s2.get(key)
    
    if not baseline_entity or not regen_entity:
        return 'baseline'
    
    # 해당 card_role의 카드만 비교
    baseline_cards = {c['card_role']: c for c in baseline_entity.get('anki_cards', [])}
    regen_cards = {c['card_role']: c for c in regen_entity.get('anki_cards', [])}
    
    if card_role not in baseline_cards or card_role not in regen_cards:
        return 'baseline'
    
    baseline_card = baseline_cards[card_role]
    regen_card = regen_cards[card_role]
    
    # 카드 내용이 실제로 달라진 경우만 regen 사용
    baseline_str = json.dumps(baseline_card, sort_keys=True, ensure_ascii=False)
    regen_str = json.dumps(regen_card, sort_keys=True, ensure_ascii=False)
    
    return 'regen' if baseline_str != regen_str else 'baseline'
```

### 2. Image-only 이미지 선택 함수

```python
def should_use_image_only_regen(group_id, entity_id, card_role, s5_validation, card_regen_entities):
    """
    Image-only regen 이미지 사용 여부 결정
    
    Args:
        group_id: 그룹 ID
        entity_id: 엔티티 ID
        card_role: 'Q1' or 'Q2'
        s5_validation: S5 validation 데이터 (keyed by group_id)
        card_regen_entities: card-regen 대상 entities set
    
    Returns:
        bool: True if should use image-only regen
    """
    key = (group_id, entity_id)
    
    # Card-regen 대상이면 이미 위에서 처리됨
    if key in card_regen_entities:
        return False
    
    # S5 validation 확인
    group_val = s5_validation.get(group_id)
    if not group_val:
        return False
    
    s2_val = group_val.get('s2_cards_validation', {})
    cards = s2_val.get('cards', [])
    
    for card in cards:
        if card.get('entity_id') == entity_id and card.get('card_role') == card_role:
            card_score = card.get('card_regeneration_trigger_score')
            img_score = card.get('image_regeneration_trigger_score')
            
            # 텍스트 OK, 이미지만 문제
            if card_score is not None and card_score >= 80:
                if img_score is not None and img_score < 80:
                    return True
    
    return False
```

### 3. S1 Visual 이미지 선택 함수

```python
def should_use_s1_visual_regen(group_id, cluster_id, s5_validation):
    """
    S1 visual regen 이미지 사용 여부 결정
    
    Args:
        group_id: 그룹 ID
        cluster_id: 클러스터 ID (e.g., 'cluster_1')
        s5_validation: S5 validation 데이터 (keyed by group_id)
    
    Returns:
        bool: True if should use S1 visual regen
    """
    group_val = s5_validation.get(group_id)
    if not group_val:
        return False
    
    s1_val = group_val.get('s1_table_validation', {})
    visuals = s1_val.get('table_visual_validations', [])
    
    for v in visuals:
        if v.get('cluster_id') == cluster_id:
            # 점수 계산
            score = (v.get('information_clarity', 0) / 5 * 25) + \
                    (v.get('anatomical_accuracy', 0) * 25) + \
                    (v.get('prompt_compliance', 0) * 25) + \
                    (v.get('table_visual_consistency', 0) * 25)
            
            return score < 80
    
    return False
```

### 4. 통합 이미지 경로 결정 함수

```python
def get_final_image_path(
    group_id, 
    entity_id, 
    card_role,
    cluster_id=None,  # S1 visual의 경우
    baseline_s2=None,
    regen_s2=None,
    s5_validation=None,
    card_regen_entities=None,
    base_dir='.'
):
    """
    최종 배포에 사용할 이미지 경로 결정
    
    Returns:
        Path: 실제 사용할 이미지 파일 경로
    """
    from pathlib import Path
    
    base_path = Path(base_dir) / '2_Data/metadata/generated/FINAL_DISTRIBUTION'
    
    # S1 Visual인 경우
    if cluster_id is not None:
        if should_use_s1_visual_regen(group_id, cluster_id, s5_validation):
            return base_path / 'images_regen' / f'IMG__FINAL_DISTRIBUTION__{group_id}__TABLE__{cluster_id}.jpg'
        else:
            return base_path / 'images' / f'IMG__FINAL_DISTRIBUTION__{group_id}__TABLE__{cluster_id}.jpg'
    
    # S2 Card인 경우
    # 1. Card-regen 확인
    image_source = get_card_image_path(group_id, entity_id, card_role, baseline_s2, regen_s2)
    
    if image_source == 'regen':
        return base_path / 'images_regen' / f'IMG__FINAL_DISTRIBUTION__{group_id}__{entity_id}__{card_role}.jpg'
    
    # 2. Image-only regen 확인
    if should_use_image_only_regen(group_id, entity_id, card_role, s5_validation, card_regen_entities):
        return base_path / 'images_regen' / f'IMG__FINAL_DISTRIBUTION__{group_id}__{entity_id}__{card_role}.jpg'
    
    # 3. Baseline 사용
    return base_path / 'images' / f'IMG__FINAL_DISTRIBUTION__{group_id}__{entity_id}__{card_role}.jpg'
```

---

## 🔍 실제 배포 적용 예시

### AppSheet Export

```python
# AppSheet CSV 생성 시
for card in all_cards:
    image_path = get_final_image_path(
        group_id=card['group_id'],
        entity_id=card['entity_id'],
        card_role=card['card_role'],
        baseline_s2=baseline_dict,
        regen_s2=regen_dict,
        s5_validation=s5_dict,
        card_regen_entities=card_regen_set
    )
    
    card['image_file'] = image_path.name
    card['image_url'] = generate_appsheet_url(image_path)
```

### Anki Deck Export

```python
# Anki 패키지 생성 시
for card in selected_cards:
    image_path = get_final_image_path(
        group_id=card['group_id'],
        entity_id=card['entity_id'],
        card_role=card['card_role'],
        baseline_s2=baseline_dict,
        regen_s2=regen_dict,
        s5_validation=s5_dict,
        card_regen_entities=card_regen_set
    )
    
    # 이미지를 Anki media folder에 복사
    shutil.copy(image_path, anki_media_folder)
```

---

## 📁 필수 데이터 파일

### 1. Baseline vs Regen S2 비교용

```python
# baseline_s2 dict 생성
baseline_s2 = {}
with open('2_Data/metadata/generated/FINAL_DISTRIBUTION/s2_results__s1armG__s2armG.jsonl') as f:
    for line in f:
        entity = json.loads(line)
        key = (entity['group_id'], entity['entity_id'])
        baseline_s2[key] = entity

# regen_s2 dict 생성
regen_s2 = {}
with open('2_Data/metadata/generated/FINAL_DISTRIBUTION/s2_results__s1armG__s2armG__regen.jsonl') as f:
    for line in f:
        entity = json.loads(line)
        key = (entity['group_id'], entity['entity_id'])
        regen_s2[key] = entity
```

### 2. S5 Validation 데이터

```python
# s5_validation dict 생성
s5_validation = {}
with open('2_Data/metadata/generated/FINAL_DISTRIBUTION/s5_validation__armG.jsonl') as f:
    for line in f:
        group = json.loads(line)
        s5_validation[group['group_id']] = group
```

### 3. Card-regen Entities Set

```python
# card_regen_entities set 생성
card_regen_entities = set()
for key in baseline_s2:
    if key in regen_s2:
        baseline_str = json.dumps(baseline_s2[key], sort_keys=True)
        regen_str = json.dumps(regen_s2[key], sort_keys=True)
        if baseline_str != regen_str:
            card_regen_entities.add(key)
```

---

## 📊 검증 스크립트

배포 전 regen 이미지 사용 개수를 검증하는 스크립트:

```python
import json
from pathlib import Path

def count_regen_usage():
    """실제 사용될 regen 이미지 개수 계산"""
    
    base_dir = Path('2_Data/metadata/generated/FINAL_DISTRIBUTION')
    
    # 데이터 로드
    baseline_s2 = {}
    with open(base_dir / 's2_results__s1armG__s2armG.jsonl') as f:
        for line in f:
            entity = json.loads(line)
            key = (entity['group_id'], entity['entity_id'])
            baseline_s2[key] = entity
    
    regen_s2 = {}
    with open(base_dir / 's2_results__s1armG__s2armG__regen.jsonl') as f:
        for line in f:
            entity = json.loads(line)
            key = (entity['group_id'], entity['entity_id'])
            regen_s2[key] = entity
    
    s5_validation = {}
    with open(base_dir / 's5_validation__armG.jsonl') as f:
        for line in f:
            group = json.loads(line)
            s5_validation[group['group_id']] = group
    
    # Card-regen 카드 카운트 (실제 변경된 카드만)
    card_regen_count = 0
    card_regen_entities = set()
    
    for key in baseline_s2:
        if key not in regen_s2:
            continue
        
        baseline_entity = baseline_s2[key]
        regen_entity = regen_s2[key]
        
        baseline_cards = {c['card_role']: c for c in baseline_entity.get('anki_cards', [])}
        regen_cards = {c['card_role']: c for c in regen_entity.get('anki_cards', [])}
        
        entity_changed = False
        for card_role in baseline_cards:
            if card_role not in regen_cards:
                continue
            
            baseline_str = json.dumps(baseline_cards[card_role], sort_keys=True)
            regen_str = json.dumps(regen_cards[card_role], sort_keys=True)
            
            if baseline_str != regen_str:
                card_regen_count += 1
                entity_changed = True
        
        if entity_changed:
            card_regen_entities.add(key)
    
    # Image-only 카드 카운트
    image_only_count = 0
    for group_id, group_val in s5_validation.items():
        s2_val = group_val.get('s2_cards_validation', {})
        cards = s2_val.get('cards', [])
        
        for card in cards:
            entity_id = card.get('entity_id')
            if not entity_id:
                continue
            
            key = (group_id, entity_id)
            if key in card_regen_entities:
                continue
            
            card_score = card.get('card_regeneration_trigger_score')
            img_score = card.get('image_regeneration_trigger_score')
            
            if card_score is not None and card_score >= 80:
                if img_score is not None and img_score < 80:
                    image_only_count += 1
    
    # S1 visual 카운트
    s1_visual_count = 0
    for group_val in s5_validation.values():
        s1_val = group_val.get('s1_table_validation', {})
        visuals = s1_val.get('table_visual_validations', [])
        
        for v in visuals:
            score = (v.get('information_clarity', 0) / 5 * 25) + \
                    (v.get('anatomical_accuracy', 0) * 25) + \
                    (v.get('prompt_compliance', 0) * 25) + \
                    (v.get('table_visual_consistency', 0) * 25)
            
            if score < 80:
                s1_visual_count += 1
    
    print(f"S2 Card-regen (실제 변경): {card_regen_count}")
    print(f"S2 Image-only: {image_only_count}")
    print(f"S1 Visuals: {s1_visual_count}")
    print(f"Total regen 사용: {card_regen_count + image_only_count + s1_visual_count}")
    
    return card_regen_count, image_only_count, s1_visual_count

if __name__ == '__main__':
    count_regen_usage()
```

**실행 결과 (예상)**:
```
S2 Card-regen (실제 변경): 334
S2 Image-only: 212
S1 Visuals: 45
Total regen 사용: 591
```

---

## ⚠️ 주의사항

### 1. 이미지 생성은 Entity 단위로

- S3/S4 파이프라인은 entity 단위로 동작
- 1,081개 이미지를 모두 생성
- **배포 단계에서만** 카드별로 선택

### 2. QA 우선순위

**필수 QA** (591장):
- 실제 사용될 regen 이미지만 검증

**선택 QA** (490장):
- 예비 이미지는 필요 시 추가 검증

### 3. 배포 스크립트 수정 필요

기존 export 스크립트가 entity 단위로 판단하는 경우:
- **카드별 판단 로직으로 수정 필요**
- 위 함수들을 참고하여 구현

### 4. 데이터 파일 의존성

다음 파일들이 모두 필요:
- `s2_results__s1armG__s2armG.jsonl` (baseline)
- `s2_results__s1armG__s2armG__regen.jsonl` (regen)
- `s5_validation__armG.jsonl` (scores)

---

## 📈 효과

### 비용 절감
- **QA 검증 부담**: 832장 → 591장 (29% 감소)
- **불필요한 이미지 교체**: 490장 방지
- **실제 개선이 필요한 카드만** 정확히 선택

### 품질 관리
- 변경되지 않은 카드는 검증된 baseline 유지
- 변경된 카드만 regen으로 교체 → 리스크 최소화
- 예비 490장은 필요 시 언제든 사용 가능

---

**작성 완료**: 2026-01-07  
**적용 단계**: AppSheet Export, Anki Export  
**검증 스크립트**: 위 `count_regen_usage()` 함수 사용

