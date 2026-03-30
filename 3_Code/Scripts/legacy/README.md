# Legacy Scripts

## 개요

이 폴더에는 현재 사용하지 않는 legacy 스크립트들이 보관되어 있습니다.

**이동 일시**: 2025-12-22

---

## Archive된 스크립트 목록

### 1. Test 스크립트들 (10개)

모든 `test_*` 스크립트들은 테스트/개발용으로 사용되었으며, 현재 프로덕션 파이프라인에서는 사용하지 않습니다.

- `test_2specialties_armA.py` - 2개 specialty 테스트
- `test_6arm_different_specialties.py` - 6-arm 다른 specialty 테스트
- `test_6arm_single_group.py` - 단일 그룹 6-arm 테스트 (Protocol 문서에서 언급되나 테스트용)
- `test_failed_groups.py` - 실패 그룹 테스트
- `test_full_arm_2groups_per_specialty.py` - Specialty당 2그룹 테스트
- `test_pdf_generation_only.py` - PDF 생성 테스트
- `test_physics_armA_sample1.sh` - Physics Arm A 샘플 테스트
- `test_s1_all_arms_sample1.py` - S1 모든 arm 샘플 테스트
- `test_s2_v31_6arm.sh` - S2 v31 6-arm 테스트
- `test_stage_separation.sh` - Stage 분리 테스트

**상태**: 테스트용 (필요 시 재생성 가능)

---

### 2. 구버전 Run 스크립트들 (5개)

새로운 버전으로 대체된 run 스크립트들입니다.

- `run_full_pipeline_armA_sample.sh` - **대체**: `run_full_pipeline_armA_sample_v8.sh`
- `run_all.sh` - 구버전 전체 실행 스크립트
- `run_6arm.sh` - **대체**: `run_6arm_s1_s2_full.py`
- `run_sample_gemini_20tables.sh` - 구버전 Gemini 샘플 스크립트
- `run_sample_gemini_2tables.sh` - 구버전 Gemini 샘플 스크립트

**상태**: 구버전 (새 버전 사용 권장)

---

### 3. Debug 스크립트 (1개)

디버깅용 스크립트입니다.

- `debug_failed_groups.py` - 실패 그룹 디버깅

**상태**: 디버그용 (필요 시 사용 가능)

---

### 4. 구버전 Smoke/Verify 스크립트들 (3개)

새로운 버전으로 대체되었거나 중복된 스크립트들입니다.

- `smoke_sample1.sh` - 구버전 smoke 테스트
- `smoke_s0_6arm_fixed12.sh` - 구버전 S0 smoke 테스트
- `verify_all.sh` - 구버전 전체 검증 스크립트

**상태**: 구버전 (현재는 `run_s0_smoke_6arm.py`, `verify_run.sh` 사용)

---

### 5. 일회성 스크립트 (1개)

일회성 작업용 스크립트입니다.

- `move_temp_files_to_temp_folder.py` - 임시 파일 정리 스크립트 (이미 실행 완료)

**상태**: 일회성 (실행 완료)

---

### 6. 오타 파일 (1개)

파일명 오타로 생성된 파일입니다.

- `verify_run.sh.ㅐ이` - 오타 파일 (올바른 파일: `verify_run.sh`)

**상태**: 삭제 가능 (오타 파일)

---

## 현재 사용 중인 핵심 스크립트들

### 실행 스크립트

1. **`run_full_pipeline_armA_sample_v8.sh`** ⭐
   - 전체 파이프라인 실행 (S1/S2 → S3 → S4 → PDF → Anki)
   - Protocol 문서에서 권장

2. **`run_6arm_s1_s2_full.py`** ⭐
   - 6-arm S1/S2 실행
   - Protocol 문서에서 언급

3. **`run_s0_smoke_6arm.py`** ⭐
   - S0 Smoke test
   - Protocol 문서에서 언급

4. **`run_s1_stress_3x.sh`** ⭐
   - S1 Stress 테스트
   - Protocol 문서에서 언급

### 생성/검증 스크립트

5. **`generate_sample_pdf_anki.py`** ⭐
   - Specialty별 랜덤 그룹 선택하여 PDF/Anki 생성
   - Protocol 문서에서 언급

6. **`generate_sample_all_specialties.py`** ⭐
   - 모든 specialty 통합 PDF/Anki 생성
   - Protocol 문서에서 언급

7. **`verify_run.sh`** ⭐
   - Run 검증 스크립트
   - Protocol 문서에서 언급

### 유틸리티 스크립트

- `generate_pdf_from_run_tag.py` - Run tag에서 PDF 생성
- `retry_missing_s1_groups.py` - S1 누락 그룹 재시도
- `retry_failed_qa_groups.py` - QA 실패 그룹 재시도
- `retry_failed_pdfs.py` - 실패 PDF 재시도
- `resume_s4_image_generation.sh` - S4 이미지 생성 재개
- `create_combined_anki_deck.py` - 통합 Anki 덱 생성
- `regenerate_s4_manifest.py` - S4 manifest 재생성
- `verify_pdf_distribution.py` - PDF 배포 검증
- `verify_pdf_distribution_detailed.py` - PDF 배포 상세 검증
- `convert_s2_to_md.py` - S2 결과를 Markdown으로 변환
- `create_google_form_qa_python.py` - Google Form QA 생성
- `create_google_form_qa.js` - Google Form QA 생성 (JS)
- `generate_stage_separation_report.py` - Stage 분리 리포트 생성
- `preflight_s2_nsweep_min.sh` - S2 Preflight 체크

---

## 참고 문서

- `3_Code/Scripts/SCRIPTS_CLEANUP_PLAN.md`: 정리 계획 문서
- `0_Protocol/05_Pipeline_and_Execution/README_run.md`: 실행 가이드
- `0_Protocol/05_Pipeline_and_Execution/Code_to_Protocol_Traceability.md`: 코드-Protocol 매핑
- `3_Code/README.md`: 코드 README

---

## 복원 방법

필요 시 legacy 폴더에서 스크립트를 복원할 수 있습니다:

```bash
# 예: test_6arm_single_group.py 복원
cp 3_Code/Scripts/legacy/test_6arm_single_group.py 3_Code/Scripts/
```

