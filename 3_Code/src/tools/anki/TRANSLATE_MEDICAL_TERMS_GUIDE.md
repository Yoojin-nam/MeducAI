# Anki 카드 의학용어 번역 가이드

이 도구는 이미 생성된 Anki 카드에서 **의학용어만** 한글에서 영어로 번역합니다. 문제 내용과 형식은 전혀 변경하지 않습니다.

## 개요

- **입력**: S2 JSONL 파일 (Anki 카드 데이터)
- **출력**: 번역된 JSONL 파일
- **번역 대상**: 의학용어만 (질병명, 해부학 용어, 검사명 등)
- **보존**: 한국어 문장 구조, 문법, 형식, 기존 영어 용어

## 사용법

### 방법 1: Python 스크립트 직접 실행

```bash
cd /path/to/workspace/workspace/MeducAI

python3 3_Code/src/tools/anki/translate_medical_terms.py \
    --input 2_Data/metadata/generated/FINAL_DISTRIBUTION/s2_results__s1armG__s2armG.jsonl \
    --output 2_Data/metadata/generated/FINAL_DISTRIBUTION/s2_results__translated.jsonl \
    --model gemini-3-flash-preview
```

### 방법 2: Shell 스크립트 사용

```bash
cd /path/to/workspace/workspace/MeducAI

./3_Code/Scripts/translate_anki_medical_terms.sh \
    --input 2_Data/metadata/generated/FINAL_DISTRIBUTION/s2_results__s1armG__s2armG.jsonl \
    --output 2_Data/metadata/generated/FINAL_DISTRIBUTION/s2_results__translated.jsonl
```

### 테스트 실행 (처음 10개 카드만)

```bash
python3 3_Code/src/tools/anki/translate_medical_terms.py \
    --input 2_Data/metadata/generated/FINAL_DISTRIBUTION/s2_results__s1armG__s2armG.jsonl \
    --output 2_Data/metadata/generated/FINAL_DISTRIBUTION/s2_results__translated_test.jsonl \
    --max_cards 10
```

## 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--input` | 입력 S2 JSONL 파일 경로 | (필수) |
| `--output` | 출력 JSONL 파일 경로 | (필수) |
| `--model` | Gemini 모델 이름 | `gemini-3-flash-preview` |
| `--batch_size` | 진행 상황 출력 주기 (N개마다) | `10` |
| `--max_cards` | 처리할 최대 레코드 수 (테스트용) | 없음 (전체) |

## 번역 예시

### 입력 (번역 전)
```
"front": "간 환자에서 Portal Hypertension 소견이 관찰됨"
"back": "정답: B\n\n근거:\n* 뇌경색의 특징적 소견"
```

### 출력 (번역 후)
```
"front": "Liver 환자에서 Portal Hypertension 소견이 관찰됨"
"back": "정답: B\n\n근거:\n* Cerebral infarction의 특징적 소견"
```

## 번역 규칙

1. **의학용어만 번역**: 질병명, 해부학 용어, 검사명, 소견명 등
2. **문장 구조 보존**: 한국어 문법, 조사(~은/는, ~을/를 등) 유지
3. **일반 단어 유지**: "환자", "검사", "관찰", "시사" 등은 그대로 유지
4. **기존 영어 유지**: 이미 영어로 된 용어는 변경하지 않음
5. **형식 보존**: 줄바꿈, 특수문자, 포맷팅 모두 유지

## 주의사항

- **API 키 필요**: `GOOGLE_API_KEY` 또는 `RAB_LLM_API_KEY` 환경변수 설정 필요
- **처리 시간**: 카드 수에 따라 시간이 걸릴 수 있습니다 (카드당 약 1-2초)
- **비용**: Gemini API 사용으로 인한 비용이 발생할 수 있습니다
- **백업 권장**: 원본 파일을 백업한 후 실행하세요

## 출력 파일 사용

번역된 JSONL 파일을 사용하여 Anki 덱을 다시 생성할 수 있습니다:

```bash
# 번역된 파일로 Anki 덱 생성
python3 3_Code/src/tools/anki/export_final_anki_integrated.py \
    --s2_baseline 2_Data/metadata/generated/FINAL_DISTRIBUTION/s2_results__translated.jsonl \
    # ... 기타 옵션
```

## 문제 해결

### API 키 오류
```
RuntimeError: Missing Gemini API key
```
**해결**: `.env` 파일에 `GOOGLE_API_KEY=your_key` 추가

### 번역 실패
일부 카드의 번역이 실패하면 원본 텍스트가 그대로 유지됩니다. 경고 메시지가 출력됩니다.

### 메모리 부족
큰 파일의 경우 `--max_cards` 옵션으로 나눠서 처리하세요.

## 관련 파일

- **스크립트**: `3_Code/src/tools/anki/translate_medical_terms.py`
- **Shell 래퍼**: `3_Code/Scripts/translate_anki_medical_terms.sh`
- **Anki 내보내기**: `3_Code/src/tools/anki/export_final_anki_integrated.py`

