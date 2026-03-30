# S4_CONCEPT 프롬프트 v2 → v3 업그레이드 분석

**분석 일자:** 2025-01-21  
**목적:** v3 프롬프트가 v2의 핵심 규칙과 맥락을 보존하면서 업그레이드되었는지 확인

---

## 📋 요약

### ✅ 개선된 점
1. **Visual Anchor Requirement 강화**: 모든 카테고리에서 시각적 요소가 필수화됨
2. **"시험포인트" 박스 선택적 처리**: 테이블 내용이 명확히 지원할 때만 포함하도록 개선
3. **Layout 지침 구체화**: 각 카테고리별 레이아웃 옵션이 더 명확해짐
4. **텍스트 예산 명확화**: 토큰/키워드 기반 제한이 더 구체적으로 표현됨

### ⚠️ 주의할 점
1. **SYSTEM 프롬프트 변경사항**: 일부 규칙이 재구성되었지만 핵심 내용은 보존됨
2. **카테고리별 일관성**: 대부분의 카테고리가 새로운 Visual Anchor Requirement를 따름

---

## 🔍 상세 비교

### S4_CONCEPT_SYSTEM (v2 → v3)

#### ✅ 보존된 핵심 규칙
- ROLE BOUNDARY: 테이블 내용만 사용, 발명 금지
- GLOBAL OUTPUT: 16:9 슬라이드, 4K 해상도, 깨끗한 배경
- DETERMINISTIC PANEL LIMIT: 최대 6개 패널 (table order 기반)
- SCHEMATIC-FIRST: QC/Physiology_Process/Equipment/Algorithm에서 다이어그램 필수
- STRICT BOUNDARY: 테이블에 없는 숫자/임계값 발명 금지

#### 🔄 변경된 부분

**1. TEXT & LANGUAGE RULES**
- **v2**: "Keep text concise; prefer keywords over sentences. Ban paragraphs globally. Use ≤ 3 keywords per expanded panel"
- **v3**: "No paragraphs. No long sentences. Prefer tokens/phrases. Use short field labels + short tokens"
- **평가**: 더 명확하고 구체적, 핵심은 보존됨 ✅

**2. PER-PANEL CONTENT**
- **v2**: "1 boxed '시험포인트' (Korean, EXACTLY one short line)" (필수)
- **v3**: "'시험포인트' box (Korean, EXACTLY one short line) ONLY IF the table provides a clear pitfall/pearl. If no reliable exam tip exists in the table content, OMIT the exam-tip box (do NOT hallucinate)."
- **평가**: 발명 방지를 위해 선택적 처리로 개선 ✅

**3. VISUAL ANCHOR REQUIREMENT (NEW in v3)**
- **v3 추가**: 모든 expanded panel에 visual anchor 필수
  - Pathology/Pattern: radiology-like thumbnail 또는 pattern schematic
  - Anatomy_Map: central anatomy schematic + callouts
  - Comparison: side-by-side comparison thumbnails/diagrams
  - Algorithm/Physiology_Process/QC/Equipment: diagram/flow/plot/schematic REQUIRED
- **평가**: v2의 "SCHEMATIC-FIRST REQUIREMENT"를 확장하여 모든 카테고리에 적용 ✅

**4. CONSISTENT SLIDE GRAMMAR**
- **v2**: "Top title bar (dark navy/charcoal), clean white background, ample whitespace."
- **v3**: "Top title bar (dark navy/charcoal) with concise title. Optional small subtitle line (Group Path) if space permits."
- **평가**: 타이틀 바 구체화, 핵심은 보존됨 ✅

---

## 📂 카테고리별 비교

### Pathology_Pattern

#### ✅ 보존된 규칙
- DETERMINISTIC EXPANSION: 첫 4-6개 행만 확장, table order 기반
- PANEL TEMPLATE: Entity name, ≤ 3 keywords, 시험포인트
- WORD BUDGET: ≤ 3 keywords, 문단 금지

#### 🔄 개선된 부분
1. **VISUAL REQUIREMENT 강화**
   - **v2**: "Pattern-first pseudo-images/illustrations emphasizing distribution/appearance (not text-only)."
   - **v3**: "Visual anchor (MANDATORY): At least one grayscale radiology-like thumbnail OR a simplified schematic mimicking radiology contrast."
   - **평가**: 시각적 요구사항이 더 구체적으로 명시됨 ✅

2. **LAYOUT 구체화**
   - **v3 추가**: "Clean 2×2 (preferred for 4) or 3×2 grid (for 5–6) with generous whitespace."
   - **평가**: 레이아웃 가이드라인 개선 ✅

3. **시험포인트 선택적 처리**
   - **v3**: "ONLY if grounded in the table. If not clearly supported by table content, OMIT this box."
   - **평가**: 발명 방지 개선 ✅

---

### Equipment

#### ✅ 보존된 규칙
- SCHEMATIC REQUIREMENT: 다이어그램 필수
- COMPONENT LABELING: 영어 컴포넌트 이름
- No hallucinated parameters

#### 🔄 개선된 부분
1. **VISUAL ANCHOR 추가**
   - **v3**: "Central block diagram is REQUIRED. Additionally, include at least one small 'artifact thumbnail/schematic' to visually show an artifact/limitation (no text-only)."
   - **평가**: 시각적 요소 강화 ✅

2. **시험포인트 선택적 처리**
   - **v3**: "Optional '시험포인트' (Korean, EXACTLY one short line) ONLY if table-supported; otherwise omit."
   - **평가**: 일관성 있는 개선 ✅

---

### QC

#### ✅ 보존된 규칙
- QC loop diagram 필수: Acquire → Measure → Compare → Action
- Metrics panel, failure → fix mini-map
- Text-only FAIL condition

#### 🔄 개선된 부분
1. **VISUAL ANCHORS 강화**
   - **v3**: "QC loop diagram is REQUIRED (central). Add at least one additional visual anchor beyond the loop: Recommended: a schematic control chart / trend plot with labeled lines (e.g., Target / Upper limit / Lower limit) WITHOUT any numeric values."
   - **평가**: 더 구체적인 시각적 요구사항 ✅

2. **QC ITEM CALLOUTS 추가**
   - **v3**: Optional callouts 구조 명시 (space permits일 때만)
   - **평가**: 유연성 제공하면서 구조 명확화 ✅

---

### Algorithm

#### ✅ 보존된 규칙
- Pipeline: Input → Steps(3–6) → Output
- Flowchart/block diagram 필수
- Step당 ≤ 2 tokens

#### 🔄 개선된 부분
1. **NODE TEMPLATE 구체화**
   - **v3**: "Optional small thumbnail/schematic icon that conveys the imaging decision (recommended, not decorative)"
   - **평가**: 시각적 요소 권장 추가 ✅

2. **시험포인트 선택적 처리**
   - **v3**: "ONLY if the table supports a specific pitfall/pearl. If not clearly supported, OMIT (do NOT hallucinate)."
   - **평가**: 일관성 ✅

---

### Comparison

#### ✅ 보존된 규칙
- Layout options (3-panel vertical split, 2×2 grid, aligned rows)
- Differentiator axes 강조
- ≤ 3 keywords per panel

#### 🔄 개선된 부분
1. **VISUAL ANCHOR 필수화**
   - **v3**: "Each expanded entity MUST include at least one radiology-like grayscale thumbnail OR a clean schematic that conveys its distinguishing pattern. Text-only comparison is a FAIL."
   - **평가**: 시각적 요소 필수화로 개선 ✅

2. **PANEL TEMPLATE 구조화**
   - **v3**: "preferably as labeled fields: Key pattern / Distribution / Location / Differentiator"
   - **평가**: 구조화 개선 ✅

---

### Anatomy_Map

#### ✅ 보존된 규칙
- Central anatomy figure 필수
- Callouts with short labels
- Others section for overflow

#### 🔄 개선된 부분
1. **CALLOUT TEMPLATE 구체화**
   - **v3**: "Up to 2 labeled tokens (English; no sentences), e.g.: Region: <token> / Landmark / Pitfall: <token>"
   - **평가**: 템플릿 명확화 ✅

2. **VISUAL ANCHOR 강화**
   - **v3**: "Each expanded row MUST be represented as a callout anchored to the figure (arrow/leader line). Text-only callouts without a real anchor on the figure are a FAIL."
   - **평가**: 시각적 연결 강조 ✅

---

### Sign_Collection

#### ✅ 보존된 규칙
- Uniform grid (2×2, 2×3, or 3×2)
- Sign name + tiny pseudo-image + keywords + 시험포인트
- ≤ 2 keywords

#### 🔄 개선된 부분
1. **VISUAL ANCHOR 명확화**
   - **v3**: "Each sign cell MUST include a tiny pseudo-image/icon: schematic (not text-only), showing the sign shape/region/pattern. 'Text-only sign cells' are a FAIL condition."
   - **평가**: 시각적 요소 필수화 ✅

2. **시험포인트 선택적 처리**
   - **v3**: "ONLY if clearly supported by table content. If not supported, OMIT (do NOT hallucinate)."
   - **평가**: 일관성 ✅

---

### Pattern_Collection

#### ✅ 보존된 규칙
- 3–5 pattern buckets
- Bucketing must be defensible using table wording
- Mini-items: entity name + 1 keyword

#### 🔄 개선된 부분
1. **VISUAL ANCHOR 필수화**
   - **v3**: "Each bucket panel MUST include a visual anchor: One representative grayscale radiology-like thumbnail OR a clean schematic that conveys the bucket's shared pattern. 'Text-only buckets' are a FAIL condition."
   - **평가**: 시각적 요소 필수화 ✅

2. **BUCKETING RULES 강화**
   - **v3**: "If table content does not support meaningful bucketing, fall back to simple buckets based on repeated table wording (still defensible), not external knowledge."
   - **평가**: 발명 방지 강화 ✅

---

### Physiology_Process

#### ✅ 보존된 규칙
- 4–7 stage arrow flow diagram
- Stages derived from table order/content
- Flowchart/block diagram 필수

#### 🔄 개선된 부분
1. **STAGE CONSTRUCTION RULE 명확화**
   - **v3**: "If the table explicitly provides a natural stage sequence, use that sequence. Otherwise, map stages to the expanded rows in table order."
   - **평가**: 규칙 명확화 ✅

2. **EXAM PITFALLS 선택적 처리**
   - **v3**: "ONLY IF clearly supported by table content. If table does not support pitfalls/pearls, OMIT this box (do NOT hallucinate)."
   - **평가**: 일관성 ✅

---

### Classification

#### ✅ 보존된 규칙
- Decision tree/taxonomy diagram
- Max 6 leaf nodes
- No invented thresholds

#### 🔄 개선된 부분
1. **VISUAL ANCHOR 추가**
   - **v3**: "Each leaf/class SHOULD include a small thumbnail/schematic (radiology-like or pattern icon) that conveys the class. At minimum: the overall tree must be a true diagram (not text list). Text-only is a FAIL."
   - **평가**: 시각적 요소 강화 ✅

2. **LEAF TEMPLATE 구조화**
   - **v3**: "preferably labeled: Core criterion / Imaging clue / Pitfall/DDx"
   - **평가**: 구조화 개선 ✅

---

### General

#### ✅ 보존된 규칙
- Structured grid (2×2, 2×3, 3×2)
- Entity name + ≤ 3 keywords + 시험포인트
- Others section

#### 🔄 개선된 부분
1. **VISUAL ANCHOR 필수화**
   - **v3**: "Each expanded panel MUST include a small radiology-like thumbnail OR a clean schematic icon conveying the key pattern. Text-only panels are a FAIL."
   - **평가**: 시각적 요소 필수화 ✅

2. **시험포인트 선택적 처리**
   - **v3**: "ONLY if table-supported."
   - **평가**: 일관성 ✅

---

## 🎯 종합 평가

### ✅ 성공적인 업그레이드 요소

1. **Visual Anchor Requirement 일관성**: 모든 카테고리에서 시각적 요소가 필수화되어 text-only 슬라이드 방지
2. **Hallucination 방지 강화**: "시험포인트" 박스와 기타 요소들이 테이블 내용 기반으로만 생성되도록 명확화
3. **구조화 개선**: 레이아웃, 템플릿, 필드 라벨링이 더 구체적으로 명시됨
4. **핵심 규칙 보존**: DETERMINISTIC EXPANSION, WORD BUDGET, STRICT BOUNDARY 등 핵심 규칙 모두 보존

### ⚠️ 주의사항

1. **SYSTEM 프롬프트 재구성**: 일부 섹션이 재구성되었지만 핵심 내용은 보존됨
2. **카테고리별 일관성**: 대부분의 카테고리가 새로운 Visual Anchor Requirement를 일관되게 따름
3. **선택적 요소 처리**: "시험포인트" 박스가 선택적으로 변경된 것은 발명 방지를 위한 개선이지만, 사용자는 이 변경을 인지해야 함

### 📝 권장사항

1. ✅ **업그레이드 승인**: v3는 v2의 핵심 규칙을 보존하면서 시각적 품질과 hallucination 방지를 개선함
2. ✅ **일관성 유지**: 모든 카테고리가 동일한 원칙(Visual Anchor, 선택적 시험포인트)을 따름
3. ⚠️ **테스트 필요**: 실제 이미지 생성에서 Visual Anchor Requirement가 제대로 구현되는지 확인 필요

---

## 🔍 누락/변경 확인 체크리스트

- [x] ROLE BOUNDARY: 보존됨
- [x] GLOBAL OUTPUT REQUIREMENTS: 보존됨 (4K 해상도 포함)
- [x] DETERMINISTIC PANEL LIMIT: 보존됨
- [x] SCHEMATIC-FIRST REQUIREMENT: 확장됨 (Visual Anchor Requirement로)
- [x] STRICT BOUNDARY: 보존됨
- [x] TEXT & LANGUAGE RULES: 개선됨 (더 명확하게)
- [x] FAIL CONDITIONS: 보존됨 (text-only 추가)
- [x] 카테고리별 특수 규칙: 대부분 보존 또는 개선됨

**결론**: ✅ v3는 v2의 핵심 규칙과 맥락을 보존하면서 시각적 품질과 hallucination 방지를 개선한 것으로 평가됨.

