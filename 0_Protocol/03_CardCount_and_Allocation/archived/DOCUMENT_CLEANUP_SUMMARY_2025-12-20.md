# CardCount and Allocation 문서 정리 요약 (2025-12-20)

**정리 일자:** 2025-12-20  
**목적:** 최근 변경 사항 반영, 문서 구조 개선, 상태 명확화

---

## 1. 문서 구조 및 상태

### 1.1 Canonical Documents (최신 상태)

**메인 정책 문서:**
- ✅ **S0_vs_FINAL_CardCount_Policy.md** - v2.1 (Canonical, Frozen)
  - S0와 FINAL의 카드 수 정책을 명확히 구분
  - S0: 고정 12장/set (3×4 엔티티 할당)
  - FINAL: 그룹별 quota (엔티티당 3장 고정)

**S0 Allocation:**
- ✅ **S0_Allocation/S0_Allocation_Artifact_Spec.md** - v2.1 (Canonical)
  - Deterministic 3×4 Entity Allocation 규칙
  - E >= 4: 첫 4개 엔티티 × 각 3장 = 12장
  - E < 4: 균등 분배하여 합계 12장 (fallback)

**FINAL Allocation:**
- ✅ **FINAL_Allocation/Allocation_Step_Card_Quota_Policy_v1.0.md** - v1.0 (Canonical, Frozen)
  - FINAL generation only
  - Group-level quota 결정
  - S0와 명확히 분리

- ✅ **FINAL_Allocation/Entity_Quota_Distribution_Policy_v1.0.md** - v1.0 (Canonical, Frozen)
  - Entity-level quota 분배 정책
  - 각 엔티티당 정확히 3장 고정
  - Legacy distribution methods는 deprecated로 표시

### 1.2 Reference Documents

**Design Rationale:**
- ✅ **Design Rationale/Why_S2_Fails_More_Than_S1.md** - 설계 근거 문서
  - S1이 S2보다 안정적인 구조적 이유 설명
  - 파이프라인 설계상 필연적 결과 설명

**Experimental:**
- ⚠️ **Experimental/S0_STABILIZE_MULTI_Allocation_Artifact_Spec.md** - v0.1 (EXPERIMENTAL)
  - Status: **EXPERIMENTAL** (Non‑Canonical, Draft)
  - Stabilization/Pilot runs only
  - Canonical S0와 명확히 구분

---

## 2. 주요 정책 요약

### 2.1 S0 Allocation Policy (v2.1)

**핵심 원칙:**
- Set-level payload: **12장 고정** (상수)
- Entity allocation: **Deterministic 3×4 규칙**
  - E >= 4: 첫 4개 엔티티 × 각 3장 = 12장
  - E < 4: 모든 엔티티에 균등 분배하여 합계 12장
- Allocation은 **기록(recording)** 단계, 결정(decision) 단계 아님

**책임 경계:**
- Allocation: 카드 수 결정 및 기록
- S2: 정확히 `cards_for_entity_exact = N` 실행
- S3: Selection 및 quota enforcement

### 2.2 FINAL Allocation Policy (v1.0)

**핵심 원칙:**
- Group-level quota: `group_target_cards = E × 3`
- Entity-level allocation: **각 엔티티당 정확히 3장** 고정
- TOTAL_CARDS = 6,000 (Canonical)

**책임 경계:**
- Allocation: Group-level quota 결정
- Entity Quota Distribution: Group quota → Entity-level allocation
- S2: 정확히 3장 실행
- S3: Quota enforcement

### 2.3 S0 vs FINAL Firewall

**명확한 분리:**
- S0는 FINAL의 축소 버전이 아님
- S0는 QA/arm comparison 전용
- FINAL은 Production/deployment 전용
- 정책적 연속성 없음

---

## 3. 문서 정리 결과

### 3.1 유지된 문서

**Canonical Documents:**
- ✅ 모든 Canonical 문서 최신 상태 유지
- ✅ S0_vs_FINAL_CardCount_Policy.md - v2.1 (메인 정책)
- ✅ S0_Allocation_Artifact_Spec.md - v2.1
- ✅ Allocation_Step_Card_Quota_Policy_v1.0.md - v1.0
- ✅ Entity_Quota_Distribution_Policy_v1.0.md - v1.0

**Reference Documents:**
- ✅ Why_S2_Fails_More_Than_S1.md - 설계 근거 문서 (유지)
- ✅ S0_STABILIZE_MULTI_Allocation_Artifact_Spec.md - Experimental (명확히 표시)

### 3.2 업데이트 사항

**Experimental 문서 명확화:**
- `S0_STABILIZE_MULTI_Allocation_Artifact_Spec.md`에 **EXPERIMENTAL** 상태 명확히 표시
- Canonical S0와의 구분 강조

### 3.3 중복 문서 확인

**결과:**
- 중복 문서 없음
- 각 문서가 고유한 역할 수행
- 병합 불필요

---

## 4. 문서 관계도

```
S0_vs_FINAL_CardCount_Policy.md (메인 정책)
├── S0_Allocation/
│   └── S0_Allocation_Artifact_Spec.md (v2.1)
│       └── Experimental/
│           └── S0_STABILIZE_MULTI_Allocation_Artifact_Spec.md (v0.1, EXPERIMENTAL)
└── FINAL_Allocation/
    ├── Allocation_Step_Card_Quota_Policy_v1.0.md (v1.0)
    └── Entity_Quota_Distribution_Policy_v1.0.md (v1.0)

Design Rationale/
└── Why_S2_Fails_More_Than_S1.md (설계 근거)
```

---

## 5. 구현 상태 요약

### 5.1 S0 Allocation 구현

**현재 상태:**
- ✅ v2.1 정책 구현 완료
- ✅ Deterministic 3×4 Entity Allocation 규칙 적용
- ✅ Allocation artifact 생성 및 검증

**코드 위치:**
- `3_Code/src/tools/allocation/s0_allocation.py`

### 5.2 FINAL Allocation 구현

**현재 상태:**
- ✅ Entity당 3장 고정 정책 적용
- ✅ Group-level quota → Entity-level allocation 변환

**참고:**
- `Entity_Quota_Distribution_Policy_v1.0.md`에 코드 스켈레톤 포함 (참고용)

---

## 6. Deprecated/Historical References

### 6.1 Entity_Quota_Distribution_Policy_v1.0.md

**Deprecated 메서드:**
- "Even + Remainder" 알고리즘 (Legacy reference)
- Minimum per entity switch (deprecated)

**현재 정책:**
- Entity당 3장 고정 (Canonical)

### 6.2 S0_vs_FINAL_CardCount_Policy.md

**Deprecated 환경 변수:**
- `CARDS_PER_ENTITY` (deprecated)
- FINAL에서는 Entity당 3장으로 고정

---

## 7. 문서 정리 완료

### 7.1 정리 완료

✅ **모든 Canonical 문서 최신 상태 확인**
✅ **Experimental 문서 명확히 표시**
✅ **문서 관계 명확화**
✅ **중복 문서 없음 확인**

### 7.2 유지된 문서 구조

```
0_Protocol/03_CardCount_and_Allocation/
├── S0_vs_FINAL_CardCount_Policy.md (✅ Canonical, v2.1)
├── S0_Allocation/
│   └── S0_Allocation_Artifact_Spec.md (✅ Canonical, v2.1)
├── FINAL_Allocation/
│   ├── Allocation_Step_Card_Quota_Policy_v1.0.md (✅ Canonical, v1.0)
│   └── Entity_Quota_Distribution_Policy_v1.0.md (✅ Canonical, v1.0)
├── Design Rationale/
│   └── Why_S2_Fails_More_Than_S1.md (✅ Reference)
└── Experimental/
    └── S0_STABILIZE_MULTI_Allocation_Artifact_Spec.md (⚠️ EXPERIMENTAL, v0.1)
```

---

## 8. 다음 단계

### 8.1 문서 유지

- 모든 Canonical 문서는 최신 상태 유지
- Experimental 문서는 명확히 표시하여 혼동 방지
- Design Rationale 문서는 참고용으로 유지

### 8.2 향후 개선 사항

- Entity_Quota_Distribution_Policy_v1.0.md의 코드 스켈레톤이 실제 구현과 일치하는지 확인
- FINAL allocation 구현 완료 시 문서 업데이트

---

**작성일:** 2025-12-20  
**작성자:** Document Cleanup Task  
**상태:** 완료

