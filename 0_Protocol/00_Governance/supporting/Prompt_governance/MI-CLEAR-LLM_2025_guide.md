MI-CLEAR-LLM_2025 문서를 분석하여, MeducAI 프로젝트의 Lead Research Engineer로서 MI-CLEAR-LLM의 핵심을 구조적이고 실행 가능한 형태로 정리한 Markdown 문서로 변환했습니다.

이 문서는 **재현 가능성(Reproducibility)**과 **투명성(Transparency)**을 엔지니어링 관점에서 강조하며, 프로젝트의 모든 단계(S0 QA, S1 Full-scale)에서 반드시 준수해야 하는 체크리스트 역할을 합니다.

---

# MI-CLEAR-LLM v2.0 요약: 엔지니어링 가이드라인

**Subtitle:** MInimum reporting items for CLear Evaluation of Accuracy Reports of Large Language Models in healthcare (LLM 정확도 평가 보고를 위한 최소 항목)
**Scope:** MeducAI 프로젝트 (S0/S1) 전체 Pipeline
**Focus:** 재현성(Reproducibility), 투명성(Transparency), 감사 가능성(Auditability)

---

## 1. 🎯 핵심 목표 및 배경

LLM 연구 보고의 일관성 및 투명성 부족 문제를 해결하기 위해 제시되었으며, 특히 **API 사용 및 Self-managed 모델**에 대한 보고 항목을 업데이트했습니다.

**MI-CLEAR-LLM의 초점:** LLM이 어떻게 **지정(specified), 접근(accessed), 적용(adapted), 테스트(applied)** 되었는지 보고하는 것. 이는 모델 출력에 영향을 미치는 방법론적 요소에 특별히 주의를 기울입니다.

---

## 2. 🧠 모델 식별 (Model Identification)

모델 성능은 버전, 환경, 학습 데이터에 따라 달라지므로, 사용된 모델을 명확하게 특정해야 합니다.

| 항목 | 요구 사항 | MeducAI 적용 |
| :--- | :--- | :--- |
| **모델 이름/버전** | 모델의 이름, 개발사, 정확한 버전 (snapshot 포함 권장) | Step01 (`01_generate_json.py`)에서 `arm_config`를 통해 모델명 고정 및 `metadata.model_version_stageX`에 기록 |
| **접근 일자** | 쿼리가 실행된 정확한 날짜 (모델이 수시로 업데이트될 수 있으므로) | `metadata.timestamp`와 `run_tag`에 실행 날짜/시간 기록 |
| **지식 Cutoff Date** | 모델의 학습 데이터 마감 날짜 (가능한 경우) | 프로젝트 README 및 `run_report.jsonl`에 명시 |
| **Self-Managed** | (해당 시) 모델 아키텍처 수정 사항, 가중치 출처, **Commit Hash** 또는 Release Tag 명시 | (`Arm F` 또는 `Open Source LLM` 사용 시) `inputs_manifest.json`에 **Git Commit Hash** 기록 |
| **모델 공유** | (권장) 실행 가능한 형태로 공용 저장소에 업로드 및 URL 제공 |  |

---

## 3. 🖥️ 모델 접근 모드 (Model Access Mode)

접근 모드는 LLM의 성능에 영향을 미치므로 명확히 보고되어야 합니다.

| 접근 모드 | 특징 | MI-CLEAR-LLM 준수 로직 |
| :--- | :--- | :--- |
| **Web-based Chatbot** | 제한된 사용자 정의, 불투명한 시스템 기능, 세션 내 **컨텍스트 메모리** 사용 | **MeducAI에서는 사용 금지** (재현성 및 변동성 문제) |
| **API Access** | 각 쿼리를 **독립적인 호출**로 처리, 맞춤형 구축 용이 | **MeducAI의 표준.** Step01 (`call_llm`)은 각 그룹/엔티티 생성을 독립적인 API 호출로 처리하여 **컨텍스트 누수 방지** |
| **Self-Managed Local** | 최대 투명성/유연성, 데이터 프라이버시 | (해당 시) **하드웨어 사양**, **처리 시간**, **인프라 요구사항**을 보고서에 명시 |

---

## 4. 🛠️ 모델 적응 전략 (Model Adaptation & Prompt Optimization)

사용된 모든 적응 전략(Adaptation Strategy)과 프롬프트 최적화(Prompt Optimization)는 구체적으로 기술되어야 합니다.

| 항목 | 요구 사항 | MeducAI 적용 |
| :--- | :--- | :--- |
| **전략 명확화** | Non-parametric (RAG, Prompting) vs. Parametric (Fine-tuning) 명확히 구분 | **Arm Configuration** (`A-F`)을 통해 RAG/Thinking **Non-parametric** 전략을 명시적 실험 변수로 고정 |
| **프롬프트 투명성** | **전체 텍스트** (System Prompt 포함)를 독자가 복사-붙여넣기 가능한 형태로 제공 | `3_Code/src/PROMPT_STAGE_X_SYSTEM/USER` 변수에 전체 텍스트 보관. Step01 실행 시 `metadata.prompt_hash`에 해시 기록 |
| **실패 보고 (권장)** | 만족스럽지 않은 프롬프트 변형 또는 최적화 시도 기록 | 프롬프트/설정 변경 시 **버전 관리(vX.X)** 및 변경 사유 명시 (Commit Log) |
| **명시적 전략** | Chain-of-Thought (CoT), Few-shot, Reflection 등 사용 시 명시 | **Arm C, D, E**에서 Thinking/CoT를 명시적으로 활성화 |

---

## 5. 🎲 비확정성 관리 (Stochasticity Management)

LLM의 고유한 무작위성(Stochasticity)을 관리하는 방식은 재현성(Reproducibility)에 매우 중요합니다.

| 항목 | 요구 사항 | MeducAI 적용 |
| :--- | :--- | :--- |
| **Temperature 값** | 사용된 **Temperature 값** 명시 (낮을수록 결정론적) | Stage-wise env vars로 고정: `TEMPERATURE_STAGE1/2`(S1/S2: `01_generate_json.py`), `TEMPERATURE_STAGE4`(S4: `04_s4_image_generator.py`), `TEMPERATURE_STAGE5`(S5: `05_s5_validator.py`). 각 실행 산출물/메트릭에 사용된 설정을 기록 |
| **반복 쿼리 횟수** | 단일 쿼리 또는 **반복 쿼리 횟수** 명시 | **MeducAI는 단일 쿼리** (API access). `retries=3` 로직은 **에러 복구**용이며, Stochasticity 관리가 아님을 명시 |
| **일관성 평가** | (반복 시) 응답 일관성 평가 (e.g., Fleiss’ kappa, CV) | S0 QA의 **Editing Time** 측정은 간접적으로 일관성 부족으로 인한 워크로드 증가를 반영 |
| **Greedy Search** | (Self-managed 시) Greedy Search Decoding 적용 등 결정론적 설정 명시 | (`Arm F` 등) 모델 Inference 시 결정론적 설정을 사용하고 `run_report`에 기록 |

---

## 6. 🛡️ 테스트 데이터 독립성 (Test Data Independence)

데이터 누수(Data Leakage)로 인한 성능 과대평가를 방지해야 합니다.

| 항목 | 요구 사항 | MeducAI 적용 |
| :--- | :--- | :--- |
| **데이터 분리** | 테스트 데이터와 모델 적응/프롬프트 개발에 사용된 데이터 간의 독립성 | **S0 QA**는 Prompt Development Set (`20 groups` 중 일부)을 사용하고, **S1 Full-scale**은 나머지 **전체 데이터셋**을 사용하여 데이터 독립성 보장 |
| **평가자 눈가림** | 모델 적응에 참여한 연구자가 테스트 데이터에 눈가림(Blinding) 처리되었는지 명시 | S0 QA **평가자(Rater)**는 어떤 Arm이 어떤 모델/설정인지 **완전 눈가림(Full Rater Blinding)** 처리 |
| **온라인 소스** | 테스트 데이터가 온라인에서 수집된 경우, **URL, 접근성, 원본 유무** 명시 | EDA 문서 (`EDA_Decision_Interpretation.md`)에 커리큘럼 데이터 소스(공식 수련 목표)의 독립성 명시 |

---

## 7. 🚀 실행 (Prompt Execution)

쿼리 실행 방식은 투명해야 합니다.

| 항목 | 요구 사항 | MeducAI 적용 |
| :--- | :--- | :--- |
| **API 독립성** | API 사용 시, 쿼리가 **독립적인 호출**로 제출되었는지 명시 | Step01 (`01_generate_json.py`)은 각 그룹/엔티티를 독립된 API 트랜잭션으로 실행 |
| **실험 스크립트** | (권장) **전체 실험 스크립트**를 부록으로 제공 (프롬프트, 설정, 하이퍼파라미터 포함) | `run_s0_smoketest_6arm.py`와 `01_generate_json.py`를 **Canonical Runner 및 Source**로 지정 |

---

## 8. ✅ MI-CLEAR-LLM v2.0 적용 최종 점검

| 항목 | 확인 사항 | 상태 |
| :--- | :--- | :--- |
| **Mode/Arm Logging** | `output_*.jsonl`에 `run_tag`, `mode`, `arm`, `prompt_hash`가 기록되었는가? | **✅ 완료** |
| **Stochasticity Fixed** | `TEMPERATURE_STAGE1/2/4/5`가 고정되었는가? | **✅ 완료** |
| **Data Independence** | S0 (Adaptation)와 S1 (Test) 데이터셋이 논리적으로 분리되었는가? | **✅ 완료** |
| **Full Blinding** | QA 평가자가 Arm 정보에 대해 눈가림 처리되었는가? | **✅ 완료** |
| **Cost/Latency** | `QA Framework v1.6`에 따라 시스템 메트릭이 결과에 통합되었는가? | **✅ 완료** (다음 작업: Summary 스크립트 정합) |