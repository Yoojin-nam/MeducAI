# Medical Term Translation Workflow

## 원칙
1. **원본 파일은 절대 수정하지 않음**
2. **번역본은 `__medterm_en.jsonl` suffix 사용**
3. **Resume 기능으로 중단 후 재개 가능**

## 파일 구조

### 원본 파일 (수정 금지)
- `s2_results__s1armG__s2armG.jsonl` (3518줄, 16M)
- `s2_results__s1armG__s2armG__regen.jsonl` (16M)

### 번역본 파일 (생성 대상)
- `s2_results__s1armG__s2armG__medterm_en.jsonl` (Baseline 번역본)
- `s2_results__s1armG__s2armG__regen__medterm_en.jsonl` (전체 Regen 번역본)
- `s2_results__s1armG__s2armG__regen__CARD_REGEN_ONLY__medterm_en.jsonl` (CARD_REGEN만 번역본)

## 작업 단계

### 1단계: Baseline 번역 완료 (현재 진행 중)
```bash
# 현재 상태: 829/3518 완료 (24%)
# Resume 모드로 자동 이어서 진행됨
python3 3_Code/src/tools/anki/translate_medical_terms.py \
    --input 2_Data/metadata/generated/FINAL_DISTRIBUTION/s2_results__s1armG__s2armG.jsonl \
    --output 2_Data/metadata/generated/FINAL_DISTRIBUTION/s2_results__s1armG__s2armG__medterm_en.jsonl \
    --model gemini-3-flash-preview \
    --max_workers 10
```

**중요**: Resume 기능이 자동으로 이미 번역된 829개를 건너뛰고 나머지 2689개만 번역합니다.

### 2단계: Regen CARD_REGEN 번역 확인 (완료)
- `s2_results__s1armG__s2armG__regen__CARD_REGEN_ONLY__medterm_en.jsonl` (383줄)
- 192번 레코드 포함 확인

### 3단계: 전체 Regen 번역 파일 생성 (Merge)
```bash
python3 3_Code/src/tools/anki/merge_full_regen_translations.py \
    --baseline_translated 2_Data/metadata/generated/FINAL_DISTRIBUTION/s2_results__s1armG__s2armG__medterm_en.jsonl \
    --regen_card_regen_only 2_Data/metadata/generated/FINAL_DISTRIBUTION/s2_results__s1armG__s2armG__regen__CARD_REGEN_ONLY__medterm_en.jsonl \
    --original_regen 2_Data/metadata/generated/FINAL_DISTRIBUTION/s2_results__s1armG__s2armG__regen.jsonl \
    --cards_csv 2_Data/metadata/generated/FINAL_DISTRIBUTION/appsheet_export/Cards.csv \
    --output 2_Data/metadata/generated/FINAL_DISTRIBUTION/s2_results__s1armG__s2armG__regen__medterm_en.jsonl
```

**Merge 로직**:
- `CARD_REGEN` 카드: Regen 번역본 사용
- `IMAGE_REGEN`, `PASS` 카드: Baseline 번역본 사용

### 4단계: Export 스크립트 업데이트
- `export_appsheet_tables.py`: `__medterm_en.jsonl` 파일 읽기
- `export_final_anki_integrated.py`: `__medterm_en.jsonl` 파일 읽기
- `export_all_specialty_decks.sh`: `__medterm_en.jsonl` 파일 경로 사용

### 5단계: 테스트 및 검증
- 번역된 파일로 AppSheet export 테스트
- 번역된 파일로 Anki export 테스트
- 샘플 카드 QA (50+ 카드 spot check)

## 현재 상태 (2025-01-06)
- ✅ Baseline 번역: 829/3518 (24%)
- ✅ Regen CARD_REGEN 번역: 383줄 완료
- ⏳ Baseline 번역 계속 진행 필요 (2689개 남음)
- ⏳ 전체 Regen merge 필요
- ⏳ Export 스크립트 업데이트 필요

## 다음 작업
1. **Baseline 번역 재개** (가장 우선)
   - API Key Rotator로 여러 키 사용하여 병렬 처리
   - Resume 모드로 자동 진행

2. **Baseline 번역 완료 후**
   - 전체 Regen merge 실행
   - Export 스크립트 업데이트
   - 통합 테스트

