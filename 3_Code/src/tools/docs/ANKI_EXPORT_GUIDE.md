# Anki Deck Export Guide

> **스크립트**: `3_Code/src/07_export_anki_deck.py`  
> **버전**: v2.1 (2026-02)  
> **주요 변경**: 2차 시험용 덱 옵션 (`--second_exam`, `--exclude_specialties`, `--subjective_only`)

---

## 개요

Anki 덱 내보내기 스크립트는 S2 카드 데이터와 S4 이미지를 결합하여 Anki 패키지(.apkg)를 생성합니다.

### 지원 기능

| 기능 | 설명 |
|------|------|
| **전체 덱 생성** | 모든 카드를 하나의 덱으로 내보내기 |
| **분과별 덱 생성** | 특정 분과만 필터링하여 덱 생성 |
| **11개 분과 일괄 생성** | 모든 분과를 개별 덱으로 한번에 생성 |
| **2차 시험용 덱** | 물리·핵의학 제외, 주관식(Q1)만 포함 (`--second_exam`) |
| **이미지 포함** | S4에서 생성된 이미지 자동 임베딩 |
| **태그 자동 생성** | 카드 유형/분과/해부/모달리티/카테고리 태그 |

---

## 기본 사용법

### 1. 전체 덱 생성 (기본)

```bash
python3 3_Code/src/07_export_anki_deck.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G
```

**출력**: `6_Distributions/anki/MeducAI_FINAL_DISTRIBUTION_armG.apkg`

---

### 2. 분과별 덱 생성 (--specialty)

특정 분과의 카드만 필터링하여 덱을 생성합니다.

```bash
python3 3_Code/src/07_export_anki_deck.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G \
  --specialty thoracic_rad
```

**출력**: `6_Distributions/anki/MeducAI_FINAL_DISTRIBUTION_Thoracic.apkg`

---

### 3. 11개 분과 일괄 생성 (--all_specialties)

모든 분과를 개별 덱으로 한번에 생성합니다.

```bash
python3 3_Code/src/07_export_anki_deck.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G \
  --all_specialties
```

**출력** (11개 파일):
```
6_Distributions/anki/
├── MeducAI_FINAL_DISTRIBUTION_Abdominal.apkg
├── MeducAI_FINAL_DISTRIBUTION_Breast.apkg
├── MeducAI_FINAL_DISTRIBUTION_Cardiovascular.apkg
├── MeducAI_FINAL_DISTRIBUTION_Genitourinary.apkg
├── MeducAI_FINAL_DISTRIBUTION_IR.apkg
├── MeducAI_FINAL_DISTRIBUTION_MSK.apkg
├── MeducAI_FINAL_DISTRIBUTION_NeuroHN.apkg
├── MeducAI_FINAL_DISTRIBUTION_NuclearMedicine.apkg
├── MeducAI_FINAL_DISTRIBUTION_Pediatric.apkg
├── MeducAI_FINAL_DISTRIBUTION_PhysicsQC.apkg
└── MeducAI_FINAL_DISTRIBUTION_Thoracic.apkg
```

---

### 4. 2차 시험용 덱 (--second_exam)

1차 시험 후 2차 주관식 시험만 남았을 때 사용합니다. **물리**(PhysicsQC)와 **핵의학**(Nuclear Medicine) 분과를 제외하고, **주관식(Q1/Basic)** 카드만 포함한 덱을 생성합니다.

```bash
python3 3_Code/src/07_export_anki_deck.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G \
  --second_exam
```

**출력**: `6_Distributions/anki/MeducAI_FINAL_DISTRIBUTION_armG_2nd_exam.apkg`

**참고**: `--second_exam`은 `--specialty`, `--all_specialties`와 동시에 사용할 수 없습니다.

---

### 5. 세부 필터 (--exclude_specialties, --subjective_only)

- **--exclude_specialties ID1,ID2**: 지정한 분과를 제외 (쉼표 구분). 예: `nuclear_medicine,phys_qc_medinfo`
- **--subjective_only**: Q1(주관식) 카드만 내보내기, Q2(객관식) 제외

조합 예시 (2차 시험과 동일한 결과를 세부 옵션으로):

```bash
python3 3_Code/src/07_export_anki_deck.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G \
  --exclude_specialties nuclear_medicine,phys_qc_medinfo \
  --subjective_only \
  --output_path 6_Distributions/anki/MeducAI_2nd_exam_custom.apkg
```

---

## 지원 분과 목록

| Specialty ID | 표시 이름 | 설명 |
|--------------|-----------|------|
| `abdominal_rad` | Abdominal | 복부영상의학 |
| `breast_rad` | Breast | 유방영상의학 |
| `cv_rad` | Cardiovascular | 심혈관영상의학 |
| `gu_rad` | Genitourinary | 비뇨생식기영상의학 |
| `ir` | IR | 인터벤션영상의학 |
| `msk_rad` | MSK | 근골격영상의학 |
| `neuro_hn_rad` | NeuroHN | 신경/두경부영상의학 |
| `nuclear_medicine` | NuclearMedicine | 핵의학 |
| `ped_rad` | Pediatric | 소아영상의학 |
| `phys_qc_medinfo` | PhysicsQC | 물리/QC/의료정보 |
| `thoracic_rad` | Thoracic | 흉부영상의학 |

---

## 전체 CLI 옵션

```
usage: 07_export_anki_deck.py [-h] [--base_dir BASE_DIR] --run_tag RUN_TAG
                              [--arm ARM] [--s1_arm S1_ARM]
                              [--export_manifest_path EXPORT_MANIFEST_PATH]
                              [--images_dir IMAGES_DIR]
                              [--output_path OUTPUT_PATH]
                              [--allow_missing_images] [--image_only]
                              [--specialty SPECIALTY] [--all_specialties]
                              [--second_exam] [--exclude_specialties ID1,ID2]
                              [--subjective_only]
```

### 필수 옵션

| 옵션 | 설명 | 예시 |
|------|------|------|
| `--run_tag` | 실행 태그 (S2 결과 위치 결정) | `FINAL_DISTRIBUTION` |

### 주요 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--base_dir` | 프로젝트 루트 디렉토리 | `.` |
| `--arm` | S2 실행 arm (A-G) | `A` |
| `--s1_arm` | S1 arm (다를 경우만 지정) | `--arm`과 동일 |
| `--images_dir` | 이미지 디렉토리 경로 | `{out_dir}/images` (원본 고해상도). **용량 절감**: `{out_dir}/images_anki` 사용 시 Anki용 압축 이미지로 .apkg 크기 대폭 감소 (예: 5GB → 200MB 수준) |
| `--output_path` | 출력 .apkg 경로 | 자동 생성 |

### 분과 필터링 옵션

| 옵션 | 설명 |
|------|------|
| `--specialty SPECIALTY` | 특정 분과만 필터링 (위 목록 참조) |
| `--all_specialties` | 11개 분과 개별 덱 일괄 생성 |
| `--second_exam` | 2차 시험용: 물리·핵의학 제외, 주관식(Q1)만. 출력: `MeducAI_{run_tag}_arm{arm}_2nd_exam.apkg` |
| `--exclude_specialties ID1,ID2` | 제외할 분과 ID (쉼표 구분) |
| `--subjective_only` | Q1(주관식) 카드만 내보내기 |

**주의**: `--specialty`와 `--all_specialties`는 동시 사용 불가. `--second_exam`은 `--specialty`, `--all_specialties`와 동시 사용 불가.

### 이미지 처리 옵션

| 옵션 | 설명 | 용도 |
|------|------|------|
| `--allow_missing_images` | 이미지 누락 시 스킵 (에러 아님) | 디버그/샘플 |
| `--image_only` | 이미지 있는 카드만 포함 | 부분 내보내기 |

**프로덕션 배포 시**: 위 옵션 사용 금지. 이미지 누락 시 S4 재실행으로 해결

### Export Manifest (선택적)

| 옵션 | 설명 |
|------|------|
| `--export_manifest_path` | S6 export manifest JSON 경로 |

Manifest 모드에서는 그룹별로 baseline vs repaired 버전을 선택합니다.

---

## 실행 예시

### 예시 1: FINAL_DISTRIBUTION 전체 덱 생성

```bash
cd /path/to/workspace/workspace/MeducAI

python3 3_Code/src/07_export_anki_deck.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G
```

### 예시 2: 특정 분과 덱 생성 (커스텀 출력 경로)

```bash
python3 3_Code/src/07_export_anki_deck.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G \
  --specialty abdominal_rad \
  --output_path 6_Distributions/MeducAI_Final_Share/Anki/MeducAI_Abdominal.apkg
```

### 예시 3: 11개 분과 일괄 생성

```bash
python3 3_Code/src/07_export_anki_deck.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G \
  --all_specialties
```

### 예시 4: Realistic 이미지 디렉토리 지정

```bash
python3 3_Code/src/07_export_anki_deck.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G \
  --images_dir 2_Data/metadata/generated/FINAL_DISTRIBUTION/images_realistic
```

### 예시 5: Export Manifest 사용 (baseline/repaired 선택)

```bash
python3 3_Code/src/07_export_anki_deck.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G \
  --export_manifest_path 2_Data/metadata/generated/FINAL_DISTRIBUTION/s6_export_manifest__armG.json
```

---

## 출력 구조

### 기본 출력 경로

```
6_Distributions/anki/
├── MeducAI_{run_tag}_arm{arm}.apkg        # 전체 덱 (기본)
├── MeducAI_{run_tag}_{Specialty}.apkg     # 분과별 덱 (--specialty)
└── ... (11개 분과별 덱)                   # --all_specialties
```

### 덱 내부 구조

- **Notes (노트)**: S2의 각 카드 (Q1, Q2)
- **Cards (카드)**: Basic 또는 MCQ 형식
- **Media (미디어)**: S4 생성 이미지 (자동 임베딩)
- **Tags (태그)**: 
  - 카드 유형: `Basic` 또는 `MCQ`
  - 분과: `Specialty:{specialty}`
  - 해부: `Anatomy:{anatomy}`
  - 모달리티: `Modality:{modality}`
  - 카테고리: `Category:{category}`

---

## 에러 처리

### 이미지 누락 에러

```
[Export] FAIL: Q1 image missing (required): IMG__FINAL_DISTRIBUTION__G001__E01__Q1.png
```

**해결 방법**:
1. S4 이미지 생성 재실행
2. 또는 `--allow_missing_images` 사용 (디버그 전용)

### 잘못된 분과 지정

```
ValueError: Invalid specialty 'invalid'. Valid values: abdominal_rad, breast_rad, ...
```

**해결 방법**: 위 분과 목록에서 정확한 ID 사용

### 분과 필터 결과 없음

```
ValueError: No records found for specialty 'ped_rad'. Valid specialties: ...
```

**해결 방법**: S2 결과에 해당 분과 데이터가 있는지 확인

---

## 관련 문서

- **메인 README**: `3_Code/README.md`
- **S2 카드 생성**: `0_Protocol/04_Step_Contracts/S2_Contract.md`
- **S4 이미지 생성**: `0_Protocol/04_Step_Contracts/S4_Contract.md`
- **Anki 사용 가이드**: `6_Distributions/MeducAI_Final_Share/Anki_Guide.pdf`

---

## 변경 이력

| 날짜 | 버전 | 변경 내용 |
|------|------|----------|
| 2026-02 | v2.1 | `--second_exam`, `--exclude_specialties`, `--subjective_only` 옵션 추가 (2차 시험용 덱) |
| 2026-01 | v2.0 | `--specialty`, `--all_specialties` 옵션 추가 |
| 2025-12 | v1.0 | 초기 버전 (전체 덱 생성만 지원) |














