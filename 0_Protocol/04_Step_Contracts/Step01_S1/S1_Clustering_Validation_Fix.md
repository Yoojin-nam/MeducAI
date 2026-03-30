# S1 Clustering Validation 오류 수정

**Date:** 2025-12-27  
**Issue:** `entity_clusters`와 `infographic_clusters` 길이 불일치 오류

---

## 문제 원인

LLM이 `entity_clusters`를 3개 생성했지만 `infographic_clusters`를 2개만 생성하여 validation 실패:
```
Stage1 entity_clusters and infographic_clusters must have same length (got 3 vs 2)
```

---

## 해결 방법

### 1. Auto-Repair 로직 추가

**파일:** `3_Code/src/01_generate_json.py`

**변경사항:**
- `S1_CLUSTER_LENGTH_REPAIR=1` (기본값)일 때 자동 수정
- `entity_clusters`가 더 많으면: 누락된 `infographic_clusters` 자동 생성
- `infographic_clusters`가 더 많으면: 매칭되지 않는 항목 제거

**로직:**
```python
if len(entity_clusters) != len(infographic_clusters):
    if entity_len > infographic_len:
        # 누락된 infographic_clusters 생성
        # cluster_id 매칭하여 기본값으로 생성
    elif infographic_len > entity_len:
        # 매칭되지 않는 infographic_clusters 제거
```

### 2. 프롬프트 강화

**파일:**
- `3_Code/prompt/S1_SYSTEM__v12.md`
- `3_Code/prompt/S1_USER_GROUP__v11.md`

**추가된 제약 조건:**
- `entity_clusters`와 `infographic_clusters`의 개수는 반드시 일치해야 함
- 각 `entity_cluster.cluster_id`에 대해 동일한 `cluster_id`를 가진 `infographic_cluster`가 반드시 존재해야 함
- 명확한 예시 추가

### 3. cluster_id 매칭 검증 개선

**변경사항:**
- 인덱스 기반 매칭 대신 `cluster_id` 기반 매칭 사용
- `S1_CLUSTER_ID_REPAIR=1` (기본값)일 때 `cluster_id` 불일치 자동 수정

---

## 환경 변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `S1_CLUSTER_LENGTH_REPAIR` | 1 | 클러스터 길이 불일치 자동 수정 (1=활성, 0=비활성) |
| `S1_CLUSTER_ID_REPAIR` | 1 | cluster_id 불일치 자동 수정 (1=활성, 0=비활성) |

---

## Backward Compatibility

- 기본값으로 auto-repair 활성화 (기존 동작 유지)
- `S1_CLUSTER_LENGTH_REPAIR=0`으로 설정하면 기존처럼 fail-fast
- Auto-repair 실패 시 여전히 validation 오류 발생

---

## 테스트 권장사항

1. 기존 실패 케이스 재실행: `heart__diagnostic_imaging__ischemic_heart_disease`
2. 다양한 클러스터 개수 테스트 (2, 3, 4개)
3. Auto-repair 로그 확인: `[WARN]` 메시지 확인

---

## 관련 파일

- `3_Code/src/01_generate_json.py` (line 2889-2955, 2990-3090)
- `3_Code/prompt/S1_SYSTEM__v12.md`
- `3_Code/prompt/S1_USER_GROUP__v11.md`

