# MeducAI — Claude Code Context

## Project Overview

MeducAI: LLM-기반 영상의학 학습 콘텐츠 생성 파이프라인 연구 프로젝트
- 7단계 파이프라인 (S1→S2→S3→S4→S5→S6→FINAL)
- 6,000 Anki 플래시카드 + 833 인포그래픽 생성 완료
- Protocol frozen v1.3.1
- 3편 논문 포트폴리오

## 3-Paper Portfolio (as of 2026-03)

| Paper | 주제 | 상태 | Target |
|-------|------|------|--------|
| **Paper 1** | S5 Multi-agent Validation | 데이터 완료 → 분석/집필 | 3-4월 |
| **Paper 2** | MLLM Image Reliability + VTT | 데이터 수집 필요 | 4-5월 |
| **Paper 3** | Educational Effectiveness | 설문 완료 → 분석/집필 | 5-6월 |

## Repository Navigation

```
0_Protocol/06_QA_and_Study/
  MeducAI_3Paper_Research_Index.md          ← 마스터 인덱스
  MeducAI_Manuscript_Preparation_Status.md  ← 논문 준비 현황 (START HERE)
  Paper1_S5_Validation/                     ← Paper 1 설계/분석 문서
  Paper2_Image_Reliability/                 ← Paper 2 설계 문서
  Paper3_Educational_Effectiveness/         ← Paper 3 설계/설문 문서
  Publication_Strategy/                     ← 출판 전략
  QA_Operations/                            ← QA 운영 (Methods 참조)

2_Data/
  qa_responses/FINAL_DISTRIBUTION/          ← Paper 1 QA 비식별화 데이터
  qa_appsheet_export/                       ← AppSheet export 데이터
  survey_responses/                         ← Paper 3 설문 데이터
  metadata/generated/FINAL_DISTRIBUTION/    ← 파이프라인 생성물

7_Manuscript/
  drafts/Paper1/                            ← Paper 1 Quarto 드래프트
    figures/                                ← 최종 그림 (fig1-fig6)
    figures/originals/                      ← 원본 그림 (번호별)
    figures/generated/                      ← 코드 생성 그림 + 스크립트
    figures/mobile_anki/                    ← 모바일 스크린샷
  references/                               ← BibTeX, CSL, PDF
  reports/                                  ← 교수/편집자 참고용 보고서
  authorship/                               ← 저자 동의서, 공동교신 제안
  docs/                                     ← Quarto/Zotero 가이드 문서
  tables/                                   ← 결과 테이블 템플릿
```

## Critical Data Warnings

1. **AppSheet 시간 컬럼 신뢰 불가**: `post_duration_sec`, `s5_duration_sec`
   - 반드시 타임스탬프에서 직접 재계산 필요
   - 상세: `QA_Operations/handoffs/APPSHEET_TIME_CALCULATION_ISSUE_2026-01-09.md`

2. **REGEN 카드 수 초과**: 263개 (계획 200개)
   - 상세: `Paper1_S5_Validation/Paper1_QA_Validation_Report.md`

## Language Convention

- 프로토콜/설계 문서: 한국어 + 영어 기술 용어
- 코드/커밋: 영어
- 의학 용어: English-only (e.g., "Dumping Syndrome" not "덤핑 증후군")

## Key Canonical Documents

- Pipeline spec: `0_Protocol/05_Pipeline_and_Execution/Pipeline_Canonical_Specification.md`
- Governance: `0_Protocol/00_Governance/meduc_ai_pipeline_canonical_governance_index.md`
- DOCS Registry: `0_Protocol/DOCS_REGISTRY.md`
- Prompt registry: `3_Code/prompt/_registry.json`
