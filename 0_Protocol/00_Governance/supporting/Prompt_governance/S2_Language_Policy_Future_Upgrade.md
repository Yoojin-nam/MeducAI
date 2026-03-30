# S2 언어 정책 향후 개선 가이드 (Future Language Policy Upgrade Guide)

**Status:** Future Improvement Plan  
**Version:** 1.0  
**Created:** 2026-01-XX  
**Purpose:** S2 프롬프트의 언어 정책 개선 방향 제시  
**Priority:** Medium (현재 생성된 카드에 영향 없음, 향후 재생성 시 적용)

**Current Production Version:**
- `S2_SYSTEM__S5R3__v12.md` (registry: `S2_SYSTEM__S5R3`)
- `S2_USER_ENTITY__S5R2__v11.md` (registry: `S2_USER_ENTITY`)
- **FINAL_DISTRIBUTION run_tag**: 위 버전으로 생성됨 (한글 사용 다수 포함)

**Note for Publication:**
- 현재 생성된 카드는 메타데이터 번역(post-processing)으로 처리
- 논문 Methodology에 "post-processing translation of medical terms" 명시 가능
- 향후 재생성 시 새 프롬프트 버전 적용 예정

---

## 배경 (Context)

현재 S2 프롬프트에는 한글 예시와 지시사항이 많이 포함되어 있어, 생성되는 Anki 카드에 한글이 과도하게 사용되는 경향이 있습니다.

**현재 상태:**
- 프롬프트에 한글 질문 예시가 다수 포함됨 (예: "가장 가능성이 높은 진단은?", "이 소견이 시사하는 진단은?")
- Back 형식 레이블이 한글로 명시됨 ("정답:", "근거:", "오답 포인트:")
- 의학 용어도 한글로 작성되는 경우가 많음

**문제점:**
- 한글 사용이 과도하여 일관성 부족
- 의학 용어의 표준화 어려움
- 국제적 활용성 제한

---

## 향후 개선 방향 (Future Improvement Direction)

### 1. 언어 정책 명시 (Language Policy Section)

S2 프롬프트에 명시적인 언어 정책 섹션을 추가해야 합니다:

```
────────────────────────
LANGUAGE POLICY (CRITICAL)
────────────────────────
- **Minimize Korean text usage**: Prefer English for question stems, explanations, and general text.
- **Korean usage is LIMITED to**:
  - Essential medical terminology that is standard in Korean radiology practice (e.g., "진단", "소견", "근거")
  - Back format labels: "정답:", "근거:", "오답 포인트:" (these are required format markers)
  - Medical terms that are commonly used in Korean (e.g., "용종증", "골간단", "기관지")
- **Use English for**:
  - Question stems when possible (e.g., "What is the most likely diagnosis?" instead of "가장 가능성이 높은 진단은?")
  - Explanations and reasoning text
  - General descriptive text
  - When English and Korean are both acceptable, prefer English
- **Avoid excessive Korean**: Do not use Korean for entire sentences or paragraphs when English equivalents are clear and appropriate.
- **Mixed language**: Avoid awkward mixing of Korean and English in the same sentence unless it's a standard medical term convention.
```

### 2. 의학 용어 영어 우선 정책 (Medical Terminology English-First Policy)

**특히 중요한 개선 사항:**

의학 용어는 가능한 한 영어로 작성하는 것이 좋습니다:

- ✅ **권장**: "diagnosis", "finding", "rationale", "distractor"
- ⚠️ **한글 허용**: 표준 한글 의학 용어가 널리 사용되는 경우 (예: "진단", "소견", "근거")
- ❌ **지양**: 한글과 영어를 혼용한 어색한 표현 (예: "Popcorn-like 석회화", "CT 영상에서 보이는 finding")

**구체적 예시:**

| 현재 (한글) | 개선 (영어 우선) | 비고 |
|------------|----------------|------|
| "가장 가능성이 높은 진단은?" | "What is the most likely diagnosis?" | 질문 stem |
| "이 소견이 시사하는 진단은?" | "What diagnosis does this finding suggest?" | 질문 stem |
| "근거:" | "Rationale:" | Back 형식 레이블 |
| "오답 포인트:" | "Distractor analysis:" | Back 형식 레이블 |
| "정답: B" | "Answer: B" | Back 형식 레이블 |

**예외 (한글 허용):**
- 표준 한글 의학 용어가 널리 사용되는 경우: "진단", "소견", "근거"
- 형식 레이블이 기존 시스템과 호환성을 위해 필요한 경우: "정답:", "근거:", "오답 포인트:"

### 3. 프롬프트 예시 업데이트 (Prompt Example Updates)

모든 프롬프트 예시를 영어 우선으로 변경:

**Q1 질문 예시:**
- ❌ 기존: "가장 가능성이 높은 진단은?"
- ✅ 개선: "What is the most likely diagnosis?" (prefer English) OR "가장 가능성이 높은 진단은?" (only if Korean is required for consistency)

**Q2 질문 예시:**
- ❌ 기존: "다음 중 Osteoid Osteoma의 치료에서 radiofrequency ablation의 주요 적응증으로 가장 적절한 것은?"
- ✅ 개선: "Which of the following is the most appropriate indication for radiofrequency ablation in the treatment of Osteoid Osteoma?"

**Back 형식 예시:**
- ❌ 기존: "정답: D\n\n근거:\n* RFA는 수술적으로 접근하기 어려운 부위에 적합"
- ✅ 개선: "Answer: D\n\nRationale:\n* RFA is suitable for surgically difficult-to-access areas"

### 4. 적용 시점 (Implementation Timeline)

**현재 (2026-01-XX):**
- ✅ FINAL_DISTRIBUTION: `S2_SYSTEM__S5R3__v12.md` 사용 (한글 다수 포함)
- ✅ 메타데이터 번역 도구 제공: `translate_medical_terms_module.py`
- ✅ 프롬프트 업그레이드 가이드 문서화 완료
- ⏸️ 프롬프트 업데이트는 보류 (이미 생성된 카드와의 일관성 유지)

**향후 재생성 시 (Post-Publication):**
- 새로운 run_tag로 S2를 재실행할 때 업데이트된 프롬프트 적용
- 예상 버전: `S2_SYSTEM__S5R3__v13.md` (또는 `S5R4__v1.md`)
- 점진적 마이그레이션 가능

**검증:**
- 샘플 생성 후 한글/영어 비율 확인
- 의학 용어 일관성 검증
- 사용자 피드백 수집

### 5. 현재 해결 방안 (Current Workaround)

**메타데이터 번역 (Post-Processing Translation):**

현재 생성된 카드의 한글 의학 용어를 영어로 번역하는 도구가 제공됩니다:

- **도구 위치**: `3_Code/src/tools/anki/translate_medical_terms.py`
- **모듈**: `translate_medical_terms_module.py`
- **방식**: LLM 기반 의학 용어만 선택적 번역 (문장 구조 보존)
- **논문 작성 시**: 
  - Methodology에 "Post-processing translation of medical terms for international accessibility" 명시
  - 원본 한글 버전과 번역 버전 모두 보관
  - 번역은 메타데이터 수정이므로 연구 결과에 영향 없음

**사용 예시:**
```bash
python3 3_Code/src/tools/anki/translate_medical_terms.py \
    --input 2_Data/metadata/generated/FINAL_DISTRIBUTION/s2_results__s1armG__s2armG.jsonl \
    --output 2_Data/metadata/generated/FINAL_DISTRIBUTION/s2_results__s1armG__s2armG__translated.jsonl
```

---

## 구현 체크리스트 (Implementation Checklist)

프롬프트 업데이트 시 다음 항목을 확인:

- [ ] `S2_SYSTEM__S5R3__v12.md` (또는 최신 버전)에 LANGUAGE POLICY 섹션 추가
- [ ] `S2_USER_ENTITY__S5R2__v11.md` (또는 최신 버전)에 LANGUAGE POLICY 섹션 추가
- [ ] 모든 질문 예시를 영어 우선으로 변경
- [ ] Back 형식 예시를 영어 우선으로 변경
- [ ] 의학 용어 영어 우선 정책 명시
- [ ] 한글 허용 예외 케이스 명확히 정의
- [ ] 샘플 생성 테스트 수행
- [ ] 생성된 카드의 언어 비율 검증

---

## 참고 사항 (Notes)

1. **기존 카드와의 호환성**: 이미 생성된 카드는 변경하지 않으며, 향후 재생성 시에만 새 정책이 적용됩니다.

2. **점진적 적용**: 모든 카드를 한 번에 재생성하지 않고, 필요에 따라 점진적으로 적용할 수 있습니다.

3. **사용자 피드백**: 실제 사용자 피드백을 수집하여 언어 정책을 지속적으로 개선해야 합니다.

4. **다른 Stage와의 일관성**: S1, S3, S4 등 다른 Stage의 언어 정책과도 일관성을 유지해야 합니다.

---

## 관련 문서 (Related Documents)

- `S2_Prompt_Improvement_Guide.md`: S2 프롬프트 개선 가이드
- `S2_Policy_and_Implementation_Summary.md`: S2 정책 및 구현 요약
- `MI-CLEAR-LLM_2025.md`: 프롬프트 엔지니어링 가이드

---

**Last Updated:** 2026-01-XX  
**Next Review:** 향후 S2 재생성 시점

