# S5R3 프롬프트 통합 요약

**작성일**: 2025-12-31  
**목적**: S5R3 프롬프트 개선 후 코드 통합 및 확인 사항 정리

---

## 1. 생성된 S5R3 프롬프트 파일

### ✅ 생성 완료
1. **S4_EXAM_SYSTEM__S5R3__v11_DIAGRAM_4x5_2K.md**
   - Text budget: ZERO TOLERANCE
   - Laterality: MANDATORY PRE-CHECK
   - View alignment: PRE-GENERATION CHECK
   - Multi-panel: ABSOLUTE FORBIDDEN
   - Modality consistency: MANDATORY PRE-CHECK

2. **S4_EXAM_USER__S5R3__v11_DIAGRAM_4x5_2K.md**
   - Text budget: ZERO (예외 없음)
   - Laterality checklist 강화
   - View consistency checklist 추가
   - Panel count checklist 추가
   - Modality consistency checklist 추가

3. **S2_SYSTEM__S5R3__v12.md**
   - Laterality requirement: HARD CONSTRAINT
   - View consistency: HARD CONSTRAINT
   - Modality consistency: HARD CONSTRAINT 추가

---

## 2. 코드 수정 사항

### ✅ 수정 완료

#### 2.1 `03_s3_policy_resolver.py`
- **S4_EXAM_PROMPT_PROFILE 환경변수에 S5R3 옵션 추가**
  - `s5r3`, `s5r3_diagram`, `s5r3_diagram_4x5_2k` 지원
  - 기본값: `v8_diagram` (S5R2)

- **`build_constraint_block()` 함수 개선**
  - S5R3 감지 시 ZERO TOLERANCE text policy 적용
  - Laterality/view/modality에 PRE-CHECK 메시지 추가
  - S5R3 vs S5R2 분기 처리

#### 2.2 `01_generate_json.py`
- **S2_SYSTEM 프롬프트 버전 선택 지원**
  - `S2_PROMPT_VERSION` 환경변수 추가
  - `s5r3` 또는 `s5r3_v12` 설정 시 S5R3 버전 사용
  - 기본값: S5R2 (기존 호환성 유지)

---

## 3. 레지스트리 상태

### ✅ 등록 완료
- `S2_SYSTEM__S5R3`: `S2_SYSTEM__S5R3__v12.md`
- `S4_EXAM_SYSTEM__S5R3`: `S4_EXAM_SYSTEM__S5R3__v11_DIAGRAM_4x5_2K.md`
- `S4_EXAM_USER__S5R3`: `S4_EXAM_USER__S5R3__v11_DIAGRAM_4x5_2K.md`

### 기본 키 (S5R3로 업데이트)
- `S2_SYSTEM`: `S2_SYSTEM__S5R3__v12.md` (기본값, 최신 버전)
- `S4_EXAM_SYSTEM`: `S4_EXAM_SYSTEM__S5R3__v11_DIAGRAM_4x5_2K.md` (기본값, 최신 버전)
- `S4_EXAM_USER`: `S4_EXAM_USER__S5R3__v11_DIAGRAM_4x5_2K.md` (기본값, 최신 버전)

**변경 사항**: 레지스트리 기본 키를 S5R3로 업데이트. 환경변수 없이 자동으로 최신 버전 사용.

---

## 4. 다른 프롬프트 파일 확인

### ✅ 변경 불필요 (S5R3 개선 계획에 없음)

#### S1 프롬프트
- `S1_SYSTEM`: S5R2 v14 사용 중 (변경 불필요)
- `S1_USER_GROUP`: S5R2 v13 사용 중 (변경 불필요)
- **이유**: S5R3 개선 계획에 S1 변경 사항 없음

#### S2_USER_ENTITY
- `S2_USER_ENTITY`: S5R2 v11 사용 중 (변경 불필요)
- **이유**: S5R3 개선 계획에 S2_USER 변경 사항 없음

#### S4_CONCEPT 프롬프트
- `S4_CONCEPT_SYSTEM`: S5R2 v5 사용 중 (변경 불필요)
- `S4_CONCEPT_USER__*`: S5R2 v5 사용 중 (변경 불필요)
- **이유**: S5R3 개선 계획에 S4_CONCEPT 변경 사항 없음 (EXAM만 개선)

#### S5 프롬프트
- `S5_SYSTEM`: S5R2 v4 사용 중 (변경 불필요)
- `S5_USER_*`: S5R2 v3/v4 사용 중 (변경 불필요)
- **이유**: S5R3 개선 계획에 S5 변경 사항 없음

---

## 5. S5R3 사용 방법

### 자동 적용 (기본값)

레지스트리 기본 키가 S5R3로 설정되어 있어, **환경변수 설정 없이 자동으로 S5R3 프롬프트가 사용됩니다**.

```bash
# S1/S2 실행 (S5R3 자동 사용)
python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag "S5R3_TEST_$(date +%Y%m%d_%H%M%S)" \
  --arm G \
  --mode FINAL \
  --stage both \
  --provider gemini

# S3 실행 (S5R3 자동 사용)
python3 3_Code/src/03_s3_policy_resolver.py \
  --base_dir . \
  --run_tag "S5R3_TEST_..." \
  --arm G

# S4 실행
python3 3_Code/src/04_s4_image_generator.py \
  --base_dir . \
  --run_tag "S5R3_TEST_..." \
  --arm G
```

### 이전 버전 사용 (필요시)

이전 S5R2 버전을 사용하려면 레지스트리에서 직접 키를 지정하거나, 코드에서 명시적으로 `S5R2` 키를 사용하도록 수정해야 합니다.

---

## 6. 확인 완료 사항

### ✅ 프롬프트 파일
- [x] S5R3 프롬프트 파일 생성 완료
- [x] 레지스트리에 S5R3 항목 등록 완료
- [x] 기본 키는 S5R2 유지 (호환성)

### ✅ 코드 통합
- [x] `03_s3_policy_resolver.py`: 기본값을 S5R3로 설정 (환경변수 분기 제거)
- [x] `01_generate_json.py`: 환경변수 분기 제거, 레지스트리 기본 키 사용
- [x] `build_constraint_block()`: S5R3 요구사항을 기본값으로 적용

### ✅ 다른 프롬프트
- [x] S1 프롬프트: 변경 불필요 확인
- [x] S2_USER_ENTITY: 변경 불필요 확인
- [x] S4_CONCEPT 프롬프트: 변경 불필요 확인
- [x] S5 프롬프트: 변경 불필요 확인

---

## 7. 다음 단계

1. **S5R3 실행 준비 완료**
   - 환경변수 설정 후 실행 가능
   - 기본값은 S5R2 유지 (기존 실행 영향 없음)

2. **테스트 실행 권장**
   - 소규모 그룹으로 S5R3 테스트 실행
   - Text budget ZERO TOLERANCE 효과 확인
   - Laterality/view/modality validation 효과 확인

3. **S5R3 vs S5R2 비교**
   - S5R3 실행 후 S5R0 vs S5R3 비교 분석
   - Expansion criteria 재평가

---

**문서 버전**: 1.0  
**최종 업데이트**: 2025-12-31

