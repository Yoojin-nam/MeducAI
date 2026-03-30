# S2 현재 상태 및 향후 업그레이드 계획

**Status:** Current State Documentation  
**Version:** 1.0  
**Created:** 2026-01-XX  
**Purpose:** S2 프롬프트의 현재 상태와 향후 업그레이드 계획 명시  
**Audience:** 논문 작성자, 향후 개발자, Git 공개 시 참고자

---

## 현재 상태 (Current Status)

### 프로덕션 프롬프트 버전

**FINAL_DISTRIBUTION run_tag에서 사용된 버전:**
- **System Prompt**: `S2_SYSTEM__S5R3__v12.md`
  - Registry key: `S2_SYSTEM__S5R3`
  - 위치: `3_Code/prompt/S2_SYSTEM__S5R3__v12.md`
  
- **User Prompt**: `S2_USER_ENTITY__S5R2__v11.md`
  - Registry key: `S2_USER_ENTITY`
  - 위치: `3_Code/prompt/S2_USER_ENTITY__S5R2__v11.md`

### 알려진 제한사항 (Known Limitations)

1. **언어 정책:**
   - 프롬프트에 한글 예시가 다수 포함됨
   - 생성된 카드에 한글이 과도하게 사용되는 경향
   - 의학 용어도 한글로 작성되는 경우가 많음

2. **영향 범위:**
   - FINAL_DISTRIBUTION의 모든 S2 생성 카드에 적용됨
   - 카드의 `front`, `back`, `options` 필드에 한글 포함

3. **현재 해결 방안:**
   - 메타데이터 번역 도구 제공: `3_Code/src/tools/anki/translate_medical_terms.py`
   - Post-processing으로 의학 용어만 선택적 번역
   - 원본 한글 버전과 번역 버전 모두 보관 가능

---

## 논문 작성 시 고려사항 (Publication Considerations)

### 메타데이터 번역의 적법성

**✅ 논문 작성에 문제 없음:**

1. **Post-processing의 성격:**
   - 번역은 생성 후 메타데이터 수정에 해당
   - LLM 생성 과정 자체는 변경하지 않음
   - 연구 결과의 타당성에 영향 없음

2. **Methodology 작성 예시:**
   ```
   "Generated Anki cards were post-processed to translate Korean medical 
   terms to English for international accessibility. The translation was 
   performed using a specialized medical terminology translator that 
   preserves sentence structure while converting only medical terms. 
   Both original Korean and translated English versions are maintained 
   for reproducibility."
   ```

3. **재현성 보장:**
   - 원본 프롬프트 버전 명시: `S2_SYSTEM__S5R3__v12.md`
   - 번역 도구 코드 공개: `translate_medical_terms_module.py`
   - 원본 데이터와 번역 데이터 모두 보관

4. **Git 공개 시:**
   - 프롬프트 버전 명확히 문서화
   - 번역 도구와 사용법 포함
   - 원본과 번역 버전 모두 포함 가능

---

## 향후 업그레이드 계획 (Future Upgrade Plan)

### 목표

향후 S2를 재생성할 때 사용할 개선된 프롬프트 버전 준비:

1. **언어 정책 명시:**
   - 영어 우선 정책 추가
   - 한글 사용 제한 명확화
   - 의학 용어 영어 우선 지시

2. **예상 버전:**
   - `S2_SYSTEM__S5R3__v13.md` 또는
   - `S2_SYSTEM__S5R4__v1.md` (새 S5R 버전인 경우)

3. **적용 시점:**
   - 논문 출간 후
   - 새로운 run_tag로 재생성 시
   - 기존 FINAL_DISTRIBUTION은 변경하지 않음

### 구현 체크리스트

향후 프롬프트 업데이트 시:

- [ ] `S2_Language_Policy_Future_Upgrade.md`의 가이드라인 따름
- [ ] 언어 정책 섹션 추가
- [ ] 모든 예시를 영어 우선으로 변경
- [ ] 샘플 생성 테스트
- [ ] 버전 번호 업데이트 (`_registry.json` 포함)
- [ ] `CHANGELOG.md`에 변경사항 기록

---

## 관련 문서 (Related Documents)

1. **프롬프트 개선 가이드:**
   - `0_Protocol/00_Governance/supporting/Prompt_governance/S2_Prompt_Improvement_Guide.md`
   - `0_Protocol/00_Governance/supporting/Prompt_governance/S2_Language_Policy_Future_Upgrade.md`

2. **프롬프트 버전 관리:**
   - `3_Code/prompt/_registry.json`
   - `3_Code/prompt/CHANGELOG.md`

3. **번역 도구:**
   - `3_Code/src/tools/anki/translate_medical_terms.py`
   - `3_Code/src/tools/anki/translate_medical_terms_module.py`

4. **정책 문서:**
   - `0_Protocol/04_Step_Contracts/Step02_S2/S2_Policy_and_Implementation_Summary.md`

---

## Git 공개 시 포함 사항 (For Git Publication)

### 필수 포함:

1. ✅ 현재 프롬프트 버전 (`S2_SYSTEM__S5R3__v12.md`, `S2_USER_ENTITY__S5R2__v11.md`)
2. ✅ 번역 도구 코드 (`translate_medical_terms*.py`)
3. ✅ 이 문서 (`S2_Current_Status_and_Future_Upgrade.md`)
4. ✅ 향후 업그레이드 가이드 (`S2_Language_Policy_Future_Upgrade.md`)

### 선택적 포함:

- 원본 한글 버전 데이터
- 번역된 영어 버전 데이터
- 번역 품질 검증 결과

---

**Last Updated:** 2026-01-XX  
**Next Review:** 향후 S2 재생성 시점 또는 논문 출간 전

