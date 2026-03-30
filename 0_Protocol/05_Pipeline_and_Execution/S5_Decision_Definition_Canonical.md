# MeducAI S5 Decision Definition (Canonical)

**Status:** Canonical  
**Version:** 2.0  
**Frozen:** Yes (Pre-defined before S5 execution)  
**Applies to:** FINAL QA Assignment and Research Design  
**Last Updated:** 2026-01-05  
**Purpose:** Define binding S5 decision criteria for FINAL QA assignment and statistical analysis

---

## 0. Purpose (Normative)

This document defines the **canonical, binding decision criteria** for determining S5 decision outcomes from S5 validation results.

**Critical Constraint**: This definition **MUST be established before S5 execution** to ensure research design integrity. The decision criteria cannot be modified after S5 results are generated, as this would constitute post-hoc protocol modification and invalidate statistical conclusions.

This definition is used for:
- FINAL QA assignment generation (`generate_final_qa_assignments.py`)
- AppSheet export (`export_appsheet_tables.py`)
- Statistical analysis and research design
- Research protocol compliance (IRB / MI-CLEAR-LLM)

---

## 1. Decision Outcomes

S5 decision has **three outcomes** (v2.0):

- **PASS**: Both card content and image pass quality thresholds
- **CARD_REGEN**: Card content needs regeneration (question/answer + image regenerated together)
- **IMAGE_ONLY_REGEN**: Only image needs regeneration (keep card content, regenerate image only)

### 1.1 Legacy Compatibility

For backward compatibility, the legacy `s5_decision` field maps:
- `PASS` → `"PASS"`
- `CARD_REGEN` → `"REGEN"`
- `IMAGE_ONLY_REGEN` → `"REGEN"`

The detailed decision is available in `s5_decision_detailed`.

**Note**: FLAG is **excluded** from this decision definition. FLAG status automatically triggers CARD_REGEN.

---

## 2. Decision Criteria (Binding)

### 2.1 Score Calculation

Two separate scores are calculated for each card:

#### 2.1.1 Card Regeneration Trigger Score (카드 점수)

Evaluates card content quality (question/answer text):

| Hard Triggers (→ 30.0) | Condition |
|------------------------|-----------|
| Blocking Error | `s5_blocking_error == True` |
| Zero Accuracy | `s5_technical_accuracy == 0.0` |

| Component | Weight | Source |
|-----------|--------|--------|
| Technical Accuracy | 50점 | 0.0/0.5/1.0 → 0-50점 |
| Educational Quality | 50점 | 1-5 Likert → 0-50점 |
| **Total** | **100점** | |

#### 2.1.2 Image Regeneration Trigger Score (이미지 점수)

Evaluates image quality (only if image exists):

| Hard Triggers (→ 30.0) | Condition |
|------------------------|-----------|
| Image Blocking Error | `s5_card_image_blocking_error == True` |
| Image Safety Flag | `s5_card_image_safety_flag == True` |
| Zero Anatomical Accuracy | `s5_card_image_anatomical_accuracy == 0.0` |

| Component | Weight | Source |
|-----------|--------|--------|
| Anatomical Accuracy | 40점 | 0.0/0.5/1.0 → 0-40점 |
| Prompt Compliance | 30점 | 0.0/0.5/1.0 → 0-30점 |
| Image Quality | 30점 | 1-5 Likert → 0-30점 |
| **Total** | **100점** | |

### 2.2 Decision Logic

```
if card_score < 70.0 OR s5_was_regenerated:
    → CARD_REGEN (regenerate question + image)
elif image_score < 70.0 OR s5_image_was_regenerated:
    → IMAGE_ONLY_REGEN (regenerate image only, keep card)
else:
    → PASS
```

### 2.3 Decision Priority

1. **CARD_REGEN** (highest priority): If card content is bad, regenerate everything
2. **IMAGE_ONLY_REGEN**: Card is OK, but image needs regeneration
3. **PASS**: Both card and image are OK

### 2.4 Default Behavior

If required fields are missing or `None`:
- Missing `card_regeneration_trigger_score` → treated as `>= 70.0` (PASS)
- Missing `image_regeneration_trigger_score` → treated as `>= 70.0` (PASS for image)
- Missing `s5_was_regenerated` → treated as `False`
- Missing `s5_image_was_regenerated` → treated as `False`

**Rationale**: Missing data defaults to PASS to avoid false positives in REGEN assignment. This is conservative for research design (minimizes Type I error).

---

## 3. Implementation Specification

### 3.1 Python Function Signatures

#### 3.1.1 Legacy Function (Backward Compatible)

```python
def determine_s5_decision(s5_record: Dict[str, Any]) -> str:
    """
    S5 판정 결정 로직 (PASS/REGEN - 레거시 호환)
    
    Returns:
        'PASS' | 'REGEN'
    """
    decision, _, _ = determine_s5_decision_v2(s5_record)
    return "PASS" if decision == "PASS" else "REGEN"
```

#### 3.1.2 Detailed Function (v2.0)

```python
def determine_s5_decision_v2(
    s5_record: Dict[str, Any],
    card_threshold: float = 70.0,
    image_threshold: float = 70.0,
) -> Tuple[str, Optional[float], Optional[float]]:
    """
    S5 판정 결정 로직 v2.0 (상세)
    
    Returns:
        Tuple of (decision, card_score, image_score)
        - decision: 'PASS' | 'CARD_REGEN' | 'IMAGE_ONLY_REGEN'
        - card_score: 카드 점수 (0-100)
        - image_score: 이미지 점수 (0-100, or None if no image)
    """
```

#### 3.1.3 Score Calculation Functions

```python
def calculate_s5_card_regeneration_trigger_score(s5_card_record: Dict) -> float:
    """Card-only score (0-100). TA 50% + EQ 50%."""

def calculate_s5_image_regeneration_trigger_score(s5_card_record: Dict) -> Optional[float]:
    """Image-only score (0-100). AA 40% + PC 30% + IQ 30%. Returns None if no image."""
```

### 3.2 Field Name Mapping

| Field (v2.0) | Legacy Alternative | Description |
|--------------|-------------------|-------------|
| `s5_card_regeneration_trigger_score` | `s5_regeneration_trigger_score` | Card content score |
| `s5_image_regeneration_trigger_score` | - | Image quality score |
| `s5_decision_detailed` | - | `PASS`/`CARD_REGEN`/`IMAGE_ONLY_REGEN` |
| `s5_decision` | - | `PASS`/`REGEN` (legacy) |
| `s5_was_regenerated` | `was_regenerated` | Card was regenerated |
| `s5_image_was_regenerated` | - | Image was regenerated |

### 3.3 Implementation Location

- **Score Calculation**: `3_Code/src/tools/multi_agent/score_calculator.py`
- **Decision Logic**: `3_Code/src/tools/qa/s5_decision.py`
- **AppSheet Export**: `3_Code/src/tools/final_qa/export_appsheet_tables.py`

---

## 4. Research Design Integrity

### 4.1 Pre-Execution Definition Requirement

This decision definition **MUST** be established and documented **before** S5 validation execution begins. This ensures:

- **No post-hoc protocol modification**: Decision criteria cannot be adjusted after seeing S5 results
- **Statistical validity**: PASS/REGEN assignment is independent of outcome data
- **Reproducibility**: Future runs use identical decision criteria
- **IRB compliance**: Protocol is fixed before data collection

### 4.2 Change Control

If decision criteria must be modified:

1. **Version bump**: Increment document version (e.g., 1.0 → 1.1)
2. **Document rationale**: Explain why change is necessary
3. **Impact assessment**: Document impact on existing S5 results
4. **Migration plan**: Define how to handle existing data with old criteria

**Note**: Changes after S5 execution completion are **strongly discouraged** and may require IRB protocol amendment.

---

## 5. Integration Points

### 5.1 FINAL QA Assignment Generation

**File**: `3_Code/src/tools/qa/generate_final_qa_assignments.py`

- Reads S5 validation results
- Applies `determine_s5_decision()` to each card
- Groups cards by decision (PASS/REGEN)
- Implements assignment logic:
  - REGEN: Census (≤200) or Cap (>200)
  - PASS: Remaining allocation

### 5.2 AppSheet Export

**File**: `3_Code/src/tools/final_qa/export_appsheet_tables.py`

- Adds `s5_decision` field to:
  - `Cards.csv`: Card-level decision
  - `S5.csv`: S5 validation results with decision
- Uses `determine_s5_decision()` function

### 5.3 Statistical Analysis

- PASS group: Used for safety validation (FN < 0.3% claim)
- REGEN group: Used for "Accept-as-is" validation
- Decision assignment is deterministic and reproducible

---

## 6. Data Schema Requirements

### 6.1 S5 Validation Record Schema

S5 validation records (`s5_validation__arm{arm}.jsonl`) MUST include:

```json
{
  "schema_version": "S5_VALIDATION_v2.0",
  "group_id": "...",
  "s2_cards_validation": {
    "cards": [
      {
        "card_id": "...",
        "blocking_error": false,
        "technical_accuracy": 1.0,
        "educational_quality": 5,
        "issues": [...],
        "card_image_validation": {
          "blocking_error": false,
          "anatomical_accuracy": 1.0,
          "prompt_compliance": 0.8,
          "image_quality": 4,
          "safety_flag": false,
          "issues": [...]
        }
      }
    ]
  }
}
```

### 6.2 Derived Fields (AppSheet Export)

After applying decision logic, the following derived fields are added:

| Field | Type | Description |
|-------|------|-------------|
| `s5_card_regeneration_trigger_score` | float | Card score (0-100) |
| `s5_image_regeneration_trigger_score` | float \| None | Image score (0-100) |
| `s5_decision` | string | Legacy: `PASS` \| `REGEN` |
| `s5_decision_detailed` | string | v2.0: `PASS` \| `CARD_REGEN` \| `IMAGE_ONLY_REGEN` |

These fields are added to:
- AppSheet export tables (`Cards.csv`, `S5.csv`)
- Assignment records (`Assignments.csv`)

---

## 7. Edge Cases and Validation

### 7.1 Missing Fields

- **Missing `s5_regeneration_trigger_score`**: Defaults to PASS
- **Missing `s5_was_regenerated`**: Defaults to PASS
- **Both missing**: Defaults to PASS

### 7.2 Invalid Values

- **`regeneration_trigger_score` out of range** (< 0 or > 100): Log warning, treat as missing
- **`s5_was_regenerated` non-boolean**: Use `_as_bool()` helper to normalize

### 7.3 Validation Checks

Before assignment generation, validate:

- [ ] All cards have `s5_decision` assigned (PASS or REGEN)
- [ ] No cards have `s5_decision == "FLAG"` (FLAG should be converted to REGEN)
- [ ] REGEN count matches expected (≤200 for census, or exactly 200 for cap)
- [ ] PASS count + REGEN count = total cards (excluding any explicitly excluded cards)

---

## 8. Related Documents

- `0_Protocol/06_QA_and_Study/QA_Operations/FINAL_QA_Assignment_Handover.md`: Implementation handover document
- `0_Protocol/04_Step_Contracts/Step05_S5/S5_Validation_Contract_Canonical.md`: S5 validation contract
- `0_Protocol/04_Step_Contracts/Step05_S5/S5_Validation_Schema_Canonical.md`: S5 output schema
- `0_Protocol/06_QA_and_Study/Paper1_S5_Validation/Paper1_Paper2_Research_Design_Spec.md`: Research design specification

---

## 9. Version History

- **v2.0** (2026-01-05): Enhanced with separate card/image decisions
  - Added `CARD_REGEN` and `IMAGE_ONLY_REGEN` decisions
  - Separate scores: `card_regeneration_trigger_score` and `image_regeneration_trigger_score`
  - Image score includes: anatomical_accuracy, prompt_compliance, image_quality
  - Backward compatible with v1.0 via `s5_decision` field

- **v1.0** (2026-01-01): Initial canonical definition
  - Established PASS/REGEN criteria
  - Defined threshold: `regeneration_trigger_score < 70.0`
  - Excluded FLAG from decision (handled within REGEN)

---

## 10. Compliance Notes

### 10.1 Research Design Integrity

This document ensures:
- **Pre-registration**: Decision criteria defined before data collection
- **No p-hacking**: Criteria cannot be adjusted after seeing results
- **Reproducibility**: Identical criteria across all runs

### 10.2 IRB / MI-CLEAR-LLM Compliance

- Decision criteria are **binding** and **pre-defined**
- No post-hoc modifications without protocol amendment
- All statistical analyses use these fixed criteria

---

**Document Status**: Canonical (Frozen)  
**Last Updated**: 2026-01-05  
**Owner**: MeducAI Research Team  
**Review Required**: Before any modification to decision criteria

