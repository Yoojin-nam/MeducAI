# Tools

**위치**: `3_Code/src/tools/`

## 개요

이 폴더에는 파이프라인에서 재사용 가능한 유틸리티 함수와 도구들이 포함되어 있습니다.

---

## 주요 파일

### 유틸리티 함수

- **`format_objective_bullets.py`** (2.1 KB)
  - 목표 목록을 Markdown bullet 형식으로 변환
  - S1 프롬프트 생성 시 사용
  - 사용: `from tools.format_objective_bullets import objective_list_to_bullets`

- **`prompt_bundle.py`** (1.9 KB)
  - 프롬프트 번들 로더
  - `3_Code/prompt/` 폴더에서 프롬프트 파일 로드
  - 사용: `from tools.prompt_bundle import load_prompt_bundle`

### 검증/테스트 도구

- **`check_models.py`** (7.1 KB)
  - 사용 가능한 모델 목록 확인
  - Google Gemini, OpenAI, DeepSeek, Anthropic 모델 확인

- **`test_gemini_api_key.py`** (11 KB)
  - Gemini API 키 테스트
  - 관련 문서: `README_API_KEY_TEST.md`

### 변환/재생성 유틸리티

- **`convert_s2_to_md.py`** (5.3 KB)
  - S2 결과 JSONL을 Markdown 형식으로 변환
  - **이동됨**: `3_Code/Scripts/` → `3_Code/src/tools/`
  - 관련 문서: `MIGRATED_SCRIPTS_README.md`

- **`regenerate_s4_manifest.py`** (7.5 KB)
  - 기존 이미지 파일들로부터 S4 manifest 재생성
  - **이동됨**: `3_Code/Scripts/` → `3_Code/src/tools/`
  - 관련 문서: `MIGRATED_SCRIPTS_README.md`

---

## 하위 디렉토리

### `final_qa/` ⭐ (CRITICAL)

> **FINAL QA 핵심 모듈** - 6,000장 카드 검증을 위한 AppSheet 통합 도구

- `export_appsheet_tables.py`: AppSheet용 CSV 테이블 내보내기
- `generate_assignments.py`: 평가자 할당 생성
- 관련 문서: `0_Protocol/06_QA_and_Study/FINAL_QA_*.md`

### `batch/`

배치 이미지 생성 도구들:
- `batch_image_generator.py`: Gemini Batch API를 사용한 대량 이미지 생성

### `allocation/`

할당(Allocation) 관련 도구들:
- `s0_allocation.py`: S0 할당 로직
- `final_distribution_allocation.py`: FINAL 배포 할당 로직
- `analyze_final_allocation.py`: 할당 분석 도구

### `s4/`

S4 이미지 생성 관련 도구들:
- `generate_realistic_images.py`: Realistic 이미지 생성 (Assignments 기반)
  - Specialist 330 pool 카드에 대해 realistic 이미지 생성
  - Assignments.csv 읽어서 대상 카드 필터링
  - 두 가지 모드 지원:
    - **Sync 모드** (기본): `04_s4_image_generator.py` 호출
    - **Batch 모드** (`--batch`): `batch_image_generator.py` 호출 (대량 생성에 적합)
  - 사용법:
    ```bash
    # Sync 모드 (실시간 생성)
    python3 generate_realistic_images.py --run_tag FINAL_DISTRIBUTION --assignments Assignments.csv
    
    # Batch 모드 (비동기 배치 생성)
    python3 generate_realistic_images.py --run_tag FINAL_DISTRIBUTION --assignments Assignments.csv --batch
    
    # 배치 상태 확인
    python3 generate_realistic_images.py --run_tag FINAL_DISTRIBUTION --assignments Assignments.csv --check_status
    ```

### `s5/`

S5 검증 관련 도구들:
- `s5_validation_payload.py`: S5 검증 페이로드 생성
- `s5_report.py`: S5 리포트 생성
- `s5r_phase1_analysis.py`: S5R Phase 1 분석

### `qa/`

QA 관련 도구들 (S0 QA 및 일반 QA):
- `s0_noninferiority.py`: S0 비열등성 분석
- `s5_decision.py`: S5 결정 로직
- `retry_failed_*.py`: 실패 그룹 재시도 도구들
- `verify_pdf_distribution*.py`: PDF 배포 검증
- 기타 QA 관련 스크립트들

자세한 내용: `MIGRATED_SCRIPTS_README.md`

### `recovery/`

복구 관련 도구들:
- `recover_images_from_archive.py`: 아카이브에서 이미지 복구
- `restore_s2_from_backup.py`: S2 백업 복원
- `match_similar_entities.py`: 유사 엔티티 매칭

### `multi_agent/`

Multi-agent 시스템 도구들:
- `score_calculator.py`: 점수 계산기

### `validation/`

검증 도구들:
- `validate_s1_s2_alignment.py`: S1-S2 정렬 검증

### `prompt_refinement/`

프롬프트 개선 도구들:
- `build_patch_backlog.py`: 패치 백로그 생성
- `make_prompt_diff_report.py`: 프롬프트 변경 리포트 생성

---

## 사용 방법

### Import 예제

```python
import sys
from pathlib import Path

# src 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import
from tools.format_objective_bullets import objective_list_to_bullets
from tools.prompt_bundle import load_prompt_bundle
from tools.convert_s2_to_md import format_card_markdown
```

### 직접 실행

```bash
# S2 결과를 Markdown으로 변환
python3 3_Code/src/tools/convert_s2_to_md.py \
  --input 2_Data/metadata/generated/RUN_TAG/s2_results__armA.jsonl \
  --output output.md

# S4 manifest 재생성
python3 3_Code/src/tools/regenerate_s4_manifest.py \
  --base_dir . \
  --run_tag RUN_TAG \
  --arm A

# 모델 확인
python3 3_Code/src/tools/check_models.py

# API 키 테스트
python3 3_Code/src/tools/test_gemini_api_key.py
```

---

## PPTX 오프라인 이미지 추출/통계 (REALISTIC 튜닝 근거)

- **`pptx_image_audit.py`**
  - `.pptx` 내부의 `ppt/media/*` 임베디드 이미지를 **원본 그대로 추출**
  - 이미지별 **luminance(밝기/대비) 통계** + **GRAY/COLOR(chroma score)** 요약
  - `manifest.jsonl`/`manifest.csv` + `report.md` + contact sheet(`.png`)를 생성

**사용 예시**:

```bash
python3 3_Code/src/tools/pptx_image_audit.py \
  --base_dir . \
  --input_dir 2_Data/raw/2024 \
  --output_dir 2_Data/eda/PPTX_IMAGE_AUDIT_20240103
```

---

## 파일 관리 규칙

- **재사용 가능한 함수**: `tools/` 루트에 위치
- **QA 관련 도구**: `tools/qa/` 폴더
- **할당 관련 도구**: `tools/allocation/` 폴더
- **문서**: 각 도구의 용도와 사용법을 README에 문서화

---

## 참고

- 이동된 스크립트: `MIGRATED_SCRIPTS_README.md`
- API 키 테스트: `README_API_KEY_TEST.md`
- Scripts 폴더: `3_Code/Scripts/` (실행 스크립트)

