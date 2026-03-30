# 배치 다운로드 문제 분석: 0g74p40fkur0au 배치

## 문제 현상
- 배치 `0g74p40fkur0au`가 여러 번 다운로드 실행됨
- 다운로드는 성공하지만 이미지 파일이 저장되지 않음
- 재실행할 때마다 계속 다운로드를 시도함

## 원인 분석

### 1. 키 매핑 불일치 문제 (의심)

`save_images_from_batch` 함수(2384-2388 라인)에서:
```python
key_to_metadata = {}
for idx, meta in enumerate(prompts_metadata):
    key = f"request_{idx:06d}"  # 항상 6자리 0 패딩 형식
    key_to_metadata[key] = meta
```

문제:
- `key_to_metadata`는 `prompts_metadata`의 순서를 기반으로 생성됨 (인덱스 0, 1, 2, ...)
- 하지만 배치 API가 반환하는 `result`의 `key`는 배치 생성 시의 인덱스일 수 있음
- 만약 배치가 여러 청크로 나뉘어져 있거나, 일부 요청이 실패했다면 인덱스가 맞지 않을 수 있음

### 2. 다운로드 전 체크 로직 문제

현재 코드 흐름:
1. `batches_to_check`에 배치 추가 (2821-2843 라인)
2. 다운로드 전 재확인 (2866-2884 라인) - 방금 추가한 수정
3. `download_result_files_parallel`로 결과 파일 다운로드
4. 다운로드 후 다시 확인 (2881-2891 라인)
5. `download_and_save_batch_images`에서 이미지 저장

문제:
- `download_and_save_batch_images` 함수(2194-2203 라인)에서도 다운로드 전 체크를 하지만, `batch_results`가 이미 있는 경우와 없는 경우가 다르게 동작
- `batch_results=None`일 때는 `prompts_metadata`의 모든 항목을 확인
- `batch_results`가 있을 때는 실제 생성된 이미지만 확인

### 3. 가능한 원인들

#### 원인 A: 키 매핑 실패
- `save_images_from_batch`에서 `key_to_metadata.get(key, {})`가 빈 딕셔너리를 반환
- 결과적으로 모든 이미지가 "No metadata found for key" 경고와 함께 스킵됨
- 이미지 저장은 실행되지 않음

#### 원인 B: 이미지 데이터 없음
- 배치 결과에 `image_data` 필드가 없거나 비어있음
- 모든 이미지가 "No image data for key" 경고와 함께 스킵됨

#### 원인 C: 파일명 생성 실패
- `make_image_filename` 함수가 예상과 다른 파일명을 생성
- 또는 파일명에 문제가 있어 저장 실패

## 해결 방안

### 즉시 확인 사항
1. 실행 로그에서 다음 경고 메시지 확인:
   - `⚠️  Warning: No metadata found for key {key}`
   - `⚠️  Warning: No image data for key {key}`
   - `❌ Error saving image for key {key}`

2. `save_images_from_batch` 함수의 출력 확인:
   - `📊 Image save summary:` 섹션
   - `Newly saved`, `Skipped`, `Errors` 개수

3. 배치 결과 파일의 키 형식 확인:
   - 배치 API가 반환하는 `key` 형식이 `request_000000`인지 `request_0`인지 확인

### 수정 제안

#### 수정 1: 키 매핑 로직 개선
`save_images_from_batch` 함수에서 `key_to_metadata` 생성 시, `results`의 실제 `key` 형식에 맞춰 매핑 생성:

```python
# 현재: prompts_metadata의 인덱스 기반
key_to_metadata = {}
for idx, meta in enumerate(prompts_metadata):
    key = f"request_{idx:06d}"
    key_to_metadata[key] = meta

# 제안: results의 실제 key 형식도 지원
key_to_metadata = {}
for idx, meta in enumerate(prompts_metadata):
    # 6자리 패딩 형식
    key_padded = f"request_{idx:06d}"
    key_to_metadata[key_padded] = meta
    # 패딩 없는 형식도 지원
    if idx < 10 or not any(r.get("key", "").startswith("request_0") for r in results):
        key_unpadded = f"request_{idx}"
        key_to_metadata[key_unpadded] = meta
```

#### 수정 2: 디버깅 로그 추가
`save_images_from_batch` 함수에 더 자세한 로그 추가:

```python
print(f"📊 Mapping stats: {len(key_to_metadata)} keys mapped from {len(prompts_metadata)} metadata entries")
print(f"📊 Results to process: {len(results)}")
for result in results[:5]:  # 처음 5개만
    key = result.get("key", "")
    print(f"   Sample key: {key}")
```

## 다음 단계

1. 실제 실행 로그 확인하여 정확한 원인 파악
2. 배치 결과 파일의 실제 키 형식 확인
3. 위의 수정 중 적절한 것을 적용

