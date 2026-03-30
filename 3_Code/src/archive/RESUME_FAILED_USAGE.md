# `--resume-failed` 옵션 사용 가이드

## 개요

`--resume-failed` 옵션은 S1 또는 S2에서 실패한 그룹만 자동으로 감지하여 재실행합니다.

## 기본 사용법

```bash
python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag "YOUR_RUN_TAG" \
  --arm G \
  --mode FINAL \
  --stage <1|2|both> \
  --resume-failed
```

## 옵션 설명

### `--resume-failed`
- **기능**: 실패한 그룹만 자동으로 감지하여 재실행
- **파일 모드**: Append 모드 (기존 데이터 보존)
- **제한사항**: `--resume`과 동시 사용 불가

### `--stage` 옵션과 조합

#### S1 실패한 그룹만 재실행
```bash
python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag "YOUR_RUN_TAG" \
  --arm G \
  --mode FINAL \
  --stage 1 \
  --resume-failed
```

#### S2 실패한 그룹만 재실행
```bash
python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag "YOUR_RUN_TAG" \
  --arm G \
  --mode FINAL \
  --stage 2 \
  --resume-failed
```

#### S1 또는 S2 실패한 그룹 모두 재실행
```bash
python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag "YOUR_RUN_TAG" \
  --arm G \
  --mode FINAL \
  --stage both \
  --resume-failed
```

## 실패 감지 로직

### S1 실패 감지
1. **시도한 그룹**: `stage1_raw__arm{arm}.jsonl`에서 읽음
2. **성공한 그룹**: `stage1_struct__arm{arm}.jsonl`에서 유효한 레코드 확인
   - 유효성 조건: `curriculum_content.entity_list`가 존재하고 리스트인 경우
3. **실패한 그룹**: 시도했지만 성공하지 않은 그룹 = `attempted_s1 - succeeded_s1`

### S2 실패 감지
1. **실행 로그**: `logs/s2_execution_log.jsonl`에서 `action="failed"`인 그룹
2. **전체 실패 그룹**: `s2_results__s1arm{s1_arm}__s2arm{arm}.jsonl`에서
   - `failed_entities >= total_entities`인 그룹 (모든 entity가 실패)
3. **부분 실패 그룹**: S1의 `entity_list`와 S2 results를 비교하여 누락된 entity가 있는 그룹
   - S1에 있는 entity가 S2 results에 없는 경우 감지
   - entity_name 정규화 (별표 제거) 후 비교

## 주의사항

### ⚠️ 제한사항
1. **`--resume`과 동시 사용 불가**
   ```bash
   # ❌ 에러 발생
   python3 3_Code/src/01_generate_json.py ... --resume --resume-failed
   ```

2. **Entity 단위 skip**: v2.1부터 일부 entity만 실패한 그룹을 재실행할 때, 이미 성공한 entity는 자동으로 skip됨
   - 예: 그룹에 20개 entity가 있고 1개만 실패한 경우 → 1개 entity만 재실행
   - 기존 성공한 entity는 skip되어 중복 생성되지 않음
   - 누락된 entity만 재실행하여 효율적

### ✅ 개선 사항 (v2.0)
1. **부분 실패 감지**: 일부 entity만 실패한 그룹도 자동으로 감지
   - S1의 `entity_list`와 S2 results를 비교하여 누락된 entity가 있는 그룹 찾기
   - entity_name 정규화 (별표 제거) 후 비교하여 정확도 향상

2. **안전 기능**
   - **파일 보존**: Append 모드로 열려 기존 데이터가 보존됨
   - **자동 종료**: 실패한 그룹이 없으면 자동으로 종료
   - **중복 방지**: 같은 그룹을 여러 번 재실행해도 append 모드로 추가됨

### ✅ 안전 기능
- **파일 보존**: Append 모드로 열려 기존 데이터가 보존됨
- **자동 종료**: 실패한 그룹이 없으면 자동으로 종료
- **중복 방지**: 같은 그룹을 여러 번 재실행해도 append 모드로 추가됨

## 사용 예시

### 예시 1: S2 실패한 그룹만 재실행
```bash
RUN_TAG="DEV_armG_mm_S5R2_after_postFix_20251230_193112__rep2"

python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag "$RUN_TAG" \
  --arm G \
  --mode FINAL \
  --stage 2 \
  --resume-failed
```

**출력 예시:**
```
[RESUME-FAILED] Found 3 failed groups. Retrying them.
[RESUME-FAILED] Filtered 8 groups. Processing 3 failed groups.
...
```

### 예시 2: S1 실패한 그룹만 재실행
```bash
python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag "$RUN_TAG" \
  --arm G \
  --mode FINAL \
  --stage 1 \
  --resume-failed
```

### 예시 3: S1 또는 S2 실패한 그룹 모두 재실행
```bash
python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag "$RUN_TAG" \
  --arm G \
  --mode FINAL \
  --stage both \
  --resume-failed
```

## 실패 감지 확인 방법

### S2 실행 로그 확인
```bash
# S2 실행 로그에서 실패한 그룹 확인
cat 2_Data/metadata/generated/YOUR_RUN_TAG/logs/s2_execution_log.jsonl | \
  jq 'select(.action=="failed") | .group_id'
```

### S1 실패 확인
```bash
# S1 raw에는 있지만 struct에는 없는 그룹 확인
python3 << 'EOF'
import json
from pathlib import Path

run_tag = "YOUR_RUN_TAG"
arm = "G"

raw_path = Path(f"2_Data/metadata/generated/{run_tag}/stage1_raw__arm{arm}.jsonl")
struct_path = Path(f"2_Data/metadata/generated/{run_tag}/stage1_struct__arm{arm}.jsonl")

# 시도한 그룹
attempted = set()
if raw_path.exists():
    with open(raw_path, 'r') as f:
        for line in f:
            if line.strip():
                rec = json.loads(line)
                gid = rec.get("group_id") or rec.get("metadata", {}).get("id")
                if gid:
                    attempted.add(gid)

# 성공한 그룹
succeeded = set()
if struct_path.exists():
    with open(struct_path, 'r') as f:
        for line in f:
            if line.strip():
                rec = json.loads(line)
                if "curriculum_content" in rec and "entity_list" in rec.get("curriculum_content", {}):
                    gid = rec.get("group_id") or rec.get("metadata", {}).get("id")
                    if gid:
                        succeeded.add(gid)

# 실패한 그룹
failed = attempted - succeeded
print(f"시도: {len(attempted)}개, 성공: {len(succeeded)}개, 실패: {len(failed)}개")
if failed:
    print("실패한 그룹:")
    for gid in sorted(failed):
        print(f"  - {gid}")
EOF
```

## `--resume` vs `--resume-failed` 비교

| 옵션 | 기능 | 파일 모드 | 사용 시기 |
|------|------|-----------|-----------|
| `--resume` | 이미 처리된 그룹은 skip, 나머지 처리 | Append | 중단된 실행을 이어서 계속 |
| `--resume-failed` | 실패한 그룹만 재실행 | Append | 실패한 그룹만 선택적으로 재시도 |

## 문제 해결

### 실패한 그룹이 감지되지 않는 경우

1. **S2 로그 확인**: `logs/s2_execution_log.jsonl`에 `action="failed"`가 있는지 확인
2. **S2 results 확인**: 모든 entity가 실패한 그룹인지 확인 (`failed_entities >= total_entities`)
3. **수동 지정**: `--only_group_id`로 수동으로 그룹 지정

```bash
# 수동으로 그룹 지정
python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag "$RUN_TAG" \
  --arm G \
  --mode FINAL \
  --stage 2 \
  --only_group_id grp_xxx \
  --only_group_id grp_yyy
```

### 일부 entity만 실패한 경우

**✅ v2.0부터 자동 감지됨**: `--resume-failed`가 S1과 S2를 비교하여 누락된 entity가 있는 그룹을 자동으로 감지합니다.

**동작 방식:**
1. S1의 `entity_list`에서 각 그룹의 예상 entity 목록 수집
2. S2 results에서 실제 생성된 entity 목록 수집
3. 비교하여 누락된 entity가 있는 그룹을 실패 그룹으로 표시
4. 해당 그룹 전체를 재실행 (일부 entity만 재실행하는 기능은 없음)

**참고:**
- 그룹 전체가 재실행되므로 기존 성공한 entity도 중복 생성될 수 있음
- Append 모드로 추가되므로 기존 데이터는 보존됨
- 중복 제거는 별도로 처리 필요

## 참고

- 실패 감지 로직: `load_failed_group_ids()` 함수 (line 5439-5700+)
  - S1 실패 감지: `stage1_raw` vs `stage1_struct` 비교
  - S2 전체 실패: `s2_execution_log.jsonl` 및 `s2_results` 파일 확인
  - S2 부분 실패: S1 `entity_list`와 S2 results 비교 (v2.0 추가)
- 옵션 정의: `--resume-failed` (line 5646-5648)
- 사용 위치: `main()` 함수 (line 5967-6033)

## 변경 이력

### v2.1 (최신)
- ✅ **Entity 단위 skip 추가**: 일부 entity만 실패한 그룹을 재실행할 때, 이미 성공한 entity는 자동으로 skip
- 기존 성공한 entity는 재실행하지 않아 중복 생성 방지
- 누락된 entity만 재실행하여 효율적

### v2.0
- ✅ **부분 실패 감지 추가**: 일부 entity만 실패한 그룹도 자동으로 감지
- S1의 `entity_list`와 S2 results를 비교하여 누락된 entity가 있는 그룹 찾기
- entity_name 정규화 (별표 제거) 후 비교하여 정확도 향상

### v1.0
- 그룹 전체 실패만 감지
- S2 실행 로그 및 전체 실패 그룹만 감지

