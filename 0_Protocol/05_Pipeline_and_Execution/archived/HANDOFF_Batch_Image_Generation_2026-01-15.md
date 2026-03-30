# 배치 이미지 생성 시스템 인계장

**작성일**: 2026-01-15  
**작성자**: AI Assistant  
**중요도**: ⚠️ **매우 높음** (비용이 많이 드는 작업)

---

## 📋 목차

1. [시스템 개요](#시스템-개요)
2. [주요 기능](#주요-기능)
3. [발생한 문제점과 해결법](#발생한-문제점과-해결법)
4. [중요 주의사항](#중요-주의사항)
5. [API 키 관리](#api-키-관리)
6. [배치 중복 방지 로직](#배치-중복-방지-로직)
7. [향후 개선 사항](#향후-개선-사항)

---

## 시스템 개요

### 목적
Google Gemini Batch API를 사용하여 대량의 이미지를 비동기적으로 생성하는 시스템입니다.

### 주요 파일
- **메인 스크립트**: `3_Code/src/tools/batch/batch_image_generator.py`
- **API 키 관리**: `3_Code/src/tools/api_key_rotator.py`
- **배치 트래킹**: `2_Data/metadata/.batch_tracking.json`
- **API 키 상태**: `2_Data/metadata/.api_key_status.json`

### 기본 사용법

```bash
# 배치 생성 및 제출
python3 3_Code/src/tools/batch/batch_image_generator.py \
  --input 2_Data/metadata/generated/FINAL_DISTRIBUTION/s3_image_spec__armG.jsonl \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --image_size 2K \
  --resume

# 배치 상태 확인 및 다운로드
python3 3_Code/src/tools/batch/batch_image_generator.py --check_status --base_dir .

# 특정 배치만 확인
python3 3_Code/src/tools/batch/batch_image_generator.py --check_status --base_dir . --batch_id <batch_id>
```

---

## 주요 기능

### 1. 배치 자동 분할
- 토큰 제한(2,000,000 tokens)에 맞춰 자동으로 배치 분할
- 배치 크기 최적화 (동적 조정)
- 토큰 사용량 사전 검증

### 2. API 키 자동 회전
- 여러 API 키 자동 감지 및 관리
- 429 (Quota Exhausted) 에러 시 자동 키 회전
- 키별 사용량 추적 및 상태 관리

### 3. 중복 방지
- 이미 제출된 배치와의 중복 체크
- 로컬에 존재하는 이미지 체크
- 배치 생성 전 필터링

### 4. 배치 상태 모니터링
- 배치 상태 자동 확인 (PENDING, RUNNING, SUCCEEDED, FAILED)
- 완료된 배치 자동 다운로드
- 배치별 이미지 존재 여부 확인

---

## 발생한 문제점과 해결법

### 문제 1: 배치 간 중복 이미지 제출

**문제 상황**:
- 여러 배치에 동일한 이미지가 중복으로 제출됨
- 예: 228개 이미지가 2개 배치에 모두 포함됨 (중복률 3.0%)
- 배치 생성 시점에 이미 제출된 배치를 체크하지 않음

**원인**:
- 배치를 먼저 생성한 후, 각 배치 제출 시점에만 중복 체크
- 배치 생성 전에 이미 제출된 항목을 필터링하지 않음

**해결법**:
```python
# 배치 생성 전에 이미 제출된 항목 필터링
# 위치: batch_image_generator.py, 라인 ~2136

# 1. 모든 프롬프트 로드
prompts_data = load_prompts_from_spec(spec_path)

# 2. 이미 제출된 배치와 로컬 이미지 체크하여 필터링
filtered_prompts = []
for prompt in prompts_data:
    # 이미 제출된 배치에 포함되어 있는지 체크
    is_submitted = check_if_submitted(prompt, tracking_data)
    # 로컬에 이미지가 존재하는지 체크
    image_exists = check_local_image(prompt, images_dir)
    
    if not is_submitted and not image_exists:
        filtered_prompts.append(prompt)

# 3. 필터링된 프롬프트만으로 배치 생성
batches = split_prompts_by_token_limit(filtered_prompts, ...)
```

**결과**: 배치 생성 전 필터링으로 배치 간 중복 완전 방지

---

### 문제 2: 이미 다운로드된 이미지 재다운로드

**문제 상황**:
- 이미 다운로드된 이미지가 다시 다운로드됨
- 배치 결과 파일을 다운로드한 후에도 이미 존재하는 이미지를 다시 저장 시도

**원인**:
- 배치 결과 다운로드 시 이미지 존재 여부를 정확히 체크하지 않음
- `prompts_metadata`만으로 체크하여 실제 생성된 이미지와 불일치

**해결법**:
```python
# check_batch_images_exist 함수 개선
# 위치: batch_image_generator.py, 라인 ~1289

def check_batch_images_exist(
    prompts_metadata: List[Dict[str, Any]],
    images_dir: Path,
    run_tag: str,
    batch_results: Optional[Dict[str, Any]] = None,  # 실제 배치 결과 추가
) -> Tuple[bool, int, int]:
    """
    배치 이미지 존재 여부 확인
    
    Args:
        batch_results: 실제 배치 결과 파일 (있으면 더 정확한 체크)
    """
    # 1차: prompts_metadata로 빠른 체크
    if not batch_results:
        # 기존 로직 (파일 시스템 기반)
        ...
    
    # 2차: batch_results로 정확한 체크 (더 정확)
    if batch_results:
        for key, result in batch_results.items():
            # 실제 생성된 이미지만 체크
            ...
```

**결과**: 실제 생성된 이미지만 정확히 체크하여 불필요한 재다운로드 방지

---

### 문제 3: run_tag 불일치로 인한 이미지 저장 위치 오류

**문제 상황**:
- 배치의 `run_tag`와 개별 프롬프트의 `run_tag`가 다를 수 있음
- 이미지가 잘못된 디렉토리에 저장되거나, 존재 여부를 잘못 체크

**원인**:
- 배치 트래킹 파일의 `run_tag`를 사용하여 이미지 디렉토리 결정
- 개별 프롬프트의 `run_tag`를 무시

**해결법**:
```python
# 실제 run_tag는 prompts_metadata에서 가져오기
actual_run_tag = prompts_metadata_list[0].get("run_tag") if prompts_metadata_list else run_tag
images_dir = base_dir / "2_Data" / "metadata" / "generated" / actual_run_tag / "images"
```

**결과**: 각 프롬프트의 실제 `run_tag`에 맞는 디렉토리에 이미지 저장

---

### 문제 4: 빈 디렉토리에서도 이미지 존재로 오인

**문제 상황**:
- 이미지 디렉토리를 백업하고 비웠는데도 "이미 존재" 메시지 표시

**원인**:
- 디렉토리 존재 여부만 체크하고, 디렉토리가 비어있는지 확인하지 않음

**해결법**:
```python
# 디렉토리가 비어있는지 명시적으로 체크
try:
    if not any(images_dir.iterdir()):
        # 디렉토리가 비어있음
        return False, len(prompts_metadata), 0
except (OSError, PermissionError):
    # 디렉토리 접근 불가
    return False, len(prompts_metadata), 0
```

**결과**: 빈 디렉토리에서도 정확히 이미지 부재 인식

---

### 문제 5: 배치별 다운로드 vs 일괄 다운로드

**문제 상황**:
- 모든 배치 상태 확인 후 일괄 다운로드
- 다운로드 진행 상황을 파악하기 어려움

**해결법**:
- 각 배치 상태 확인 후 즉시 다운로드하도록 변경
- `download_and_save_batch_images` 함수로 배치별 독립 다운로드

**결과**: 배치별로 즉시 다운로드되어 진행 상황 파악 용이

---

## 중요 주의사항

### ⚠️ 비용 관련

1. **이미지 생성 비용이 매우 높음**
   - 2K 이미지: 약 2,500 tokens/이미지
   - 중복 제출 시 불필요한 비용 발생
   - **반드시 중복 체크 로직이 작동하는지 확인**

2. **배치 생성 전 필터링 필수**
   - 이미 제출된 배치와 로컬 이미지를 반드시 체크
   - 필터링 없이 배치 생성하면 중복 발생

3. **배치 다운로드는 무료**
   - 이미지 생성에만 비용 발생
   - 다운로드는 무료이므로 안전하게 재시도 가능

### 🔒 중복 방지 규칙

**절대 다시 배치 신청하면 안 되는 경우:**

1. ✅ **이미 로컬에 저장된 이미지**
   - `2_Data/metadata/generated/{run_tag}/images/` 디렉토리에 파일 존재
   - 파일명: `IMG__{run_tag}__grp_{group_id}__{entity_id}__{card_role}.jpg`

2. ✅ **이미 배치로 제출된 이미지**
   - `.batch_tracking.json`에 기록된 배치에 포함
   - 상태가 PENDING, RUNNING, SUCCEEDED인 배치

3. ✅ **같은 (run_tag, group_id, entity_id, card_role, spec_kind) 조합**
   - 이 조합이 고유 키로 사용됨
   - 동일한 조합은 한 번만 제출되어야 함

### 📊 API 키 관리

**API 키 번호 규칙:**
- `GOOGLE_API_KEY_X`에서 X가 뒷자리 숫자
- **뒷자리 숫자가 같으면 같은 계정**
- 예: `GOOGLE_API_KEY_24`, `GOOGLE_API_KEY_43` → 서로 다른 계정

**계정별 배치 신청량 균등 분배 (향후 개선 필요):**
- 현재는 순차적으로 키를 사용 (첫 번째 키부터)
- 향후 개선: 각 계정별로 비슷한 양의 배치를 분배하도록 개선 필요

---

## 배치 중복 방지 로직

### 현재 구현된 중복 방지

#### 1단계: 배치 생성 전 필터링 (가장 중요)

```python
# 위치: batch_image_generator.py, 라인 ~2136

# 1. 이미 제출된 배치 체크
for api_key_str, api_batches in tracking_data.get("batches", {}).items():
    for chunk in api_batches.get("chunks", []):
        if chunk_status in ("JOB_STATE_PENDING", "JOB_STATE_RUNNING", "JOB_STATE_SUCCEEDED"):
            # prompts_metadata와 비교하여 중복 체크
            ...

# 2. 로컬 이미지 존재 체크
if images_dir.exists():
    filename = make_image_filename(...)
    if (images_dir / filename).exists():
        # 이미 존재함
        ...

# 3. 필터링된 프롬프트만으로 배치 생성
batches = split_prompts_by_token_limit(filtered_prompts, ...)
```

#### 2단계: 배치 제출 시 안전장치

```python
# 위치: batch_image_generator.py, 라인 ~2299

# 각 배치 제출 전에 다시 한 번 체크 (안전장치)
for prompt in batch_prompts:
    # 이미 제출되었는지 체크
    is_submitted = check_if_submitted(prompt, tracking_data)
    # 로컬에 존재하는지 체크
    image_exists = check_local_image(prompt, images_dir)
    
    if is_submitted or image_exists:
        # 제외
        ...
```

#### 3단계: 다운로드 시 중복 방지

```python
# 위치: batch_image_generator.py, download_and_save_batch_images

# 이미지 저장 전에 파일 존재 여부 체크
if image_path.exists():
    print(f"⚠️  Skipping {filename} (file already exists)")
    continue
```

### 중복 체크 키

```python
entity_key = (
    prompt.get("run_tag", run_tag),
    prompt.get("group_id", ""),
    prompt.get("entity_id", ""),
    prompt.get("card_role", ""),
    prompt.get("spec_kind", ""),
)
```

이 5개 필드의 조합이 고유 키로 사용됩니다.

---

## API 키 관리

### API 키 로테이터 (`api_key_rotator.py`)

**주요 기능:**
1. `.env` 파일에서 자동으로 `GOOGLE_API_KEY_X` 감지
2. 429 에러 시 자동 키 회전
3. 키별 사용량 추적 (일일 요청 수, 실패 횟수)
4. 키 상태 저장 (`.api_key_status.json`)

**키 상태:**
- `active`: 사용 가능
- `inactive`: 일일 할당량 소진 또는 연속 실패

**키 회전 조건:**
- 429 RESOURCE_EXHAUSTED 에러 발생
- 연속 실패 (기본값: 3회)

### 현재 문제점: 계정별 균등 분배 미구현

**현재 동작:**
- 첫 번째 키부터 순차적으로 사용
- 키가 소진되면 다음 키로 회전

**개선 필요:**
- 각 계정(뒷자리 숫자)별로 비슷한 양의 배치 분배
- 예: 7개 키가 있으면 각 키에 약 1/7씩 분배

**개선 방안 (향후):**
```python
# 배치를 생성할 때 각 API 키에 균등하게 분배
def distribute_batches_by_account(batches, api_keys):
    """
    배치를 계정별로 균등하게 분배
    """
    # 계정별로 그룹화 (뒷자리 숫자 기준)
    accounts = group_keys_by_account(api_keys)
    
    # 배치를 계정별로 분배
    distributed = {}
    for i, batch in enumerate(batches):
        account = accounts[i % len(accounts)]
        if account not in distributed:
            distributed[account] = []
        distributed[account].append(batch)
    
    return distributed
```

---

## 배치 트래킹 파일 구조

### `.batch_tracking.json`

```json
{
  "batches": {
    "api_key_1": {
      "run_tag": "FINAL_DISTRIBUTION",
      "prompts_hash": "bbb413e9cc981175",
      "chunks": [
        {
          "batch_id": "batches/xxx",
          "status": "JOB_STATE_SUCCEEDED",
          "created_at": "2026-01-02T21:07:15",
          "num_requests": 228,
          "api_key_index": 1,
          "api_key_number": 5,
          "prompts_metadata": [...]
        }
      ]
    }
  }
}
```

**중요 필드:**
- `api_key_number`: 실제 `GOOGLE_API_KEY_X`의 X 값 (계정 식별용)
- `prompts_metadata`: 각 프롬프트의 메타데이터 (중복 체크용)
- `status`: 배치 상태 (PENDING, RUNNING, SUCCEEDED, FAILED)

---

## 향후 개선 사항

### 1. 계정별 균등 분배 (우선순위: 높음)

**현재 문제:**
- 첫 번째 키부터 순차 사용
- 일부 계정에만 집중될 수 있음

**개선 방안:**
- 배치 생성 시 각 계정(뒷자리 숫자)별로 균등 분배
- 각 계정의 일일 할당량을 고려한 분배

### 2. 중복 배치 자동 감지 및 정리

**현재 문제:**
- 이미 제출된 중복 배치가 트래킹 파일에 남아있음
- 수동으로 정리해야 함

**개선 방안:**
- 중복 배치 자동 감지 스크립트
- 중복 배치 중 하나를 자동으로 제거하는 옵션

### 3. 배치 상태 모니터링 개선

**현재:**
- `--check_status`로 수동 확인

**개선 방안:**
- 주기적으로 자동 체크
- 완료된 배치 자동 다운로드
- 알림 기능 (이메일, 슬랙 등)

### 4. 비용 추적

**개선 방안:**
- 배치별 예상 비용 계산
- 계정별 실제 비용 추적
- 일일/월별 비용 리포트

### 5. 배치 재시도 로직

**현재:**
- 실패한 배치는 수동으로 재시도

**개선 방안:**
- 일시적 오류(503, 500) 자동 재시도
- 실패한 배치 자동 재제출 옵션

---

## 체크리스트

### 배치 제출 전 확인사항

- [ ] 이미 제출된 배치와 중복되지 않는지 확인
- [ ] 로컬에 이미지가 존재하지 않는지 확인
- [ ] API 키가 충분한지 확인 (`check_api_key_status.py`)
- [ ] 토큰 사용량이 제한 내인지 확인
- [ ] `run_tag`가 올바른지 확인

### 배치 제출 후 확인사항

- [ ] 배치가 성공적으로 생성되었는지 확인
- [ ] `.batch_tracking.json`에 올바르게 기록되었는지 확인
- [ ] 배치 상태 모니터링 (`--check_status`)

### 배치 다운로드 후 확인사항

- [ ] 모든 이미지가 올바른 디렉토리에 저장되었는지 확인
- [ ] 중복 이미지가 없는지 확인
- [ ] 누락된 이미지가 없는지 확인

---

## 유용한 명령어

### API 키 상태 확인
```bash
python3 3_Code/Scripts/check_api_key_status.py
```

### 배치 중복 확인
```bash
python3 << 'EOF'
import json
from pathlib import Path
from collections import defaultdict

tracking_path = Path("2_Data/metadata/.batch_tracking.json")
with open(tracking_path, "r") as f:
    data = json.load(f)

all_entities = defaultdict(list)
for api_key_str, api_batches in data.get("batches", {}).items():
    for chunk in api_batches.get("chunks", []):
        if chunk.get("status") in ("JOB_STATE_PENDING", "JOB_STATE_RUNNING", "JOB_STATE_SUCCEEDED"):
            for meta in chunk.get("prompts_metadata", []):
                key = (meta.get("run_tag"), meta.get("group_id"), meta.get("entity_id"), 
                       meta.get("card_role"), meta.get("spec_kind"))
                all_entities[key].append(chunk.get("batch_id", "")[:20])

duplicates = {k: v for k, v in all_entities.items() if len(v) > 1}
print(f"중복: {len(duplicates)}개")
EOF
```

### 배치별 이미지 개수 확인
```bash
python3 << 'EOF'
import json
from pathlib import Path

tracking_path = Path("2_Data/metadata/.batch_tracking.json")
with open(tracking_path, "r") as f:
    data = json.load(f)

for api_key_str, api_batches in data.get("batches", {}).items():
    print(f"\n{api_key_str}:")
    for chunk in api_batches.get("chunks", []):
        batch_id = chunk.get("batch_id", "")[:20]
        num_requests = chunk.get("num_requests", 0)
        status = chunk.get("status", "")
        print(f"  {batch_id}: {num_requests}개 ({status})")
EOF
```

---

## 연락처 및 참고 자료

- **배치 API 문서**: [Google Gemini Batch API](https://ai.google.dev/gemini-api/docs/batch)
- **토큰 제한**: 2,000,000 tokens per batch (Tier 1)
- **배치 만료 시간**: 48시간 (PENDING/RUNNING 상태)

---

**⚠️ 마지막 경고: 이미지 생성은 비용이 매우 높습니다. 중복 체크를 반드시 확인하고 배치를 제출하세요!**

