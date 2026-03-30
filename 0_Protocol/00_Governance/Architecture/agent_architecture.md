# MeducAI Agent Architecture

## 전체 Agent 구조도

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MeducAI Pipeline Architecture                        │
└─────────────────────────────────────────────────────────────────────────────┘

                            INPUT: Curriculum CSV
                                      │
                                      ▼
        ┌─────────────────────────────────────────────────────────┐
        │  S1 Agent (Content Generator)                            │
        │  File: 01_generate_json.py                              │
        │  ─────────────────────────────────────────────────────  │
        │  Role: Master Table & Entity List 생성                  │
        │  LLM: ✓ (Gemini Pro/Flash)                              │
        │  Output: stage1_struct__arm{arm}.jsonl                  │
        └─────────────────────────────────────────────────────────┘
                                      │
                                      ▼
        ┌─────────────────────────────────────────────────────────┐
        │  S2 Agent (Card Generator)                               │
        │  File: 01_generate_json.py (내부 모듈)                  │
        │  ─────────────────────────────────────────────────────  │
        │  Role: Anki 카드 생성 (Q1/Q2) + Image Hints            │
        │  LLM: ✓ (Gemini Pro/Flash)                              │
        │  Output: s2_results__arm{arm}.jsonl                     │
        │          (카드 텍스트 + image_hint)                      │
        └─────────────────────────────────────────────────────────┘
                                      │
                                      ▼
        ┌─────────────────────────────────────────────────────────┐
        │  S3 Agent (Policy Resolver & Image Spec Compiler)       │
        │  File: 03_s3_policy_resolver.py                         │
        │  ─────────────────────────────────────────────────────  │
        │  Role: Image policy 결정 + 이미지 생성 spec 컴파일      │
        │  LLM: ✗ (순수 컴파일러, deterministic)                  │
        │  Output: image_policy_manifest__arm{arm}.jsonl          │
        │          s3_image_spec__arm{arm}.jsonl                  │
        └─────────────────────────────────────────────────────────┘
                                      │
                                      ▼
        ┌─────────────────────────────────────────────────────────┐
        │  S4 Agent (Image Generator)                              │
        │  File: 04_s4_image_generator.py                         │
        │  ─────────────────────────────────────────────────────  │
        │  Role: 이미지 생성 (Card 이미지 + Table 이미지)         │
        │  LLM: ✓ (Gemini Pro/Flash for image generation)         │
        │  Output: IMG__*.jpg files                                │
        │          s4_image_manifest__arm{arm}.jsonl              │
        └─────────────────────────────────────────────────────────┘
                                      │
                                      ▼
        ┌─────────────────────────────────────────────────────────┐
        │  S5 Agent (Validator & Quality Checker)                  │
        │  File: 05_s5_validator.py                               │
        │  ─────────────────────────────────────────────────────  │
        │  Role: 콘텐츠 품질 검증 + RAG 기반 검증                │
        │  LLM: ✓ (Gemini Pro with RAG)                           │
        │  Output: s5_validation__arm{arm}.jsonl                  │
        │          (validation scores + patch_hints)              │
        └─────────────────────────────────────────────────────────┘
                                      │
                          ┌───────────┴───────────┐
                          │                       │
                          ▼                       ▼
           ┌──────────────────────┐    ┌──────────────────────┐
           │  Pass Quality Gate   │    │  Fail Quality Gate   │
           └──────────────────────┘    └──────────────────────┘
                          │                       │
                          │                       ▼
                          │         ┌─────────────────────────────────────────────────┐
                          │         │  S6 Agent (Positive Instruction Generator)      │
                          │         │  File: 06_s6_positive_instruction_agent.py      │
                          │         │  ───────────────────────────────────────────── │
                          │         │  Role: S5 피드백을 긍정적 지시사항으로 변환    │
                          │         │  LLM: ✓ (Gemini Flash for transformation)       │
                          │         │  Output: s3_image_spec__regen_enhanced.jsonl   │
                          │         └─────────────────────────────────────────────────┘
                          │                       │
                          │                       ▼
                          │                 S4 재생성 (Regen)
                          │                       │
                          └───────────┬───────────┘
                                      ▼
                    ┌─────────────────────────────────────┐
                    │         Export Pipeline              │
                    ├─────────────────────────────────────┤
                    │  - PDF (07_build_set_pdf.py)        │
                    │  - Anki (07_export_anki_deck.py)    │
                    └─────────────────────────────────────┘
                                      │
                                      ▼
                              Final Distribution
```

## Agent 상세 설명

### 1. S1 Agent (Content Generator)
- **파일**: `3_Code/src/01_generate_json.py`
- **역할**: 커리큘럼 CSV를 기반으로 Master Table과 Entity List 생성
- **LLM 사용**: ✓ (Gemini Pro/Flash)
- **입력**: `groups_canonical.csv`, learning objectives
- **출력**: `stage1_struct__arm{arm}.jsonl`
- **특징**: Group-first processing, 6-arm 실험 설계 지원

### 2. S2 Agent (Card Generator)
- **파일**: `3_Code/src/01_generate_json.py` (내부 모듈)
- **역할**: Anki 플래시카드 생성 (Q1: Basic, Q2: MCQ) + Image Hints
- **LLM 사용**: ✓ (Gemini Pro/Flash)
- **입력**: S1 output
- **출력**: `s2_results__arm{arm}.jsonl` (카드 텍스트 + image_hint)
- **특징**: 2-card policy (Q1/Q2), 이미지는 뒷면에만 배치

### 3. S3 Agent (Policy Resolver & Image Spec Compiler)
- **파일**: `3_Code/src/03_s3_policy_resolver.py`
- **역할**: Image policy 결정 + 이미지 생성 specification 컴파일
- **LLM 사용**: ✗ (순수 컴파일러, deterministic)
- **입력**: S1/S2 outputs
- **출력**: 
  - `image_policy_manifest__arm{arm}.jsonl`
  - `s3_image_spec__arm{arm}.jsonl`
- **특징**: Template-based compilation, LLM 호출 없음

### 4. S4 Agent (Image Generator)
- **파일**: `3_Code/src/04_s4_image_generator.py`
- **역할**: 실제 이미지 생성 (Card 이미지 + Table 시각화)
- **LLM 사용**: ✓ (Gemini Pro/Flash for image generation)
- **입력**: S3 image specs
- **출력**: 
  - `IMG__*.jpg` files (4:5 card images, 16:9 table visuals)
  - `s4_image_manifest__arm{arm}.jsonl`
- **특징**: Fail-fast for required images, parallel processing

### 5. S5 Agent (Validator & Quality Checker)
- **파일**: `3_Code/src/05_s5_validator.py`
- **역할**: 콘텐츠 품질 검증 + RAG 기반 evidence 검증
- **LLM 사용**: ✓ (Gemini Pro with RAG)
- **입력**: S1/S2/S4 outputs + RAG evidence
- **출력**: `s5_validation__arm{arm}.jsonl`
  - validation scores
  - patch_hints (재생성이 필요한 경우)
- **특징**: LLM-based quality gate, evidence-based validation

### 6. S6 Agent (Positive Instruction Generator)
- **파일**: `3_Code/src/06_s6_positive_instruction_agent.py`
- **역할**: S5의 부정적 피드백(patch_hint)을 긍정적 지시사항으로 변환
- **LLM 사용**: ✓ (Gemini Flash for transformation)
- **입력**: 
  - S5 validation results (patch_hints)
  - S3 image specs
  - S4 generated images
- **출력**: `s3_image_spec__regen_enhanced.jsonl`
- **특징**: 
  - Transformation layer (negative → positive instructions)
  - TABLE=Pro (complex), CARD=Flash (simple)
  - Thinking: always ON
  - RAG: OFF (regeneration task)

## Data Flow

```
groups_canonical.csv
       │
       ▼
   [S1 Agent] ──────► stage1_struct__arm{arm}.jsonl
       │
       ▼
   [S2 Agent] ──────► s2_results__arm{arm}.jsonl
       │                  (with image_hint)
       ▼
   [S3 Agent] ──────► s3_image_spec__arm{arm}.jsonl
       │                  image_policy_manifest__arm{arm}.jsonl
       ▼
   [S4 Agent] ──────► IMG__*.jpg
       │                  s4_image_manifest__arm{arm}.jsonl
       ▼
   [S5 Agent] ──────► s5_validation__arm{arm}.jsonl
       │                  (scores + patch_hints)
       │
       ├──► Quality Pass ──► Export (PDF/Anki)
       │
       └──► Quality Fail ──► [S6 Agent]
                                │
                                ▼
                        s3_image_spec__regen_enhanced.jsonl
                                │
                                ▼
                          [S4 Agent] (Regen)
                                │
                                ▼
                          Updated images
```

## Agent 특성 비교

| Agent | LLM | RAG | Thinking | Temperature | Purpose |
|-------|-----|-----|----------|-------------|---------|
| S1 | ✓ | ✗ | ✓ | Variable | Content generation |
| S2 | ✓ | ✗ | ✓ | Variable | Card generation |
| S3 | ✗ | ✗ | ✗ | N/A | Deterministic compilation |
| S4 | ✓ | ✗ | ✗ | 0.2 | Image generation |
| S5 | ✓ | ✓ | ✓ | 0.2 | Quality validation |
| S6 | ✓ | ✗ | ✓ | 0.3 | Instruction transformation |

## Key Design Principles

1. **Group-first Processing**: 모든 agent는 group 단위로 처리
2. **Reproducibility**: MI-CLEAR-LLM compliant, deterministic when possible
3. **Idempotency**: 동일 입력 → 동일 출력 (재실행 가능)
4. **Fail-fast**: Critical errors는 즉시 실패 (특히 S3/S4)
5. **Quality Gate**: S5 validation이 export의 quality gate 역할
6. **Regeneration Loop**: S5 → S6 → S4 재생성 순환

## Agent 간 통신 방식

- **파일 기반**: 모든 agent 간 통신은 JSONL 파일로 수행
- **RUN_TAG 중심**: 모든 출력은 `<run_tag>` 디렉토리에 저장
- **ARM별 분리**: 각 실험 arm(A-F)별로 독립적인 파일 생성
- **Manifest 추적**: 각 단계는 manifest 파일로 처리 내역 추적

---

**생성 날짜**: 2026-01-06  
**프로젝트**: MeducAI - Medical Education AI Pipeline  
**문서 버전**: 1.0

