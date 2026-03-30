---
date: 2026-01-01
context: OptionC + S4 repaired integration, S4 quota exhaustion / key-rotation confusion, metrics reconciliation
repo: MeducAI
---

### 요약 (한 줄 결론)
- 오늘 발생한 비용/진행률 괴리는 **S4 대량 생성 중 429(quota exceeded) 실패가 폭증**했고, 동시에 **동일 이미지 키에 대한 중복 성공 호출(덮어쓰기)**가 누적되면서 생김.

---

### 1) Option C + S4 repaired 통합 관련 (동작/버그/패치)

#### 1.1. 증상
- `05c_option_c_orchestrator.py`에서 `--include_s4`를 켜도 S4 repaired가 안 돌고 `s4_image_manifest__armG__repaired.jsonl`이 생성되지 않는 케이스 발생.
- `s5_validation__armG__postrepair.jsonl`에 target group 레코드가 남지 않는 케이스 발생(사용자가 Ctrl+C로 S5 중단한 경우 포함).

#### 1.2. 원인
- baseline S5 JSONL의 카드 레코드에서 `entity_id`가 없는 형태가 존재하여, Option C가 S4 타겟 추출을 0으로 계산할 수 있었음.

#### 1.3. 적용된 코드 변경
- 파일: `3_Code/src/05c_option_c_orchestrator.py`
- 변경: S4 타겟 추출 시 `entity_id`가 없으면 `card_id` 포맷(`{entity_id}__{card_role}__{idx}`)에서 `entity_id`를 파싱해 fallback.

#### 1.4. 운영 체크 (dry-run로 S4 타겟 확인)
- dry-run에서 아래가 0이 아니면 S4 repaired가 정상적으로 “돌 준비”가 된 상태:
  - `[OptionC] S4 targets: entities=... roles=...`

---

### 2) “진행률은 큰데 실제 이미지 파일이 적다” (S4 spec/manifest/files 정합성)

#### 2.1. 진행률 10570의 출처
- `FINAL_DISTRIBUTION` run_tag에서:
  - `2_Data/metadata/generated/FINAL_DISTRIBUTION/s3_image_spec__armG.jsonl` 라인 수 = **10570**

#### 2.2. S4 manifest vs 실제 이미지 파일
- `FINAL_DISTRIBUTION` run_tag에서:
  - `s4_image_manifest__armG.jsonl` 라인 수 = **3852**
  - 실제 `images/` 파일 수(존재하는 jpg/png) = **245**
  - manifest 중 `generation_success=true` + 파일 존재 = **245**
  - manifest가 참조하는 파일이 디스크에 없는 엔트리 = **3607**
- 결론: `3850/10570`은 “저장 성공 이미지 수”가 아니라 **처리/시도 카운트(실패 포함)**와 더 유사.

---

### 3) 비용이 새는 구간: S4 실패 원인(429 폭증)

#### 3.1. 실패 원인 집계 (metrics 기준)
- 파일: `2_Data/metadata/generated/FINAL_DISTRIBUTION/logs/s4_image_metrics.jsonl`
- 집계 결과:
  - `ok=true` 호출: **498**
  - `ok=false` 호출: **3688**
  - 실패 bucket:
    - **429 RESOURCE_EXHAUSTED / “You exceeded your current quota…”**: **3686**
    - **503 UNAVAILABLE / deadline expired**: **2**
- 결론: 실패의 거의 전부가 **429 quota exceeded**.

> NOTE: 이 429는 “RPD 소진”만이 아니라, Google GenAI 쪽 **프로젝트/계정/모델 단위 quota/빌링 상태**에 의해 발생할 수 있음.

---

### 4) “ok 호출 498인데 실제 파일 245” (중복 성공 호출 + 최종 실패)

#### 4.1. 조인 기준
- metrics / manifest를 `(run_tag, spec_kind, group_id, entity_id, card_role)` 키로 조인

#### 4.2. 결과 (FINAL_DISTRIBUTION armG)
- metrics:
  - `ok_calls=498`
  - `ok_unique_keys=256`
  - `ok_duplicate_calls=242`  ← **같은 키로 2번 이상 성공(덮어쓰기/재실행)**
- manifest(최신):
  - metrics-ok unique 256개 중
    - `manifest success=true`: **245**
    - `manifest success!=true`: **11**  ← **API ok로 기록됐지만 최종적으로는 실패 처리된 키**
    - `manifest missing`: **0**
- 파일 존재:
  - `manifest success=true` 245개는 전부 파일 존재(0 missing)

#### 4.3. 중복 성공 호출의 원인(오늘 데이터 기준)
- `s3_image_spec__armG.jsonl` 자체는 키 중복이 **0개**(spec 중복이 원인은 아님).
- 중복 성공 호출은 다음 가능성이 큼:
  - **동일 run_tag로 S4를 여러 번 재실행**(부분 성공 후 재실행 포함)
  - 실행 환경/프롬프트가 바뀌어 같은 키를 다시 생성(실제 `prompt_hash`가 달라지는 케이스 관측)
  - 파일이 없다고 판단되는 상태에서 재생성(폴더 이동/삭제/다른 경로 실행 등)
- 운영 권장:
  - 대량 S4 재개는 **항상 `--resume` 우선**(실패한 것만 재시도)
  - 프롬프트/스펙이 바뀌면 **run_tag를 새로**(같은 run_tag 재사용 시 중복 호출 비용 증가)

---

### 5) “키 로테이션이 이상하다 / 특정 key만 과도 호출” (사용자 관측과 로컬 상태의 불일치)

#### 5.1. 로컬 상태(Repo에 기록된 rotator state)
- 파일: `2_Data/metadata/.api_key_status.json`
- 이 파일은 ApiKeyRotator의 **로컬 추정 상태**(실제 콘솔 usage의 SSOT 아님).
- 오늘 시점에 `GOOGLE_API_KEY_1..14`가 모두 `is_active=false`로 찍히는 상태가 확인됨.

#### 5.2. 사용자 관측
- Google API 콘솔에서:
  - “모든 key가 RPD 소진이거나 호출되지도 않았다”
  - “특정 Key만 엄청 호출되었다”

#### 5.3. 가능한 원인 가설(우선순위)
- **(H1) .env에 서로 다른 번호 변수들이 실제로는 같은 API key 값을 복사해 둔 경우**
  - 로테이터는 14개 key를 “다른 슬롯”으로 보지만, 콘솔에서는 **동일 key**로만 집계되어 “특정 key만 과도 호출”처럼 보임.
- **(H2) 실행 프로세스 환경에서 일부 키가 로드되지 않았거나(빈 값/권한/제약), START_INDEX로 특정 구간만 반복 사용**
  - `API_KEY_ROTATOR_START_INDEX` / `GOOGLE_API_KEY_START_INDEX` 설정 여부 확인 필요.
- **(H3) 429의 원인이 RPD가 아니라 ‘프로젝트/계정/빌링/모델’ quota인 경우**
  - 이런 경우 콘솔의 “RPD”와 무관하게 429가 발생할 수 있고, 여러 키로 돌려도 동일 프로젝트 quota에 막힐 수 있음.

#### 5.4. 확인 체크리스트(권장)
- `.env`에서 `GOOGLE_API_KEY_1..N` 값이 **서로 다른지**(중복 여부) 확인
- `.env`에서 `API_KEY_ROTATOR_START_INDEX` / `GOOGLE_API_KEY_START_INDEX` 값 확인
- Google GenAI 콘솔에서 **API key별**로 usage가 분리되는지(프로젝트 단위 aggregate인지) 확인
- 429 에러 문자열이 “RPD limit”인지 “billing/quota exceeded”인지 메시지 원문 확인

---

### 6) 산출물/리포트(오늘 생성)
- 실제 존재 이미지 인덱스(armG, FINAL_DISTRIBUTION):
  - `2_Data/metadata/generated/FINAL_DISTRIBUTION/reports/s4_existing_images__armG.md`
- metrics vs manifest 정합 리포트:
  - `2_Data/metadata/generated/FINAL_DISTRIBUTION/reports/s4_metrics_vs_manifest_reconcile__armG.md`


