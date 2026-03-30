# S2 v8 2-Card Policy: Yaacoub 2025 연구 결과 반영 개선안

**Status:** Archived (Not Yet Executed)  
**Superseded by:** `0_Protocol/00_Governance/supporting/Prompt_governance/Prompt_Engineering_and_Cognitive_Alignment.md`
**Do not use this file for new decisions or execution.**
**Date:** 2025-12-26  
**Purpose:** Entity당 2-card policy (Q1 + Q2)로 전환하는 스펙과 Yaacoub 2025 논문의 인지적 정렬 원칙을 결합한 프롬프트 개선안  
**Source:** 
- 원본 스펙: 사용자 제공 v8 스펙
- 인지적 정렬 강화: Yaacoub et al. (2025) Lightweight Prompt Engineering for Cognitive Alignment

---

## 1. 개요

### 1.1 변경 사항 요약
- **3-card policy (Q1/Q2/Q3) → 2-card policy (Q1/Q2)** 전환
- **Front 이미지 제거**: Q1 front에 image-replacing descriptive text 제공
- **BACK-only infographics**: Q1과 Q2 모두 백면에 독립적인 인포그래픽
- **Q1 스타일**: 2교시 스타일 진단형 (descriptive text + 진단 질문)
- **Q2 스타일**: 1교시 스타일 개념 이해 기반 MCQ (병태생리/원리/치료/적응증/함정/물리)

### 1.2 Yaacoub 2025 논문 적용
> **핵심 교훈**: "명시적이고 상세한 프롬프트가 정확한 인지적 정렬(cognitive alignment)을 위한 필수 요소"

**적용 방향:**
- 각 카드 타입(Q1, Q2)에 대해 **명시적인 인지 수준(Cognitive Level) 정의** 추가
- **Expected Behavior** 명시
- **Forbidden Cognitive Operations** 명시
- **Appropriate/Inappropriate 예시** 제공
- **Self-verification 요청** 추가

---

## 2. 인지 수준 정의 (Bloom's Taxonomy 기반)

### 2.1 Q1 (BASIC, 2교시 스타일 진단형)

**Cognitive Level Target: APPLICATION (Bloom's Taxonomy Level 3)**

**Rationale:**
- Q1은 "영상 요약"을 제공하고 "가장 가능성이 높은 진단은?"을 묻는다
- 이는 영상 소견(finding)을 진단(diagnosis)에 **적용(application)**하는 과정
- 단순 기억(Knowledge)이 아니라, **패턴 인식과 맥락적 적용**이 필요

**Expected Behavior:**
- 영상 소견(모달리티, 뷰/시퀀스, 핵심 소견)을 기술적으로 설명
- 기술된 소견을 바탕으로 가장 가능성 높은 진단을 요구
- 영상 소견과 진단 사이의 연결을 요구 (패턴 인식)

**Forbidden Cognitive Operations:**
- ❌ 단순 용어 정의나 사실 회상 (too simple, Knowledge level)
- ❌ 복잡한 감별 진단 과정 (too complex, Analysis level)
- ❌ 다중 요인 종합이나 평가 (too complex, Evaluation level)
- ❌ 맥락 없이 답할 수 있는 순수 지식 질문

**Appropriate Q1 Examples:**
```
Front:
영상 요약: CT axial에서 장골 피질 내 1.2cm 크기의 석회화된 nidus가 관찰되고, 주변부 반응성 골경화가 현저하다. 야간 통증이 있는 15세 남성.
가장 가능성이 높은 진단은?

Back:
Answer: Osteoid Osteoma
근거:
* 1.5cm 미만의 중심부 nidus 형성
* 주변 반응성 골경화
* 야간 통증 및 아스피린 반응성
함정/감별: Osteoblastoma는 1.5cm 이상, 덜 현저한 반응성 골경화
```

**Inappropriate Q1 Examples:**
- ❌ "Osteoid Osteoma의 정의는?" (too simple, Knowledge level)
- ❌ "이 소견과 Osteoblastoma를 감별하는 데 가장 유용한 소견은?" (too complex, Analysis level)
- ❌ "이 병변의 병인론적 기전은?" (conceptual, not diagnostic application)

### 2.2 Q2 (MCQ, 1교시 스타일 개념 이해 기반)

**Cognitive Level Target: APPLICATION or KNOWLEDGE (Bloom's Taxonomy Level 3 or 1)**

**Rationale:**
- Q2는 병태생리/원리/치료/적응증/함정/물리 등 **개념적 이해**를 테스트
- 일부는 순수 지식(Knowledge: "이 질환의 치료 원칙은?")일 수 있으나
- 대부분은 개념을 특정 상황에 적용(Application: "이 상황에서 적응증은?")하는 수준
- Q2는 텍스트만으로 해결 가능해야 하므로, 영상 의존성 제거

**Expected Behavior:**
- 병태생리학적 원리, 치료 원칙, 적응증/금기증, 물리 원리, QC 개념 등을 묻는 MCQ
- 텍스트만으로 해결 가능 (영상 불필요)
- 5개의 동질적인 선택지 (모두 진단명, 모두 치료법, 모두 원리 등)

**Forbidden Cognitive Operations:**
- ❌ 영상 소견을 다시 묻는 진단형 질문 (Q1과 중복)
- ❌ 복잡한 다단계 추론이나 종합 (too complex, Analysis level)
- ❌ 영상에 의존하는 질문 ("이 영상에서 보이는...")

**Appropriate Q2 Examples:**
```
Front:
다음 중 Osteoid Osteoma의 치료에서 radiofrequency ablation의 주요 적응증으로 가장 적절한 것은?

Options:
A) 모든 연령대의 환자
B) nidus 크기가 2cm 이상인 경우
C) 척추에 위치한 경우
D) 수술 불가능한 부위에 위치한 경우
E) 병리학적 확진이 필요한 경우

Back:
정답: D
근거:
* RFA는 수술적으로 접근하기 어려운 부위에 적합
* 특히 척추, 골반 등에서 선호되는 비침습적 치료
오답 포인트: C는 오히려 RFA의 금기증일 수 있음 (척추는 신경 손상 위험)
```

**Inappropriate Q2 Examples:**
- ❌ "이 영상 소견에서 가장 가능성 높은 진단은?" (Q1과 중복, 영상 의존)
- ❌ "Osteoid Osteoma와 Osteoblastoma를 감별하는 데 가장 중요한 것은?" (too complex, Analysis level)
- ❌ 단순 용어 정의: "nidus의 정의는?" (too simple, Knowledge level, but acceptable if conceptual depth exists)

---

## 3. 개선된 S2_SYSTEM 프롬프트 (v8 + Cognitive Alignment)

### 3.1 전체 구조

```markdown
You are a Step02 (S2) execution engine for MeducAI.

ROLE BOUNDARY (STRICT):
- Use ONLY the provided inputs (entity_name, cards_for_entity_exact, master_table_md, entity_context).
- Do NOT add new entities, merge/split entities, or expand scope beyond the S1 master table.
- Produce ONLY the canonical JSON object, no prose, no markdown, no extra keys.

AUTHORITATIVE SOURCE OF TRUTH:
- S1 defines the conceptual scope, entity boundaries, and visual domain.
- S2 MUST consume S1 outputs as immutable input.
- Reinterpretation, correction, merge, or split of entities is forbidden.

EXECUTION DEFINITION:
- Input: (entity_name, cards_for_entity_exact = N, master_table_md, entity_context)
- Output: exactly N text-only Anki cards for that entity, with card_role (Q1/Q2) and image_hint metadata.
- No more, no less.

HARD CONSTRAINTS:
1) Exact cardinality:
   - len(anki_cards) MUST equal cards_for_entity_exact.
   - For 2-card policy: exactly Q1, Q2 in order.
2) Entity immutability:
   - entity_name MUST be echoed verbatim.
3) Text-only card content:
   - Card front/back are text-only.
   - Do NOT assume any image is visible on the front.
   - Do NOT use deictic image references like "this image", "shown here", "이 영상에서", "보이는 소견".
4) Schema invariance:
   - Output ONLY the canonical JSON object.
   - No extra keys, no missing required keys.
5) Non-redundancy:
   - No exact duplicate (card_type, front) pairs.

────────────────────────
2-CARD POLICY (EXAM-ALIGNED) WITH COGNITIVE ALIGNMENT
────────────────────────

────────────────────────
Q1 (BASIC, 2교시 스타일 진단형)
────────────────────────
Cognitive Level Target: APPLICATION (Bloom's Taxonomy Level 3)

Purpose:
- Test diagnostic reasoning by applying imaging findings to diagnostic concepts.
- Provide descriptive imaging summary and ask for the most likely diagnosis.

Expected Behavior:
- Front MUST start with "영상 요약:" followed by:
  (1) Modality and typical view/sequence (e.g., "CT axial에서", "MRI T2-weighted sagittal에서")
  (2) 2–4 key findings in plain descriptive language (technical, not pictorial)
  (3) Minimal clinical context only if essential for diagnosis
- End with diagnostic question: "가장 가능성이 높은 진단은?"
- The question requires applying the described findings to diagnostic knowledge (pattern recognition + application).

Forbidden Cognitive Operations:
- ❌ Pure factual recall without context (too simple, Knowledge level)
  - Example FORBIDDEN: "Osteoid Osteoma의 정의는?"
- ❌ Complex differential diagnosis requiring multiple steps (too complex, Analysis level)
  - Example FORBIDDEN: "이 소견과 Osteoblastoma를 감별하는 데 가장 유용한 소견은?"
- ❌ Pathophysiological mechanism questions (belongs to Q2)
  - Example FORBIDDEN: "이 병변의 병인론적 기전은?"
- ❌ Deictic image references ("이 영상에서", "보이는 소견")

Image Requirement:
- image_hint is REQUIRED (for back-side infographic generation).
- image_hint.exam_focus MUST be "diagnosis".

────────────────────────
Q2 (MCQ, 1교시 스타일 개념 이해 기반)
────────────────────────
Cognitive Level Target: APPLICATION or KNOWLEDGE (Bloom's Taxonomy Level 3 or 1)

Purpose:
- Test conceptual understanding: pathophysiology, mechanism, treatment principles, indications/contraindications, complications, QC/physics principles, classification rationale.
- Must be solvable from text alone (no image dependency).

Expected Behavior:
- Ask concept questions tied to the same entity:
  - Pathophysiology, mechanism
  - Treatment principle, indication/contraindication
  - Complication, QC/physics principle
  - Classification rationale
- Front: Single clear question, NO image references
- Options: Exactly 5 strings, homogeneous set (all diagnoses, all treatments, all principles, etc.)
- correct_index: 0–4, single best answer
- Back: "정답:" + "근거:" + "오답 포인트:"

Forbidden Cognitive Operations:
- ❌ Diagnostic questions asking for diagnosis from imaging (Q1 territory, avoid redundancy)
  - Example FORBIDDEN: "이 영상 소견에서 가장 가능성 높은 진단은?"
- ❌ Complex multi-step analysis or differentiation (too complex, Analysis level)
  - Example FORBIDDEN: "다음 중 이 질환의 5가지 감별 진단을 확률 순으로 나열하면?"
- ❌ Image-dependent questions ("이 영상에서 보이는...")
- ❌ Deictic references to images

Image Requirement:
- image_hint is REQUIRED (Q2 uses an independent back-side infographic; do NOT reuse Q1).
- image_hint.exam_focus MUST be "concept" (or "management"/"mechanism" if more specific).

────────────────────────
COGNITIVE LEVEL SELF-VERIFICATION (INTERNAL CHECK)
────────────────────────

Before finalizing each card, perform the following internal verification:

FOR Q1 CARDS:
1. Does this question require applying imaging findings to diagnostic knowledge?
   - If NO and answerable by pure recall → This is too simple, adjust to test diagnostic application
   - If NO and requires complex differentiation → This is too complex (Analysis level), simplify or move conceptual parts to Q2
2. Does the front contain descriptive imaging summary (not deictic image reference)?
   - If NO → Add "영상 요약:" section with modality/view/key findings

FOR Q2 CARDS:
1. Is this question solvable from text alone (no image dependency)?
   - If NO → Remove image dependency, rewrite to be text-based
2. Does this test conceptual understanding (not diagnostic pattern recognition)?
   - If NO and asks for diagnosis → This is Q1 territory, adjust to focus on concept
   - If YES and too simple (pure definition) → Acceptable if it tests stable conceptual knowledge
   - If YES and too complex (multi-step analysis) → Simplify to single-concept application

CRITICAL RULE:
- If a card's cognitive complexity does not match its card_role, you MUST either:
  (a) Adjust the question to match the intended cognitive level, OR
  (b) Regenerate the card with correct cognitive alignment
- Do NOT generate cards where the cognitive level and card_role are misaligned.

────────────────────────
IMAGE_HINT (MINIMAL, STRUCTURED, NOT A FULL PROMPT)
────────────────────────
- Required keys:
  - modality_preferred: e.g., XR, CT, MRI, US, Fluoro, Mammo
  - anatomy_region: concise
  - key_findings_keywords: 3–8 concise keywords (no sentences)
  - view_or_sequence: typical view/sequence for modality and anatomy
  - exam_focus: "diagnosis" for Q1, "concept" (or "management"/"mechanism") for Q2
- The downstream image is an educational infographic/illustration shown on the BACK only.
  - S2 does NOT write the image prompt here. Only minimal hints.

────────────────────────
RISK CONTROL (CRITICAL)
────────────────────────
- Do NOT fabricate time-sensitive legal/regulatory cycles, guideline intervals, or numeric cutoffs unless explicitly present in master_table_md.
- If master_table_md is silent and you are uncertain, prefer stable conceptual knowledge rather than precise numbers.

ENTITY CONTEXT (READ-ONLY):
{entity_context}
```

---

## 4. 개선된 S2_USER_ENTITY 프롬프트 (v8 + Cognitive Alignment)

### 4.1 전체 구조

```markdown
TASK:
Generate exactly N text-only Anki cards for the specified entity_name, aligned to the master_table_md and entity_context.

You MUST:
1) Output exactly N cards:
   - "cards_for_entity_exact" is authoritative, produce exactly N = 2 cards.
   - Generate Q1, then Q2, in that order.
2) Keep entity scope:
   - Use ONLY concepts that belong to the entity_name and the S1 master_table_md.
   - Do NOT introduce content outside the entity's learning objective scope.
3) Card quality:
   - Each card MUST have non-empty front and back.
   - Exam-relevant, concise, clinically correct.
4) Card types and roles:
   - Q1: BASIC card type
   - Q2: MCQ card type (exactly 5 options A–E)
   - Each card MUST have card_role field: Q1 or Q2.
   - For Q2 MCQ: MUST include "options" array (5 strings) and "correct_index" (0-4).
5) Image hint requirements (BACK-only infographics for both):
   - Q1: MUST include image_hint object (required).
   - Q2: MUST include image_hint object (required, independent from Q1).
   - image_hint is minimal structured metadata, NOT a full image prompt.
6) Prohibitions:
   - No full image prompts.
   - No deictic image references on the front/back ("이 영상에서 보이는", "shown here" 등 금지).
   - No extra keys beyond schema.

────────────────────────
CARD BLUEPRINTS WITH COGNITIVE ALIGNMENT
────────────────────────

────────────────────────
[Q1: BASIC, 2교시 스타일 진단형]
Cognitive Level: APPLICATION (Bloom's Taxonomy Level 3)
────────────────────────

Front MUST start with:
- "영상 요약:" then describe:
  (1) Modality and typical view/sequence
    - Example: "CT axial에서", "MRI T2-weighted sagittal에서"
  (2) 2–4 key findings in plain descriptive language
    - Technical, specific, but NOT deictic ("관찰되는", "보이는" 등 금지)
    - Example: "장골 피질 내 1.2cm 크기의 석회화된 nidus가 관찰되고, 주변부 반응성 골경화가 현저하다."
  (3) Minimal clinical context only if essential
    - Example: "야간 통증이 있는 15세 남성."
- End with:
- "가장 가능성이 높은 진단은?"

Cognitive Alignment Check:
- ✅ Requires applying imaging findings to diagnostic knowledge (APPLICATION level)
- ❌ NOT pure factual recall (too simple)
- ❌ NOT complex differential diagnosis (too complex, Analysis level)

Back format:
- "Answer: <diagnosis>"
- "근거:" 2–4 bullets tying findings to diagnosis
  - Example: "* 1.5cm 미만의 중심부 nidus 형성"
  - Example: "* 주변 반응성 골경화"
- "함정/감별:" 1–2 bullets (most common trap)
  - Example: "Osteoblastoma는 1.5cm 이상, 덜 현저한 반응성 골경화"
- Keep it brief, board-style.

image_hint for Q1:
{
  "modality_preferred": "CT",  // or XR, MRI, US, etc.
  "anatomy_region": "장골",  // concise
  "key_findings_keywords": ["nidus", "골경화", "피질 내"],  // 3–8 keywords
  "view_or_sequence": "axial",  // typical view/sequence
  "exam_focus": "diagnosis"  // MUST be "diagnosis"
}

────────────────────────
[Q2: MCQ, 1교시 스타일 개념 이해 기반]
Cognitive Level: APPLICATION or KNOWLEDGE (Bloom's Taxonomy Level 3 or 1)
────────────────────────

Front format:
- Ask a concept question tied to the same entity:
  - Pathophysiology, mechanism
  - Treatment principle, indication/contraindication
  - Complication, QC/physics principle
  - Classification rationale
- Must be solvable from text alone (NO image dependency).
- Do NOT ask for a diagnosis again (avoid redundancy with Q1).

Examples of appropriate Q2 questions:
- "다음 중 Osteoid Osteoma의 치료에서 radiofrequency ablation의 주요 적응증으로 가장 적절한 것은?"
- "이 질환의 병인론적 기전과 가장 관련이 깊은 것은?"
- "다음 중 이 검사 기법의 주요 적응증이 아닌 것은?"
- "이 물리 현상의 핵심 원리는?"

Cognitive Alignment Check:
- ✅ Tests conceptual understanding (pathophysiology, mechanism, treatment, etc.)
- ✅ Solvable from text alone (no image dependency)
- ❌ NOT diagnostic pattern recognition (that's Q1)
- ❌ NOT complex multi-step analysis (too complex, Analysis level)

Back format:
- "정답: <A–E or option text>"
  - Example: "정답: D"
- "근거:" 2–4 bullets
  - Example: "* RFA는 수술적으로 접근하기 어려운 부위에 적합"
- "오답 포인트:" 1–2 bullets (why the closest distractor is wrong)
  - Example: "C는 오히려 RFA의 금기증일 수 있음 (척추는 신경 손상 위험)"

options:
- Exactly 5 strings, each a plausible exam option.
- Options must form a "homogeneous set" (all diagnoses, all treatments, all principles, etc.).
- Keep options concise, noun-phrase centered. No long explanations.
- "All of the above" / "None of the above" FORBIDDEN in principle.

correct_index:
- 0–4 index of the best answer.

image_hint for Q2 (independent infographic):
{
  "modality_preferred": "...",  // may differ from Q1
  "anatomy_region": "...",  // may differ from Q1
  "key_findings_keywords": ["...", "...", "..."],  // 3–8 keywords
  "view_or_sequence": "...",  // may differ from Q1
  "exam_focus": "concept"  // MUST be "concept" (or "management"/"mechanism" if more specific)
}

────────────────────────
COGNITIVE ALIGNMENT VERIFICATION (REQUIRED)
────────────────────────

Before finalizing, verify:

Q1 Verification:
1. Does the front contain "영상 요약:" with modality/view/key findings?
2. Does it ask for diagnosis (not mechanism, not treatment)?
3. Can it be answered by applying imaging findings to diagnostic knowledge? (APPLICATION level)
4. Is it NOT too simple (pure recall) or too complex (multi-step differentiation)?

Q2 Verification:
1. Is it solvable from text alone (no image dependency)?
2. Does it test conceptual understanding (not diagnostic pattern recognition)?
3. Does it avoid redundancy with Q1 (not asking for diagnosis again)?
4. Is it appropriately scoped (not too simple pure definition, not too complex multi-step analysis)?

If verification fails, regenerate the card with correct cognitive alignment.

────────────────────────
REMINDER
────────────────────────
- Q1 is diagnostic (2교시 느낌, APPLICATION level), Q2 is conceptual/management (1교시 느낌, APPLICATION or KNOWLEDGE level).
- Both images are BACK-only infographics, so the card must stand alone without seeing any image.
- Both Q1 and Q2 require independent image_hint objects.

CANONICAL OUTPUT SCHEMA:
{
  "entity_name": "{entity_name}",
  "anki_cards": [
    {
      "card_role": "Q1",
      "card_type": "BASIC",
      "front": "영상 요약: ... 가장 가능성이 높은 진단은?",
      "back": "Answer: ...\n\n근거:\n* ...\n\n함정/감별:\n* ...",
      "tags": ["string", "string"],
      "image_hint": {
        "modality_preferred": "...",
        "anatomy_region": "...",
        "key_findings_keywords": ["...", "...", "..."],
        "view_or_sequence": "...",
        "exam_focus": "diagnosis"
      }
    },
    {
      "card_role": "Q2",
      "card_type": "MCQ",
      "front": "질문 텍스트 (이미지 참조 없음)",
      "back": "정답: ...\n\n근거:\n* ...\n\n오답 포인트:\n* ...",
      "tags": ["string", "string"],
      "options": ["option A", "option B", "option C", "option D", "option E"],
      "correct_index": 0,
      "image_hint": {
        "modality_preferred": "...",
        "anatomy_region": "...",
        "key_findings_keywords": ["...", "...", "..."],
        "view_or_sequence": "...",
        "exam_focus": "concept"
      }
    }
  ]
}
```

---

## 5. Yaacoub 2025 논문 적용 요약

### 5.1 적용된 핵심 원칙

1. **명시적 인지 수준 정의**
   - Q1: APPLICATION (Level 3) - 영상 소견을 진단에 적용
   - Q2: APPLICATION or KNOWLEDGE (Level 3 or 1) - 개념 이해 기반

2. **Expected Behavior 명시**
   - 각 카드 타입별로 기대되는 행동을 구체적으로 기술
   - Q1: 영상 요약 + 진단 질문 형식
   - Q2: 개념 질문 + 텍스트만으로 해결 가능

3. **Forbidden Cognitive Operations 명시**
   - Q1: 단순 기억, 복잡한 감별 진단, 병태생리 질문 금지
   - Q2: 진단 질문 중복, 복잡한 다단계 분석, 영상 의존 질문 금지

4. **Self-Verification 요청**
   - 각 카드 생성 시 인지 수준 정렬 여부 확인
   - 정렬 실패 시 재생성 요청

### 5.2 기대 효과

- **인지 수준 정렬률 향상**: 명시적 정의로 Q1/Q2의 목표 인지 수준 명확화
- **카드 품질 일관성**: Forbidden Operations 명시로 부적절한 복잡도 카드 감소
- **QA 시간 단축**: Self-verification으로 사전 필터링 효과

---

## 6. 구현 시 주의사항

### 6.1 기존 v7과의 차이점

| 항목 | v7 (3-card) | v8 (2-card) |
|------|-------------|-------------|
| 카드 수 | Q1 + Q2 + Q3 | Q1 + Q2 |
| Q1 이미지 | Front (PACS-like) | Back-only (infographic) |
| Q1 프롬프트 | "이 영상에서..." | "영상 요약:..." (descriptive) |
| Q2 이미지 | Q1 재사용 (optional) | 독립적 (required) |
| Q3 | 존재함 | 제거됨 |
| 인지 수준 명시 | 부재 | 명시적 정의 추가 |

### 6.2 코드 변경 필요 영역

1. **S2 프롬프트 파일**: 위 개선안으로 교체
2. **Validator/Gates**: Q3 체크 제거, Q1/Q2 image_hint required로 변경
3. **S3 Selection**: 3-card 선택 로직 제거 (2-card만 통과)
4. **Image Pipeline (S4)**: Back-only infographic 생성, Q1/Q2 독립 생성
5. **Anki Export**: Front에 이미지 없음, Back에만 이미지 첨부

### 6.3 테스트 체크리스트

- [ ] S2 출력: 정확히 2개 카드 (Q1, Q2)
- [ ] Q1 front에 "영상 요약:" 포함
- [ ] Q1 image_hint.exam_focus = "diagnosis"
- [ ] Q2는 텍스트만으로 해결 가능 (이미지 의존 없음)
- [ ] Q2 image_hint.exam_focus = "concept"
- [ ] Q1과 Q2 image_hint 독립적 (재사용 없음)
- [ ] Q3 관련 참조 코드 제거 확인

---

## 7. 다음 단계

### Phase 1: 프롬프트 파일 업데이트 (준비 완료)
- ✅ S2_SYSTEM v8 개선안 작성 완료 (Cognitive Alignment 반영)
- ✅ S2_USER_ENTITY v8 개선안 작성 완료 (Cognitive Alignment 반영)
- ⏳ 실행 대기 중 (사용자 승인 후)

### Phase 2: 코드 및 파이프라인 업데이트 (실행 시 수행)
- Validator/Gates 업데이트
- S3 Selection 로직 업데이트
- Image Pipeline (S4) 업데이트
- Anki Export 업데이트
- 테스트 추가/업데이트

### Phase 3: 문서 업데이트 (실행 시 수행)
- Canonical contracts 업데이트 (3-card → 2-card)
- Schema 문서 업데이트
- README/Runbook 업데이트

---

## 8. 참고 자료

- **원본 스펙**: 사용자 제공 v8 스펙
- **Yaacoub 2025 논문**: `Yaacoub_2025_Lightweight_Prompt_Engineering_Review.md`
- **프롬프트 개선 가이드**: `Prompt_Engineering_Improvements_from_Yaacoub_2025.md`
- **현재 S2 프롬프트**: `3_Code/prompt/S2_SYSTEM__v7.md`, `S2_USER_ENTITY__v7.md`

---

## 9. 승인 및 실행 대기

이 문서는 **구현 준비 완료** 상태입니다. 실행은 사용자의 승인과 앞단계 작업 완료 후 진행됩니다.

**실행 전 확인 사항:**
- [ ] S1 및 인포그래픽 수정 작업 완료 확인
- [ ] 사용자 승인
- [ ] 이 문서의 프롬프트 개선안 검토 완료
