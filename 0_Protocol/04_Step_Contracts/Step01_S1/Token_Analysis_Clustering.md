# Token Usage Analysis: Clustering in S1

**작성일**: 2025-12-23  
**목적**: S1에 clustering logic 포함 시 토큰 사용량 분석

---

## 현재 설정

- **S1**: arm E (gemini-3-pro-preview)
- **S2**: arm C (gemini-3-flash-preview, thinking=True, RAG=False)

---

## Gemini 3 Pro Preview 제한

- **Input**: 1M tokens
- **Output**: 64k tokens

---

## 현재 S1 토큰 사용량 (기본)

### Input 토큰

| 구성 요소 | 추정 토큰 | 비고 |
|----------|----------|------|
| System Prompt (S1_SYSTEM__v12.md) | ~2,366 | 고정 |
| User Prompt (S1_USER_GROUP__v11.md) | ~670 | 고정 |
| Objective Bullets | 가변 | 그룹마다 다름 (보통 500-2000 tokens) |
| **총 Input (기본)** | **~3,500-5,000** | objective_bullets 크기에 따라 |

### Output 토큰

| 구성 요소 | 추정 토큰 | 비고 |
|----------|----------|------|
| master_table_markdown_kr | ~1,500-2,500 | 10-20 rows × 6 columns |
| entity_list | ~100-300 | 10-20 entities |
| visual_type_category | ~10 | 단일 값 |
| **총 Output (기본)** | **~1,600-2,800** | entity 수에 따라 |

---

## Clustering 추가 시 토큰 사용량

### Input 토큰 추가

| 구성 요소 | 추정 토큰 | 비고 |
|----------|----------|------|
| Clustering 지시사항 (프롬프트에 추가) | ~300-500 | entity_list > 8일 때만 |
| **총 Input (clustering 포함)** | **~3,800-5,500** | 여전히 매우 여유 |

### Output 토큰 추가

| 구성 요소 | 추정 토큰 | 비고 |
|----------|----------|------|
| entity_clusters | ~200-400 | 1-3 clusters, 각 3-8 entities |
| infographic_clusters | ~300-600 | 1-3 clusters, 각 프롬프트 ~100-200 tokens |
| **총 Output (clustering 포함)** | **~2,100-3,800** | 여전히 매우 여유 |

---

## 시나리오별 토큰 사용량

### 시나리오 1: Entity ≤ 8개 (기본 동작)

- **Input**: ~3,500-5,000 tokens
- **Output**: ~1,600-2,800 tokens
- **Clustering**: 실행 안 함

### 시나리오 2: Entity > 8개 (Clustering 실행)

- **Input**: ~3,800-5,500 tokens
- **Output**: ~2,100-3,800 tokens
- **Clustering**: 실행됨

### 시나리오 3: 매우 큰 그룹 (20 entities, 많은 objectives)

- **Input**: ~6,000-8,000 tokens (objective_bullets가 매우 긴 경우)
- **Output**: ~4,000-5,000 tokens (3 clusters)
- **Clustering**: 실행됨

---

## 결론

### ✅ 토큰 제한 충족

1. **Input 제한 (1M tokens)**:
   - 현재 사용량: ~3,500-8,000 tokens
   - 여유 공간: **99.2% 이상** 여유

2. **Output 제한 (64k tokens)**:
   - 현재 사용량: ~1,600-5,000 tokens
   - 여유 공간: **92% 이상** 여유

### ✅ Clustering 포함 시 영향

- **Input 추가**: ~300-500 tokens (3-5% 증가)
- **Output 추가**: ~500-1,000 tokens (20-30% 증가)
- **전체 영향**: 미미함

### ✅ 권장사항

1. **Clustering을 S1에 포함해도 토큰 부족 걱정 없음**
2. **Gemini 3 Pro Preview의 1M input / 64k output 제한은 충분히 여유 있음**
3. **Objective bullets가 매우 긴 경우에도 문제 없음**

---

## 추가 고려사항

### Objective Bullets 크기

- 일반적인 그룹: 5-15 objectives → ~500-1,500 tokens
- 큰 그룹: 20-40 objectives → ~2,000-4,000 tokens
- 매우 큰 그룹: 40+ objectives → ~4,000-8,000 tokens

모든 경우에서 1M tokens 제한 내에 충분히 포함됨.

### Master Table 크기

- 10 rows: ~1,500 tokens
- 15 rows: ~2,200 tokens
- 20 rows: ~3,000 tokens

모든 경우에서 64k tokens 제한 내에 충분히 포함됨.

---

## 실제 테스트 권장

프로덕션 배포 전에 다음을 테스트하는 것을 권장:

1. **가장 큰 그룹** (entity 20개, objectives 40+개)로 테스트
2. **Clustering 포함/미포함** 비교 테스트
3. **실제 토큰 사용량** 모니터링

하지만 분석 결과, 토큰 부족 문제는 발생하지 않을 것으로 예상됩니다.

