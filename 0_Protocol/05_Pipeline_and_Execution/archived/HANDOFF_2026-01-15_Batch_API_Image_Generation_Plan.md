# HANDOFF: Gemini Batch API를 활용한 이미지 생성 계획

**작성일:** 2026-01-15  
**작성자:** AI Assistant  
**목적:** Tier 1 사용자로서 비용 절감(50%)을 위해 Batch API를 사용한 대량 이미지 생성 계획 수립  
**관련 문서:**
- `0_Protocol/00_Governance/supporting/LLM-operation/Batch.md` - Batch API 공식 가이드라인
- `3_Code/src/tools/batch/batch_image_generator.py` - 배치 처리 전용 코드 (작성 완료)

---

## 1. 배경 및 목적

### 1.1 현재 상황
- **API Tier:** Tier 1 (Batch enqueued tokens 한도: 2,000,000 토큰)
- **목표:** 약 500장의 2K 해상도 이미지 생성
- **모델:** `gemini-3-pro-image-preview` (models/nano-banana-pro-preview)
- **비용 절감:** Batch API 사용 시 **50% 할인** (표준 비용의 절반)

### 1.2 요구사항
- 기존 동기식 코드 (`04_s4_image_generator.py`)는 수정하지 않음
- 배치 처리 로직은 새로운 파일 (`batch_image_generator.py`)에 독립적으로 구현
- 토큰 한도 내에서 안전하게 처리 가능한 배치 크기 결정

---

## 2. 토큰 계산 결과 (Feasibility Analysis)

### 2.1 실제 프롬프트 길이 분석

**프롬프트 템플릿 분석:**
- System 프롬프트: **10,003자** (`S4_EXAM_SYSTEM__S5R3__v11_DIAGRAM_4x5_2K.md`)
- User 프롬프트: **6,246자** (`S4_EXAM_USER__S5R3__v11_DIAGRAM_4x5_2K.md`)
- 템플릿 합계: **16,249자**
- Placeholder 치환 값 추가: 약 **400자**
- Constraint block 추가: 약 **1,000자**
- **최종 예상 프롬프트 길이: 약 17,649자**

### 2.2 토큰 소모량 계산

| 항목 | 값 |
|------|-----|
| 입력 토큰 (프롬프트) | 약 **5,294 토큰** (17,649자 × 0.3) |
| 출력 토큰 (2K 이미지) | **2,500 토큰** (고정) |
| **요청당 총 토큰** | 약 **7,794 토큰** |

### 2.3 배치 최대 요청 가능 장수

**Tier 1 한도: 2,000,000 토큰**

| 기준 | 최대 요청 수 | 비고 |
|------|------------|------|
| **90% 안전 마진** | **약 230장** | ✅ 권장 |
| **100% 사용** | **약 256장** | ⚠️ 위험 부담 있음 |

### 2.4 프롬프트 길이 변동에 따른 범위

프롬프트 길이가 변동할 경우:

| 프롬프트 길이 | 안전 범위 (90%) | 최대 한도 (100%) |
|-------------|--------------|----------------|
| 80% (14,119자) | 267장 | 296장 |
| 90% (15,884자) | 247장 | 275장 |
| **100% (17,649자)** | **230장** | **256장** |
| 110% (19,413자) | 216장 | 240장 |
| 120% (21,178자) | 203장 | 225장 |

### 2.5 결론: 500장 처리 전략

**500장을 요청하려면:**
- **2-3개의 배치로 분할 필요**
- 각 배치당 **200-230장**으로 구성 권장
- 예시:
  - 배치 1: 200장
  - 배치 2: 200장
  - 배치 3: 100장
  - 총 500장

---

## 3. Batch API 가이드라인 (핵심 내용)

### 3.1 Batch API 개요

- **비용:** 표준 API 대비 **50% 할인**
- **처리 시간:** 목표 24시간 이내 (대부분 더 빠름)
- **용도:** 대규모 비급속 작업 (데이터 전처리, 평가 등)
- **비동기 처리:** 즉시 응답 불필요한 작업에 적합

### 3.2 요청 방법

#### 방법 1: Inline Requests (소규모)
- 20MB 미만의 작은 배치에 적합
- `GenerateContentRequest` 객체를 직접 배치 생성 요청에 포함

#### 방법 2: Input File (대규모, **권장**)
- JSONL 파일 사용
- 최대 파일 크기: **2GB**
- 이미지 생성 등 대규모 작업에 적합

### 3.3 JSONL 파일 포맷

각 라인은 다음과 같은 형식:

```json
{"key": "request-1", "request": {"contents": [{"parts": [{"text": "prompt"}]}], "generation_config": {...}}}
```

**이미지 생성 예시:**
```json
{
  "key": "request-1",
  "request": {
    "contents": [{"parts": [{"text": "Generate a 2K medical diagram..."}]}],
    "generation_config": {
      "responseModalities": ["TEXT", "IMAGE"],
      "imageConfig": {
        "aspectRatio": "4:5",
        "imageSize": "2K"
      }
    }
  }
}
```

### 3.4 작업 흐름

1. **JSONL 파일 생성** → 로컬에 저장
2. **파일 업로드** → File API를 사용하여 Google 서버에 업로드
3. **배치 작업 생성** → `batches.create()` API 호출
4. **상태 모니터링** → 주기적으로 상태 확인 (Polling)
5. **결과 다운로드** → 완료 후 결과 파일 다운로드

### 3.5 작업 상태 (Job States)

- `JOB_STATE_PENDING`: 대기 중
- `JOB_STATE_RUNNING`: 처리 중
- `JOB_STATE_SUCCEEDED`: 성공 (결과 다운로드 가능)
- `JOB_STATE_FAILED`: 실패 (에러 확인 필요)
- `JOB_STATE_CANCELLED`: 취소됨
- `JOB_STATE_EXPIRED`: 48시간 초과로 만료

### 3.6 Python SDK 사용법 (요약)

```python
from google import genai
from google.genai import types

client = genai.Client()

# 1. 파일 업로드
uploaded_file = client.files.upload(
    file='my-batch-requests.jsonl',
    config=types.UploadFileConfig(display_name='my-batch-requests', mime_type='jsonl')
)

# 2. 배치 작업 생성
batch_job = client.batches.create(
    model="gemini-3-pro-image-preview",  # 또는 "models/nano-banana-pro-preview"
    src=uploaded_file.name,
    config={'display_name': "batch-image-generation"}
)

# 3. 상태 모니터링
job_name = batch_job.name
while True:
    batch_job = client.batches.get(name=job_name)
    if batch_job.state.name in ('JOB_STATE_SUCCEEDED', 'JOB_STATE_FAILED', ...):
        break
    time.sleep(30)  # 30초 대기

# 4. 결과 다운로드
if batch_job.state.name == 'JOB_STATE_SUCCEEDED':
    result_file_name = batch_job.dest.file_name
    file_content = client.files.download(file=result_file_name)
    # JSONL 결과 파일 파싱 및 처리
```

### 3.7 Best Practices

- **대규모 요청에는 파일 입력 방식 사용** (20MB 이상)
- **에러 처리:** `batchStats.failedRequestCount` 확인
- **작업 중복 제출 방지:** 배치 작업 생성은 idempotent하지 않음
- **매우 큰 배치는 분할:** 필요시 중간 결과를 위해 작은 배치로 분할

---

## 4. 구현 현황

### 4.1 작성 완료: `batch_image_generator.py`

**위치:** `3_Code/src/tools/batch/batch_image_generator.py`

**주요 기능:**
1. ✅ 토큰 한도 계산 (Feasibility Check)
   - `estimate_tokens_per_request()`: 요청당 토큰 추정
   - `calculate_batch_feasibility()`: 배치 가능성 계산
   - `print_feasibility_report()`: 결과 출력

2. ✅ JSONL 파일 생성
   - `create_jsonl_file()`: Gemini Batch API 포맷 JSONL 생성
   - 이미지 생성 설정 포함 (aspect_ratio, image_size, temperature)

3. ✅ 파일 업로드
   - `upload_file()`: Google 서버에 JSONL 파일 업로드

4. ✅ 배치 작업 생성
   - `create_batch_job()`: 업로드된 파일로 배치 작업 생성
   - 모델: `gemini-3-pro-image-preview` 명시

5. ✅ 상태 확인 및 모니터링
   - `check_batch_status()`: 배치 작업 상태 조회
   - `monitor_batch_job()`: 주기적 모니터링

### 4.2 주의사항

⚠️ **실제 API 구조 확인 필요:**
- 코드에 여러 API 패턴을 시도하도록 작성됨
- Google Gemini Batch API 공식 문서를 참고하여 정확한 API 구조 확인 필요
- 특히 `client.files.upload()` 및 `client.batches.create()`의 정확한 파라미터 구조

---

## 5. 실행 계획 (Implementation Plan)

### Phase 1: 준비 단계

**5.1 API 구조 확인 및 코드 수정**
- [ ] Google Gemini Batch API 공식 문서 확인
- [ ] `batch_image_generator.py`의 API 호출 부분 검증
- [ ] 필요시 API 패턴 수정

**5.2 테스트 환경 준비**
- [ ] 소규모 테스트 배치 (10-20장) 준비
- [ ] 테스트용 프롬프트 리스트 생성
- [ ] API 키 확인 및 권한 확인

### Phase 2: 소규모 테스트

**5.3 첫 번째 배치 테스트**
- [ ] 10-20장 규모의 JSONL 파일 생성
- [ ] 파일 업로드 테스트
- [ ] 배치 작업 생성 테스트
- [ ] 상태 모니터링 테스트
- [ ] 결과 다운로드 및 파싱 테스트

**5.4 검증 항목**
- [ ] JSONL 파일 포맷 정확성
- [ ] 업로드 성공 여부
- [ ] 배치 작업 생성 성공 여부
- [ ] 결과 파일 다운로드 및 파싱 성공
- [ ] 생성된 이미지 품질 확인

### Phase 3: 실제 배치 실행

**5.5 500장 처리 전략**

**옵션 A: 3개 배치로 분할 (권장)**
- 배치 1: 200장 (안전)
- 배치 2: 200장 (안전)
- 배치 3: 100장 (안전)
- 각 배치 간 1-2시간 간격 권장 (서버 부하 분산)

**옵션 B: 2개 배치로 분할**
- 배치 1: 230장 (90% 마진)
- 배치 2: 270장 (약간 위험, 105% 사용)
  - ⚠️ 두 번째 배치는 토큰 한도 초과 위험 있음
  - 250장으로 제한하는 것을 권장

**5.6 실행 순서**

1. **프롬프트 준비**
   ```bash
   # s3_image_spec.jsonl에서 prompt_en 추출
   python3 extract_prompts_from_spec.py \
     --input 2_Data/metadata/generated/<run_tag>/s3_image_spec__armA.jsonl \
     --output batch_prompts.jsonl
   ```

2. **토큰 계산 및 검증**
   ```bash
   python3 3_Code/src/tools/batch/batch_image_generator.py
   # 프롬프트 리스트를 입력하면 feasibility check 자동 수행
   ```

3. **배치 크기 결정 및 분할**
   - 500장 → 200장, 200장, 100장으로 분할
   - 각 배치별 JSONL 파일 생성

4. **배치 1 실행**
   ```python
   # batch_image_generator.py 수정 후 실행
   python3 3_Code/src/tools/batch/batch_image_generator.py
   ```

5. **상태 모니터링**
   - 30분-1시간 간격으로 상태 확인
   - 완료 대기 (최대 24시간)

6. **결과 확인 및 검증**
   - 결과 파일 다운로드
   - 이미지 품질 확인
   - 실패한 요청 확인 및 재처리 계획

7. **배치 2, 3 반복**

### Phase 4: 결과 처리 및 통합

**5.7 결과 파일 처리**
- [ ] JSONL 결과 파일 파싱
- [ ] 이미지 데이터 추출 (base64 디코딩)
- [ ] 기존 S4 이미지 생성 로직과의 호환성 확인
- [ ] 이미지 파일 저장 (기존 경로 구조 유지)

**5.8 실패 처리**
- [ ] 실패한 요청 식별
- [ ] 재시도 전략 수립
- [ ] 필요시 동기식 API로 재생성

---

## 6. 예상 일정 및 리소스

### 6.1 예상 시간

| 단계 | 예상 시간 | 비고 |
|------|----------|------|
| Phase 1: 준비 | 2-4시간 | API 구조 확인 및 코드 수정 |
| Phase 2: 소규모 테스트 | 2-3시간 | 테스트 및 검증 |
| Phase 3: 실제 배치 실행 | 24-48시간 | 배치 처리 시간 (비동기) |
| Phase 4: 결과 처리 | 2-4시간 | 결과 다운로드 및 통합 |
| **총 예상 시간** | **30-60시간** | 대부분 배치 처리 대기 시간 |

### 6.2 비용 비교

**동기식 API (기존 방식):**
- 요청당: 7,794 토큰 × $X = $Y
- 500장: 500 × $Y = $500Y

**Batch API (50% 할인):**
- 요청당: 7,794 토큰 × $X × 0.5 = $0.5Y
- 500장: 500 × $0.5Y = $250Y
- **절감액: $250Y (50% 절감)**

---

## 7. 리스크 및 대응 방안

### 7.1 주요 리스크

| 리스크 | 가능성 | 영향 | 대응 방안 |
|--------|--------|------|----------|
| API 구조 불일치 | 중간 | 높음 | 공식 문서 확인 후 코드 수정 |
| 토큰 한도 초과 | 낮음 | 높음 | 90% 마진 사용, 배치 분할 |
| 배치 작업 실패 | 낮음 | 중간 | 소규모 테스트 먼저, 실패 시 재시도 |
| 처리 시간 초과 (48시간) | 매우 낮음 | 낮음 | 배치 크기 조정, 작은 배치로 분할 |
| 이미지 품질 이슈 | 낮음 | 중간 | 샘플 검증, 필요시 재생성 |

### 7.2 롤백 계획

- Batch API 실패 시 기존 동기식 코드 (`04_s4_image_generator.py`)로 즉시 전환 가능
- 배치 작업 취소: `client.batches.cancel(name=batch_job.name)`

---

## 8. 체크리스트

### 실행 전 체크리스트
- [ ] API 키 확인 및 권한 확인
- [ ] Tier 1 한도 확인 (2,000,000 토큰)
- [ ] 프롬프트 리스트 준비 완료
- [ ] `batch_image_generator.py` 코드 검토 완료
- [ ] 소규모 테스트 계획 수립

### 실행 중 체크리스트
- [ ] JSONL 파일 생성 성공
- [ ] 파일 업로드 성공
- [ ] 배치 작업 생성 성공
- [ ] 배치 ID 기록
- [ ] 상태 모니터링 시작

### 실행 후 체크리스트
- [ ] 모든 배치 작업 완료 확인
- [ ] 결과 파일 다운로드 완료
- [ ] 이미지 품질 검증
- [ ] 실패한 요청 목록 작성
- [ ] 비용 확인 (50% 절감 확인)

---

## 9. 참고 자료

### 9.1 관련 문서
- `0_Protocol/00_Governance/supporting/LLM-operation/Batch.md` - Batch API 공식 가이드라인
- `3_Code/src/tools/batch/batch_image_generator.py` - 배치 처리 코드
- `3_Code/src/04_s4_image_generator.py` - 기존 동기식 이미지 생성 코드
- `3_Code/prompt/S4_EXAM_*.md` - 실제 사용 중인 프롬프트 템플릿

### 9.2 외부 링크
- [Gemini Batch API 문서](https://ai.google.dev/gemini-api/docs/batch-api)
- [Batch API Cookbook](https://github.com/google-gemini/cookbook/blob/main/quickstarts/Batch_mode.ipynb)
- [Gemini Pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [Rate Limits](https://ai.google.dev/gemini-api/docs/rate-limits#batch-mode)

---

## 10. 다음 단계 (Next Steps)

1. **즉시 실행 가능한 작업:**
   - [ ] Google Gemini Batch API 공식 문서 확인
   - [ ] `batch_image_generator.py`의 API 호출 부분 검증 및 수정
   - [ ] 소규모 테스트 (10-20장) 준비

2. **단기 작업 (1-2일 내):**
   - [ ] 소규모 테스트 실행 및 검증
   - [ ] 실제 프롬프트 리스트 준비 (500장)
   - [ ] 배치 분할 전략 최종 결정

3. **중기 작업 (1주일 내):**
   - [ ] 실제 배치 실행 (500장, 2-3개 배치로 분할)
   - [ ] 결과 검증 및 통합
   - [ ] 문서화 및 경험 공유

---

**문서 버전:** 1.0  
**최종 업데이트:** 2026-01-15

