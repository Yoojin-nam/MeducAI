# S5 기반 프롬프트 개선 방법론 (Canonical)

**Status**: Canonical (process doc)  
**Version**: 1.0  
**Last Updated**: 2025-12-28  
**Scope**: S5 validation 리포트를 활용해 S1/S2 프롬프트를 체계적으로 개선하는 방법론

---

## 1. 개요

S5는 LLM 기반 검증 단계로, S1 테이블과 S2 카드의 품질을 평가하고 이슈를 분류합니다. 이 문서는 **S5 리포트에서 추출한 신호를 프롬프트 개선으로 연결하는 반복 루프**를 설명합니다.

### 핵심 원칙
- **Read-only validation**: S5는 생성물을 수정하지 않음
- **Actionable signals**: 이슈는 `issue_code`, `recommended_fix_target`, `prompt_patch_hint`로 구조화
- **Offline refinement**: 프롬프트 개선은 별도 dev run_tag에서 수행 후 freeze
- **Traceability**: 모든 변경은 run_tag, 리포트, 프롬프트 버전으로 추적 가능

---

## 2. S5 리포트 구조

### 2.1 리포트 생성
```bash
python3 -m tools.s5.s5_report \
  --base_dir /path/to/workspace/workspace/MeducAI \
  --run_tag <RUN_TAG> \
  --arm <ARM>
```

출력: `2_Data/metadata/generated/<RUN_TAG>/reports/s5_report__arm<ARM>.md`

### 2.2 리포트 주요 섹션

#### Summary
- S1 blocking tables 비율
- S2 blocking cards 비율
- 평균 technical_accuracy, educational_quality

#### Issue Taxonomy
- S1/S2 issue types (예: `clinical_safety`, `nomenclature`, `terminology_precision`)
- S1/S2 issue codes (예: `SAFETY_TUMOR_MIMIC`, `OUTDATED_TERM_BAC`, `TERM_MISTRANSLATION`)
- `recommended_fix_target` 분포 (예: `S1_TABLE_CONTENT`, `Back`, `Front text`)

#### Patch Backlog (액션형)
이 섹션이 핵심입니다. `issue_code` × `recommended_fix_target` × `prompt_patch_hint`를 그룹화합니다:

```markdown
### Target: `S1_TABLE_CONTENT` (n=3)
- **OUTDATED_TERM_BAC**: 1
- **DVT_RECURRENCE_THRESHOLD**: 1
- **MISSING_KEY_EXAM_POINT**: 1

### Target: `Front text` (n=1)
- **TERM_MISTRANSLATION**: 1
  - patch_hint: Ensure 'Post-thrombotic' is translated as '혈전후' rather than '번역후'.
```

---

## 3. 프롬프트 개선 프로세스

### 3.1 단계별 워크플로우

```
1. S5 실행 → 리포트 생성
   ↓
2. Patch Backlog에서 P0/P1 선정
   - P0: blocking_error=true (임상 안전성)
   - P1: terminology/nomenclature/exam-fit (품질 개선)
   ↓
3. 프롬프트에 구체적 규칙 추가
   - 예: "Bland thrombus는 내부 조영증강 없음. 내부 조영증강은 tumor thrombus의 특징."
   - 예: "Deep vein reflux 기준은 >1.0s. Superficial vein은 >0.5s."
   - 예: "post-/pre- 접두는 의학용어로 번역 ('혈전후', '수술후'). '번역후' 같은 일반어 금지."
   ↓
4. 새 dev run_tag로 재생성 (동일 그룹)
   ↓
5. S5 재검증 → 전/후 비교
   ↓
6. 개선 확인되면 freeze (프롬프트 버전 고정)
```

### 3.2 실제 적용 사례 (2025-12-28)

#### 사례 1: DVT CT Enhancement 안전성 오류 (P0)
**발견**:
- `grp_92ab25064f`에서 S1 table에 "Subacute DVT: 혈전 내 조영 증강 일부 관찰 가능"
- S5 판단: `blocking_error=true`, `issue_code=SAFETY_TUMOR_MIMIC`
- 문제: Bland thrombus는 avascular이므로 내부 조영증강 없음. 내부 조영증강은 tumor thrombus의 특징.

**프롬프트 패치** (`S1_SYSTEM__v12.md`):
```markdown
11) Medical Safety
- **CRITICAL**: For venous thrombosis (DVT), NEVER state that thrombus enhances internally on CT.
  - Bland thrombus is avascular and does NOT enhance internally.
  - Internal enhancement is the hallmark of **tumor thrombus** (HCC, RCC, Leiomyosarcoma).
  - For chronic recanalization, use "Enhancement of recanalized channels" (not "internal enhancement").
```

**결과**: 재검증 시 `blocking_error=false`로 개선 확인.

#### 사례 2: Venous Reflux Cutoff 정밀도 (P1)
**발견**:
- S1 table에 "Post-thrombotic Syndrome: Venous reflux > 0.5s"
- S5 판단: `issue_code=DIAGNOSTIC_CRITERIA`
- 문제: >0.5s는 superficial vein 기준. Deep vein은 >1.0s (SVS/AVF guidelines).

**프롬프트 패치** (`S1_SYSTEM__v12.md`):
```markdown
- **CRITICAL**: When citing venous reflux thresholds:
  - Deep veins (femoral/popliteal): > 1.0s (SVS/AVF guidelines)
  - Superficial veins: > 0.5s
  - If context is unclear, specify both: "> 1.0s (deep) / > 0.5s (superficial)"
```

**결과**: 재검증 시 이슈 해소 확인.

#### 사례 3: 번역 오류 (P1)
**발견**:
- S2 card에 "번역후 증후군" (Post-thrombotic → "번역후"로 오역)
- S5 판단: `issue_code=TERM_MISTRANSLATION`, `recommended_fix_target=Front text`

**프롬프트 패치** (`S2_SYSTEM__v8.md`):
```markdown
- **CRITICAL**: Medical prefix translation rules:
  - "post-" → "혈전후", "수술후", "이식후" (context-dependent medical term)
  - "pre-" → "수술전", "이식전"
  - NEVER use generic translations like "번역후", "이전후"
```

**결과**: 재검증 시 오역 감소 확인.

#### 사례 4: S5 테이블 프롬프트 업그레이드 (인프라)
**문제**: S1 이슈가 `recommended_fix_target=UNKNOWN`으로 나와 액션 불가.

**해결**: `S5_USER_TABLE__v2.md` 생성
- `issue_code`, `recommended_fix_target`, `prompt_patch_hint` 출력을 명시적으로 요구
- S1 이슈도 S2처럼 액션형 신호 생성 가능하게 개선

---

## 4. 프롬프트 버전 관리

### 4.1 버전 규칙
- 프롬프트 변경 시 파일명에 버전 번호 증가: `S1_SYSTEM__v12.md` → `S1_SYSTEM__v13.md`
- `3_Code/prompt/_registry.json` 업데이트:
  ```json
  {
    "S1_SYSTEM": "S1_SYSTEM__v13.md",
    "S2_SYSTEM": "S2_SYSTEM__v9.md"
  }
  ```

### 4.2 Freeze 절차
Formal run 전:
1. 프롬프트 버전 고정 (registry hash 기록)
2. Schema version 고정
3. Model settings 고정 (temperature, thinking, RAG)
4. Freeze 근거 문서화:
   - 어떤 run_tag에서 검증했는지
   - 어떤 리포트에서 패치를 추출했는지
   - 전/후 비교 결과

---

## 5. S5 프롬프트 자체 개선

### 5.1 S5 프롬프트 버전
- `S5_SYSTEM__v2.md`: blocking_error semantics 명확화
- `S5_USER_TABLE__v2.md`: 액션형 필드 출력 요구
- `S5_USER_CARD__v2.md`: MCQ options/correct_index 평가 추가

### 5.2 S5 스키마 확장
`S5_VALIDATION_v1.0` → `S5_VALIDATION_v1.1` (optional fields):
- `issues[].issue_code`
- `issues[].recommended_fix_target`
- `issues[].prompt_patch_hint`
- `issues[].confidence`
- `issues[].evidence_ref`

---

## 6. 체크리스트 (다음 agent용)

### 6.1 S5 리포트 분석
- [ ] `s5_report__arm{arm}.md` 생성 확인
- [ ] Patch Backlog 섹션 확인
- [ ] P0 (blocking) vs P1 (non-blocking) 분류
- [ ] `issue_code` × `fix_target` × `hint` 매핑 확인
- [ ] `S2_EXAM_FOCUS_ENTITY_TYPE_MISMATCH` 이슈 확인 (v1.1+ 스키마, entity type-aware validation)
  - Entity type별 발생 패턴 확인
  - Sign/QC/Overview entity의 exam_focus 불일치 패턴 분석

### 6.2 프롬프트 패치 작성
- [ ] 대상 프롬프트 파일 식별 (`S1_SYSTEM`, `S2_SYSTEM`, `S2_USER_ENTITY` 등)
- [ ] 구체적 규칙 추가 (예시 포함)
- [ ] Entity type-specific 규칙 추가 (v9+ 프롬프트의 경우)
  - Sign entity: `exam_focus="pattern"` or `"sign"` (NOT `"diagnosis"`)
  - QC entity: `exam_focus="procedure"`, `"measurement"`, or `"principle"` (NOT `"diagnosis"`)
  - Overview entity: `exam_focus="concept"` or `"classification"` (NOT `"diagnosis"`)
- [ ] 버전 번호 증가
- [ ] Registry 업데이트

### 6.3 재검증
- [ ] 새 dev run_tag 생성 (동일 그룹)
- [ ] S1/S2 재생성
- [ ] S5 재실행
- [ ] 리포트 비교 (blocking 감소, issue_code 감소 확인)

### 6.4 Freeze
- [ ] 프롬프트 버전 고정
- [ ] Schema version 고정
- [ ] Model settings 고정
- [ ] Freeze 근거 문서화

---

## 7. 참고 파일

- S5 리포트 생성: `3_Code/src/tools/s5/s5_report.py`
- S5 검증 실행: `3_Code/src/05_s5_validator.py`
- 프롬프트 레지스트리: `3_Code/prompt/_registry.json`
- S5 스키마: `0_Protocol/04_Step_Contracts/Step05_S5/S5_Validation_Schema_Canonical.md`
- 오프라인 개선 프로세스: `0_Protocol/05_Pipeline_and_Execution/S5_Error_Analysis_and_Iterative_Refinement_Canonical.md`
- Entity Type Validation 가이드: `0_Protocol/05_Pipeline_and_Execution/S5_Entity_Type_Validation_Feedback_Guide.md` (v1.1+ 스키마의 `S2_EXAM_FOCUS_ENTITY_TYPE_MISMATCH` 이슈 코드 처리)

---

## 8. 주의사항

1. **Estimand Protection**: Formal run의 primary endpoint는 Pre-S5 human ratings 사용. S5 기반 개선은 dev slice에서만 수행.
2. **Backward Compatibility**: Schema 변경은 optional fields로 추가하거나 명시적 버전 bump.
3. **Traceability**: 모든 변경은 run_tag, 리포트, 프롬프트 버전으로 추적 가능해야 함 (MI-CLEAR-LLM 준수).

