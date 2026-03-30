# 배치 이미지 생성 시스템 - 문제점 및 해결 방안 인계서

**작성일**: 2026-01-15  
**작성자**: AI Assistant  
**목적**: 배치 이미지 생성 시스템에서 발생한 주요 문제점과 해결 방법, 향후 작업 방향 정리

---

## 📋 목차

1. [주요 문제점 및 해결 방법](#주요-문제점-및-해결-방법)
2. [현재 구현 상태](#현재-구현-상태)
3. [알려진 이슈](#알려진-이슈)
4. [향후 작업 방향](#향후-작업-방향)
5. [참고 자료](#참고-자료)

---

## 🔍 주요 문제점 및 해결 방법

### 1. 404 NOT_FOUND 에러 (파일 접근 불가)

**문제 상황**:
- API 키를 로테이션한 후 배치 작업을 생성하려고 할 때 `404 NOT_FOUND` 에러 발생
- 에러 메시지: `'Requested entity was not found.'`

**원인 분석**:
- 파일은 첫 번째 API 키(`GOOGLE_API_KEY_2`)로 업로드됨
- 429 에러 발생 후 API 키를 로테이션하여 두 번째 키(`GOOGLE_API_KEY_3`)로 변경
- 두 번째 키로 배치 작업을 생성하려고 시도하지만, 파일은 첫 번째 키로 업로드되어 두 번째 키로는 접근 불가
- Google Gemini API의 파일은 API 키별로 격리되어 있음

**해결 방법**:
- API 키를 로테이션할 때 파일도 새로운 API 키로 재업로드하도록 수정
- `batch_image_generator.py`의 배치 생성 루프에서 429 또는 404 에러 발생 시:
  1. API 키를 다음 키로 로테이션
  2. JSONL 파일을 새로운 API 키로 재업로드
  3. 재업로드된 파일 URI로 배치 작업 생성 재시도

**수정된 코드 위치**:
- `3_Code/src/tools/batch/batch_image_generator.py` (약 1522-1600번 줄)
- 429/404 에러 처리 로직에 파일 재업로드 추가

```python
# API 키 로테이션 후
print(f"📤 Re-uploading file with new API key...")
file_uri = upload_file(jsonl_path, api_key=current_api_key)
if not file_uri:
    print(f"❌ Failed to re-upload file with new key, skipping this batch")
    break
```

---

### 2. 429 RESOURCE_EXHAUSTED 에러 (할당량 소진)

**문제 상황**:
- 배치 작업 생성 시 `429 RESOURCE_EXHAUSTED` 에러 발생
- 에러 메시지: `'You exceeded your current quota, please check your plan and billing details.'`

**원인 분석**:
- 단일 API 키의 할당량(quota)이 소진됨
- 여러 배치를 연속으로 생성할 때 할당량 제한에 도달

**해결 방법**:
- `ApiKeyRotator`를 사용하여 자동으로 다음 API 키로 전환
- 모든 사용 가능한 API 키를 시도한 후에도 실패하면 해당 배치를 건너뛰고 다음 배치로 진행
- 실패한 배치는 `.batch_tracking.json`에 기록하지 않아 나중에 재시도 가능하도록 함

**현재 동작**:
1. 429 에러 발생 시 `ApiKeyRotator.rotate_on_quota_exhausted()` 호출
2. 다음 사용 가능한 API 키로 전환
3. 파일을 새 키로 재업로드
4. 배치 작업 생성 재시도
5. 모든 키를 시도한 후에도 실패하면 배치 건너뛰기

---

### 3. API 키 로테이션 시 파일 재업로드 누락

**문제 상황**:
- API 키를 로테이션했지만 파일은 이전 키로 업로드된 상태로 유지
- 새로운 키로 배치 작업 생성 시 404 에러 발생

**해결 방법**:
- API 키 로테이션 시 반드시 파일도 재업로드하도록 수정
- 404 에러도 429 에러와 동일하게 처리하여 자동 재시도

**수정 내용**:
```python
# 404 에러도 429와 동일하게 처리
is_429_error = "429_QUOTA_EXHAUSTED" in error_str
is_404_error = "404" in error_str or "NOT_FOUND" in error_str

if (is_429_error or is_404_error) and rotator is not None:
    # API 키 로테이션
    # 파일 재업로드 (중요!)
    file_uri = upload_file(jsonl_path, api_key=current_api_key)
```

---

### 4. 실패한 배치가 추적 파일에 기록되는 문제

**문제 상황**:
- 429 에러로 인해 배치 생성에 실패했는데도 `.batch_tracking.json`에 기록됨
- 이후 재시도 시 이미 제출된 것으로 간주되어 건너뛰어짐

**해결 방법**:
- 배치 작업이 성공적으로 생성된 경우에만 `.batch_tracking.json`에 기록
- `create_batch_job()`가 `None`을 반환하거나 예외가 발생하면 기록하지 않음

**현재 동작**:
```python
if batch_job:
    # 성공한 경우에만 기록
    # ... tracking_data에 추가 ...
else:
    # 실패한 경우 기록하지 않음
    print("⚠️  Note: This batch is NOT recorded in tracking file, so entities can be retried later")
```

---

## ✅ 현재 구현 상태

### 완료된 기능

1. **동적 배치 분할**
   - 토큰 제한에 따라 자동으로 배치 분할
   - 이미지 크기(2K/4K)에 따른 토큰 계산
   - `spec_kind`에 따른 해상도 자동 설정 (S1_TABLE_VISUAL → 4K)

2. **API 키 관리**
   - `ApiKeyRotator`를 통한 다중 API 키 관리
   - 429 에러 시 자동 키 로테이션
   - `.env` 파일에서 최신 키 로드 (매 실행마다)

3. **배치 추적 시스템**
   - `.batch_tracking.json`을 통한 배치 상태 추적
   - 중복 제출 방지
   - API 키 번호(절대값) 저장으로 정확한 키 식별

4. **에러 처리**
   - 429 에러: 자동 키 로테이션 + 파일 재업로드
   - 404 에러: 자동 키 로테이션 + 파일 재업로드
   - 실패한 배치는 추적 파일에 기록하지 않음

5. **이미지 저장**
   - 기존 파일 덮어쓰기 방지
   - `run_tag` 기반 디렉토리 구조
   - 파일명 유효성 검사 (특수문자 처리)

---

## ⚠️ 알려진 이슈

### 1. 들여쓰기 오류 (부분적으로 해결됨)

**상태**: 사용자가 수동으로 수정함

**발생 위치**:
- `3_Code/src/tools/batch/batch_image_generator.py` 471번 줄
- `3_Code/src/tools/batch/batch_image_generator.py` 552번 줄
- `3_Code/src/tools/batch/batch_image_generator.py` 1504, 1507, 1510번 줄 등

**해결 방법**:
- Python 들여쓰기 규칙 준수 (4칸 또는 일관된 들여쓰기)
- IDE의 자동 포맷팅 기능 활용

---

### 2. 모든 API 키 소진 시 처리

**현재 동작**:
- 모든 API 키가 429 에러를 반환하면 배치를 건너뛰고 다음 배치로 진행
- 실패한 배치는 추적 파일에 기록하지 않아 나중에 재시도 가능

**개선 가능 사항**:
- 재시도 간격 설정 (예: 1시간 후 자동 재시도)
- API 키별 할당량 모니터링 및 예측

---

### 3. 파일 업로드 실패 시 처리

**현재 동작**:
- 파일 업로드 실패 시 해당 배치를 건너뛰고 다음 배치로 진행

**개선 가능 사항**:
- 파일 업로드 재시도 로직 추가
- 업로드 실패 원인 로깅

---

## 🚀 향후 작업 방향

### 1. 에러 처리 강화

- **목표**: 더 세밀한 에러 분류 및 처리
- **작업 내용**:
  - 네트워크 에러 vs API 에러 구분
  - 일시적 에러(429, 503)와 영구적 에러(404, 401) 구분
  - 재시도 전략 개선 (exponential backoff)

### 2. 모니터링 및 로깅

- **목표**: 배치 작업 상태를 실시간으로 모니터링
- **작업 내용**:
  - 배치 작업 진행률 대시보드
  - API 키별 사용량 추적
  - 실패한 배치 자동 재시도 스케줄러

### 3. 성능 최적화

- **목표**: 배치 처리 속도 향상
- **작업 내용**:
  - 병렬 배치 제출 (API 제한 내에서)
  - 파일 업로드 최적화
  - 배치 크기 동적 조정

### 4. 사용자 경험 개선

- **목표**: 더 명확한 피드백 및 제어
- **작업 내용**:
  - 진행률 표시 개선
  - 상세한 에러 메시지
  - 배치 취소 기능

---

## 📚 참고 자료

### 관련 파일

1. **메인 스크립트**:
   - `3_Code/src/tools/batch/batch_image_generator.py` - 배치 이미지 생성 메인 로직

2. **유틸리티**:
   - `3_Code/src/tools/api_key_rotator.py` - API 키 로테이션 관리

3. **설정 파일**:
   - `.env` - API 키 설정
   - `.batch_tracking.json` - 배치 추적 데이터

4. **문서**:
   - `5_Meeting/HANDOFF_2026-01-15_Batch_API_Image_Generation_Plan.md` - 초기 계획서
   - `0_Protocol/00_Governance/supporting/LLM-operation/Batch.md` - Gemini Batch API 공식 문서

### 주요 함수

1. **`upload_file()`** (433-479번 줄)
   - JSONL 파일을 Google 서버에 업로드
   - API 키별로 파일이 격리됨

2. **`create_batch_job()`** (482-555번 줄)
   - 배치 작업 생성
   - 429 에러 시 `ValueError("429_QUOTA_EXHAUSTED")` 발생

3. **`main()`** (약 1400-1650번 줄)
   - 배치 생성 메인 루프
   - API 키 로테이션 및 파일 재업로드 로직 포함

### API 키 관리

- **로드**: `.env` 파일에서 `GOOGLE_API_KEY_N` 형식으로 로드
- **로테이션**: `ApiKeyRotator.rotate_on_quota_exhausted()` 또는 수동 인덱스 증가
- **추적**: `.batch_tracking.json`에 `api_key_number` (절대값) 저장

---

## 🔧 문제 해결 체크리스트

배치 생성 중 문제가 발생하면 다음을 확인:

1. **404 에러 발생 시**:
   - [ ] API 키가 로테이션되었는지 확인
   - [ ] 파일이 새 키로 재업로드되었는지 확인
   - [ ] `.batch_tracking.json`의 `api_key_number`가 올바른지 확인

2. **429 에러 발생 시**:
   - [ ] 사용 가능한 다른 API 키가 있는지 확인
   - [ ] `.env` 파일에 활성화된 키가 있는지 확인
   - [ ] API 키 할당량이 소진되었는지 확인

3. **배치가 건너뛰어지는 경우**:
   - [ ] `.batch_tracking.json`에서 이미 제출된 배치인지 확인
   - [ ] 배치 상태가 `JOB_STATE_PENDING`, `JOB_STATE_RUNNING`, `JOB_STATE_SUCCEEDED` 중 하나인지 확인

4. **파일 재업로드 실패 시**:
   - [ ] JSONL 파일이 존재하는지 확인
   - [ ] 파일 크기가 제한을 초과하지 않는지 확인
   - [ ] 네트워크 연결 상태 확인

---

## 📝 추가 참고 사항

### 배치 상태 확인

```bash
python3 3_Code/src/tools/batch/batch_image_generator.py --check_status --base_dir .
```

이 명령어는:
- `.batch_tracking.json`의 모든 배치 상태를 확인
- 완료된 배치(`JOB_STATE_SUCCEEDED`)의 결과를 자동 다운로드
- 올바른 API 키를 사용하여 상태 확인 (404 에러 방지)

### 배치 생성 명령어 예시

```bash
python3 3_Code/src/tools/batch/batch_image_generator.py \
  --input 2_Data/metadata/generated/FINAL_DISTRIBUTION/s3_image_spec__armG.jsonl \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --image_size 2K \
  --resume
```

### 주의사항

1. **API 키 격리**: 각 API 키로 업로드된 파일은 해당 키로만 접근 가능
2. **파일 재업로드**: API 키를 변경할 때는 반드시 파일도 재업로드해야 함
3. **배치 추적**: 실패한 배치는 추적 파일에 기록하지 않아 재시도 가능
4. **할당량 관리**: API 키 할당량이 소진되면 24시간 후 재설정 (일반적으로)

---

---

## ✅ 최근 완료된 작업 (2026-01-15)

### `--check_status` 모드의 404 에러 처리 개선

**문제**:
- `--check_status` 실행 시 일부 배치에서 404 에러 발생
- 모든 API 키를 시도해도 찾을 수 없는 배치가 있음
- 현재 traceback이 출력되어 사용자 경험이 좋지 않음

**완료된 수정 사항**:
1. ✅ `check_batch_status()` 함수 (약 1103-1107번 줄):
   - 404 에러는 조용히 처리 (traceback 출력하지 않음)
   - `None` 반환만 하도록 수정
   - 다른 에러는 여전히 출력 및 traceback 표시

2. ✅ `--check_status` 모드의 배치 확인 루프 (약 1563-1609번 줄):
   - 404 에러 발생 시 조용히 다음 키 시도
   - 모든 키를 시도한 후에도 찾을 수 없으면 간단한 메시지만 출력
   - 다른 에러는 경고 메시지로 출력

**수정 결과**:
- ✅ 404 에러 발생 시 traceback 없이 조용히 처리
- ✅ 모든 키를 시도한 후에도 찾을 수 없으면 간단한 경고 메시지만 출력
- ✅ 사용자 경험 개선 (깔끔한 출력)

**수정된 코드**:
```python
# check_batch_status() 함수
except Exception as e:
    error_str = str(e)
    if "404" in error_str or "NOT_FOUND" in error_str:
        # 404 에러는 조용히 처리 (traceback 없이)
        return None
    else:
        # 다른 에러는 출력
        print(f"❌ Error checking batch status: {e}")
        import traceback
        traceback.print_exc()
        return None
```

---

## 📌 향후 개선 가능 사항

1. **중간**: 배치 상태 확인 시 불필요한 출력 최소화
2. **낮음**: 배치가 삭제되었거나 다른 계정으로 이동한 경우 처리 로직 개선

---

**마지막 업데이트**: 2026-01-15 (완료)  
**문서 버전**: 1.2

