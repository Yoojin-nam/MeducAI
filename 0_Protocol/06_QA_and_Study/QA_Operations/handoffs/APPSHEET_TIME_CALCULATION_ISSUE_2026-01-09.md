# AppSheet Time Calculation Issue - Ratings Sheet

**Date**: 2026-01-09  
**Status**: Known Issue (Requires Fix Before Analysis)  
**Severity**: High (Data Integrity)  
**Affected Component**: AppSheet Ratings 시트 duration_sec 컬럼들

---

## Executive Summary

Ratings 시트의 시간(초) 계산에서 **post_duration_sec와 s5_duration_sec에 컬럼 매핑/계산 로직 오류** 발견. post_duration_sec가 실제로는 s5 duration 값을 담고 있으며, s5_duration_sec는 비어있음.

**Critical Finding**: 98개 행에서 post_duration_sec = s5 경과시간 (잘못된 값)

---

## 1. 오류 상세 분석

### 1.1 구간별 시간 계산 검토 결과

| 구간 | 컬럼명 | 상태 | 비고 |
|------|--------|------|------|
| **Pre** | `pre_duration_sec` | ✅ 정상 | `pre_submitted_ts - pre_started_ts`와 일치 |
| **Realistic Image** | `realistic_image_duration_sec` | ✅ 정상 | 해당 10개 행 모두 계산 일치 |
| **S5** | `s5_duration_sec` | ❌ **누락** | 컬럼은 존재하나 **전부 비어있음** (계산/저장 로직 누락) |
| **Post** | `post_duration_sec` | ❌ **오류** | 대부분 행에서 post 구간 시간과 불일치 |

### 1.2 post_duration_sec 오류 원인 (명확)

**현상**: post_duration_sec가 post 구간 시간이 아니라, **s5 구간의 경과시간을 담고 있음**

**정량 분석**:
- `post_duration_sec == post 경과시간` (정상): **9개 행**
- `post_duration_sec == s5 경과시간` (오류): **98개 행**
- 즉, 대부분의 경우 s5 duration이 post_duration_sec를 덮어씀

**추정 원인**:
- AppSheet의 액션/봇/수식에서 post_duration_sec를 업데이트하는 로직이 s5 단계에서도 동일 컬럼에 쓰고 있음
- s5_duration_sec를 따로 저장하는 로직이 구현되지 않음
- s5가 완료되지 않은 일부 행에서만 post 경과시간이 남아있어 혼합된 상태

---

## 2. 타임스탬프 구조 (참고)

### 2.1 타임스탬프 자체는 정상

타임스탬프 컬럼들은 정상적으로 기록되고 있음:
- `pre_started_ts`, `pre_submitted_ts`
- `post_started_ts`, `post_submitted_ts`
- `realistic_image_started_ts`, `realistic_image_submitted_ts`
- `s5_started_ts`, `s5_submitted_ts`

### 2.2 단계 간 타임스탬프 관계

다음 관계가 거의 고정으로 관찰됨:
```
post_started_ts == pre_submitted_ts (전부 동일)
realistic_image_started_ts == post_started_ts (전부 동일)
s5_started_ts ≈ post_submitted_ts (거의 동일, 1초 차이 1건)
```

**해석**: "단계 시작 시간"을 별도로 찍지 않고, **이전 단계 제출 시각을 다음 단계 시작으로 복사**하는 구조로 구성됨

---

## 3. 실무 대응 방안

### 3.1 분석(통계) 단계 권장 사항 ⚠️

**❌ duration_sec 컬럼을 직접 사용하지 말 것**

**✅ 항상 타임스탬프 차이로 재계산하여 사용**:

```python
# 안전한 계산 방법
pre_elapsed = pre_submitted_ts - pre_started_ts
post_elapsed = post_submitted_ts - post_started_ts
s5_elapsed = s5_submitted_ts - s5_started_ts
realistic_image_elapsed = realistic_image_submitted_ts - realistic_image_started_ts
```

**근거**:
- 타임스탬프는 정확하게 기록됨
- duration_sec 컬럼은 로직 오류로 신뢰할 수 없음
- 재계산이 유일한 안전한 방법

### 3.2 AppSheet 수정 방향 (개발 측면)

#### 즉시 수정 필요

1. **post_duration_sec 보호**
   - s5 단계에서 post_duration_sec를 덮어쓰지 않도록 조건 추가
   - post 전용 계산 컬럼을 고정
   - 액션/봇에서 컬럼 타겟 분리

2. **s5_duration_sec 구현**
   - 계산식/액션/봇이 누락된 상태
   - s5 단계 완료 시 별도로 s5_duration_sec에 저장하는 로직 추가
   - `s5_submitted_ts - s5_started_ts` 계산식 구현

#### 설계 고려사항

3. **중단/재개 시 시간 측정 정책 결정**
   - "In progress"로 중단 후 재개하는 경우:
     - **Option A**: 누적 active time (세션 합산)
     - **Option B**: Wall-clock elapsed (타임스탬프 차이) ← 현재 구조
   - 현재 시트는 Option B (wall-clock)에 가까움
   - 명시적으로 정책 문서화 필요

---

## 4. 감사(Audit) 산출물

### 4.1 생성된 파일

**파일명**: `appsheet_time_audit.xlsx`

**시트 구성**:
- **Summary**: 전체 오류 요약
- **BoundaryChecks**: 경계값 검증
- **TopPostMismatches**: post_duration_sec 불일치 상위 케이스
- **TimeAudit_All**: 전체 행 감사 결과

**컬럼**:
- 각 구간의 `elapsed_sec` (타임스탬프 기반 재계산)
- 기존 `duration_sec` 값
- 불일치 플래그 및 차이(초)

### 4.2 감사 결과 핵심 수치

```
총 행 수: ~107개 (realistic_image가 있는 행 10개 포함)

post_duration_sec:
  - 정상 (post elapsed와 일치): 9개
  - 오류 (s5 elapsed와 일치): 98개
  - 오류율: 91.6%

s5_duration_sec:
  - 비어있음: 100%
  - 계산/저장 로직 완전 누락
```

---

## 5. 수정 체크리스트 (AppSheet 개발자용)

### Phase 1: 긴급 수정 (데이터 무결성)

- [ ] post_duration_sec 덮어쓰기 방지
  - [ ] s5 액션에서 post_duration_sec 업데이트 제거
  - [ ] post 전용 액션/수식 분리
  - [ ] 조건문 추가: `IF(ISBLANK([s5_duration_sec]), UPDATE_POST, UPDATE_S5)`

- [ ] s5_duration_sec 구현
  - [ ] s5_duration_sec 계산 수식 추가
  - [ ] s5 제출 액션에 s5_duration_sec 저장 로직 추가
  - [ ] 테스트: s5 완료 시 올바른 값 저장 확인

### Phase 2: 데이터 복구

- [ ] 기존 데이터 수정
  - [ ] 98개 행의 post_duration_sec를 타임스탬프 기반으로 재계산
  - [ ] s5_duration_sec를 타임스탬프 기반으로 계산하여 채움
  - [ ] 백업 후 일괄 업데이트 실행

- [ ] 검증
  - [ ] 감사 스크립트 재실행
  - [ ] 불일치율 0% 확인
  - [ ] 샘플 행 수동 검증

### Phase 3: 예방 조치

- [ ] 문서화
  - [ ] 각 duration_sec 컬럼의 계산 로직 명시
  - [ ] 액션/봇 트리거 조건 문서화
  - [ ] 타임스탬프 복사 로직 명시적 설명

- [ ] 모니터링
  - [ ] 주간 감사 스크립트 자동 실행
  - [ ] duration_sec 불일치 알림 설정
  - [ ] 신규 단계 추가 시 duration_sec 로직 체크리스트 적용

---

## 6. 분석 단계 주의사항

### 6.1 통계 분석 시 필수 전처리

```python
# ❌ 절대 하지 말 것
df['post_time'] = df['post_duration_sec']  # 오염된 데이터

# ✅ 반드시 이렇게
df['post_time'] = (df['post_submitted_ts'] - df['post_started_ts']).dt.total_seconds()
df['s5_time'] = (df['s5_submitted_ts'] - df['s5_started_ts']).dt.total_seconds()
```

### 6.2 결측치 처리

- `s5_submitted_ts`가 없는 경우: s5 미완료 → s5_time = NA
- `realistic_image_submitted_ts`가 없는 경우: realistic image 평가 없음 → realistic_time = NA
- 분석 시 명시적으로 제외 또는 별도 처리

### 6.3 보고서 작성 시

**Methods 섹션에 명시**:
> "AppSheet에서 제공된 duration_sec 컬럼의 데이터 무결성 문제로 인해, 모든 경과 시간은 타임스탬프 차이(submitted_ts - started_ts)를 직접 계산하여 사용하였다."

---

## 7. Related Documents

### AppSheet Export Documentation
- `0_Protocol/06_QA_and_Study/QA_Operations/AppSheet_QA_System_Specification.md`
- `0_Protocol/06_QA_and_Study/QA_Operations/handoffs/APP_SHEET_EXPORT_HANDOFF_2026-01-09.md`

### FINAL QA Design
- `0_Protocol/06_QA_and_Study/Paper1_S5_Validation/Paper1_Paper2_Research_Design_Spec.md`
- `0_Protocol/06_QA_and_Study/Paper1_S5_Validation/Paper1_QA_Endpoints_Definition.md`

### Tools
- Export tool: `3_Code/src/tools/final_qa/export_appsheet_tables.py`
- Verification tool: `3_Code/src/tools/final_qa/verify_appsheet_translation_sources.py`

---

## 8. Action Items

### For Immediate Attention

1. **[ ] 분석 팀에 전달**: duration_sec 컬럼 사용 금지, 타임스탬프 재계산 필수
2. **[ ] AppSheet 개발**: post_duration_sec 덮어쓰기 수정, s5_duration_sec 구현
3. **[ ] 데이터 복구**: 기존 98개 행의 post_duration_sec 재계산
4. **[ ] 검증**: 감사 스크립트 재실행하여 수정 확인

### For Documentation

5. **[ ] Methods 섹션**: 시간 계산 방법 명시
6. **[ ] Supplementary**: 감사 결과 및 수정 내역 첨부
7. **[ ] README 업데이트**: AppSheet 데이터 주의사항 추가

---

## 9. Audit Trail

**Issue Discovered**: 2026-01-09  
**Audit File Generated**: `appsheet_time_audit.xlsx`  
**Documented By**: MeducAI QA Team  
**Status**: Open (Awaiting Fix)

**Verification Required**:
- [ ] AppSheet 수정 완료
- [ ] 데이터 복구 완료
- [ ] 감사 재실행 통과 (불일치율 0%)
- [ ] 분석 코드 업데이트 완료

---

**Critical Reminder**: 🚨 **분석 시작 전 반드시 이 문서를 검토하고 타임스탬프 기반 재계산을 적용할 것**

**Last Updated**: 2026-01-09  
**Next Review**: 수정 완료 후 검증 단계

