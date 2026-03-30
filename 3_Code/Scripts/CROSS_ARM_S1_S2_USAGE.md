# Cross-Arm S1/S2 사용 가이드

**Last Updated:** 2025-12-23

## 개요

S1과 S2를 서로 다른 arm으로 실행할 수 있으며, **방법 1 (파일명 개선) + 방법 2 (RUN_TAG 분리)**를 함께 사용하여 안전하게 관리할 수 있습니다.

---

## 방법 1: S2 출력 파일명에 S1 arm 정보 포함 (✅ 구현 완료)

S2 출력 파일명이 `s2_results__s1arm{S1_ARM}__s2arm{S2_ARM}.jsonl` 형식으로 변경되었습니다.

**장점:**
- 같은 S2 arm이라도 S1 arm이 다르면 다른 파일에 저장되어 덮어쓰기 방지
- 파일명만 봐도 어떤 S1 arm과 S2 arm 조합인지 명확히 알 수 있음

---

## 방법 2: RUN_TAG 분리 사용 (권장)

S1과 S2를 다른 RUN_TAG로 분리하여 관리하면 더욱 안전하고 명확합니다.

**장점:**
- 각 실험 단계를 명확히 구분
- 실수로 덮어쓰는 것을 방지
- 추적 및 관리가 용이

---

## 사용 시나리오

### 시나리오: S1 A, E 실행 후 각각 S2 A, B, C 실행

#### 1단계: S1 실행 (RUN_TAG 분리)

```bash
# S1 A 실행
RUN_TAG_S1_A="FINAL_S1_A_$(date +%Y%m%d_%H%M%S)"
python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag "$RUN_TAG_S1_A" \
  --arm A \
  --mode FINAL \
  --stage 1

# S1 E 실행
RUN_TAG_S1_E="FINAL_S1_E_$(date +%Y%m%d_%H%M%S)"
python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag "$RUN_TAG_S1_E" \
  --arm E \
  --mode FINAL \
  --stage 1

# RUN_TAG 저장
echo "S1_A: $RUN_TAG_S1_A" > run_tags.txt
echo "S1_E: $RUN_TAG_S1_E" >> run_tags.txt
```

**생성되는 파일:**
```
2_Data/metadata/generated/FINAL_S1_A_YYYYMMDD_HHMMSS/
└── stage1_struct__armA.jsonl

2_Data/metadata/generated/FINAL_S1_E_YYYYMMDD_HHMMSS/
└── stage1_struct__armE.jsonl
```

#### 2단계: S1 A 결과로 S2 A, B, C 실행

```bash
# RUN_TAG 로드
RUN_TAG_S1_A="FINAL_S1_A_20251223_120000"  # 위에서 저장한 태그

# S2 A 실행 (S1 A 결과 사용)
RUN_TAG_S2_A="FINAL_S1A_S2A_$(date +%Y%m%d_%H%M%S)"
python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag "$RUN_TAG_S2_A" \
  --arm A \
  --s1_arm A \
  --mode FINAL \
  --stage 2

# S2 B 실행 (S1 A 결과 사용)
RUN_TAG_S2_B="FINAL_S1A_S2B_$(date +%Y%m%d_%H%M%S)"
python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag "$RUN_TAG_S2_B" \
  --arm B \
  --s1_arm A \
  --mode FINAL \
  --stage 2

# S2 C 실행 (S1 A 결과 사용)
RUN_TAG_S2_C="FINAL_S1A_S2C_$(date +%Y%m%d_%H%M%S)"
python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag "$RUN_TAG_S2_C" \
  --arm C \
  --s1_arm A \
  --mode FINAL \
  --stage 2
```

**생성되는 파일:**
```
2_Data/metadata/generated/FINAL_S1A_S2A_YYYYMMDD_HHMMSS/
└── s2_results__s1armA__s2armA.jsonl

2_Data/metadata/generated/FINAL_S1A_S2B_YYYYMMDD_HHMMSS/
└── s2_results__s1armA__s2armB.jsonl

2_Data/metadata/generated/FINAL_S1A_S2C_YYYYMMDD_HHMMSS/
└── s2_results__s1armA__s2armC.jsonl
```

#### 3단계: S1 E 결과로 S2 A, B, C 실행

```bash
# RUN_TAG 로드
RUN_TAG_S1_E="FINAL_S1_E_20251223_120000"  # 위에서 저장한 태그

# S2 A 실행 (S1 E 결과 사용)
RUN_TAG_S2_A="FINAL_S1E_S2A_$(date +%Y%m%d_%H%M%S)"
python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag "$RUN_TAG_S2_A" \
  --arm A \
  --s1_arm E \
  --mode FINAL \
  --stage 2

# S2 B 실행 (S1 E 결과 사용)
RUN_TAG_S2_B="FINAL_S1E_S2B_$(date +%Y%m%d_%H%M%S)"
python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag "$RUN_TAG_S2_B" \
  --arm B \
  --s1_arm E \
  --mode FINAL \
  --stage 2

# S2 C 실행 (S1 E 결과 사용)
RUN_TAG_S2_C="FINAL_S1E_S2C_$(date +%Y%m%d_%H%M%S)"
python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag "$RUN_TAG_S2_C" \
  --arm C \
  --s1_arm E \
  --mode FINAL \
  --stage 2
```

**생성되는 파일:**
```
2_Data/metadata/generated/FINAL_S1E_S2A_YYYYMMDD_HHMMSS/
└── s2_results__s1armE__s2armA.jsonl

2_Data/metadata/generated/FINAL_S1E_S2B_YYYYMMDD_HHMMSS/
└── s2_results__s1armE__s2armB.jsonl

2_Data/metadata/generated/FINAL_S1E_S2C_YYYYMMDD_HHMMSS/
└── s2_results__s1armE__s2armC.jsonl
```

---

## 파일명 형식

### S1 출력
- `stage1_struct__arm{ARM}.jsonl`
- 예: `stage1_struct__armA.jsonl`, `stage1_struct__armE.jsonl`

### S2 출력 (새로운 형식)
- `s2_results__s1arm{S1_ARM}__s2arm{S2_ARM}.jsonl`
- 예: 
  - `s2_results__s1armA__s2armA.jsonl` (S1 A → S2 A)
  - `s2_results__s1armA__s2armB.jsonl` (S1 A → S2 B)
  - `s2_results__s1armE__s2armA.jsonl` (S1 E → S2 A)

---

## 안전성 보장

### 방법 1 + 방법 2 동시 사용 시:

1. **파일명 레벨 보호:**
   - 같은 S2 arm이라도 S1 arm이 다르면 다른 파일명
   - 예: `s2_results__s1armA__s2armA.jsonl` vs `s2_results__s1armE__s2armA.jsonl`

2. **RUN_TAG 레벨 보호:**
   - 각 실험 조합을 다른 RUN_TAG로 분리
   - 실수로 같은 RUN_TAG를 사용해도 파일명이 다르므로 안전

3. **이중 보호:**
   - 두 가지 방법을 함께 사용하면 실수로 인한 데이터 손실 위험이 최소화됨

---

## 주의사항

1. **하위 호환성:**
   - 기존 코드에서 `s2_results__arm{ARM}.jsonl` 형식을 찾는 경우 업데이트 필요
   - 예: `03_s3_policy_resolver.py`, `07_export_anki_deck.py` 등

2. **S1 arm 지정:**
   - S2 실행 시 `--s1_arm`을 명시적으로 지정하는 것을 권장
   - 생략 시 기본값은 `--arm`과 동일

3. **RUN_TAG 관리:**
   - S1 RUN_TAG를 파일에 저장하여 나중에 참조 가능하도록 관리
   - 예: `run_tags.txt`, `run_tag_*.txt`

---

## 예시 스크립트

```bash
#!/bin/bash
# S1 A, E 실행 후 각각 S2 A, B, C 실행

# S1 실행
RUN_TAG_S1_A="FINAL_S1_A_$(date +%Y%m%d_%H%M%S)"
RUN_TAG_S1_E="FINAL_S1_E_$(date +%Y%m%d_%H%M%S)"

echo "S1 A: $RUN_TAG_S1_A"
echo "S1 E: $RUN_TAG_S1_E"

# S1 A 실행
python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag "$RUN_TAG_S1_A" \
  --arm A \
  --mode FINAL \
  --stage 1

# S1 E 실행
python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag "$RUN_TAG_S1_E" \
  --arm E \
  --mode FINAL \
  --stage 1

# S1 A 결과로 S2 A, B, C 실행
for s2_arm in A B C; do
  RUN_TAG_S2="FINAL_S1A_S2${s2_arm}_$(date +%Y%m%d_%H%M%S)"
  python3 3_Code/src/01_generate_json.py \
    --base_dir . \
    --run_tag "$RUN_TAG_S2" \
    --arm "$s2_arm" \
    --s1_arm A \
    --mode FINAL \
    --stage 2
done

# S1 E 결과로 S2 A, B, C 실행
for s2_arm in A B C; do
  RUN_TAG_S2="FINAL_S1E_S2${s2_arm}_$(date +%Y%m%d_%H%M%S)"
  python3 3_Code/src/01_generate_json.py \
    --base_dir . \
    --run_tag "$RUN_TAG_S2" \
    --arm "$s2_arm" \
    --s1_arm E \
    --mode FINAL \
    --stage 2
done
```

---

## 요약

✅ **방법 1 (파일명 개선)**: S2 출력 파일명에 S1 arm 정보 포함  
✅ **방법 2 (RUN_TAG 분리)**: 각 실험 조합을 다른 RUN_TAG로 관리  
✅ **이중 보호**: 두 방법을 함께 사용하여 최대한 안전하게 관리

