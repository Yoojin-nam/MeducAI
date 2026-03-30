# Pipeline Implementation Update Log — 2025-12-20

**Status:** Canonical  
**Version:** 1.0  
**Last Updated:** 2025-12-20  
**Purpose:** 파이프라인 실행 도구 및 유틸리티 업데이트 이력

---

## 개요

이 문서는 2025-12-20에 수행된 파이프라인 실행 도구 및 유틸리티 업데이트를 기록합니다.

---

## 주요 변경 사항

### 1. 6-Arm 실행 스크립트 개선

**파일:** `3_Code/Scripts/run_6arm_s1_s2_full.py`

#### 1.1 Arms 선택 옵션 추가

**추가 기능:**
- `--arms` 옵션 추가: 특정 arm만 선택하여 실행 가능
- 기본값: 모든 arm (A, B, C, D, E, F)

**사용 예시:**
```bash
# Arm A만 실행
python3 3_Code/Scripts/run_6arm_s1_s2_full.py \
  --run_tag test_armA \
  --sample 1 \
  --arms A

# 여러 arm 선택
python3 3_Code/Scripts/run_6arm_s1_s2_full.py \
  --run_tag test_AB \
  --sample 1 \
  --arms A B
```

**관련 코드:**
- `main()` 함수의 argument parser

---

#### 1.2 리포트 저장 위치 변경

**변경 전:**
- 프로젝트 루트: `6ARM_S1_S2_RESULTS_{run_tag}.md`

**변경 후:**
- `2_Data/metadata/generated/{run_tag}/6ARM_S1_S2_RESULTS_{run_tag}.md`

**장점:**
- 각 run_tag의 실행 결과와 리포트가 함께 저장됨
- 프로젝트 루트가 깔끔해짐
- 실행 결과 관리가 용이함

**관련 코드:**
- `main()` 함수의 리포트 경로 설정 부분

---

### 2. 모델 확인 도구 업데이트

**파일:** `3_Code/src/tools/check_models.py`

#### 2.1 Gemini SDK 변경

**변경 전:**
- `google.generativeai` SDK 사용

**변경 후:**
- `google.genai` SDK 사용 (새로운 SDK)

**변경 사항:**
- `genai.configure()` → `genai.Client(api_key=api_key)`
- `genai.list_models()` → `client.models.list()`
- 이미지 생성 모델과 텍스트 생성 모델 구분 표시

**관련 코드:**
- `list_gemini_models()` 함수 전체 재작성

---

## 코드 변경 사항

### 파일: `3_Code/Scripts/run_6arm_s1_s2_full.py`

**추가:**
- `--arms` argument parser 옵션
- 리포트 저장 디렉토리 생성 로직

**수정:**
- `arms` 변수: 하드코딩 → `args.arms`에서 가져오기
- 리포트 경로: 프로젝트 루트 → `generated/{run_tag}/` 디렉토리

---

### 파일: `3_Code/src/tools/check_models.py`

**수정:**
- `list_gemini_models()` 함수 전체 재작성
- 새로운 `google.genai` SDK 사용
- 이미지/텍스트 모델 구분 표시

---

## 마이그레이션 가이드

### 기존 리포트 파일 이동

프로젝트 루트에 있던 리포트 파일들을 각 run_tag 디렉토리로 이동:

```bash
# 자동 이동 스크립트 (이미 실행됨)
for file in 6ARM_S1_S2_RESULTS_*.md; do
  run_tag=$(echo "$file" | sed 's/6ARM_S1_S2_RESULTS_//; s/\.md$//')
  target_dir="2_Data/metadata/generated/$run_tag"
  mkdir -p "$target_dir"
  mv "$file" "$target_dir/"
done
```

**이동된 리포트:**
- 총 18개 리포트 파일 이동 완료
- 각 run_tag 디렉토리에 저장됨

---

## 테스트 결과

### 테스트 실행
- Run Tag: `test_armA_sample1_v5`
- Arm: A만 선택
- Sample: 1

### 결과
- ✅ `--arms A` 옵션 정상 작동
- ✅ 리포트가 올바른 위치에 저장됨
- ✅ 전체 파이프라인 (S1→S2→S3→S4) 정상 실행

---

## 관련 문서

- `Code_to_Protocol_Traceability.md`: 코드-프로토콜 추적성 맵
- `README_run.md`: 실행 가이드

---

### 3. 샘플 PDF/Anki 생성 스크립트 추가

**새 파일:**
- `3_Code/Scripts/generate_sample_pdf_anki.py`: Specialty별 랜덤 그룹 선택하여 PDF/Anki 생성
- `3_Code/Scripts/generate_sample_all_specialties.py`: 모든 specialty 통합 PDF/Anki 생성
- `3_Code/Scripts/test_6arm_single_group.py`: 단일 그룹에 대한 6-arm 전체 파이프라인 테스트

**기능:**
- `generate_sample_pdf_anki.py`: 각 specialty에서 랜덤으로 1개 그룹 선택, 개별 PDF/Anki 생성
- `generate_sample_all_specialties.py`: 모든 specialty에서 랜덤으로 1개씩 선택, 통합 PDF 1개 + 통합 Anki 1개 생성
- `test_6arm_single_group.py`: 지정된 그룹에 대해 6-arm 전체 파이프라인 테스트

**사용 예시:**
```bash
# 모든 specialty 통합 샘플 생성
python3 3_Code/Scripts/generate_sample_all_specialties.py \
  --run_tag SAMPLE_ALL_20251220_180008 \
  --arm A

# 특정 그룹 6-arm 테스트
python3 3_Code/Scripts/test_6arm_single_group.py \
  --group_key knee_joint__diagnostic_imaging \
  --run_tag TEST_6ARM_20251220
```

**관련 코드:**
- `3_Code/Scripts/generate_sample_pdf_anki.py`
- `3_Code/Scripts/generate_sample_all_specialties.py`
- `3_Code/Scripts/test_6arm_single_group.py`

---

### 4. S4 Manifest 재생성 스크립트 추가

**새 파일:**
- `3_Code/Scripts/regenerate_s4_manifest.py`: 기존 이미지 파일로부터 S4 manifest 재생성

**기능:**
- 이미지 디렉토리를 스캔하여 파일명에서 메타데이터 추출
- S3 spec과 매칭하여 원본 entity_id 형식 유지
- S4 manifest 재생성

**사용 예시:**
```bash
python3 3_Code/Scripts/regenerate_s4_manifest.py \
  --run_tag SAMPLE_ALL_20251220_180008 \
  --arm A
```

**관련 코드:**
- `3_Code/Scripts/regenerate_s4_manifest.py`

---

## 변경 이력

- **2025-12-20 (오후)**: 추가 업데이트
  - 샘플 PDF/Anki 생성 스크립트 추가
  - S4 manifest 재생성 스크립트 추가
- **2025-12-20 (오전)**: 초기 업데이트
  - `--arms` 옵션 추가
  - 리포트 저장 위치 변경
  - 모델 확인 도구 SDK 업데이트

