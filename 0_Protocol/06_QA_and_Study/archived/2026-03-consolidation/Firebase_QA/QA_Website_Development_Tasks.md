# QA 웹사이트 제작 작업 목록

**문서 상태:** 작업 계획  
**작성일:** 2025-12-17  
**관련 문서:**
- `Survey Site Implementation Notes.md`
- `Time Measurement Protocol.md`
- `QA_Framework.md`
- `QA_Evaluation_Rubric.md`
- `S0_QA_Form_One-Screen_Layout.md`

---

## 개요

본 문서는 MeducAI Pipeline-1 QA (S0, S1)를 위한 Firebase 기반 QA 웹사이트 제작을 위한 작업 목록을 정리합니다.

---

## 1. 프로젝트 초기 설정

### 1.1 기술 스택 결정
- [ ] **프론트엔드 프레임워크 선택**
  - React, Vue, 또는 Next.js 등
  - 모바일/태블릿 반응형 지원 고려
- [ ] **Firebase 프로젝트 생성 및 설정**
  - Firebase Console에서 프로젝트 생성
  - Firestore Database 활성화
  - Authentication 설정 (필요 시)
- [ ] **개발 환경 설정**
  - Git 저장소 초기화
  - 의존성 관리 (npm/yarn)
  - 환경 변수 설정

---

## 2. Firestore 데이터베이스 구조

### 2.1 컬렉션 구조 구현
- [ ] **`runs/{run_tag}` 컬렉션**
  - run_tag, phase, created_at, frozen
  - idle_threshold_sec (고정값 30)
  - ui_version, rubric_version
  - arm_blinding_enabled
- [ ] **`assignments/{assignment_id}` 컬렉션**
  - run_tag, phase, reviewer_id, reviewer_role
  - items 배열 (set_id/card_id, arm_blinded_code, order_index, status)
- [ ] **`sessions/{session_id}` 컬렉션**
  - 메타데이터 필드 (run_tag, phase, set_id/card_id, reviewer_id 등)
  - 시간 측정 필드 (timestamp_start_ms, active_duration_sec 등)
  - events 배열 (임베딩)
  - evaluation 객체 (S0/S1 평가 데이터)

---

## 3. 인증 및 보안

### 3.1 인증 시스템
- [ ] **Reviewer 인증 구현**
  - Pseudonymized reviewer_id 생성/관리
  - 역할 기반 접근 제어 (Resident/Attending)
- [ ] **Firestore Security Rules**
  - Reviewer는 자신의 assignment/session만 read/write
  - Arm 정보는 서버 사이드에서만 접근 가능
  - Admin 전용 aggregate 컬렉션 보호

---

## 4. S0 QA 화면 구현

### 4.1 레이아웃
- [ ] **One-Screen Layout 구현**
  - 좌측: Artifact 콘텐츠 (Master Table, Cards, Infographic)
  - 우측: 평가 폼 (Rubric, Critical Flags)
  - 하단: Submit 버튼
- [ ] **Set Metadata 표시**
  - Run tag, Group ID, Arm ID (blinded), Evaluator role
  - 자동 타임스탬프

### 4.2 평가 폼 필드
- [ ] **Card Evaluation 섹션**
  - B1: Blocking Error (Yes/No) + 조건부 코멘트
  - B2: Overall Card Quality (1-5 Likert)
  - B3: Edit Time (구간값: 0-1분/1-3분/3-5분/5분 초과)
  - B4: Evidence Comment (조건부)
- [ ] **Table & Infographic Safety Gate**
  - C1: Critical Error (Yes/No)
  - C2: Scope/Alignment Failure (Yes/No)
  - C3: Gate Result (자동 계산)

### 4.3 콘텐츠 표시
- [ ] **Master Table 렌더링**
- [ ] **12개 Anki Cards 표시** (6엔티티 × 2문항)
- [ ] **Infographic 표시** (있는 경우)

---

## 5. S1 QA 화면 구현

### 5.1 레이아웃
- [ ] **Card 단위 평가 화면**
  - Card 콘텐츠 표시
  - 빠른 평가 폼 (2-5개 항목)
  - Next 카드 자동 로드

### 5.2 평가 폼 필드
- [ ] **Binary 항목**
  - binary_accept
  - major_revision_flag
  - minor_revision_flag
  - adjudication_needed (선택)
  - safety_flag (선택)
- [ ] **Short comment** (선택)

---

## 6. Time Measurement 시스템

### 6.1 상태 머신 구현
- [ ] **Active/Idle 상태 관리**
  - ACTIVE ↔ IDLE 전환 로직
  - 30초 idle threshold 구현
  - last_event_ts_ms 추적
- [ ] **시간 누적 계산**
  - active_accum_ms
  - idle_accum_ms
  - total_duration_sec

### 6.2 이벤트 추적
- [ ] **Interaction 이벤트 리스너**
  - scroll
  - keydown/input
  - click
  - focus/blur (탭 전환 감지)
- [ ] **이벤트 로깅**
  - view, scroll, click, edit, idle_enter, idle_exit, save, submit
  - 타임스탬프 기록
  - events 배열에 append

### 6.3 UX 개선
- [ ] **Idle 상태 배너**
  - "비활성 상태로 기록이 일시 중지되었습니다" 메시지
  - Non-blocking (강제 종료 금지)
- [ ] **Draft Save 기능** (선택)
  - 장시간 작업 대비

---

## 7. Assignment 시스템

### 7.1 배정 관리
- [ ] **Assignment 생성 로직**
  - Reviewer별 배정 생성
  - 랜덤 순서 (order_index)
  - Arm blinding 코드 생성
- [ ] **진행 상태 관리**
  - todo → in_progress → done
  - 현재 평가 중인 item 추적

### 7.2 Arm Blinding
- [ ] **Blinded Code 생성**
  - 실제 arm 정보는 서버에서만 매핑
  - UI에는 arm_blinded_code만 표시
  - 예: "X3", "Q7" 등

---

## 8. 데이터 저장 및 검증

### 8.1 Session 저장
- [ ] **Submit 시 데이터 저장**
  - 모든 메타데이터
  - 시간 측정 결과
  - 평가 데이터
  - 이벤트 로그
- [ ] **데이터 검증**
  - 필수 필드 확인
  - 타입 검증
  - 범위 검증 (Likert 1-5 등)

### 8.2 Edit Metrics
- [ ] **편집 관련 필드**
  - edit_event (boolean)
  - edit_char_count
  - edit_block_count

---

## 9. 서버 사이드 집계

### 9.1 Cloud Functions 또는 배치 스크립트
- [ ] **집계 로직 구현**
  - run_tag × arm × role별 통계
  - P95 active time 계산
  - zero_edit_rate 계산
  - blocking_error_rate 계산
- [ ] **Incremental 업데이트**
  - sessions 문서 생성 시 자동 집계
  - 또는 BigQuery export 후 배치 분석

---

## 10. 관리자 기능

### 10.1 대시보드
- [ ] **진행 상황 모니터링**
  - Reviewer별 완료율
  - Set/Card별 평가 상태
  - 전체 진행률
- [ ] **데이터 품질 확인**
  - 누락된 필드 확인
  - 이상치 탐지
  - Time measurement 검증
- [ ] **Assignment 관리**
  - 배정 수정
  - 재배정 기능

---

## 11. 테스트 및 검증

### 11.1 기능 테스트
- [ ] **Time Measurement 정확도**
  - Idle threshold 30초 정확히 동작
  - Active/Idle 전환 정확성
  - 시간 누적 계산 검증
- [ ] **데이터 저장 검증**
  - 모든 필드 저장 확인
  - 이벤트 로그 저장 확인
  - 타입 및 형식 검증
- [ ] **Arm Blinding 확인**
  - UI에서 arm 정보 노출되지 않음
  - Blinded code만 표시
- [ ] **Assignment 랜덤 순서**
  - 순서 유지 확인
  - 진행 상태 업데이트 확인

### 11.2 사용성 테스트
- [ ] **S0 화면 테스트**
  - One-screen layout 동작
  - 스크롤 및 네비게이션
  - 폼 제출 흐름
- [ ] **S1 화면 테스트**
  - 카드 간 빠른 전환
  - 평가 폼 간편성
- [ ] **반응형 테스트**
  - 모바일/태블릿/데스크톱
  - 다양한 화면 크기

### 11.3 보안 테스트
- [ ] **접근 제어 검증**
  - Reviewer는 자신의 데이터만 접근
  - Arm 정보 보호 확인
- [ ] **데이터 무결성**
  - 서버 사이드 검증
  - 클라이언트 조작 방지

---

## 12. 문서화 및 배포

### 12.1 문서화
- [ ] **사용자 가이드**
  - Reviewer용 매뉴얼
  - 평가 방법 안내
- [ ] **개발자 문서**
  - 아키텍처 설명
  - API 문서
  - 배포 가이드

### 12.2 배포 준비
- [ ] **프로덕션 환경 설정**
  - Firebase 프로젝트 설정
  - 환경 변수 설정
  - 도메인 연결 (필요 시)
- [ ] **모니터링 설정**
  - 에러 로깅
  - 성능 모니터링
  - 사용량 추적

---

## 우선순위

### Phase 1 (핵심 기능)
1. Firebase 프로젝트 설정
2. Firestore 컬렉션 구조
3. S0 QA 화면 기본 구현
4. Time Measurement 시스템
5. 데이터 저장 로직

### Phase 2 (완성도 향상)
6. S1 QA 화면
7. Assignment 시스템
8. Arm Blinding
9. UX 개선

### Phase 3 (고급 기능)
10. 서버 사이드 집계
11. 관리자 대시보드
12. 테스트 및 검증

---

## 참고 사항

- **Time Measurement Protocol**에 따라 active_duration_sec가 primary metric
- **QA Framework v2.0**의 모든 요구사항 준수
- **S0_QA_Form_One-Screen_Layout** 레이아웃 정확히 구현
- **Arm Blinding**은 연구 무결성을 위해 필수
- 모든 데이터는 **pseudonymized reviewer_id** 사용

---

## 체크리스트 (최소 테스트)

다음 항목들이 정확히 작동하는지 확인:

1. ✅ Idle threshold가 정확히 30초에서 작동
2. ✅ idle_enter/exit가 이벤트로 기록
3. ✅ "수정 없음 + submit"도 세션 저장
4. ✅ 탭 이동(blur/focus) 시 idle 처리
5. ✅ 랜덤 배정 순서 유지
6. ✅ Arm 정보가 UI에서 노출되지 않음
7. ✅ Sessions 문서에 active/idle/total 모두 기록

---

**작성자:** MeducAI Study Team  
**최종 업데이트:** 2025-12-17

