# QA PDF 생성 및 리뷰어 배정 준수 검증 리포트

**검증 일자:** 2025-12-22  
**검증 범위:** Blindness, Mapping, LLM 호출 로그, MI-CLEAR-LLM 준수  
**검증 대상:** QA PDF 생성 및 리뷰어 배정 프로세스

---

## 1. Executive Summary

### 전체 준수 상태

| 항목 | 상태 | 심각도 | 비고 |
|------|------|--------|------|
| **Blindness** | ⚠️ **부분 준수** | **높음** | PDF 생성 스크립트가 blinded 모드 미사용 |
| **Mapping** | ✅ 준수 | 낮음 | Surrogate mapping 파일 존재 |
| **LLM 호출 로그** | ✅ 준수 | 낮음 | 토큰/시간 로그 정상 기록 |
| **MI-CLEAR-LLM** | ✅ 준수 | 낮음 | Prompt hash, config snapshot 기록됨 |

---

## 2. 상세 검증 결과

### 2.1 Blindness (블라인드 처리)

#### ✅ 준수 사항

1. **Blinding 절차 문서화**
   - `QA_Blinding_Procedure.md` 존재 및 명확한 규정 정의
   - Metadata stripping 요구사항 명시:
     - 모델명, provider명 제거
     - arm ID 제거
     - prompt 문구 및 system message 흔적 제거
     - generation timestamp, run tag 제거
     - 토큰 수, latency, cost 제거
     - 파일명에 generation 정보 포함 금지

2. **PDF 빌더 blinded 모드 지원**
   - `07_build_set_pdf.py`에 `--blinded` 플래그 구현됨
   - Surrogate ID 사용 로직 구현됨 (line 2160-2170)
   - Footer 제거 (line 2241: "No footer (evaluators should not see group/arm information)")

3. **Surrogate Mapping 파일 존재**
   - `0_Protocol/06_QA_and_Study/QA_Operations/surrogate_map.csv` 존재
   - Format: `group_id,arm,surrogate_set_id`

#### ❌ 미준수 사항 (심각)

1. **PDF 생성 스크립트 blinded 모드 미사용**
   - **파일:** `3_Code/src/tools/qa/generate_qa_pdfs_allow_missing_images.py`
   - **문제:** `07_build_set_pdf.py` 호출 시 `--blinded` 플래그를 전달하지 않음
   - **위치:** Line 73-82
   ```python
   cmd = [
       sys.executable,
       str(pdf_script),
       "--base_dir", str(base_dir),
       "--run_tag", run_tag,
       "--arm", arm,
       "--group_id", group_id,
       "--out_dir", str(out_dir),
       "--allow_missing_images",  # Allow missing images
       # ❌ --blinded 플래그 누락
       # ❌ --set_surrogate_csv 플래그 누락
   ]
   ```

2. **결과**
   - PDF 파일명에 `group_id`와 `arm` 정보가 노출됨
   - Format: `SET_{group_id}_arm{arm}_{run_tag}.pdf` (line 2172)
   - 이는 **QA Blinding Procedure v2.0 위반**

#### 🔧 권장 조치

1. **즉시 조치 (필수)**
   ```python
   # generate_qa_pdfs_allow_missing_images.py 수정 필요
   cmd = [
       sys.executable,
       str(pdf_script),
       "--base_dir", str(base_dir),
       "--run_tag", run_tag,
       "--arm", arm,
       "--group_id", group_id,
       "--out_dir", str(out_dir),
       "--allow_missing_images",
       "--blinded",  # ✅ 추가
       "--set_surrogate_csv", "0_Protocol/06_QA_and_Study/QA_Operations/surrogate_map.csv",  # ✅ 추가
   ]
   ```

2. **검증 절차**
   - 생성된 PDF 파일명 확인
   - PDF 내용에서 metadata 제거 여부 확인
   - Footer에 group/arm 정보 노출 여부 확인

---

### 2.2 Mapping (리뷰어-아티팩트 매핑)

#### ✅ 준수 사항

1. **Surrogate Mapping 파일**
   - 위치: `0_Protocol/06_QA_and_Study/QA_Operations/surrogate_map.csv`
   - Format: `group_id,arm,surrogate_set_id`
   - 예시:
     ```csv
     group_id,arm,surrogate_set_id
     group_10,F,SET_001
     group_02,D,SET_002
     ```

2. **Assignment Plan 문서화**
   - `QA_Assignment_Plan.md` 존재
   - 매핑 파일 접근 제어 규정:
     - QA 운영자만 접근 가능
     - Reviewers에게 절대 공유되지 않음

3. **PDF 빌더 매핑 로드 기능**
   - `load_surrogate_map()` 함수 구현됨 (line 201-220)
   - Blinded 모드에서 surrogate ID 사용 (line 2161-2164)

#### ⚠️ 주의 사항

1. **매핑 파일 검증 필요**
   - 모든 QA 대상 (group_id, arm) 조합이 매핑 파일에 포함되어 있는지 확인 필요
   - 누락된 경우 hash-based surrogate로 fallback (line 2167-2170) - 권장하지 않음

---

### 2.3 LLM 호출 로그 (토큰 및 시간)

#### ✅ 준수 사항

1. **Runtime Metadata 기록**
   - **파일:** `3_Code/src/01_generate_json.py`
   - **위치:** Line 2637-2646 (S1), Line 2899-2924 (S2)
   - **기록 항목:**
     ```python
     "runtime": {
         "latency_sec": rt_s1.get("latency_sec"),
         "input_tokens": rt_s1.get("input_tokens"),
         "output_tokens": rt_s1.get("output_tokens"),
         "total_tokens": rt_s1.get("total_tokens"),
         # S2도 동일한 구조로 기록
         "latency_sec_stage1": ...,
         "latency_sec_stage2": ...,
         "input_tokens_stage1": ...,
         "output_tokens_stage1": ...,
         "input_tokens_stage2": ...,
         "output_tokens_stage2": ...,
     }
     ```

2. **LLM 호출 시점 기록**
   - `call_llm()` 함수에서 latency 측정 (line 1133, 1231, 1319)
   - `time.perf_counter()` 사용하여 정확한 시간 측정
   - Provider별 토큰 정보 추출:
     - Gemini: `prompt_token_count`, `candidates_token_count` (line 1165-1171)
     - OpenAI: `prompt_tokens`, `completion_tokens` (line 1237-1243)
     - Anthropic: `input_tokens`, `output_tokens` (line 1326-1335)

3. **RAG 메트릭 기록**
   - `rag_queries_count`, `rag_sources_count` 기록됨 (line 2914-2915)

#### ✅ 검증 완료

- 모든 LLM 호출에 대해 토큰 및 시간 정보가 정상적으로 기록됨
- Stage1과 Stage2 모두 별도로 기록됨
- Provider별로 적절한 필드명 사용

---

### 2.4 MI-CLEAR-LLM 준수

#### ✅ 준수 사항

1. **Prompt Bundle Hash 기록**
   - **위치:** `3_Code/src/01_generate_json.py`
   - **Line 2713, 2897:** `"prompt_bundle_hash": bundle.get("prompt_bundle_hash")`
   - 모든 생성 레코드에 포함됨

2. **Prompt File IDs 기록**
   - **Line 2712, 2896:** `"prompt_file_ids": bundle.get("prompt_file_ids")`
   - 각 단계별 prompt 파일 경로 기록

3. **Config Snapshot 기록**
   - **Line 2900-2924:** Runtime metadata에 다음 정보 포함:
     ```python
     "runtime": {
         "run_tag": run_tag,
         "mode": mode,
         "arm": arm,
         "provider": provider,
         "model_stage1": model_stage1,
         "model_stage2": model_stage2,
         "thinking_enabled": thinking_enabled,
         "thinking_budget": thinking_budget,
         "thinking_level": thinking_level,
         "rag_enabled": rag_enabled,
         "rag_mode": rag_mode,
         # ... 토큰 및 시간 정보
     }
     ```

4. **Temperature 고정**
   - **Line 3044:** `# MI-CLEAR-LLM: Fixed temperature for reproducibility (default 0.2 for all stages)`
   - 재현성을 위한 temperature 고정

5. **문서 준수**
   - `Pipeline_Execution_Plan.md`에 MI-CLEAR-LLM 요구사항 명시됨
   - Required metadata fields 정의됨 (Line 60-84)

#### ✅ 검증 완료

- MI-CLEAR-LLM 요구사항이 모두 충족됨
- Prompt hash, config snapshot, runtime metrics 모두 기록됨

---

## 3. 종합 평가 및 권장 사항

### 3.1 즉시 조치 필요 (Critical)

1. **PDF 생성 스크립트 blinded 모드 적용**
   - `generate_qa_pdfs_allow_missing_images.py` 수정
   - `--blinded` 및 `--set_surrogate_csv` 플래그 추가
   - 기존 생성된 PDF 재생성 필요

2. **Blinding 무결성 검증**
   - 생성된 PDF 파일명 확인
   - PDF 내용에서 metadata 제거 여부 확인
   - Footer/Header에 식별 정보 노출 여부 확인

### 3.2 개선 권장 사항

1. **자동화된 Blinding 검증**
   - PDF 생성 후 자동으로 blinding 규정 준수 여부 검증하는 스크립트 추가
   - 파일명, 메타데이터, 콘텐츠 검사

2. **매핑 파일 검증**
   - 모든 QA 대상 조합이 매핑 파일에 포함되어 있는지 자동 검증
   - 누락 시 경고 및 오류 처리

3. **문서화 보완**
   - PDF 생성 프로세스에 blinded 모드 사용이 필수임을 명시
   - QA 배포 전 체크리스트에 blinding 검증 항목 추가

---

## 4. 검증 체크리스트

### 4.1 Blindness

- [x] Blinding 절차 문서화됨
- [x] PDF 빌더 blinded 모드 지원
- [x] Surrogate mapping 파일 존재
- [ ] **PDF 생성 스크립트 blinded 모드 사용** ⚠️ **미준수**
- [ ] 생성된 PDF 파일명 검증
- [ ] PDF 내용 metadata 제거 검증

### 4.2 Mapping

- [x] Surrogate mapping 파일 존재
- [x] Assignment plan 문서화됨
- [x] 매핑 파일 접근 제어 규정
- [ ] 모든 QA 대상 조합 매핑 확인 필요

### 4.3 LLM 호출 로그

- [x] Runtime metadata 구조 정의됨
- [x] 토큰 정보 기록됨 (input/output/total)
- [x] Latency 기록됨 (stage1/stage2)
- [x] RAG 메트릭 기록됨
- [x] Provider별 적절한 필드명 사용

### 4.4 MI-CLEAR-LLM

- [x] Prompt bundle hash 기록됨
- [x] Prompt file IDs 기록됨
- [x] Config snapshot 기록됨
- [x] Temperature 고정됨
- [x] 문서 준수 확인됨

---

## 5. 결론

### 준수 상태 요약

- **LLM 호출 로그:** ✅ 완전 준수
- **MI-CLEAR-LLM:** ✅ 완전 준수
- **Mapping:** ✅ 준수 (검증 필요)
- **Blindness:** ⚠️ **부분 준수** - **즉시 조치 필요**

### 최우선 조치 사항

**PDF 생성 스크립트에 blinded 모드를 적용하여 논문의 엄격함을 지켜야 합니다.**

현재 상태로는 PDF 파일명에 `group_id`와 `arm` 정보가 노출되어 QA Blinding Procedure v2.0을 위반하고 있습니다.

---

**검증자:** AI Assistant  
**검증 일자:** 2025-12-22  
**다음 검증 권장 일자:** PDF 생성 스크립트 수정 후

