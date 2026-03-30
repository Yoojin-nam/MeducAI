# 공동 1저자 [Engineer]에게 보내는 Multi-Agent 설계 자문 요청

**작성일**: 2025-12-20  
**수신인**: [Engineer] (공동 1저자)  
**목적**: Multi-Agent 설계를 통한 오류 제어 실현 가능성 자문 요청

---

## 1. 현재 상황 및 문제 정의

### 1.1 배포 요구사항 (통계적 기준)

**목표**: FINAL 생성 6000문항 배포를 위한 통계적 검증

**Acceptance Sampling 규칙:**
- **샘플 크기**: n = 838 cards (PPS + 층화 샘플링)
- **Acceptance Criterion**: blocking error **≤ 2건** → PASS
- **통계적 보장**: blocking error rate < 1%를 **one-sided 99% confidence**로 보장
- **통계 방법**: Clopper–Pearson upper bound (Acceptance sampling)

**Blocking Error 정의:**
- Accuracy = 0.0 (치명적 오류 또는 오개념 유발 가능)
- 판정 기준: 전문의 최종 판정

### 1.2 현재 상황

**관찰된 결과:**
- **샘플**: 24문제 중
- **Blocking Error**: 2건
  - 1건: 이미지 생성 문제로 해결 가능 (non-critical)
  - 1건: **Critical error** (내용 오류)

**문제:**
- 현재 에러율: 2/24 = 8.3%
- 목표 에러율: < 1% (838개 샘플에서 ≤ 2건)
- **Critical error 1건이 전체 배포를 막고 있음**

---

## 2. 제안: Multi-Agent 설계를 통한 오류 제어

### 2.1 제안 배경

현재 파이프라인은 **순차적 구조**로, S2 (카드 생성) 이후 자동 검증 및 재생성 메커니즘이 없습니다. 

**제안**: S2 생성 이후 **검토 LLM (Review Agent)**을 추가하여:
1. 생성된 카드의 품질 평가
2. Blocking error 자동 탐지
3. 피드백 생성 및 S2 재생성 유도
4. 반복적 개선 루프 (최대 3회)

### 2.2 제안된 구조

```
현재 구조:
S1 (LLM) → S2 (LLM) → S3 (코드) → S4 (LLM)

제안 구조 (Multi-Agent):
S1 (LLM) → S2 (생성 Agent) ↔ 검토 LLM (검토 Agent) → S3 (코드) → S4 (LLM)
              ↑                    ↓
              └── 피드백 루프 ──────┘
```

**검토 Agent 역할:**
- 생성된 카드의 품질 평가 (quality_score: 0.0-1.0)
- Blocking error 탐지 및 분류
- 구체적인 피드백 생성 (JSON 형식)
- 재생성 필요 여부 판단 (revision_needed: true/false)

**피드백 루프:**
- 검토 Agent가 blocking error 또는 품질 문제 발견
- 피드백을 S2 Agent에 전달
- S2 Agent가 피드백을 반영하여 재생성
- 최대 3회 반복 또는 품질 기준 충족 시 종료

---

## 3. 실현 가능성 및 기술적 요구사항

### 3.1 현재 파이프라인 구조

**프롬프트 기반 제어:**
- S1, S2는 **프롬프트로 완전히 제어**됨
- 프롬프트 파일 위치: `3_Code/prompt/`
- 프롬프트 템플릿 변수 사용: `{entity_name}`, `{cards_for_entity_exact}` 등

**코드 구조:**
- 메인 실행 스크립트: `3_Code/src/01_generate_json.py`
- LLM 호출 함수: `call_llm()` (공통 모듈)
- 프롬프트 로딩: `load_prompt_bundle()` (프롬프트 번들 시스템)

### 3.2 필요한 구현 작업

**프롬프트 설계 (프로그래머 도움 없이 가능):**
- ✅ 검토 LLM용 프롬프트 작성 (`S2_REVIEW_SYSTEM__v1.md`, `S2_REVIEW_USER__v1.md`)
- ✅ S2 프롬프트에 피드백 반영 로직 추가
- ✅ 피드백 형식 정의 (JSON 스키마)

**코드 수정 (프로그래머 도움 필요):**
- ⚠️ 피드백 루프 구현 (while/for 루프)
- ⚠️ 검토 LLM 호출 함수 추가
- ⚠️ 피드백 파싱 및 S2 프롬프트에 전달
- ⚠️ 반복 제어 로직 (최대 3회, 종료 조건)

**예상 코드 변경량:**
- `01_generate_json.py`: 약 50-100줄 추가/수정
- 프롬프트 로딩 부분: 약 10-20줄 수정

---

## 4. 프로그램 구조 상세 설명

### 4.1 전체 파이프라인 구조

```
MeducAI Pipeline:
├── S0: QA / Model Comparison (6-arm factorial)
├── S1: Group-level Structuring (LLM)
│   └── Output: master_table + entity_list (JSON)
├── S2: Entity-level Card Generation (LLM)
│   └── Input: S1 output
│   └── Output: anki_cards (Q1, Q2, Q3 per entity)
├── S3: Selection & QA Gate (코드, LLM 없음)
│   └── Policy resolution, image spec compilation
├── S4: Image Generation (LLM)
│   └── Input: S3 image specs
│   └── Output: PNG images
└── S5: Export (PDF/Anki packaging)
```

### 4.2 핵심 설계 원칙

**책임 분리 (Separation of Concerns):**
- 각 단계는 명확히 분리된 책임
- LLM은 "생성"만 담당, "결정"은 코드에서 수행
- Fail-Fast 정책: 경계 위반 시 즉시 실패

**프롬프트 기반 제어:**
- 모든 LLM 동작은 프롬프트로 제어
- 프롬프트는 버전 관리됨 (`_registry.json`)
- 프롬프트 변경은 코드 수정 없이 가능

**Canonical 문서 시스템:**
- 모든 정책과 설계는 문서로 고정 (Canonical)
- 코드는 문서의 구현체
- IRB/논문에서 문서를 직접 인용 가능

### 4.3 코드 구조

**메인 실행 스크립트:**
```
3_Code/src/01_generate_json.py
├── process_single_group()  # 그룹별 처리
│   ├── Stage 1 (S1): Group-level structuring
│   │   ├── 프롬프트 로드 (S1_SYSTEM, S1_USER_GROUP)
│   │   ├── LLM 호출 (call_llm())
│   │   └── 검증 (validate_stage1())
│   │
│   └── Stage 2 (S2): Entity-level card generation
│       ├── 각 entity별로 반복
│       ├── 프롬프트 로드 (S2_SYSTEM, S2_USER_ENTITY)
│       ├── LLM 호출 (call_llm())
│       └── 검증 (validate_stage2())
│
├── call_llm()  # 공통 LLM 호출 함수
│   ├── Provider별 클라이언트 관리
│   ├── Retry/backoff 처리
│   └── 로깅 및 메타데이터 기록
│
└── validate_stage2()  # S2 출력 검증
    ├── 스키마 검증
    ├── 카드 수 검증 (exact N)
    └── 필수 필드 검증
```

**프롬프트 시스템:**
```
3_Code/prompt/
├── _registry.json  # 프롬프트 파일 매핑
├── S1_SYSTEM__v10.md
├── S1_USER_GROUP__v11.md
├── S2_SYSTEM__v7.md
├── S2_USER_ENTITY__v7.md
└── S4_*.md (이미지 생성 프롬프트)
```

**프롬프트 로딩:**
```python
# 프롬프트 번들 로드
bundle = load_prompt_bundle(...)
P_S2_SYS = bundle["prompts"]["S2_SYSTEM"]
P_S2_USER_T = bundle["prompts"]["S2_USER_ENTITY"]

# 템플릿 변수 포맷팅
s2_user = safe_prompt_format(
    P_S2_USER_T,
    entity_name=entity_name,
    cards_for_entity_exact=expected_n,
    master_table=master_table_md,
    ...
)
```

### 4.4 데이터 흐름

**S1 → S2 흐름:**
```
S1 Output (stage1_struct__arm{A}.jsonl):
{
  "group_id": "G0123",
  "entity_list": [
    {"entity_id": "G0123__E01", "entity_name": "Miliary pattern"}
  ],
  "master_table_markdown_kr": "..."
}
    ↓
S2 Input: entity_list의 각 entity
    ↓
S2 Output (s2_results__arm{A}.jsonl):
{
  "entity_id": "G0123__E01",
  "anki_cards": [
    {"card_role": "Q1", "front": "...", "back": "..."},
    {"card_role": "Q2", "front": "...", "back": "..."},
    {"card_role": "Q3", "front": "...", "back": "..."}
  ]
}
```

**제안: S2 → 검토 LLM → S2 재생성 흐름:**
```
S2 Output
    ↓
검토 LLM Input: anki_cards 배열
    ↓
검토 LLM Output (feedback JSON):
{
  "quality_score": 0.75,
  "blocking_errors": ["Critical: Incorrect medical fact in Q1"],
  "suggestions": ["Revise Q1 front to clarify terminology"],
  "revision_needed": true
}
    ↓
S2 재생성 (피드백 포함):
- S2 프롬프트에 previous_feedback 변수 추가
- S2가 피드백을 반영하여 재생성
```

---

## 5. Multi-Agent 설계의 장점

### 5.1 오류 제어 효과

**예상 효과:**
- **Critical error 자동 탐지**: 검토 Agent가 blocking error 사전 발견
- **자동 재생성**: 피드백 반영으로 오류 수정 가능성 증가
- **품질 향상**: 반복적 개선으로 평균 품질 점수 상승

**통계적 기대:**
- 현재: 24개 중 2개 에러 (8.3%)
- 목표: 838개 중 ≤ 2개 에러 (< 0.24%)
- **Multi-Agent 도입 시**: Critical error 발생률 감소 기대

### 5.2 연구적 가치

**학술적 기여:**
- Multi-Agent LLM 시스템의 교육 콘텐츠 생성 적용
- 피드백 루프를 통한 품질 개선 메커니즘 검증
- Human-in-the-loop vs Multi-Agent 비교 가능

**논문 포인트:**
- "Collaborative LLM agents with iterative feedback loops"
- "Automatic quality control through agent-based review"

---

## 6. 자문 요청 사항

### 6.1 기술적 실현 가능성

1. **구현 복잡도 평가**
   - 현재 파이프라인 구조에서 피드백 루프 구현의 기술적 난이도
   - 예상 개발 시간 및 리소스

2. **성능 및 비용 고려**
   - 검토 LLM 추가 호출로 인한 API 비용 증가
   - 반복 재생성으로 인한 지연 시간
   - 최적 반복 횟수 및 종료 조건

3. **안정성 및 신뢰성**
   - 검토 Agent의 오탐지(false positive) 가능성
   - 피드백 품질 보장 메커니즘
   - 무한 루프 방지 전략

### 6.2 설계 검토

1. **Multi-Agent 아키텍처 설계**
   - 에이전트 간 통신 프로토콜
   - 피드백 형식 및 스키마
   - 상태 관리 및 추적성

2. **통합 전략**
   - 기존 파이프라인과의 통합 방법
   - 하위 호환성 유지
   - 점진적 도입 가능 여부

---

## 7. Git Repository 정보

**Repository URL:**
```
https://github.com/Yoojin-nam/MeducAI.git
```

**Repository 구조:**
```
MeducAI/
├── 0_Protocol/          # Canonical 문서 (정책, 설계)
├── 1_Secure_Participant_Info/  # 참가자 정보 (제한 접근)
├── 2_Data/              # 데이터 및 메타데이터
├── 3_Code/              # 소스 코드
│   ├── src/            # 메인 스크립트
│   │   └── 01_generate_json.py  # S1/S2 실행
│   └── prompt/         # LLM 프롬프트
├── 6_Distributions/     # 배포용 산출물
└── README.md           # 프로젝트 개요
```

**주요 문서 위치:**
- 파이프라인 설계: `0_Protocol/05_Pipeline_and_Execution/Pipeline_Canonical_Specification.md`
- QA 프레임워크: `0_Protocol/06_QA_and_Study/QA_Framework.md`
- Multi-Agent 분석: `0_Protocol/06_QA_and_Study/Study_Design/Multi_Agent_Classification_Analysis.md`
- Multi-Agent 설계 가능성: `0_Protocol/06_QA_and_Study/Study_Design/Multi_Agent_Design_Feasibility_Analysis.md`

**Git 접근:**
- 현재 모든 작업은 Git에 커밋되어 있습니다
- **GitHub ID를 알려주시면 repository에 collaborator로 초대하겠습니다**

---

## 8. 다음 단계

### 8.1 즉시 가능한 작업

1. **프롬프트 설계** (프로그래머 도움 없이)
   - 검토 LLM 프롬프트 작성
   - 피드백 형식 정의
   - S2 프롬프트 수정

2. **프로토타입 테스트** (수동)
   - 검토 LLM 수동 실행
   - 피드백 품질 검증
   - 재생성 효과 확인

### 8.2 협업 필요 작업

1. **코드 구현**
   - 피드백 루프 로직
   - 검토 LLM 통합
   - 반복 제어 메커니즘

2. **검증 및 테스트**
   - 통합 테스트
   - 성능 평가
   - 오류율 개선 검증

---

## 9. 연락처 및 협업

**Repository Owner:**
- GitHub: Yoojin-nam
- Email: [email-redacted]

**협업 요청:**
- GitHub ID를 알려주시면 repository에 collaborator로 초대하겠습니다
- 코드 리뷰 및 설계 검토 협의 가능
- 실시간 협업 (GitHub Issues, Pull Requests) 가능

---

## 10. 요약

**현재 상황:**
- 6000문제 배포를 위해 838개 샘플에서 blocking error ≤ 2건 필요
- 현재 24개 샘플에서 2건 발견 (1건 critical)
- Critical error 1건이 전체 배포를 막고 있음

**제안:**
- Multi-Agent 설계 (S2 생성 Agent ↔ 검토 Agent 피드백 루프)
- 자동 오류 탐지 및 재생성 메커니즘
- 통계적 오류율 개선 기대

**요청:**
- 기술적 실현 가능성 자문
- 설계 검토 및 개선 제안
- 구현 협업 가능 여부

**Git Repository:**
- https://github.com/Yoojin-nam/MeducAI.git
- GitHub ID 알려주시면 collaborator로 초대

---

**감사합니다. 검토 및 자문 부탁드립니다.**

