# S5 피드백 라운드 기반 버전 네이밍 (S5R) — Canonical

**작성일**: 2025-12-29  
**목적**: 프롬프트 개선을 “개인 직관 수정”이 아닌 **S5 feedback loop(라운드 기반)**로 운영하기 위해, 실험/문서/산출물에서 일관되게 사용하는 **직관적 버전 네이밍 규칙**을 정의한다.

---

## 1. 핵심 원칙

### 1.1 S5R 라운드가 1차 식별자
- 앞으로의 프롬프트 개선 버전은 `vXX`보다 **`S5R<k>`(S5 Round)** 를 우선 표기한다.
- `S5R0` = S5 피드백 반영 전(초기), `S5R1` = 1차 반영, `S5R2` = 2차 반영 … (증가만 허용)

### 1.2 “파일명/레지스트리”는 최소 변경(파이프라인 안정성)
- 파이프라인은 `3_Code/prompt/_registry.json`를 단일 소스로 읽는다.
- 따라서 기존 `__vXX` 파일은 **삭제/대규모 rename 금지**.
- 신규 버전부터 파일명에 `__S5Rk`를 추가하는 것을 권장한다(기존 v파일은 유지).

### 1.3 Text(S1/S2)와 Image(S4)는 가능하면 동일 라운드로 정렬
- 가능하면 같은 라운드 번호를 사용: 예) `S1/S2/S4 = S5R2`
- 불가피하게 분리될 경우에만 suffix를 사용:
  - Text만 변경: `S5Rk_T`
  - Image만 변경: `S5Rk_I`

### 1.4 파일명 규칙 (프롬프트 파일)

**파일명 구조:**
```
{PROMPT_NAME}__S5R{k}__v{XX}.md
```

**예시:**
- `S1_SYSTEM__S5R0__v12.md` (현재 baseline)
- `S1_SYSTEM__S5R1__v13.md` (1차 개선)
- `S2_SYSTEM__S5R0__v9.md` (현재 baseline)
- `S2_SYSTEM__S5R1__v10.md` (1차 개선)

**원칙:**
- 파일명에 S5R 라운드와 v버전을 모두 포함하여 추적성 확보
- 파일명만 봐도 S5R 라운드 파악 가능
- 레지스트리(`_registry.json`)와 파일명이 일치하여 혼란 감소
- 기존 `__vXX` 파일은 유지 (하위 호환성)
- 신규 버전부터 `__S5Rk__vXX` 형식 사용

**레지스트리 업데이트:**
- `3_Code/prompt/_registry.json`에서 해당 항목을 새 파일명으로 업데이트
- 예: `"S1_SYSTEM": "S1_SYSTEM__S5R0__v12.md"`

---

## 2. 3-layer 네이밍 구조

### 2.1 Layer A — 개선 라운드
- `S5R<k>` (예: `S5R0`, `S5R2`)

### 2.2 Layer B — 대상(모달리티/스테이지)
- Text: `S1`, `S2`
- Image: `S4_EXAM`(card image), `S4_TABLE_VISUAL`/`S4_CONCEPT`(infographic/concept)

### 2.3 Layer C — 실험 조건(운영 추적)
- `preFix` / `postFix` (수정 전/후)
- `before_rerun` / `after` (동시기 비교 조건)
- Replicate: `__rep1`, `__rep2` …

---

## 3. v버전 ↔ S5R 라운드 매핑(문서/리포트 표기용)

> 이 매핑은 **문서/Methods/표**에서 1차 표기로 사용한다. (코드 실행은 `_registry.json`이 가리키는 파일에 의해 결정)

| S5R 라운드 | Text (S1/S2) | Image (S4) | 비고 |
|---|---|---|---|
| **S5R0** | S1 `v12`, S2 `v9` | S4 baseline set (예: `S4_EXAM_*__v8_DIAGRAM_4x5_2K`, `S4_CONCEPT_*__v3`) | S5 피드백 반영 전(초기) |
| **S5R1** | S1 `v13`, S2 `v10` | (변경 없으면 baseline 유지) | historical run 존재 |
| **S5R2** | S1 `v14`, S2 `v11` | (개선 시 S4도 S5R2로 정렬 권장) | 현재 text freeze 상태 |

---

## 4. Run tag 규칙(권장; 즉시 적용 가능)

Run tag는 분석/재현의 핵심 식별자이므로, **여기부터 S5R 중심으로 강제**한다.

### 4.1 기본 패턴
`DEV_arm<ARM>_mm_<S5Rk>_<condition>_YYYYMMDD_HHMMSS__repN`

예시(Arm G, 동시기 비교 + replicates):
- `DEV_armG_mm_S5R0_before_rerun_preFix_YYYYMMDD_HHMMSS__rep1`
- `DEV_armG_mm_S5R0_before_rerun_preFix_YYYYMMDD_HHMMSS__rep2`
- `DEV_armG_mm_S5R2_after_postFix_YYYYMMDD_HHMMSS__rep1`
- `DEV_armG_mm_S5R2_after_postFix_YYYYMMDD_HHMMSS__rep2`

### 4.2 (옵션) 이미지 라운드/모델을 run_tag에 보조 표기
- 이미지 프롬프트/모델이 따로 움직일 때만 suffix 추가:
  - `...__imgS5R2`
  - `...__imgModelNanoBananaPro`

### 4.3 (권장) Cross-evaluation용 “평가 judge 버전” 표기

배경:
- “생성 프롬프트 개선 효과(Target 1)”를 주장하려면, before/after 산출물을 **동일 S5 validator prompt/version(고정 judge)** 으로 평가해야 합니다.
  (Canonical: `0_Protocol/05_Pipeline_and_Execution/S5R_Experiment_Power_and_Significance_Plan.md`)

원칙:
- 동일 `run_tag` 폴더 안에서 S5 validator를 서로 다른 judge 버전으로 여러 번 돌리면 산출물(`s5_validation__arm*.jsonl`, report)이 **덮어쓰기/혼합**될 수 있습니다.
  따라서 cross-evaluation 결과는 **별도 run_tag로 분리**하는 것을 권장합니다.

권장 패턴:
- `DEV_arm<ARM>_mm_<S5Rgen>_<condition>_YYYYMMDD_HHMMSS__repN__evalS5R<k>`
  - `S5Rgen`: 생성 프롬프트 라운드(콘텐츠 생성 조건)
  - `evalS5R<k>`: 평가에 사용한 S5 validator 라운드(고정 judge)

예시:
- `DEV_armG_mm_S5R0_before_rerun_preFix_20251229_120000__rep1__evalS5R2`
  - 의미: “S5R0 생성물”을 “S5R2 judge”로 평가한 결과 저장

---

## 5. 문서/논문(Methods/Results) 표기 규칙

- 본문에는 `vXX` 대신 **S5R 라운드**를 1차 표기한다.
- 부록/각주에 v↔S5R 매핑을 둔다.

예시:
- “We compared a contemporaneous baseline (**S5R0**) and a post-refinement condition (**S5R2**)…”
- Appendix: “S5R2 corresponds to S1 `v14` and S2 `v11`.”


