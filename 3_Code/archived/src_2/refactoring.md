# Step02 제거를 위한 JSONL-only 전환 패치 설계서 (1-page)

**목표:** Step01 JSONL을 **Single Source of Truth**로 유지하면서, Step04.5/Step04/Step05까지 **전 구간 JSONL consumer**로 전환하여 `02_postprocess_results.py`(CSV normalization)를 **비필수(옵션 뷰)**로 만든다.
**원칙:** RUN_TAG-centric, arm-aware suffix 유지, “Truth=JSONL / View=CSV(선택)”로 재정의.

---

## 0) 현재 병목(왜 Step02가 아직 “필요해 보이는가”)

* Step03.5는 이미 **selected JSONL을 생성**하지만(동시에 CSV도 생성) 
* Step04.5는 **CSV만 입력**으로 받음 
* Step04(Anki export)도 **selected CSV만 입력**으로 받음 
* Step05(QA distribution)도 **prompts CSV + selected CSV를 전제로 Step03/04를 호출**  

즉, **Step02가 “필요한 게 아니라” downstream이 CSV consumer로 남아 있어서 Step02 산출물(CSV)이 필요했던 상태**다.

---

## 1) Canonical 파일명/경로 규칙 (패치 후)

### 1.1 Truth(JSONL) — 유지/강화

* Step01 output(기존 유지):

  * `2_Data/metadata/generated/<RUN_TAG>/output_<provider>_<RUN_TAG>__armX.jsonl` 
* Step03.5 selected(기존 유지):

  * `2_Data/metadata/generated/<RUN_TAG>/selected_<RUN_TAG>__armX.jsonl` 

### 1.2 View(CSV) — “옵션 도구”로 격하

* `selected_<RUN_TAG>__armX.csv`는 **디버깅/검토용 선택 산출물**로만 남김(기본 OFF 권장) 

### 1.3 Deck stats(JSON) — 유지

* `2_Data/metadata/generated/<RUN_TAG>/deck_stats_<provider>_<RUN_TAG>__armX.json` (권장: arm suffix 포함)

---

## 2) 변경 범위(파일/함수/CLI 계약)

### A) `03_5_select_deck.py` (Step03.5) — “selected JSONL”을 표준으로 확정

**현 상태:** JSONL 입력, selected JSONL+CSV 동시 출력 
**패치:**

1. **기본 출력은 selected JSONL만** (CSV는 `--emit_csv_view` 옵션일 때만)
2. Step05/04/04.5가 사용할 **표준 selected_jsonl_path()** 헬퍼를 노출

   * 현재 이미 `out_selected_jsonl()` 존재 

**새/변경 CLI**

* `--emit_csv_view` (default: false)

---

### B) `04_5_check_deck_stats.py` (Step04.5) — JSONL consumer로 전환

**현 상태:** CSV loader 중심 (`load_csv_stable`, `pd.read_csv`) , 입력도 CSV로 명시 
**패치:**

1. 입력을 `--input_jsonl`로 받는 경로를 추가(기본은 selected JSONL)
2. `read_jsonl()` 구현(03.5의 read_jsonl을 복사/공유)
3. 내부 통계는 `list[dict] → DataFrame` 변환 후 기존 로직 재사용(coverage/mix/sanity)

**새/변경 CLI**

* `--arm`은 이미 존재(arm suffix 대응) 
* `--input_jsonl` (신규, `--input_csv`와 상호배타)
* `--selected` 유지하되, JSONL에서는 “selected JSONL”을 기본으로 삼도록 정리

---

### C) `04_export_anki.py` (Step04) — JSONL consumer로 전환

**현 상태:** CSV 입력만 가정(`--input_csv`, `load_csv`) , required columns 보정도 DataFrame 기반 
**패치:**

1. `--input_jsonl` 옵션 추가(권장: selected JSONL)
2. `load_cards()`를 신설:

   * JSONL이면 `read_jsonl → DataFrame`
   * CSV이면 기존 `load_csv`
3. required columns 보정 로직은 그대로 유지(DF 기반 재사용)

**새/변경 CLI**

* `--input_jsonl` (신규)
* `--input_csv`는 legacy 유지(디버그/호환)
* 입력 우선순위: `input_jsonl > input_csv > default_resolver`

---

### D) `05_build_qa_distribution.py` (Step05) — prompts CSV 의존 제거 + Step03/04 호출 계약 변경

**현 상태:**

* `guess_csv_paths()`로 `image_prompts_*.csv`, `table_infographic_prompts_*.csv`, `anki_cards_selected_*.csv`를 전제로 함 
* Step03 호출도 `--input_csv`로 고정  
* Step04 호출도 `--input_csv`로 고정 

**패치:**

1. `guess_csv_paths()`를 `guess_jsonl_paths()`로 교체:

   * `output_<provider>_<run_tag>__armX.jsonl` (Step01)
   * `selected_<run_tag>__armX.jsonl` (Step03.5)
2. Step03(이미지 생성) 호출을 JSONL-only 방식으로 변경:

   * entity: `03_generate_images.py --input_kind entity --run_tag ...` (입력 JSONL은 표준 위치에서 로드)
   * table: `--input_kind table`
   * 더 이상 prompts CSV를 넘기지 않음
3. Step04 export 호출을 JSONL로 변경:

   * `04_export_anki.py --input_jsonl selected_<...>.jsonl`
4. 필요 시, “뷰 산출”이 필요하면 별도 optional 스크립트에서 CSV를 생성(본 Step05에는 포함하지 않음)

---

## 3) JSONL 최소 계약(Downstream 필수 키)

`03_5_select_deck.py`가 이미 “필수 스키마”를 명시합니다: `group_id, record_id, front, back` 
Step04/04.5 수준에서 추가로 사실상 필요한 키(권장):

* `entity_name`
* `card_type`
* `tags`
* `specialty`, `anatomy`, `topic`
* (옵션) `row_image_necessity`, `row_image_prompt_en` (entity image)

**정책:** 누락 시 Step04/04.5에서 “하드 실패”가 아니라, 현재 CSV 기반처럼 **빈 값으로 보정**(단, safety gate/QA에 필요한 필드는 경고/리포트에 기록).

---

## 4) 단계별 “완료 기준”(Acceptance Criteria)

1. Step03.5 실행 후 `selected_<RUN_TAG>__armX.jsonl` 생성 확인 
2. Step04.5가 selected JSONL로 stats 산출(기존 coverage/mix/sanity 유지)
3. Step04가 selected JSONL로 `.apkg` 생성(이미지 attach 로직 유지)
4. Step05가 **CSV 없이도** end-to-end로:

   * 이미지 생성(03) + 덱 생성(04) + run_report 생성까지 완료

---

## 5) Step02의 최종 처리(권장)

* `02_postprocess_results.py`는 삭제하지 말고 **`tools/jsonl_to_csv_view.py`로 격하**:

  * “사람이 보는 용도(EDA/QA 테이블/필터링)”만 담당
  * 파이프라인 필수 경로에서 제거

---

원하시면, 위 설계서 기준으로 **P0 최소 변경(04.5 + 04 + 05만)** 버전과, **완전 정리(03.5 CSV 기본 OFF 포함)** 버전, 두 가지로 패치 순서를 나눠서 제시하겠습니다.
