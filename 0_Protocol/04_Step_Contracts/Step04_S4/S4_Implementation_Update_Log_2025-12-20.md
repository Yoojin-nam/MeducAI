# S4 Implementation Update Log — 2025-12-20

**Status:** Canonical  
**Version:** 1.1  
**Last Updated:** 2025-12-20  
**Purpose:** S4 Image Generator 구현 업데이트 이력

---

## 개요

이 문서는 2025-12-20에 수행된 S4 (Image Generator) 구현 업데이트를 기록합니다.

---

## 주요 변경 사항

### 1. 이미지 생성 모델 변경 (Model Update)

**변경 전:**
- 기본 모델: `"gemini-2.5-flash-image"`

**변경 후:**
- 기본 모델: `"models/nano-banana-pro-preview"` (Gemini 3 Pro Image Preview)
- 환경 변수 `S4_IMAGE_MODEL`로 오버라이드 가능

**영향:**
- 더 높은 품질의 이미지 생성 가능
- 4K 해상도 지원 (테이블 비주얼용)

**관련 코드:**
- `04_s4_image_generator.py`: `IMAGE_MODEL` 상수

---

### 2. 스펙 종류별 분기 처리 (Spec Kind Branching)

**추가 기능:**
- `spec_kind`에 따라 다른 aspect ratio와 해상도 적용
- 카드 이미지와 테이블 비주얼 구분 처리

**설정:**

| spec_kind | Aspect Ratio | Image Size | 해상도 |
|-----------|--------------|------------|--------|
| `S2_CARD_IMAGE` | 4:5 | 1K | 1024x1280 |
| `S1_TABLE_VISUAL` | 16:9 | 2K | 더 높은 해상도 |

**관련 코드:**
- `04_s4_image_generator.py`: `generate_image()` 함수의 config 설정 부분

---

### 3. 파일명 규칙 확장 (Filename Rule Extension)

**변경 전:**
- 카드 이미지만: `IMG__{run_tag}__{group_id}__{entity_id}__{card_role}.png`

**변경 후:**
- 카드 이미지: `IMG__{run_tag}__{group_id}__{entity_id}__{card_role}.png`
- 테이블 비주얼: `IMG__{run_tag}__{group_id}__TABLE.png`

**관련 코드:**
- `04_s4_image_generator.py`: `make_image_filename()` 함수

---

### 4. Fail-Fast 규칙 확장 (Fail-Fast Extension)

**변경 전:**
- Q1 이미지 생성 실패 시만 FAIL-FAST

**변경 후:**
- Q1 이미지 생성 실패 → FAIL-FAST
- Q2 이미지 생성 실패 → FAIL-FAST (NEW)
- 테이블 비주얼 이미지 생성 실패 → FAIL-FAST (NEW)

**관련 코드:**
- `04_s4_image_generator.py`: `process_s4()` 함수의 실패 추적 로직

---

### 5. 이미지 추출 로직 개선 (Image Extraction Enhancement)

**개선 사항:**
- 더 강력한 응답 구조 파싱
- PNG 헤더 검증 추가
- 상세한 디버깅 정보 출력
- archived 코드의 간단한 방식 반영

**응답 구조 처리 순서:**
1. `response.candidates[0].content.parts` (가장 일반적)
2. `response.parts` (직접 parts)
3. 디버깅 정보 출력 (실패 시)

**PNG 검증:**
- 추출된 데이터가 PNG 헤더(`\x89PNG\r\n\x1a\n`)로 시작하는지 확인
- 파일 크기 검증 (100바이트 미만이면 실패)

**관련 코드:**
- `04_s4_image_generator.py`: `extract_image_from_response()` 함수

---

## 코드 변경 사항

### 파일: `3_Code/src/04_s4_image_generator.py`

**수정 함수:**
1. `make_image_filename()`:
   - `spec_kind` 파라미터 추가
   - 테이블 비주얼 파일명 처리 추가

2. `extract_image_from_response()`:
   - 응답 구조 파싱 개선
   - PNG 헤더 검증 추가
   - 디버깅 정보 강화

3. `generate_image()`:
   - `spec_kind`에 따른 aspect ratio/size 분기
   - PNG 헤더 검증
   - 파일 저장 검증

4. `process_s4()`:
   - Q2와 테이블 비주얼도 fail-fast 처리
   - `spec_kind` 필드 처리

**추가 상수:**
- `TABLE_ASPECT_RATIO = "16:9"`
- `TABLE_SIZE = "2K"`

---

## 출력 아티팩트 변경

### `s4_image_manifest__arm{arm}.jsonl`

**추가 필드:**
- `spec_kind`: `"S2_CARD_IMAGE"` 또는 `"S1_TABLE_VISUAL"`

**예시:**
```json
{
  "schema_version": "S4_IMAGE_MANIFEST_v1.0",
  "run_tag": "RUN_20251220",
  "group_id": "G001",
  "entity_id": "E001",
  "entity_name": "뇌경색",
  "card_role": "Q1",
  "spec_kind": "S2_CARD_IMAGE",  // 추가됨
  "media_filename": "IMG__RUN_20251220__G001__E001__Q1.png",
  "image_path": "/path/to/images/IMG__RUN_20251220__G001__E001__Q1.png",
  "generation_success": true,
  "image_required": true
}
```

**테이블 비주얼 예시:**
```json
{
  "schema_version": "S4_IMAGE_MANIFEST_v1.0",
  "run_tag": "RUN_20251220",
  "group_id": "G001",
  "entity_id": null,
  "entity_name": null,
  "card_role": null,
  "spec_kind": "S1_TABLE_VISUAL",  // 새로 추가
  "media_filename": "IMG__RUN_20251220__G001__TABLE.png",
  "image_path": "/path/to/images/IMG__RUN_20251220__G001__TABLE.png",
  "generation_success": true,
  "image_required": true
}
```

---

## 검증 규칙 변경

### Q2 검증 강화

**변경 전:**
- Q2 이미지 생성 실패 → 경고만 출력

**변경 후:**
- Q2 이미지 생성 실패 → `RuntimeError` 예외 발생 (FAIL-FAST)

### 테이블 비주얼 검증 추가

**새로운 규칙:**
- 테이블 비주얼 이미지 생성 실패 → `RuntimeError` 예외 발생 (FAIL-FAST)

---

## 하위 호환성

### 기존 S3 출력과의 호환성

- ✅ 기존 S3 출력 스키마와 호환 (`spec_kind` 필드가 없어도 기본값 `"S2_CARD_IMAGE"` 사용)
- ✅ 기존 이미지 스펙도 정상 처리

---

## 테스트 결과

### 테스트 실행
- Run Tag: `test_armA_sample1_v5`
- Arm: A
- Sample: 1

### 결과
- ✅ S1: 성공
- ✅ S2: 성공
- ✅ S3: 성공
- ✅ S4: 성공 (모든 이미지 생성 완료)

---

## 관련 문서

- `Entity_Definition_S4_Canonical.md`: S4 엔티티 정의
- `S4_Image_Cost_and_Resolution_Policy.md`: 이미지 비용 및 해상도 정책
- `S3_to_S4_Input_Contract_Canonical.md`: S3→S4 입력 계약
- `S3_S4_Code_Documentation.md`: 코드 동작 방식 문서 (프로젝트 루트)

---

### 6. Infographic만 생성하는 옵션 추가 (Selective Generation)

**추가 기능:**
- `--only-infographic` 옵션 추가
- Infographic(S1_TABLE_VISUAL)만 생성하고 카드 이미지(S2_CARD_IMAGE)는 스킵

**사용 예시:**
```bash
# Infographic만 생성
python3 3_Code/src/04_s4_image_generator.py \
  --base_dir . \
  --run_tag RUN_20251220 \
  --arm A \
  --only-infographic

# 모든 이미지 생성 (기존 동작)
python3 3_Code/src/04_s4_image_generator.py \
  --base_dir . \
  --run_tag RUN_20251220 \
  --arm A
```

**이유:**
- Infographic만 빠르게 재생성할 때 유용
- 카드 이미지는 이미 생성되어 있고 Infographic만 업데이트할 때 사용

**관련 코드:**
- `04_s4_image_generator.py`: `process_s4()` 함수에 `only_infographic` 파라미터 추가
- 스펙 필터링 로직 추가

---

## 변경 이력

- **2026-01-05**: Positive Regen (Option C Image Regeneration) 구현 완료
  - `--image_type regen` 완전 구현 (S5 `prompt_patch_hint` 기반)
  - Manifest 분리 정책 확정: `s4_image_manifest__armX__regen.jsonl`
  - Same RUN_TAG + 폴더/suffix 분리 (baseline 보존)
  - 참조: `S5_Positive_Regen_Procedure.md` (운영 가이드)
- **2026-01-15**: 이미지 타입별 폴더 및 파일명 규칙 추가
  - `--image_type` CLI 인자 추가 (anki, realistic, regen)
  - `--filename_suffix` CLI 인자 추가
  - 폴더 자동 설정 (images_anki/, images_realistic/, images_regen/)
  - 파일명 suffix 자동 설정 (_realistic, _regen)
  - 기본값은 기존 방식 유지 (하위 호환성 보장)
- **2025-12-20 (오후)**: 추가 업데이트
  - `--only-infographic` 옵션 추가
- **2025-12-20 (오전)**: 초기 구현 업데이트
  - 모델명 변경 (nano-banana-pro-preview)
  - 스펙 종류별 분기 처리
  - 파일명 규칙 확장
  - Fail-fast 규칙 확장
  - 이미지 추출 로직 개선

---

## 7. 이미지 타입별 폴더 및 파일명 규칙 (Image Type-based Folder & Filename Rules)

### 7.1 CLI 인자 추가

**새로운 인자:**
- `--image_type`: 이미지 타입 지정 (선택적, 기본값: None - 기존 방식 유지)
  - `anki`: `images_anki/` 폴더 사용, suffix 없음
  - `realistic`: `images_realistic/` 폴더 사용, `_realistic` suffix 추가
  - `regen`: `images_regen/` 폴더 사용, `_regen` suffix 추가 ✅ **구현 완료 (2026-01-05)**
    - S5 `prompt_patch_hint` 기반 positive regen
    - Same RUN_TAG (폴더 + suffix로 구분)
    - Manifest 분리: `s4_image_manifest__armX__regen.jsonl`
- `--filename_suffix`: 파일명 suffix 수동 지정 (선택적)

### 7.2 자동 설정 로직

**폴더 자동 설정:**
- `--image_type`이 지정되지 않으면: `images/` 폴더 (기존 방식)
- `--image_type anki`: `images_anki/` 폴더
- `--image_type realistic`: `images_realistic/` 폴더
- `--image_type regen`: `images_regen/` 폴더 ✅ **구현 완료 (2026-01-05)**

**파일명 suffix 자동 설정:**
- `--image_type`이 지정되지 않으면: suffix 없음 (기존 방식)
- `--image_type realistic`: `_realistic` suffix 추가
- `--image_type regen`: `_regen` suffix 추가 ✅ **구현 완료 (2026-01-05)**

**Manifest 분리 정책 (2026-01-05 추가):**
- Baseline: `s4_image_manifest__armX.jsonl`
- Regen: `s4_image_manifest__armX__regen.jsonl` (separate file to avoid overwrite)
- Realistic: `s4_image_manifest__armX__realistic.jsonl` (if applicable)

### 7.3 하위 호환성

- ✅ CLI 인자 없이 실행하면 기존 방식(`images/` 폴더, suffix 없음) 유지
- ✅ 기존에 생성된 이미지 파일과 호환

### 7.4 사용 예시

```bash
# 기존 방식 (기본값)
python 04_s4_image_generator.py --run_tag RUN_20251220 --arm G
# 결과: images/IMG__...Q1.jpg

# Realistic 이미지
python 04_s4_image_generator.py --run_tag RUN_20251220 --arm G --image_type realistic
# 결과: images_realistic/IMG__...Q1_realistic.jpg

# Regen 이미지 (향후)
python 04_s4_image_generator.py --run_tag RUN_20251220 --arm G --image_type regen
# 결과: images_regen/IMG__...Q1_regen.jpg
```

**관련 코드:**
- `04_s4_image_generator.py`: `make_image_filename()` 함수에 `suffix` 파라미터 추가
- `04_s4_image_generator.py`: `process_s4()` 함수에 `image_type`, `filename_suffix` 파라미터 추가
- `04_s4_image_generator.py`: 자동 설정 로직 추가

---

## 8. Export 단계 변경 (AppSheet Export)

### 8.1 폴더 구조 보존

- `export_appsheet_tables.py`에서 이미지 복사 시 폴더 구조 보존
- 상대 경로 반환 (예: `images_anki/IMG__...Q1.jpg`, `images_realistic/IMG__...Q1_realistic.jpg`)

**관련 코드:**
- `export_appsheet_tables.py`: `_copy_image()` 함수 수정 (폴더 구조 보존 옵션 추가)

---

