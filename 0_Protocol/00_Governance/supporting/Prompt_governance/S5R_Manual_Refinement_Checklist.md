# S5R 수동 프롬프트 개선 체크리스트

**Status**: Canonical  
**Version**: 1.0  
**Last Updated**: 2025-12-29  
**Purpose**: S5 기반 프롬프트 개선 시 필수 확인 사항

---

## 사전 준비 (Pre-Refinement)

- [ ] S5 validation이 완료되었는지 확인
- [ ] Primary input (`s5_validation__arm{arm}.jsonl`) 존재 확인
- [ ] Run tag 기록
- [ ] 현재 프롬프트 버전 확인 (`_registry.json` 참조)

---

## 1. 스키마 불변성 확인 (Schema Invariance Check)

**Non-Negotiable**: 다음은 절대 변경 불가

- [ ] JSON 스키마 구조 변경 없음
- [ ] 필수 키 추가/삭제/이름 변경 없음
- [ ] 데이터 타입 변경 없음
- [ ] 중첩 레벨 변경 없음
- [ ] Enum 값 변경 없음

**허용되는 변경만 수행**:
- [ ] 프롬프트 텍스트 개선 (규칙 추가, 명확화)
- [ ] 예시 업데이트
- [ ] 제약사항 강화

---

## 2. 개발 지표 선택 및 기록 (Development Metrics)

- [ ] Primary metric 선택: `blocking_issue_rate_per_group` (기본값)
- [ ] Primary metric 값 기록 (Before)
- [ ] Secondary metrics 선택 (선택사항)
- [ ] Secondary metrics 값 기록 (Before)

---

## 3. 반복 정책 준수 (Iteration Policy)

- [ ] 현재 S5R 라운드 확인 (S5R0, S5R1, S5R2)
- [ ] 반복 횟수 확인 (최대 2단계)
- [ ] 중지 규칙 확인:
  - [ ] Blocking issue 제거됨?
  - [ ] Marginal gain 임계값 미만?
  - [ ] 최대 반복 도달?

---

## 4. Patch Backlog 생성 (Patch Backlog)

- [ ] JSONL 파일에서 이슈 추출 (primary truth source)
- [ ] `issue_code`별 집계
- [ ] `recommended_fix_target`별 그룹화
- [ ] 우선순위 결정 (P0: blocking, P1: high-frequency)
- [ ] Patch Backlog 파일 저장: `patch_backlog__S5R{k}.json`

---

## 5. 프롬프트 편집 (Prompt Editing)

- [ ] 현재 프롬프트 파일 로드
- [ ] Patch Backlog 참고하여 변경 계획 수립
- [ ] 각 변경의 근거 기록:
  - [ ] Issue code
  - [ ] Issue count
  - [ ] Examples (최소 1-2개)
- [ ] 스키마 불변성 재확인 (변경 후)

---

## 6. Diff 생성 및 검토 (Diff Generation)

- [ ] Diff 리포트 생성: `diff_report__{PROMPT_NAME}__S5R{k}.md`
- [ ] Diff 검토:
  - [ ] 의도한 변경만 포함?
  - [ ] 실수로 삭제된 섹션 없음?
  - [ ] 스키마 관련 키워드 변경 없음?

---

## 7. Smoke Validation (Smoke Check)

- [ ] 스키마 불변성 검증 실행
- [ ] 필수 섹션 존재 확인
- [ ] 마크다운 형식 유효성 확인
- [ ] JSON 스키마 참조 정확성 확인
- [ ] 검증 결과 기록

---

## 8. 변경 이력 기록 (Change Log)

- [ ] Change Log 작성: `change_log__S5R{k}.md`
- [ ] 다음 정보 포함:
  - [ ] 변경된 프롬프트 목록
  - [ ] 각 변경의 근거 (issue_code, count, examples)
  - [ ] Primary metric 변화 (Before → After)
  - [ ] Run tag
  - [ ] Refinement date
  - [ ] Commit hash (커밋 후)

---

## 9. 추적 가능성 확인 (Traceability)

- [ ] Run tag 기록
- [ ] S5 snapshot ID 기록 (가능한 경우)
- [ ] Refinement date 기록
- [ ] Commit hash 기록 (커밋 후)
- [ ] 프롬프트 파일 헤더에 모든 정보 포함

---

## 10. 프롬프트 버전 관리 (Version Management)

- [ ] 새 프롬프트 파일 생성: `{PROMPT_NAME}__S5R{k}__v{XX}.md`
- [ ] 이전 버전 아카이브: `archive/`로 이동
- [ ] 레지스트리 업데이트: `_registry.json` 수정
- [ ] Git 커밋: 모든 변경사항 커밋

---

## 11. 데이터 누수 방지 확인 (Data Leakage Disclaimer)

- [ ] Development set 사용임을 명시
- [ ] Generalization claim 없음을 확인
- [ ] Holdout evaluation 필요성 언급 (별도 엔드포인트)

---

## 12. 최종 확인 (Final Check)

- [ ] 모든 체크리스트 항목 완료
- [ ] 모든 아티팩트 저장됨
- [ ] Git 커밋 완료
- [ ] Change Log 최종 확인
- [ ] 다음 단계 계획 (재생성 또는 freeze)

---

## 체크리스트 사용법

1. 프롬프트 개선 시작 전: "사전 준비" 섹션 확인
2. 개선 과정 중: 각 섹션 순서대로 체크
3. 완료 후: "최종 확인" 섹션으로 마무리

**중요**: 모든 항목을 완료해야 프롬프트 개선이 완료된 것으로 간주됩니다.

