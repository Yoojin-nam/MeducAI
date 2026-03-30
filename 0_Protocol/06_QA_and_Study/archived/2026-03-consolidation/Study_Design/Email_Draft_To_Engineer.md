# [Engineer]에게 보내는 이메일 초안

---

**제목**: MeducAI Multi-Agent 설계 자문 요청 - 오류 제어를 위한 피드백 루프 구현

---

안녕하세요, [Engineer]님.

6000문제 배포를 위한 통계적 검증 과정에서 문제가 발생하여 Multi-Agent 설계를 통한 오류 제어 방안을 검토 중입니다. 기술적 실현 가능성과 설계 검토를 위해 자문을 요청드립니다.

## 현재 상황

**배포 요구사항:**
- 6000문제 배포를 위해 **838개 샘플에서 blocking error ≤ 2건** 필요
- 통계적 보장: blocking error rate < 1% (one-sided 99% confidence, Clopper–Pearson)

**현재 문제:**
- 24개 샘플 평가 결과: **blocking error 2건 발견**
  - 1건: 이미지 생성 문제 (해결 가능)
  - **1건: Critical error (내용 오류)**
- 현재 에러율: 8.3% → 목표: < 0.24%
- Critical error 1건이 전체 배포를 막고 있음

## 제안: Multi-Agent 설계를 통한 오류 제어

현재 파이프라인은 순차적 구조(S1 → S2 → S3 → S4)로, S2 카드 생성 이후 자동 검증 메커니즘이 없습니다.

**제안 구조:**
```
S2 (생성 Agent) ↔ 검토 LLM (검토 Agent) → S3
     ↑                    ↓
     └── 피드백 루프 ──────┘
```

**검토 Agent 역할:**
- 생성된 카드의 품질 평가 및 blocking error 자동 탐지
- 구체적인 피드백 생성 (JSON 형식)
- 재생성 필요 여부 판단

**피드백 루프:**
- 검토 Agent가 오류 발견 → 피드백 생성
- S2 Agent가 피드백 반영하여 재생성
- 최대 3회 반복 또는 품질 기준 충족 시 종료

## 프로그램 구조 요약

**현재 파이프라인:**
- **S1**: Group-level 구조화 (LLM) → master_table + entity_list
- **S2**: Entity-level 카드 생성 (LLM) → anki_cards (Q1, Q2, Q3)
- **S3**: 선택 및 QA gate (코드, LLM 없음)
- **S4**: 이미지 생성 (LLM)

**핵심 설계 원칙:**
- 프롬프트 기반 제어: 모든 LLM 동작은 프롬프트로 제어 (`3_Code/prompt/`)
- 책임 분리: 각 단계는 명확히 분리된 책임
- Fail-Fast: 경계 위반 시 즉시 실패

**코드 구조:**
- 메인 실행: `3_Code/src/01_generate_json.py`
  - `process_single_group()`: 그룹별 처리
  - `call_llm()`: 공통 LLM 호출 함수
  - `validate_stage2()`: S2 출력 검증
- 프롬프트 시스템: `3_Code/prompt/_registry.json`에 매핑
- 프롬프트 템플릿 변수: `{entity_name}`, `{cards_for_entity_exact}` 등

**필요한 구현:**
- 검토 LLM 호출 함수 추가
- 피드백 루프 구현 (while/for 루프)
- 피드백 파싱 및 S2 프롬프트에 전달
- 예상 코드 변경: 약 50-100줄 (01_generate_json.py)

## 자문 요청 사항

1. **기술적 실현 가능성**
   - 현재 구조에서 피드백 루프 구현의 난이도
   - 예상 개발 시간 및 리소스
   - 성능/비용 고려사항

2. **설계 검토**
   - Multi-Agent 아키텍처 설계 적절성
   - 에이전트 간 통신 프로토콜
   - 통합 전략 및 하위 호환성

3. **협업 가능 여부**
   - 구현 협업 가능 여부
   - 코드 리뷰 및 설계 검토

## Git Repository

**Repository:** https://github.com/Yoojin-nam/MeducAI.git

**주요 문서:**
- 파이프라인 설계: `0_Protocol/05_Pipeline_and_Execution/Pipeline_Canonical_Specification.md`
- Multi-Agent 분석: `0_Protocol/06_QA_and_Study/Study_Design/Multi_Agent_Classification_Analysis.md`
- Multi-Agent 설계 가능성: `0_Protocol/06_QA_and_Study/Study_Design/Multi_Agent_Design_Feasibility_Analysis.md`

**GitHub ID를 알려주시면 repository에 collaborator로 초대하겠습니다.**

현재 모든 작업은 Git에 커밋되어 있으며, 코드와 문서를 확인하실 수 있습니다.

---

검토 및 자문 부탁드립니다. 추가로 필요한 정보가 있으시면 언제든지 연락 주세요.

감사합니다.

---

**작성자**: [Study Coordinator]
**Email**: [email-redacted]
**Repository**: [repository-url]

