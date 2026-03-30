# Batch Processing History

**Last Updated**: 2026-01-15  
**Purpose**: MeducAI 프로젝트의 Batch API 사용 기록 및 텍스트 수정 작업 이력  
**Scope**: FINAL_DISTRIBUTION Arm G의 배치 처리 작업 전체 타임라인

---

## 개요

본 문서는 MeducAI FINAL_DISTRIBUTION armG 파이프라인에서 수행된 모든 배치 처리 작업을 시간순으로 정리합니다. 주요 내용:

- Gemini Batch API를 이용한 대규모 텍스트 repair
- S5 feedback 기반 S1/S2 재생성
- Positive regeneration 파이프라인 테스트
- 중복 제거 및 데이터 정제 작업

---

## Timeline

### 2026-01-15: Positive Regen Phase 3 실제 테스트

**문서**: `HANDOFF_2026-01-15_Positive_Regen_Phase3_Real_Test.md`

#### 작업 목표
Positive regeneration pipeline의 실제 이미지 생성 테스트 (2-3개 카드)를 수행하여 전체 파이프라인이 작동하는지 확인하고 생성된 이미지의 품질을 검증.

#### 완료된 Phase
- ✅ **Phase 1**: Protocol 문서 업데이트 완료
- ✅ **Phase 2**: 스크립트 구현 완료
  - S6 agent (`06_s6_positive_instruction_agent.py`)
  - Positive regen orchestrator (`positive_regen_runner.py`)
  - S4 수정 (manifest 분리, `--image_type regen`)
- ✅ **Phase 3-1**: Dry-run 테스트 완료 (논리 검증)
- 🟡 **Phase 3-2**: 실제 이미지 생성 테스트 (API 키 설정 필요)

#### 해결된 기술 문제

**1. S6 Agent Import 문제** ✅
- **문제**: `positive_regen_runner.py`에서 S6 agent를 import할 수 없었음
- **해결**: `importlib.util`을 사용하여 파일명 `06_s6_positive_instruction_agent.py`를 직접 로드

**2. Prompt Template Formatting 문제** ✅
- **문제**: 프롬프트 템플릿의 JSON 예제에 있는 중괄호 `{}`가 Python의 `.format()` 메서드와 충돌
- **해결**: 프롬프트 템플릿의 JSON 예제에서 중괄호를 `{{`와 `}}`로 이스케이프

**3. API Key 미설정** ✅
- **문제**: S6 agent가 LLM 호출 시 `GOOGLE_API_KEY` 환경 변수가 설정되지 않음
- **해결**: `06_s6_positive_instruction_agent.py`와 `positive_regen_runner.py`에서 `base_dir` 기반 `.env` 파일 로딩 추가

#### S3 Spec 선택 로직 (중요)

이미지 재생성 시 카드 텍스트 재생성 여부에 따라 적절한 S3 spec을 선택:

**Case 1: 카드 리젠이 뜬 경우**
- 조건: `card_regeneration_trigger_score < 90.0`
- S3 spec 선택: **Repaired 우선** (카드 텍스트와 이미지가 일치해야 함)

**Case 2: 이미지 리젠만 뜬 경우**
- 조건: `image_regeneration_trigger_score < 90.0` AND `card_regeneration_trigger_score >= 90.0`
- S3 spec 선택: **Baseline 사용** (원본 카드 텍스트와 일치해야 함)

#### 대상 카드 선정
| # | Group ID | Entity ID | Card Role | Score | Issue Summary |
|---|----------|-----------|-----------|-------|---------------|
| 1 | `grp_023d60ba08` | `DERIVED:9bdeff847613` | Q1 | 30.0 | Laterality error (bowel loops on wrong side) |
| 2 | `grp_0bddd64828` | `DERIVED:9a97a6c86834` | Q1 | 30.0 | Content mismatch (chest wall anatomy missing) |
| 3 | `grp_043427ea12` | `DERIVED:ffad4d7519c4` | Q2 | 30.0 | Laterality error (fistula to wrong pyriform sinus) |

#### 관련 파일
- `3_Code/src/06_s6_positive_instruction_agent.py` - S6 agent 핵심 로직
- `3_Code/src/tools/regen/positive_regen_runner.py` - Orchestrator
- `3_Code/prompt/S6_POSITIVE_INSTRUCTION__v1.md` - S6 프롬프트 템플릿

---

### 2026-01-06: 배치 다운로드 및 중복 제거

**문서**: `HANDOFF_2026-01-06_Batch_Recovery_and_Deduplication.md`

#### 작업 요약

1. ✅ 배치 텍스트 repair 결과 다운로드 및 적용
2. ✅ 6개 파싱 에러 수동 복구
3. ✅ S2 entity 중복 제거 (29개)
4. ✅ S3 image spec 재생성
5. ✅ 이미지 검증 (누락 없음 확인)

#### 핵심 결과
- **S1 테이블**: 321개 (변동 없음)
- **S2 카드**: 7,018개 → 3,509 entities (dedup 전: 3,538)
- **S3 spec**: 7,752개 (재생성 완료)
- **기존 이미지**: 7,811개 (모두 정상)

#### Phase 1: 배치 다운로드 및 파싱 에러 복구

**초기 다운로드 결과**:
```
성공: 22 S1 + 328 S2 = 350개
실패: 6 S2 카드 (JSON 파싱 에러)
```

**실패 원인**:
- LLM 출력이 토큰 제한에 도달하여 JSON이 잘리고 대부분 공백으로 채워짐
- 일부는 같은 내용을 무한 반복하는 패턴 포함

**개선된 파싱 로직** (`batch_text_repair.py` 수정):
1. JSON 파싱 에러 시 마크다운 코드 블록 추출 시도
2. 원본 배치 결과 자동 저장
3. 실패한 라인 상세 로깅 (line number, key, error)
4. S1/S2 분류별 실패 통계

**수동 복구 작업**:
- 스크립트: `3_Code/src/tools/batch/fix_truncated_json.py`
- 방법: 원본 텍스트에서 trailing whitespace 제거, 누락된 닫는 중괄호/대괄호 추가
- 결과: 실패한 6개 카드 모두 성공적으로 복구됨

#### Phase 2: 중복 제거 (Deduplication)

**중복 발견**:
```
총 레코드:        3,538개
고유 entities:    3,509개
중복 entities:    27개 (29개 레코드 중복)
```

**중복 entity 예시**:
- `grp_5b7e2986f4/DERIVED:8ff677ad2f1b`: **4회 출현** (가장 많음)
- 나머지 26개 entities: 각 2회 출현

**Deduplication 전략** (`deduplicate_s2_entities.py`):
1. (group_id, entity_id)를 기준으로 그룹화
2. 중복 발견 시:
   - Repair metadata가 있는 레코드 우선 선택
   - 둘 다 있거나 없으면 첫 번째 레코드 유지
3. 나머지 중복 레코드 제거

**결과**:
```
Before:  3,538 records
After:   3,509 records
Removed: 29 duplicates
```

#### Phase 3: S3 Image Spec 재생성

**실행 명령**:
```bash
python3 3_Code/src/03_s3_policy_resolver.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G \
  --s1_path 2_Data/metadata/generated/FINAL_DISTRIBUTION/stage1_struct__armG__regen.jsonl \
  --s2_path 2_Data/metadata/generated/FINAL_DISTRIBUTION/s2_results__s1armG__s2armG__regen.jsonl
```

**통계**:
```
총 spec:          7,752개 (이전: 7,810개)
  - S2_CARD_IMAGE:   6,175개
  - S2_CARD_CONCEPT: 900개
  - S1_TABLE_VISUAL: 735개 (321개 그룹)
```

**변화**:
- Deduplication으로 58개 감소 (7,810 → 7,752)
- 29개 중복 entities × 2 (Q1+Q2) = 58개 감소와 정확히 일치

#### 생성된 유틸리티 스크립트
```
3_Code/src/tools/batch/
  - manual_batch_recovery.py
  - fix_truncated_json.py
  - apply_recovered_cards.py
  - deduplicate_s2_entities.py
```

---

### 2026-01-06: Batch API 구현 수정

**문서**: `HANDOFF_2026-01-06_Batch_API_Corrections.md`

#### 작업 요약

공식 Gemini Batch API 문서를 참고하여 **3가지 중요한 수정**을 완료:

1. ✅ MIME type: `"application/jsonl"` → `"jsonl"`
2. ✅ Batch src: `file_uri` → `uploaded_file.name`
3. ✅ Result download: 추측 기반 → 공식 `client.files.download()` 메서드

#### 수정 사항 상세

**1. File Upload - MIME Type 수정** ✅

**Before (잘못됨)**:
```python
uploaded_file = client.files.upload(
    file=jsonl_content.encode("utf-8"),
    config={
        "display_name": "...",
        "mime_type": "application/jsonl",  # ❌ 잘못된 MIME type
    }
)
```

**After (올바름)**:
```python
uploaded_file = client.files.upload(
    file=jsonl_content.encode("utf-8"),
    config={
        "display_name": "...",
        "mime_type": "jsonl",  # ✅ 공식 API 스펙
    }
)
```

**2. Batch Creation - src 파라미터 수정** ✅

**Before (잘못됨)**:
```python
batch = client.batches.create(
    model=S1R_MODEL,
    src=file_uri,  # ❌ URI 대신 file name 사용해야 함
)
```

**After (올바름)**:
```python
batch = client.batches.create(
    model=S1R_MODEL,
    src=uploaded_file.name,  # ✅ file name (e.g., "files/abc123")
    config={
        "display_name": "text_repair_batch_...",
    }
)
```

**3. Result Download - 공식 API 메서드 사용** ✅

**Before (잘못됨)**:
```python
# 추측 기반 구현 - output_uri 사용
output_uri = getattr(batch, "output_uri", None)
file_name = str(output_uri).split("/")[-1]
result_file = client.files.get(name=file_name)
content_bytes = result_file.read()  # ❌ 존재하지 않는 메서드
```

**After (올바름)**:
```python
# 공식 API 스펙 준수
if batch.dest and batch.dest.file_name:
    result_file_name = batch.dest.file_name
    file_content_bytes = client.files.download(file=result_file_name)  # ✅ 공식 메서드
    result_content = file_content_bytes.decode("utf-8")
```

#### 변경된 파일
- `3_Code/src/tools/batch/batch_text_repair.py`
- `3_Code/src/tools/batch/README_TEXT_REPAIR.md`

#### 공식 API 스펙 핵심 요약

**File Upload**:
```python
uploaded_file = client.files.upload(
    file='my-batch-requests.jsonl',
    config=types.UploadFileConfig(
        display_name='my-batch-requests',
        mime_type='jsonl'  # ← 'jsonl', not 'application/jsonl'
    }
)
# Returns: File object with .name attribute (e.g., "files/abc123")
```

**Batch Creation**:
```python
batch_job = client.batches.create(
    model="gemini-2.5-flash",
    src=uploaded_file.name,  # ← Use file name
    config={
        'display_name': "my-batch-job",
    },
)
# Returns: Batch object with .name attribute (e.g., "batches/xyz789")
```

**Result Download**:
```python
if batch_job.state.name == 'JOB_STATE_SUCCEEDED':
    if batch_job.dest and batch_job.dest.file_name:
        result_file_name = batch_job.dest.file_name
        file_content_bytes = client.files.download(file=result_file_name)
        result_content = file_content_bytes.decode('utf-8')
```

---

### 2026-01-06: S2 Repair 결정 및 방향

**문서**: `HANDOFF_2026-01-06_S2_Repair_Decision.md`

#### 핵심 문제

**S5 피드백이 S2 Regen에 전혀 반영되지 않아 문제가 수정되지 않았습니다.**

| 항목 | 값 |
|------|------|
| 총 재생성된 카드 | 720개 |
| 텍스트 변경된 카드 | **0개** |
| 텍스트 문제 있는 카드 | 53개 (미해결) |
| 이미지 문제 카드 | 287개 (Positive Regen으로 일부 해결) |

#### 현재 Regen 파이프라인 분석

| 스크립트 | 용도 | S5 피드백 활용 |
|----------|------|---------------|
| `fast_s2_regen.py` | S2 카드 재생성 | ❌ **미사용** |
| `positive_regen_runner.py` | S4 이미지 재생성 | ✅ 사용 (S6 agent) |
| S1 테이블 재생성 | 해당 스크립트 없음 | ❌ **존재하지 않음** |

#### 문제의 원인

```python
# fast_s2_regen.py 현재 동작 방식
for entity in triggered_entities:
    # S5 피드백(suggested_fix, prompt_patch_hint)을 무시
    # 같은 프롬프트로 01_generate_json.py 재실행
    subprocess.run(["python3", "01_generate_json.py", ...])
    # → 같은 결과 생성 → 문제 미해결
```

**결론**: S5가 "이렇게 고쳐라"고 알려줘도, 재생성 시 그 정보가 전혀 전달되지 않음.

#### 미해결 텍스트 문제 (53개 카드)

**문제 유형별 분류**:

| 유형 | 심각도 | 예시 |
|------|--------|------|
| **Guideline/Protocol 오류** | 🔴 High | ICRP/SNMMI 가이드라인과 불일치 |
| **Medical Terminology 오류** | 🟠 Medium-High | GJ vs EJ, Involution failure |
| **MCQ 복수 정답** | 🔴 High | ABPA 문항: A와 D 모두 정답 |
| **Technical/Anatomical 오류** | 🟠 Medium | K-space center 설명 오류 |

**Score 분포 (Tech Accuracy 기준)**:

| Score | 개수 | 심각도 |
|-------|------|--------|
| 0.0 | 20개 | 🔴 Critical |
| 0.5 | 31개 | 🟠 Major |
| 1.0 | 2개 | 🟡 Minor |

#### 해결 방안 옵션

**Option A: 수동 수정 (권장 - 단기)**
- 대상: 53개 카드 중 Score 0.0인 20개 우선
- 방법: S5 `suggested_fix` 참고하여 직접 수정
- 장점: 확실한 수정, 즉시 적용 가능
- 단점: 노동 집약적

**Option B: S2R Repair Agent 개발 (중기)**
- 개념: `positive_regen_runner.py`와 유사한 텍스트 버전
- 구성요소:
  1. S5 피드백 추출기
  2. S6-Text agent (negative→positive 변환)
  3. Enhanced S2 프롬프트 생성기
  4. S2 재생성 + S5' 재검증
- 장점: 자동화, 재사용 가능
- 단점: 개발 시간 필요

**Option C: 파이프라인 패치 (단기-중기)**
- 방법: `fast_s2_regen.py`에 S5 hint 주입
- 장점: 기존 코드 활용
- 단점: S1 프롬프트 구조 이해 필요

**Option D: 하이브리드 (권장)**
1. 즉시: Score 0.0 카드 20개 수동 수정
2. 단기: Score 0.5 카드 중 blocking 이슈 수동 수정
3. 중기: Option C 개발로 자동화

---

### 2026-01-05: S3 Spec 정리 및 Positive Regen 설계

**문서**: `HANDOFF_2026-01-05_S3_Spec_Organization_And_Positive_Regen.md`

#### S3 Spec 버전 혼란 문제 해결

S3 image spec 파일들이 여러 번 변경되면서 (regen용, realistic용 등) 원본 추적이 어려웠음.

**분석 결과**:

| 항목 | 현재 S3 | 백업 S3 | 실제 이미지 |
|------|---------|---------|------------|
| S1_TABLE_VISUAL | **735** ✅ | 731 | 735 |
| S2_CARD_IMAGE | 6,175 | 8,201 | - |
| S2_CARD_CONCEPT | 900 | 1,638 | - |
| S2 총합 | **7,075** ✅ | 9,839 ❌ | 7,076 |
| **총합** | **7,810** ✅ | 10,570 ❌ | **7,811** |

**결론: 현재 S3 (`s3_image_spec__armG.jsonl`)가 정확!**

#### S3 Spec 파일 현황

```
FINAL_DISTRIBUTION/
├── s3_image_spec__armG.jsonl                     # 현재 원본 (7,810줄, diagram)
├── s3_image_spec__armG__realistic.jsonl          # REALISTIC 변환 (7,810줄)
├── s3_image_spec__armG__realistic_filtered.jsonl # 필터링된 버전
├── s3_image_spec__armG__realistic_retry.jsonl    # 재시도용
├── s3_image_spec__armG__repaired.jsonl           # 수리된 버전
└── s3_image_spec__armG__repaired__s2only.jsonl   # S2만 수리
```

#### S3 Spec 정리 작업

**정리 스크립트**: `3_Code/Scripts/organize_s3_specs.py`

**Suffix 명명 규칙 (확정)**:
```
# 원본 (절대 수정 금지)
s3_image_spec__arm{X}__original_diagram.jsonl

# 파생 버전 (항상 suffix 필수)
s3_image_spec__arm{X}__realistic_v{N}.jsonl         # REALISTIC 변환
s3_image_spec__arm{X}__regen_positive_v{N}.jsonl    # Positive regen용
s3_image_spec__arm{X}__filtered_{criteria}.jsonl    # 필터링
s3_image_spec__arm{X}__repaired_{target}.jsonl      # 수리
```

#### Positive Regen 파이프라인 설계 (Option C)

기존 S5 결과의 `prompt_patch_hint`를 활용하여 S3 재컴파일 없이 regen 수행.

**아키텍처**:
```
┌─────────────────────────────────────────────────────────────────┐
│ Phase 1: S5 Validation (이미 완료)                              │
│ - image_regeneration_trigger_score < 90 → regen 대상            │
│ - issues[].prompt_patch_hint → 개선 힌트                        │
└─────────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 2: prompt_patch_hint → positive_instructions 변환         │
│ - 카드 이미지: Flash 또는 룰기반 (단순 변환)                      │
│ - 인포그래픽: Pro 모델 (복잡한 레이아웃 분석 필요)                │
└─────────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 3: S4 Regen (gemini-2.5-flash-image)                     │
│ - 입력: 원본 S3 prompt_en + positive_instructions delta          │
│ - 출력: 개선된 이미지                                             │
└─────────────────────────────────────────────────────────────────┘
```

**핵심 장점**:
1. **S3 Spec 재사용**: 기존 `prompt_en` 그대로 사용, 복잡한 프롬프트 버전 관리 우회
2. **Flash 모델 유지**: 카드 이미지는 Flash로 충분, 비용 효율적
3. **S5 결과 활용**: `prompt_patch_hint` 필드 이미 존재

**모델 선택 기준**:

| 이미지 유형 | Phase 2 모델 | 이유 |
|------------|-------------|------|
| 카드 이미지 | **Flash** (또는 룰기반) | 단순 변환, 비용 효율 |
| 인포그래픽 | **Pro** | 복잡한 레이아웃 분석 필요 |

---

## 관련 스크립트 및 도구

### 배치 처리 스크립트
```
3_Code/src/tools/batch/
  ├── batch_text_repair.py          # 메인 배치 오케스트레이터
  ├── batch_image_generator.py      # 이미지 배치 생성 (별도)
  ├── fix_truncated_json.py         # JSON 파싱 에러 수동 복구
  ├── apply_recovered_cards.py      # 복구된 카드 적용
  ├── deduplicate_s2_entities.py    # 중복 제거
  └── README_TEXT_REPAIR.md         # 사용 가이드
```

### Regeneration 스크립트
```
3_Code/src/tools/regen/
  ├── positive_regen_runner.py      # Positive regen 오케스트레이터
  ├── fast_s2_regen.py              # S2 카드 재생성 (S5 미활용)
  └── s1r_s2r_agent.py              # 동기 fallback agent
```

### S3 Spec 관리
```
3_Code/Scripts/
  └── organize_s3_specs.py          # S3 정리 스크립트
```

---

## 프롬프트 템플릿

### Repair Prompts
```
3_Code/prompt/
  ├── S1R_SYSTEM__v1.md             # S1 repair agent
  ├── S2R_SYSTEM__v1.md             # S2 repair agent
  └── S6_POSITIVE_INSTRUCTION__v1.md # S6 positive instruction agent
```

---

## Threshold 정책 변경 이력

### 초기 설정: Threshold 90
- S5 validation에서 90점 기준으로 PASS/REGEN 판정
- 배치 repair 요청 생성 시 90점 미만 카드 선택

### 수정: Threshold 80 (2026-01-06)
- S5 validation 결과 분석 후 80점으로 하향 조정
- 관련 문서: `DECISION_2026-01-06_Threshold_80_Rationale.md`
- `batch_text_repair.py` threshold 90→80 수정
- Baseline 덮어쓰기 → `__regen` 별도 저장으로 변경

---

## 주의사항

### 1. Baseline 보존 원칙
- Baseline 파일들은 절대 수정 안됨
- 모든 regen은 `__regen` suffix 사용
- 배포 시 경로 매핑으로 regen 이미지 사용

### 2. 배치 비용 및 제한
- **비용**: S1=Pro (~$0.10/request), S2=Flash (~$0.02/request)
- **Rate limit**: 404/429 에러 시 자동 재시도
- **Token limit**: max_output_tokens=64000로 증가됨

### 3. API 키 로테이션
- 배치 제출 시 랜덤 키 선택
- 조회/다운로드 시 원래 키 사용 (tracking JSON에 기록)

### 4. 중복 제거
- Deduplication 완료됨 (3,509 entities = clean)
- 추가 dedup 불필요

---

## 검증 명령어

### 중복 확인
```python
cd /path/to/workspace/workspace/MeducAI && python3 -c "
import json
from collections import Counter

for filename in ['s2_results__s1armG__s2armG.jsonl', 's2_results__s1armG__s2armG__regen.jsonl']:
    filepath = f'2_Data/metadata/generated/FINAL_DISTRIBUTION/{filename}'
    
    entity_keys = []
    with open(filepath, 'r') as f:
        for line in f:
            if not line.strip():
                continue
            record = json.loads(line)
            key = (record['group_id'], record['entity_id'])
            entity_keys.append(key)
    
    counts = Counter(entity_keys)
    duplicates = {k: v for k, v in counts.items() if v > 1}
    
    print(f'{filename}:')
    print(f'  Total: {len(entity_keys)}')
    print(f'  Unique: {len(set(entity_keys))}')
    print(f'  Duplicates: {len(duplicates)}')
    print()
"
```

### 배치 상태 확인
```bash
python3 3_Code/src/tools/batch/batch_text_repair.py --check_status
```

### 배치 재제출
```bash
python3 3_Code/src/tools/batch/batch_text_repair.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G \
  --mode mixed \
  --submit
```

---

## 참고 문서

### Protocol 문서
- `0_Protocol/00_Governance/supporting/LLM-operation/Batch.md` - Batch API 공식 문서
- `0_Protocol/05_Pipeline_and_Execution/S6_Positive_Instruction_Agent_Spec.md` - S6 스펙

### 5_Meeting 원본 문서
- `HANDOFF_2026-01-15_Positive_Regen_Phase3_Real_Test.md`
- `HANDOFF_2026-01-06_Batch_Recovery_and_Deduplication.md`
- `HANDOFF_2026-01-06_Batch_API_Corrections.md`
- `HANDOFF_2026-01-06_S2_Repair_Decision.md`
- `HANDOFF_2026-01-05_S3_Spec_Organization_And_Positive_Regen.md`

---

**문서 작성일**: 2026-01-15  
**최종 업데이트**: 2026-01-15  
**상태**: 통합 완료

