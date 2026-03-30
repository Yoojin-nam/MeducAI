# Handoff: 의학용어만 영어화 (문장/형식 불변) — S2 baseline + S2(repaired/regen) + AppSheet Export + Anki Export

작성일: 2026-01-07  
프로젝트 루트: `/path/to/workspace/workspace/MeducAI`

## 0) 목표(요구사항) 요약

사용자 요구:
- **이미 만들어진 Anki 문제에서 “문제 내용/형식은 전혀 바꾸지 않고” “의학용어만” 한글→영어로 바꾸기**
- 이 변경은 **Anki만이 아니라 AppSheet Export의 S2(baseline)와 S2(repaired/regen)에도 동일 적용**되어야 함
- 현재 상황: **Anki export는 “Regen된 S2(=repaired S2)”를 입력으로 사용하지 않는 경향**이 있어, AppSheet와 Anki 사이에 언어 정책이 어긋날 위험이 큼

핵심 성공 조건:
- `front/back/options` 텍스트에서 **의학용어만 영어로** (질병명/해부/소견/검사/병태생리 등)
- **문장 구조(조사/어미/문법)**, **포맷(줄바꿈/불릿/정답표기/HTML)**, **의미/카드 구조**는 불변
- baseline와 repaired(regen) 양쪽에 동일 정책 적용 → **QA/AppSheet/Anki 전부 일관**


## 1) 현재 코드/데이터 흐름 분석(중요 발견)

### 1.1 S2 “baseline” 파일 위치(예시)

실제 FINAL 실행 산출물 예:
- `2_Data/metadata/generated/FINAL_DISTRIBUTION/s2_results__s1armG__s2armG.jsonl`
  - 각 라인 = S2 record (entity 단위)
  - `anki_cards[]` 안에 `front/back/options` 포함

샘플에서 확인된 한글 의학용어 혼입 예:
- `"Answer: Dumping Syndrome (덤핑 증후군)"`
- `"Answer: 내탈장 (Internal Hernia)"`

→ 단순 용어 치환이 아니라 “의학용어만”을 영어화하면서 한국어 문장 골격은 유지해야 함.

### 1.2 AppSheet Export가 baseline + repaired S2를 모두 다루는 구조

파일:
- `3_Code/src/tools/final_qa/export_appsheet_tables.py`

중요 로직:
- `s2_results__*.jsonl` 을 baseline S2로 로드하여 `Cards.csv` 생성
- `s2_results__*__repaired.jsonl` 이 있으면 **카드별 regen 텍스트 인덱스**를 만들어 diff/regen 판단 및 컬럼 생성에 사용

코드 스니펫(참조):

```468:708:3_Code/src/tools/final_qa/export_appsheet_tables.py
def _build_s2_regenerated_index(s2_results_repaired_path: Path) -> Dict[str, Dict[str, str]]:
    """
    Build a per-card content index from repaired S2 results.

    Returns:
      card_uid -> {"front": str, "back": str}
    """
    out: Dict[str, Dict[str, str]] = {}
    for row in _read_jsonl(s2_results_repaired_path):
        group_id = row.get("group_id", "") or ""
        entity_id = row.get("entity_id", "") or ""
        if not group_id or not entity_id:
            continue
        anki_cards = row.get("anki_cards") or []
        for idx, c in enumerate(anki_cards):
            card_role = c.get("card_role", "") or ""
            if not card_role:
                continue
            card_type = c.get("card_type", "") or ""
            front = c.get("front", "") or ""
            back = c.get("back", "") or ""
            mcq_options = c.get("options") or []
            # ... (MCQ front formatting / md bold strip 등) ...
```

→ 따라서 “완벽하게 동일 변경”을 하려면 AppSheet Export에서도:
- baseline S2에서 쓰는 텍스트(=Cards.csv의 `front/back/options`)를 번역해야 하고
- repaired S2 인덱스가 비교하는 텍스트도 같은 정책으로 번역해야 함  
  (안 그러면 “regen 여부 판단”, “diff용 텍스트”가 언어 차이 때문에 깨질 수 있음)

### 1.3 Anki Export가 “repaired S2”를 직접 쓰지 않는 케이스 존재

파일(Anki 최종 통합 export 예):
- `3_Code/src/tools/anki/export_final_anki_integrated.py`

요약:
- `--s2_baseline` + `--s2_regen` 을 별도 입력으로 받음
- S5 decision에 따라 어떤 카드의 텍스트를 baseline vs regen에서 가져올지 결정

주의:
- 사용자 말대로 “Anki는 Regen된 S2 포함 안되어 있음”이라는 운영 상황이 있을 수 있음
  - 즉 실제 실행 플로우가 `export_final_anki_integrated.py`가 아닌 `3_Code/src/07_export_anki_deck.py` 중심일 수 있음(또는 baseline만 넣는 관행)
  - 다음 agent는 **현재 실제로 어떤 exporter를 쓰는지(배포 스크립트/명령)**부터 확인해야 함


## 2) 이미 추가/수정된 코드(현 상태)

### 2.1 번역 로직 모듈 (재사용 가능)

- `3_Code/src/tools/anki/translate_medical_terms_module.py`
  - `MedicalTermTranslator` 클래스
  - **개선된 SYSTEM_PROMPT** 포함(“의학용어만 번역”, “나머지 불변”, “불확실하면 유지” 등 안전 규칙)
  - `translate_s2_jsonl_file()` 제공: S2 JSONL 전체를 번역하여 새 JSONL 생성

### 2.2 CLI 래퍼(번역 스크립트)

- `3_Code/src/tools/anki/translate_medical_terms.py`
  - 위 모듈을 import하여 파일 단위 변환

### 2.3 실행 스크립트/가이드(기본)

- `3_Code/Scripts/translate_anki_medical_terms.sh`
- `3_Code/src/tools/anki/TRANSLATE_MEDICAL_TERMS_GUIDE.md`

### 2.4 기술적 주의점(중요)

`GeminiClient`는 JSON 응답 parsing helper 중심(`generate_json`)이라,
현재 번역은 **text-only 응답**이 필요하여 내부 멤버를 사용:
- `client._client.models.generate_content(...)`
- `client._types.GenerateContentConfig(...)`

→ 안정성/유지보수 관점에서 다음 agent가 할 일:
- `preprocess/gemini_utils.py`에 **공식적인 `generate_text()`** 같은 wrapper를 추가해 internal 접근 제거 권장


## 3) “완벽하게 동일 변경”을 위한 추천 아키텍처(중요)

두 가지 선택지 중 하나로 가는 게 안전함.

### 선택지 A: “파일 변환 후 기존 exporter 재사용” (가장 단순/리스크 낮음)

1) baseline S2 JSONL → 번역본 생성
2) repaired/regen S2 JSONL → 번역본 생성
3) AppSheet export를 번역본 S2들을 입력으로 돌리거나, `run_dir` 안에서 파일명을 exporter가 발견하도록 배치
4) Anki export도 번역본 S2(그리고 필요한 경우 regen용 번역본 S2)를 입력으로 사용

장점:
- 기존 exporter 로직을 거의 안 건드려도 됨
- AppSheet/Anki 모두 동일한 “번역된 S2”를 소스로 사용하므로 불일치 가능성이 낮음

주의:
- exporter들이 자동 glob로 파일을 잡기 때문에, 파일명 규칙을 맞추거나 CLI 옵션을 추가해야 함(현재 exporter는 s2 경로를 명시적으로 받지 않는 경우가 있음)

### 선택지 B: exporter 내부에 “번역 옵션”을 통합 (운영 편하지만 코드변경 큼)

AppSheet:
- `export_appsheet_tables.py`에 `--translate_med_terms` 같은 flag 추가
- `Cards.csv` 생성 직전에:
  - baseline 카드의 `front/back/options` 번역 적용
  - repaired 인덱스 빌드 시에도 동일 번역 적용

Anki:
- Anki exporter(`07_export_anki_deck.py` 혹은 `export_final_anki_integrated.py`)에 동일 flag 추가
- 노트 생성 직전 `front/back/options` 번역 적용
- (regen 텍스트 포함 여부가 exporter마다 다르므로) “regen 텍스트를 쓰는 경로”에도 번역 적용

장점:
- CLI 한 번에 해결(운영 편함)
단점:
- 카드별 diff/regen 판단이 텍스트 기반이면 **번역 적용 타이밍**이 중요해짐(동일 시점/동일 규칙 필수)


## 4) 다음 agent를 위한 실행 계획(차근차근)

### Step 0 — “현재 실제 운영 커맨드” 확인
- 어떤 파일로 Anki 덱을 만들고 있는지 확인:
  - `3_Code/src/07_export_anki_deck.py` 사용?  
  - `3_Code/src/tools/anki/export_final_anki_integrated.py` 사용?  
  - 어떤 run_tag 디렉토리/arm을 쓰는지 확인

### Step 1 — 번역 프롬프트/정확성 재검증
- `translate_medical_terms_module.py`의 SYSTEM_PROMPT는 “의학용어만 번역”을 강제하도록 작성됨
- QA를 위해 20~50 record 정도 샘플 변환 후:
  - 한국어 조사/문법 유지 여부
  - 의학용어 누락/오역 여부
  - 줄바꿈/불릿/정답표기 깨짐 여부
  - “이미 영어+한글 병기” 케이스(예: `Internal Hernia (내탈장)`)에서 원하는 동작 정의(한글 괄호 제거/유지?)

### Step 2 — 일괄 적용 전략 선택
- **권장: 선택지 A(파일 변환 후 exporter 재사용)**  
  이유: AppSheet도 baseline+repaired를 읽고, Anki도 baseline/regen 경로가 다양할 수 있어 “소스 파일을 통일”하는 게 제일 안전.

### Step 3 — AppSheet export에 적용
파일:
- `3_Code/src/tools/final_qa/export_appsheet_tables.py`

필요 작업(선택지 A라면):
- run_dir 안에 다음 파일들을 준비:
  - `s2_results__...jsonl` (번역본으로 교체하거나 번역본을 baseline로 인식하도록 명명)
  - `s2_results__...__repaired.jsonl` (번역본)

필요 작업(선택지 B라면):
- exporter에 flag 추가 + 카드 텍스트 번역을 카드 row 구성 직전에 수행
- `_build_s2_regenerated_index()`에서도 같은 번역을 적용해 비교 일관성 유지

### Step 4 — Anki export에 적용
현재 코드상 후보:
- `3_Code/src/07_export_anki_deck.py` (가이드 문서가 이걸 메인이라 말함)
- `3_Code/src/tools/anki/export_final_anki_integrated.py` (S5 decision 기반 baseline/regen 선택)

작업 방향:
- 실제로 “regen S2를 안 쓰는” 경로가 있다면, **regen S2 번역본을 만들어도 활용이 안 됨** → exporter를 바꾸거나, exporter에 regen S2 입력을 추가해야 함.
- 최소 요구: Anki에서 사용되는 모든 텍스트 소스(baseline든 regen이든)에 번역을 적용

### Step 5 — 성능/비용 개선(권장)
현재 방식은 “텍스트 덩어리마다 LLM 호출” → 비용/시간 큼.
가능하면:
- (1) 텍스트에서 한글 토큰/용어 후보를 추출 → unique set
- (2) 용어 리스트를 batch로 번역(사전/매핑 생성)  
  - 프로젝트에 `translation_map_v2.json` 계열/Tag translation JSON이 이미 존재함
- (3) 카드 텍스트에는 “용어 매핑 치환”만 수행  
→ 훨씬 빠르고 일관됨(용어 통일)


## 5) 바로 참고할 파일 목록(핵심)

- S2 baseline 예시:
  - `2_Data/metadata/generated/FINAL_DISTRIBUTION/s2_results__s1armG__s2armG.jsonl`
- AppSheet exporter:
  - `3_Code/src/tools/final_qa/export_appsheet_tables.py`
- Anki exporter(통합):
  - `3_Code/src/tools/anki/export_final_anki_integrated.py`
- (메인일 가능성 높은) Anki exporter 가이드:
  - `3_Code/src/tools/docs/ANKI_EXPORT_GUIDE.md`
- 번역 모듈/CLI:
  - `3_Code/src/tools/anki/translate_medical_terms_module.py`
  - `3_Code/src/tools/anki/translate_medical_terms.py`


## 6) 남은 TODO (다음 agent가 수행)

1. `export_appsheet_tables.py`에 번역 통합(또는 번역본 S2를 baseline/repaired로 인식시키는 운영 플로우 확정)
2. 실제 사용하는 Anki export 경로에서 “baseline/regen 모두” 번역 적용
3. 가능하면 `gemini_utils.py`에 `generate_text()` wrapper 추가(내부 멤버 접근 제거)
4. 비용/시간 최적화: 용어 set 기반 batch 번역 + 치환


