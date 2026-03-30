# Regeneration Agents Implementation History

**Last Updated**: 2026-01-06  
**Purpose**: S1R/S2R 재생성 에이전트 구현 기록  
**Scope**: FINAL_DISTRIBUTION armG의 텍스트 재생성 에이전트 개발 및 배치 통합

---

## 개요

본 문서는 S1R (S1 Repair)과 S2R (S2 Repair) 에이전트의 구현 및 배치 API 통합 작업을 시간순으로 정리합니다.

---

## Timeline

### 2026-01-06: S1R + S2R Batch 구현 완료

**문서**: `HANDOFF_2026-01-06_S1R_S2R_Implementation_Complete.md`, `HANDOFF_2026-01-06_S1R_S2R_Batch_Implementation_Complete.md`

#### 작업 요약

S1R + S2R Batch API 구현 및 실행이 성공적으로 완료되었습니다.

**Key Results**:
- **성공률**: 98.4% (367/373)
- **적용 완료**: S1 28개, S2 366개
- **비용 절감**: 50% (~$8 절감)
- **소요 시간**: 25분

#### 실행 결과

| 항목 | 요청 | 성공 | 적용 |
|------|------|------|------|
| **S1 Tables** | 28 | 28 | 28 |
| **S2 Cards** | 345 | 339 | 366 |
| **총합** | 373 | 367 | 394 |

#### 구현 완료된 작업

1. **Request Builder** ✅ - S5 피드백 기반 배치 요청 생성
2. **Tracking System** ✅ - 배치 메타데이터 추적 및 저장
3. **Error Handling** ✅ - 404/429 자동 재시도, API 키 로테이션
4. **Result Parser** ✅ - 배치 결과 파싱 및 JSONL 병합
5. **CLI Interface** ✅ - submit, check_status, download_and_apply
6. **API Key Fix** ✅ - 배치별 원래 키로 조회/다운로드
7. **max_output_tokens** ✅ - 64k로 증가 (토큰 초과 방지)

---

### 2026-01-06: S1R/S2R Agent 구현

**문서**: `HANDOFF_2026-01-06_S1R_S2R_Agent_Implementation.md`

#### 에이전트 설계

**S1R Agent** - S1 Table Repair:
- Input: S1 table data + S5 feedback
- Output: Repaired table with medical accuracy improvements
- Model: gemini-2.5-pro (Pro 필요 - 복잡한 테이블 구조)

**S2R Agent** - S2 Card Repair:
- Input: S2 card data + S5 feedback
- Output: Repaired card with MCQ/content improvements
- Model: gemini-2.5-flash (Flash 충분 - 단순 텍스트)

#### 핵심 기능

**1. S5 Feedback Integration**:
```python
def extract_s5_feedback(s5_validation: Dict) -> Dict:
    """
    S5 validation 결과에서 repair 힌트 추출
    
    Returns:
    - blocking_error: bool
    - technical_accuracy: float (0.0/0.5/1.0)
    - educational_quality: int (1-5)
    - issues: List[Dict]  # type, severity, description, suggested_fix
    """
```

**2. Repair Prompt Generation**:
```python
def build_repair_prompt(
    original_content: Dict,
    s5_feedback: Dict,
    repair_type: str  # "s1" or "s2"
) -> str:
    """
    S5 feedback을 반영한 repair 프롬프트 생성
    
    Components:
    - Original content
    - Issues identified by S5
    - Suggested fixes
    - Guidelines for improvement
    """
```

**3. Response Validation**:
```python
def validate_repair_response(
    response: Dict,
    original: Dict,
    repair_type: str
) -> Tuple[bool, Optional[str]]:
    """
    Repair 결과 검증
    
    Checks:
    - Schema compliance
    - Required fields present
    - No data loss
    - Format consistency
    """
```

---

### 2026-01-06: Batch Text Repair 통합

**문서**: `HANDOFF_2026-01-06_S1R_S2R_Batch_Implementation_Complete.md`

#### Batch API 통합 아키텍처

```
S5 Validation Results
  ↓
Filter (trigger_score < 80)
  ↓
Build Batch Requests (JSONL)
  ↓
Upload to Gemini Files API
  ↓
Submit Batch Job
  ↓
Poll for Completion
  ↓
Download Results
  ↓
Parse & Validate
  ↓
Apply to JSONL files
```

#### 구현 파일

**1. Main Orchestrator**: `3_Code/src/tools/batch/batch_text_repair.py` (1,400+ lines)

**Functions**:
- `submit_batch_with_retry()` - 배치 제출 (retry logic 포함)
- `check_batch_status()` - 배치 상태 확인
- `download_batch_results()` - 결과 다운로드
- `parse_batch_results()` - JSONL 파싱 및 검증
- `apply_repairs()` - S1/S2 파일에 적용

**2. Synchronous Fallback**: `3_Code/src/tools/regen/s1r_s2r_agent.py` (360+ lines)

**Functions**:
- `repair_s1_table()` - S1 단일 테이블 repair
- `repair_s2_card()` - S2 단일 카드 repair
- `validate_repair()` - Repair 결과 검증

**3. Prompt Templates**:
- `3_Code/prompt/S1R_SYSTEM__v1.md` - S1 repair 프롬프트
- `3_Code/prompt/S2R_SYSTEM__v1.md` - S2 repair 프롬프트

#### Batch Request Format

**JSONL Request**:
```json
{
  "request": {
    "method": "POST",
    "endpoint": "/v1/models/gemini-2.5-pro:generateContent",
    "body": {
      "contents": [
        {
          "role": "user",
          "parts": [{"text": "...repair prompt..."}]
        }
      ],
      "generationConfig": {
        "temperature": 0.3,
        "maxOutputTokens": 64000
      }
    }
  },
  "metadata": {
    "group_id": "grp_xxx",
    "entity_id": "DERIVED:xxx",  // S2 only
    "repair_type": "s1" | "s2",
    "original_score": 75.0
  }
}
```

#### Tracking System

**File**: `.batch_tracking.json`

**Schema**:
```json
{
  "batch_id": "bch_xxx",
  "submitted_at": "2026-01-06T10:00:00Z",
  "api_key_index": 2,
  "repair_type": "mixed",
  "num_requests": 373,
  "s1_count": 28,
  "s2_count": 345,
  "status": "COMPLETED",
  "completed_at": "2026-01-06T10:25:00Z",
  "success_count": 367,
  "failure_count": 6,
  "output_file": "path/to/results.jsonl"
}
```

---

### 파싱 에러 처리

**문서**: `HANDOFF_2026-01-06_Batch_Recovery_and_Deduplication.md`

#### 발견된 문제

**초기 다운로드 결과**:
```
성공: 22 S1 + 328 S2 = 350개
실패: 6 S2 카드 (JSON 파싱 에러)
```

**실패 원인**:
- LLM 출력이 토큰 제한에 도달하여 JSON이 잘리고 대부분 공백으로 채워짐
- 일부는 같은 내용을 무한 반복하는 패턴 포함

#### 개선된 파싱 로직

**파일**: `3_Code/src/tools/batch/batch_text_repair.py`

**추가된 기능**:
1. JSON 파싱 에러 시 마크다운 코드 블록 추출 시도
2. 원본 배치 결과 자동 저장
3. 실패한 라인 상세 로깅 (line number, key, error)
4. S1/S2 분류별 실패 통계

#### 수동 복구

**스크립트**: `3_Code/src/tools/batch/fix_truncated_json.py`

**복구 방법**:
1. 원본 텍스트에서 trailing whitespace 제거
2. 누락된 닫는 중괄호/대괄호 추가
3. 무한 반복 패턴 제거
4. JSON validation

**결과**: 실패한 6개 카드 모두 성공적으로 복구됨

---

## 프롬프트 설계

### S1R Prompt Structure

**System Prompt** (`S1R_SYSTEM__v1.md`):
```markdown
# Role
You are a medical education content repair agent specializing in radiology table accuracy.

# Task
Repair S1 Master Table based on S5 validation feedback.

# Input
1. Original S1 table (JSON)
2. S5 validation results
3. Issues identified

# Output
Repaired S1 table (JSON) with:
- Corrected technical accuracy
- Improved educational quality
- Fixed guideline compliance
- Preserved structure and formatting
```

### S2R Prompt Structure

**System Prompt** (`S2R_SYSTEM__v1.md`):
```markdown
# Role
You are a medical education MCQ repair agent specializing in radiology board-style questions.

# Task
Repair S2 Anki Card based on S5 validation feedback.

# Input
1. Original S2 card (JSON)
2. S5 validation results
3. Issues identified

# Output
Repaired S2 card (JSON) with:
- Corrected MCQ options and answers
- Improved clinical relevance
- Fixed difficulty level
- Preserved entity metadata
```

---

## Usage Examples

### Submit Batch

```bash
python3 3_Code/src/tools/batch/batch_text_repair.py \
    --base_dir . --run_tag FINAL_DISTRIBUTION --arm G \
    --mode mixed --submit
```

### Check Status

```bash
python3 3_Code/src/tools/batch/batch_text_repair.py --check_status
```

### Download and Apply

```bash
python3 3_Code/src/tools/batch/batch_text_repair.py \
    --base_dir . --run_tag FINAL_DISTRIBUTION --arm G \
    --download_and_apply
```

### Synchronous Fallback (single card)

```python
from tools.regen.s1r_s2r_agent import repair_s2_card

repaired = repair_s2_card(
    original_card=card_data,
    s5_feedback=feedback,
    model="gemini-2.5-flash"
)
```

---

## Performance Metrics

### Batch vs Synchronous

| Metric | Batch | Synchronous | Improvement |
|--------|-------|-------------|-------------|
| Cost per request | $0.02 | $0.04 | **50% savings** |
| Total time (373 requests) | 25 min | ~60 min | **58% faster** |
| Success rate | 98.4% | 100% | -1.6% |
| Scalability | High | Low | Batch wins |

### Model Costs

| Model | Cost per 1M input | Cost per 1M output | Use Case |
|-------|-------------------|-------------------|----------|
| gemini-2.5-flash | $0.075 | $0.30 | S2 repair (text) |
| gemini-2.5-pro | $1.25 | $5.00 | S1 repair (complex tables) |

---

## Error Handling

### API Errors

**404 Not Found**:
- Cause: Batch ID not found (wrong API key)
- Solution: Use original API key from tracking JSON

**429 Rate Limit**:
- Cause: Too many requests
- Solution: Automatic retry with exponential backoff

**500 Internal Server Error**:
- Cause: Gemini API temporary failure
- Solution: Retry up to 3 times

### Parsing Errors

**Truncated JSON**:
- Cause: max_output_tokens exceeded
- Solution: Increased to 64k tokens

**Malformed Response**:
- Cause: LLM hallucination or formatting error
- Solution: Manual review and fix_truncated_json.py

---

## API Key Rotation

### Strategy

**Multiple API Keys**:
- Key 1, Key 2, Key 3 in `.env`
- Random selection on batch submit
- Original key stored in tracking JSON

**Usage**:
```python
# Submit: use random key
api_key = random.choice([KEY1, KEY2, KEY3])
batch = client.batches.create(...)
tracking["api_key_index"] = key_index

# Download: use original key
api_key = KEYS[tracking["api_key_index"]]
results = client.batches.get(batch_id)
```

---

## 관련 스크립트

### Repair Agents
```
3_Code/src/tools/
  ├── batch/
  │   └── batch_text_repair.py          # Main batch orchestrator
  └── regen/
      └── s1r_s2r_agent.py              # Synchronous fallback
```

### Recovery Tools
```
3_Code/src/tools/batch/
  ├── fix_truncated_json.py             # JSON repair tool
  └── apply_recovered_cards.py          # Apply manual fixes
```

---

## 참고 문서

### Protocol 문서
- `0_Protocol/00_Governance/supporting/LLM-operation/Batch.md`

### 5_Meeting 원본 문서
- `HANDOFF_2026-01-06_S1R_S2R_Implementation_Complete.md`
- `HANDOFF_2026-01-06_S1R_S2R_Batch_Implementation_Complete.md`
- `HANDOFF_2026-01-06_S1R_S2R_Agent_Implementation.md`

---

**문서 작성일**: 2026-01-06  
**최종 업데이트**: 2026-01-06  
**상태**: 통합 완료

