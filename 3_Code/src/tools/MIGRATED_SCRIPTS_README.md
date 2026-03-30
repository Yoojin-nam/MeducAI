# Migrated Scripts from Scripts/

**이동 일시**: 2025-12-22

---

## 개요

`3_Code/Scripts` 폴더에 있던 재사용 가능한 유틸리티 스크립트들을 `tools/` 폴더로 이동했습니다.

---

## tools/에 이동된 스크립트

### 1. `convert_s2_to_md.py` (5.3 KB)

**용도**: S2 결과 JSONL을 Markdown 형식으로 변환

**사용법**:
```bash
python3 3_Code/src/tools/convert_s2_to_md.py \
  --input 2_Data/metadata/generated/RUN_TAG/s2_results__armA.jsonl \
  --output output.md
```

**특징**:
- S2 결과 파일을 읽어서 Markdown 형식으로 변환
- 카드 정보, 선택지, 이미지 힌트 등을 보기 좋게 포맷팅

---

### 2. `regenerate_s4_manifest.py` (7.5 KB)

**용도**: 기존 이미지 파일들로부터 S4 manifest 재생성

**사용법**:
```bash
python3 3_Code/src/tools/regenerate_s4_manifest.py \
  --base_dir . \
  --run_tag RUN_TAG \
  --arm A
```

**특징**:
- 이미 생성된 이미지 파일들을 스캔하여 manifest 재생성
- 이미지 파일명에서 메타데이터 추출 (run_tag, group_id, entity_id, card_role 등)
- S4 manifest가 누락되었거나 손상된 경우 유용

---

## tools/qa/에 이동된 스크립트

### 1. `retry_missing_s1_groups.py` (10.6 KB)

**용도**: S1 출력에서 누락된 그룹들 재시도

**사용법**:
```bash
python3 3_Code/src/tools/qa/retry_missing_s1_groups.py \
  --base_dir . \
  --run_tag RUN_TAG \
  --arms A B C
```

**참고**: `tools/qa/retry_failed_s1_groups.py`와 기능이 유사하나, 세부 동작이 다를 수 있음

---

### 2. `retry_failed_qa_groups.py` (17.2 KB)

**용도**: QA 실패 그룹 재시도

**사용법**:
```bash
python3 3_Code/src/tools/qa/retry_failed_qa_groups.py \
  --base_dir . \
  --run_tag RUN_TAG \
  --arm A
```

---

### 3. `retry_failed_pdfs.py` (4.7 KB)

**용도**: PDF 생성 실패 재시도

**사용법**:
```bash
python3 3_Code/src/tools/qa/retry_failed_pdfs.py \
  --base_dir . \
  --run_tag RUN_TAG \
  --arm A
```

---

### 4. `verify_pdf_distribution.py` (11.1 KB)

**용도**: PDF 배포 검증

**사용법**:
```bash
python3 3_Code/src/tools/qa/verify_pdf_distribution.py \
  --base_dir . \
  --run_tag RUN_TAG
```

---

### 5. `verify_pdf_distribution_detailed.py` (11.4 KB)

**용도**: PDF 배포 상세 검증

**사용법**:
```bash
python3 3_Code/src/tools/qa/verify_pdf_distribution_detailed.py \
  --base_dir . \
  --run_tag RUN_TAG
```

---

## Import 방법

다른 Python 스크립트에서 이 모듈들을 import하여 사용할 수 있습니다:

```python
import sys
from pathlib import Path

# src 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import
from tools.convert_s2_to_md import format_card_markdown
from tools.regenerate_s4_manifest import parse_image_filename
```

---

## 참고

- 원래 위치: `3_Code/Scripts/`
- 이동된 위치: `3_Code/src/tools/` 또는 `3_Code/src/tools/qa/`
- 관련 문서: `3_Code/Scripts/TOOLS_MIGRATION_PLAN.md`

