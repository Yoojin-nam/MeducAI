# Legacy 파일 및 코드 정리 요약

**정리 일시**: 2025-12-22

---

## 정리 내용

### 1. Legacy 메타데이터 파일 이동

**이동 위치**: `2_Data/metadata/` → `2_Data/metadata/legacy/`

#### 이동된 파일들

| 파일 | 크기 | 설명 |
|------|------|------|
| `partial_results.json` | 59 KB | 이전 LLM 실행 결과 (visual_type, anki_type 등) |
| `taxonomy.json` | 167 KB | Taxonomy 계층 구조 (05_Taxonomy 노트북 출력) |
| `translation_map.json` | 21 KB | 한글→영어 번역 맵 (용어 사전 형태) |
| **총계** | **~247 KB** | |

#### 정리 이유

- ✅ 현재 파이프라인에서 사용하지 않음
- ✅ 모든 정보는 최종 SSOT인 `Radiology_Curriculum_Weight_Factor.xlsx`에 포함됨
- ✅ 코드베이스에서 참조하지 않음 (grep 검색 결과 없음)

#### 생성된 문서

- `2_Data/metadata/legacy/README.md`: Legacy 파일 상세 설명
- `2_Data/metadata/LEGACY_FILES_README.md`: 업데이트 (이동 완료 상태 반영)

---

### 2. Legacy 코드 정리 문서화

**위치**: `3_Code/archived/`

#### Archived 코드 현황

- **Python 파일**: 40개
- **백업 파일** (.bak, .BAK): 37개
- **하위 폴더**: 4개
  - `src_old/`: 이전 버전 소스 코드 (24개 파일)
  - `src_2/`: 중간 버전 소스 코드 (23개 파일)
  - `refer/`: 참고용 코드 예제 (4개 파일)
  - `03_Human_Baseline/`: Human Baseline 프로토콜 문서 (2개 파일)

#### 생성된 문서

- `3_Code/archived/README.md`: Archived 코드 설명 및 구조 정리

---

## 현재 사용 중인 파일 및 코드

### 메타데이터 파일 (SSOT)

- `2_Data/processed/Radiology_Curriculum_Weight_Factor.xlsx`: **최종 SSOT**
- `2_Data/metadata/groups_canonical.csv`: Groups 캐논컬 데이터
- `2_Data/metadata/groups_canonical.meta.json`: Groups 메타데이터

### 소스 코드

- `3_Code/src/`: 현재 사용 중인 소스 코드
- `3_Code/Scripts/`: 실행 스크립트들
- `3_Code/notebooks/`: Jupyter 노트북들 (01~04 + Tag/Weight)

---

## 번역 데이터 저장 위치

번역 기록은 다음 파일들에 저장되어 있습니다:

1. **`Radiology_Curriculum_Translated_DB.xlsx`**
   - 번역 컬럼: `Specialty_EN_LABEL`, `Specialty_EN_TAG`, `Anatomy_EN_LABEL`, `Anatomy_EN_TAG`, `Modality_Type_EN_LABEL`, `Modality_Type_EN_TAG`, `Category_EN_LABEL`, `Category_EN_TAG`, `Objective_EN`

2. **`Radiology_Curriculum_Weight_Factor.xlsx`** (최종 SSOT)
   - 위의 번역 컬럼 + Tag + weight_factor 포함

**참고**: `translation_map.json`은 용어 사전 형태의 매핑 딕셔너리로, Excel 파일의 행별 번역이 아닙니다.

---

## 전처리 파이프라인 요약

```
Radiology_Curriculum.pdf (원본)
  ↓
01_Parser → Radiology_Curriculum.xlsx (raw)
  ↓
02_Enrichment → Radiology_Curriculum_Enriched.xlsx (Topic, Archetype 추가)
  ↓
03_EDA → EDA 보고서 (분석만)
  ↓
04_Translate → Radiology_Curriculum_Translated_DB.xlsx (한글→영어 번역)
  ↓
06_Tag → Radiology_Curriculum_Tagged.xlsx (Tag 자동 생성)
  ↓
0_Merge_Weights → Radiology_Curriculum_Weight_Factor.xlsx (최종 SSOT)
  ↓
0_build_groups_canonical.py → groups_canonical.csv (SSOT)
```

---

## 참고 문서

- `2_Data/metadata/LEGACY_FILES_README.md`: Legacy 파일 상세 분석
- `2_Data/metadata/legacy/README.md`: Legacy 파일 설명
- `3_Code/archived/README.md`: Archived 코드 설명
- `0_Protocol/00_Governance/Upstream_Curriculum_Preparation_and_LLM_Usage.md`: 전처리 프로토콜

---

## 다음 단계 (선택 사항)

1. ✅ **완료**: Legacy 메타데이터 파일 이동
2. ✅ **완료**: Legacy 코드 문서화
3. 🔄 **선택**: Git에서 legacy 파일들을 .gitignore에 추가 (필요시)
4. 🔄 **선택**: Archived 코드 중 완전히 불필요한 백업 파일들 삭제 (신중하게 검토 후)

---

**정리 완료일**: 2025-12-22

