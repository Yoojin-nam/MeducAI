# Legacy Notebooks

## 개요

이 폴더에는 현재 전처리 파이프라인에서 사용하지 않는 legacy 노트북들이 보관되어 있습니다.

**이동 일시**: 2025-12-22

---

## 이동된 노트북

### `RaB-LLM_05_Taxonomy.ipynb` (~36 KB)

- **용도**: Taxonomy 구조 생성 (Specialty → Anatomy → Topic 계층)
- **입력**: `Radiology_Curriculum_Translated_DB.xlsx`
- **출력**: `taxonomy.json` (이미 `2_Data/metadata/legacy/`로 이동됨)
- **상태**: ❌ 미사용
  - 현재 코드(`0_build_groups_canonical.py`, `01_generate_json.py` 등)에서 참조하지 않음
  - Taxonomy 정보는 `Radiology_Curriculum_Weight_Factor.xlsx`에 포함되어 있음

---

## 현재 사용 중인 노트북들

다음 노트북들은 현재 전처리 파이프라인에서 사용 중입니다:

1. **`RaB-LLM_01_Parser.ipynb`** - PDF 파싱
2. **`RaB-LLM_02_Enrichment.ipynb`** - Topic, Archetype 추가
3. **`RaB-LLM_03_Curriculum_EDA.ipynb`** - EDA 분석
4. **`RaB-LLM_04_Curriculum_translate.ipynb`** - 한글→영어 번역
5. **`RaB-LLM_06_tag_autogenerator.ipynb`** - Tag 자동 생성
6. **`0_merge_weights.ipynb`** - 가중치 병합 (최종 SSOT 생성)

---

## 전처리 파이프라인

```
Radiology_Curriculum.pdf
  ↓
01_Parser → Radiology_Curriculum.xlsx
  ↓
02_Enrichment → Radiology_Curriculum_Enriched.xlsx
  ↓
03_EDA (분석만)
  ↓
04_Translate → Radiology_Curriculum_Translated_DB.xlsx
  ↓
06_Tag → Radiology_Curriculum_Tagged.xlsx
  ↓
0_Merge_Weights → Radiology_Curriculum_Weight_Factor.xlsx (최종 SSOT)
```

**참고**: 05_Taxonomy는 이전에 사용되었으나 현재 파이프라인에서는 제외됨.

---

## 참고

- Legacy metadata 파일: `2_Data/metadata/legacy/`
- 현재 전처리 파이프라인: `0_Protocol/00_Governance/Upstream_Curriculum_Preparation_and_LLM_Usage.md`

