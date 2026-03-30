# Anatomy Map 개선 방안 종합 정리

**작성일**: 2026-01-04  
**상태**: 분석 완료, V7 구현됨  
**관련 파일**: 
- `3_Code/prompt/S4_CONCEPT_USER__Anatomy_Map__S5R2__v7.md`
- `3_Code/prompt/_registry.json`

---

## 1. 문제 분석

### 핵심 문제
LLM 이미지 생성 모델이 의학적으로 정확한 해부학적 위치/화살표를 그릴 수 없음

### 구체적 증상
- Bochdalek = posterior라고 알아도 그림은 랜덤하게 anterior에 그림
- Liver segmentation, vessel branching 같은 복잡한 구조는 거의 항상 틀림
- 텍스트로 "posterior"라고 적어놓고 그림은 반대로 그리는 경우 다수

### 근본 원인
**프롬프트를 아무리 강화해도 해결 불가** - 이미지 생성 모델의 의학 지식 자체가 부족함

---

## 2. 제안된 방법들

### 2.1 Hybrid Region (V7 - 구현 완료)

```
+--------------------------------------------------+
|  [Title Bar]                                      |
+--------------------------------------------------+
|   +---------+     +---------------------------+   |
|   |  Head   |     | [Structure Card 1]        |   |
|   | (blue)  |     |  Name + Location + Cue    |   |
|   +---------+     +---------------------------+   |
|   | Thorax  |     | [Structure Card 2]        |   |
|   | (green) |     |  Name + Location + Cue    |   |
|   +---------+     +---------------------------+   |
|   | Abdomen |     | [Structure Card 3]        |   |
|   |(orange) |     |  Name + Location + Cue    |   |
|   +---------+     +---------------------------+   |
|   | Pelvis  |     | [Structure Card 4]        |   |
|   |(purple) |     |  Name + Location + Cue    |   |
|   +---------+     +---------------------------+   |
+--------------------------------------------------+
```

| 항목 | 내용 |
|------|------|
| **장점** | 화살표 완전 제거, 색상 매칭으로 안전한 연결 |
| **단점** | 공간 관계 직관성 낮음, 너무 단순할 수 있음 |
| **구현 상태** | ✅ 완료 (`S4_CONCEPT_USER__Anatomy_Map__S5R2__v7.md`) |

---

### 2.2 Numbered Tag 방식

```
+--------------------------------------------------+
|    +-----+                                        |
|    | ①② |  [Region Map]                          |
|    | ③④ |                                        |
|    +-----+                                        |
|                                                   |
|  ① Structure A: Description                      |
|  ② Structure B: Description                      |
|  ③ Structure C: Description                      |
+--------------------------------------------------+
```

| 항목 | 내용 |
|------|------|
| **장점** | 화살표보다 안전, 직관적 매칭 |
| **단점** | 번호 위치도 틀릴 수 있음, 근본 문제 해결 안됨 |
| **구현 상태** | ❌ 미구현 |

---

### 2.3 Text-Heavy Location 방식

```
+--------------------------------------------------+
|  +----------+  +--------------------------------+ |
|  | Simple   |  | Structure Card                 | |
|  | 4-6      |  | Name: RPA                      | |
|  | Regions  |  | Location: posterior to aorta,  | |
|  | Only     |  |   anterior to right bronchus   | |
|  +----------+  | Adjacent: SVC, right atrium    | |
|                +--------------------------------+ |
+--------------------------------------------------+
```

| 항목 | 내용 |
|------|------|
| **장점** | 상세한 위치 정보, 텍스트로 정확성 보장 |
| **단점** | 맵에 화살표 허용 시 여전히 오류 가능, 시각적 직관성 감소 |
| **구현 상태** | ❌ 미구현 |

---

### 2.4 Schematic Thumbnail 방식

```
+--------------------------------------------------+
| +-------------+  +-------------+  +-------------+ |
| |[Mini-schem]|  |[Mini-schem]|  |[Mini-schem]| |
| | RPA        |  | LPA        |  | MPA        | |
| | Location.. |  | Location.. |  | Location.. | |
| +-------------+  +-------------+  +-------------+ |
+--------------------------------------------------+
```

| 항목 | 내용 |
|------|------|
| **장점** | 중앙 맵 불필요, 모듈식 구조 |
| **단점** | 개별 thumbnail도 오류 가능, 복잡도 증가 |
| **구현 상태** | ❌ 미구현 |

---

### 2.5 Structure-Card Grid (General 스타일)

```
+--------------------------------------------------+
| +-------------+  +-------------+  +-------------+ |
| | Entity 1   |  | Entity 2   |  | Entity 3   | |
| | Feature A  |  | Feature A  |  | Feature A  | |
| | Feature B  |  | Feature B  |  | Feature B  | |
| +-------------+  +-------------+  +-------------+ |
+--------------------------------------------------+
```

| 항목 | 내용 |
|------|------|
| **장점** | 이미 검증된 General 스타일, 안정적 |
| **단점** | 공간 관계 표현 어려움, Anatomy 특성 살리기 어려움 |
| **구현 상태** | ❌ 미구현 (General 프롬프트 참조 가능) |

---

### 2.6 Comparison Table 방식

```
+--------------------------------------------------+
| | Entity  | Location | Adjacent | Pitfall      | |
| |---------|----------|----------|--------------|  |
| | RPA     | Post.    | SVC, RA  | LPA와 혼동    | |
| | LPA     | Ant-lat. | Aorta    | -            | |
+--------------------------------------------------+
```

| 항목 | 내용 |
|------|------|
| **장점** | 정보 정확성 보장, 비교 학습에 유용 |
| **단점** | 시각적 흥미 감소, 그림 없음 |
| **구현 상태** | ❌ 미구현 |

---

### 2.7 Relationship Map (개념 관계도)

```
+--------------------------------------------------+
|                                                   |
|    [MPA] ──분지──> [RPA]                          |
|      │                                            |
|      └──분지──> [LPA]                             |
|                                                   |
|    Adjacent: [Aorta] ─인접─ [RPA]                 |
+--------------------------------------------------+
```

| 항목 | 내용 |
|------|------|
| **장점** | 해부학 그림 없이 관계만 표현, 오류 발생 가능성 낮음 |
| **단점** | 공간 위치 정보 부족, 추상적 |
| **구현 상태** | ❌ 미구현 |

---

### 2.8 Text-Only Table (완전 텍스트)

```
+--------------------------------------------------+
| ## Pulmonary Artery Anatomy                       |
|                                                   |
| | Structure | Location      | Key Feature      | |
| |-----------|---------------|------------------| |
| | MPA       | Central       | Bifurcation point| |
| | RPA       | Posterior     | Longer, horizontal|
| | LPA       | Anterolateral | Shorter, oblique | |
+--------------------------------------------------+
```

| 항목 | 내용 |
|------|------|
| **장점** | 오류 가능성 제로, 가장 안전 |
| **단점** | 시각적 학습 효과 없음, 인포그래픽 목적에 안 맞음 |
| **구현 상태** | ❌ 미구현 |

---

## 3. 안전성 vs 학습효과 매트릭스

| 방법 | 안전성 | 학습효과 | 구현 난이도 | 상태 |
|------|--------|----------|-------------|------|
| Text-Only Table | ★★★★★ | ★★☆☆☆ | 쉬움 | - |
| Comparison Table | ★★★★★ | ★★★☆☆ | 쉬움 | - |
| **Hybrid Region (V7)** | ★★★★☆ | ★★★☆☆ | 쉬움 | **구현됨** |
| Relationship Map | ★★★★☆ | ★★★☆☆ | 중간 | - |
| Structure-Card Grid | ★★★★☆ | ★★★☆☆ | 쉬움 | - |
| Text-Heavy Location | ★★★☆☆ | ★★★★☆ | 중간 | - |
| Numbered Tag | ★★★☆☆ | ★★★★☆ | 중간 | - |
| Schematic Thumbnail | ★★☆☆☆ | ★★★★☆ | 어려움 | - |
| 현행 V6 (화살표+맵) | ★☆☆☆☆ | ★★★★★ | - | 문제있음 |

---

## 4. S5 → 프롬프트 수정 → 재생성 접근법 분석

### 4.1 현재 아키텍처

```
S5 Validation → issues + prompt_patch_hint → S5R Repair Plan → S4 Regeneration
```

### 4.2 문제 유형별 효과

| 문제 유형 | S5→프롬프트 수정 효과 | 이유 |
|----------|----------------------|------|
| Text 오타/누락 | ✅ 효과 있음 | 프롬프트에 정확한 텍스트 명시 가능 |
| 엔티티 누락 | ✅ 효과 있음 | 프롬프트에 누락된 엔티티 추가 |
| 레이아웃 문제 | ⚠️ 제한적 | 레이아웃 지시 가능하나 보장 없음 |
| **해부학적 위치 오류** | ❌ 효과 없음 | LLM 이미지 모델의 의학 지식 부족 |
| **화살표/연결선 오류** | ❌ 효과 없음 | 공간 관계 이해 능력 한계 |

### 4.3 결론

프롬프트 수정→재생성은 텍스트/레이아웃 오류에는 효과가 있지만, **해부학적 위치 오류는 근본적으로 해결되지 않음**.

---

## 5. 권장 실행 계획

### 5.1 현재 상태
- V7 (Hybrid Region) 프롬프트 구현 완료
- `_registry.json` 업데이트됨
- Anatomy_Map 그룹 55개 존재

### 5.2 테스트 순서

1. **1단계**: V7으로 1-2개 그룹 테스트 실행
2. **2단계**: 결과 확인 후 만족스러우면 55개 전체 적용
3. **3단계**: 불만족 시 다른 방법 (Relationship Map, Comparison Table) 추가 고려

### 5.3 실행 명령어

```bash
# 1. S3 재실행 (프롬프트 반영)
python 3_Code/src/03_s3_policy_resolver.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G \
  --s1_arm G

# 2. Anatomy_Map TABLE 이미지 55개 삭제
while read grp; do
  rm -f "2_Data/metadata/generated/FINAL_DISTRIBUTION/images/IMG__FINAL_DISTRIBUTION__${grp}__TABLE.jpg"
done < /tmp/anatomy_groups.txt
echo "삭제 완료: 55개 TABLE 이미지"

# 3. 배치 실행 (삭제된 이미지만 새로 생성)
python 3_Code/src/tools/batch/batch_image_generator.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G \
  --only-infographic
```

### 5.4 Anatomy_Map 그룹 ID 목록 추출

```bash
# Anatomy_Map 그룹 ID 목록 저장
grep '"visual_type_category": *"Anatomy_Map"' \
  2_Data/metadata/generated/FINAL_DISTRIBUTION/stage1_struct__armG.jsonl | \
  python3 -c "import sys, json; [print(json.loads(line)['group_id']) for line in sys.stdin]" \
  > /tmp/anatomy_groups.txt

echo "총 Anatomy_Map 그룹: $(wc -l < /tmp/anatomy_groups.txt)개"
```

---

## 6. 관련 파일 목록

| 파일 | 설명 |
|------|------|
| `3_Code/prompt/S4_CONCEPT_USER__Anatomy_Map__S5R2__v6.md` | 기존 프롬프트 (화살표+맵, 문제있음) |
| `3_Code/prompt/S4_CONCEPT_USER__Anatomy_Map__S5R2__v7.md` | 새 프롬프트 (Hybrid Region) |
| `3_Code/prompt/_registry.json` | 프롬프트 레지스트리 (v7으로 업데이트됨) |
| `3_Code/src/03_s3_policy_resolver.py` | S3 정책 리졸버 |
| `3_Code/src/04_s4_image_generator.py` | S4 이미지 생성기 |
| `3_Code/src/tools/batch/batch_image_generator.py` | 배치 이미지 생성기 |

---

## 7. 변경 이력

| 날짜 | 변경 내용 |
|------|----------|
| 2026-01-04 | 문서 생성, 8가지 방법 분석, V7 구현 완료 |


