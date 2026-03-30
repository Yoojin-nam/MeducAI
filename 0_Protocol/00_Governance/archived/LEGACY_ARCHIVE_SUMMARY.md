# Legacy 파일 Archive 요약

**작업 일시**: 2025-12-22

---

## Archive 완료 내역

### 1. Configs Legacy

**위치**: `3_Code/configs/legacy/`

| 파일 | 크기 | 상태 | 이유 |
|------|------|------|------|
| `tagging_rules_v1.0.json` | 1.8 KB | Archive | v1.1로 대체됨 |
| `Tagging_Standard_v1.0.md` | 4.1 KB | Archive | 참고용 문서 (코드에서 직접 참조 안 함) |

**현재 사용 중**:
- `tagging_rules_v1.1.json` (962 KB) - 현재 사용 중
- `styles.json` (2.3 KB) - 현재 사용 중

---

### 2. Notebooks Legacy

**위치**: `3_Code/notebooks/legacy/`

| 파일 | 크기 | 상태 | 이유 |
|------|------|------|------|
| `RaB-LLM_05_Taxonomy.ipynb` | 36 KB | Archive | 현재 전처리 파이프라인에서 사용 안 함 |

**현재 사용 중** (6개):
1. `RaB-LLM_01_Parser.ipynb` - PDF 파싱
2. `RaB-LLM_02_Enrichment.ipynb` - Topic, Archetype 추가
3. `RaB-LLM_03_Curriculum_EDA.ipynb` - EDA 분석
4. `RaB-LLM_04_Curriculum_translate.ipynb` - 한글→영어 번역
5. `RaB-LLM_06_tag_autogenerator.ipynb` - Tag 자동 생성
6. `0_merge_weights.ipynb` - 가중치 병합

---

## 주의사항

### `RaB-LLM_06_tag_autogenerator.ipynb` 참고

이 노트북이 `tagging_rules_v1.0.json`을 참조하고 있습니다:
```python
TAG_RULES_PATH = os.path.join(PROJECT_ROOT, "3_Code/configs/tagging_rules_v1.0.json")
```

**권장사항**:
- 필요시 노트북에서 `tagging_rules_v1.1.json`을 사용하도록 업데이트 가능
- 또는 legacy 폴더에서 v1.0 파일을 복원하여 사용 가능

---

## 이전 Archive 작업

### Metadata Legacy
- **위치**: `2_Data/metadata/legacy/`
- **파일**: `partial_results.json`, `taxonomy.json`, `translation_map.json`

### Generated Folders
- **위치**: `99_archived/generated_old/`
- **내용**: `S0_QA_final_time` 제외한 71개 run_tag 폴더

---

---

### 3. Scripts Legacy

**위치**: `3_Code/Scripts/legacy/`

**Archive된 스크립트**: 약 22개

| 카테고리 | 개수 | 설명 |
|---------|------|------|
| test_* | 10개 | 테스트 스크립트들 |
| old run_* | 5개 | 구버전 run 스크립트들 (v8로 대체) |
| debug_* | 1개 | 디버그 스크립트 |
| old smoke/verify | 3개 | 구버전 smoke/verify 스크립트들 |
| one_time | 1개 | 일회성 스크립트 |
| typo | 1개 | 오타 파일 (`verify_run.sh.ㅐ이`) |

**현재 사용 중인 핵심 스크립트**:
- `run_full_pipeline_armA_sample_v8.sh` ⭐
- `run_6arm_s1_s2_full.py` ⭐
- `run_s0_smoke_6arm.py` ⭐
- `generate_sample_pdf_anki.py` ⭐
- `generate_sample_all_specialties.py` ⭐
- `verify_run.sh` ⭐

---

## 참고 문서

- `3_Code/configs/legacy/README.md`: Configs legacy 설명
- `3_Code/notebooks/legacy/README.md`: Notebooks legacy 설명
- `3_Code/Scripts/legacy/README.md`: Scripts legacy 설명
- `3_Code/Scripts/SCRIPTS_CLEANUP_PLAN.md`: Scripts 정리 계획
- `2_Data/metadata/legacy/README.md`: Metadata legacy 설명
- `99_archived/generated_old/README.md`: Generated folders archive 설명

