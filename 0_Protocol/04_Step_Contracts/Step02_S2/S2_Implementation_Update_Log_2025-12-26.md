# S2 Implementation Update Log — 2025-12-26

**Status:** Canonical  
**Version:** 2.0  
**Last Updated:** 2025-12-26  
**Purpose:** S2 v8 2-card policy 전환 및 이미지 최적화 구현 이력

---

## 개요

이 문서는 2025-12-26에 수행된 S2 (Stage 2) 프롬프트 v8 업데이트, 2-card policy 전환, 그리고 Anki 앱 최적화를 위한 이미지 규격 개선을 기록합니다.

---

## 주요 변경 사항

### 1. S2 프롬프트 v8 개선 (2-Card Policy + Cognitive Alignment)

**파일:**
- `3_Code/prompt/S2_SYSTEM__v8.md`
- `3_Code/prompt/S2_USER_ENTITY__v8.md`

**프롬프트 레지스트리:**
- `3_Code/prompt/_registry.json`에 S2 v8 프롬프트 등록

#### 1.1 3-Card → 2-Card Policy 전환

**변경 사항:**
- Entity당 카드 수: 3개 (Q1/Q2/Q3) → 2개 (Q1/Q2)
- Q3 카드 제거
- Q1, Q2 모두 image_hint REQUIRED (독립적)

**목적:**
- 시험 스타일 정렬: Q1 (2교시 진단형), Q2 (1교시 개념 이해)
- 이미지 배치 명확화: Back-only infographics
- 인지적 정렬 강화 (Yaacoub 2025 논문 적용)

#### 1.2 Cognitive Alignment 적용

**Yaacoub 2025 논문 반영:**
- Q1: APPLICATION (Bloom's Taxonomy Level 3) - 영상 소견을 진단에 적용
- Q2: APPLICATION or KNOWLEDGE (Level 3 or 1) - 개념 이해 기반

**추가된 요소:**
- 명시적 인지 수준 정의
- Expected Behavior 구체화
- Forbidden Cognitive Operations 명시
- Self-verification 요청

#### 1.3 Q1 Front 형식 변경

**변경 사항:**
- Front 이미지 제거
- "영상 요약:" 섹션 추가 (descriptive text)
- Modality + view/sequence + key findings 기술
- 진단 질문: "가장 가능성이 높은 진단은?"

**예시:**
```
Front:
영상 요약: CT axial에서 장골 피질 내 1.2cm 크기의 석회화된 nidus가 관찰되고, 주변부 반응성 골경화가 현저하다. 야간 통증이 있는 15세 남성.
가장 가능성이 높은 진단은?

Back:
Answer: Osteoid Osteoma
근거:
* 1.5cm 미만의 중심부 nidus 형성
* 주변 반응성 골경화
함정/감별: Osteoblastoma는 1.5cm 이상, 덜 현저한 반응성 골경화
```

---

### 2. 코드 개선 및 검증 업데이트

#### 2.1 validate_stage2() 함수 수정

**파일:** `3_Code/src/01_generate_json.py`

**위치:** 라인 2496-2742

**변경 사항:**
- `len(anki_cards) == 3` → `len(anki_cards) == 2`로 변경
- Q3 관련 모든 검증 로직 제거
- Q1, Q2만 허용 (card_role 검증)
- Q1 image_hint: REQUIRED
- Q2 image_hint: REQUIRED (독립적)
- Q3 관련 모든 참조 제거

**스키마 버전:** v3.1 → v3.2

#### 2.2 cards_for_entity_exact 기본값 변경

**파일:** `3_Code/src/01_generate_json.py`

**위치:** 라인 3262

**변경 사항:**
- `FINAL_CARDS_PER_ENTITY = 3` → `FINAL_CARDS_PER_ENTITY = 2`

#### 2.3 S3 Policy Resolver 업데이트

**파일:** `3_Code/src/03_s3_policy_resolver.py`

**변경 사항:**
- Q3 policy 로직 제거
- Q1, Q2만 처리
- Q2 image_required: True (독립적 이미지)

#### 2.4 Anki Export 이미지 배치 수정

**파일:** `3_Code/src/07_export_anki_deck.py`

**변경 사항:**
- Q1: Image on back only (기존: front 또는 back)
- Q2: Image on back only (기존: Q1 재사용)
- Q3 관련 로직 제거

**현재 로직 (v8, 2-card):**
- Q1: Front 텍스트만, Back에 이미지
- Q2: Front 텍스트만, Back에 이미지 (Q1과 독립적)

#### 2.5 PDF Builder 업데이트

**파일:** `3_Code/src/07_build_set_pdf.py`

**변경 사항:**
- Q3 관련 정렬 로직 제거
- Q1, Q2만 처리

---

### 3. 이미지 규격 최적화 (Anki 앱 호환성)

#### 3.1 JPEG 압축 품질 최적화

**파일:** `3_Code/src/04_s4_image_generator.py`

**위치:** 라인 667

**변경 사항:**
- Quality: 95 → 85로 조정
- `optimize=True` 유지
- 목표: 파일 크기 ≤ 100KB (Anki 권장)

**이유:**
- Anki 앱 권장: 파일 크기 ≤ 100KB
- 현재 해상도: 1024×1280 (합계 2304px, 권장보다 큼)
- 압축으로 파일 크기 제어, 시각적 품질 유지

#### 3.2 이미지 파일 크기 검증 추가

**파일:** `3_Code/src/04_s4_image_generator.py`

**위치:** 라인 674-687

**추가 기능:**
- 생성된 이미지 파일 크기 검증
- 100KB 초과 시 경고 출력
- 파일 크기 KB 단위로 표시

**구현:**
```python
file_size_kb = file_size / 1024
if file_size > 100 * 1024:  # 100KB
    print(f"[S4] Warning: Image file size ({file_size_kb:.1f} KB) exceeds Anki recommendation (100 KB): {output_path}", file=sys.stderr)
else:
    print(f"[S4] Successfully saved image: {file_size_kb:.1f} KB ({format_type} data)")
```

---

## 영향 및 호환성

### 하위 호환성

- ⚠️ **Breaking Change**: 3-card policy → 2-card policy
- 기존 3-card 출력과 호환되지 않음
- 마이그레이션 필요: 기존 run tag 재실행 권장

### 마이그레이션 필요 사항

**3-card policy run tag 사용자:**
1. S2 출력 파일에서 Q3 카드 존재 여부 확인
2. 2-card policy로 재실행 필요

**재실행 방법:**
```bash
# 전체 파이프라인 재실행
NEW_RUN_TAG="FULL_PIPELINE_V8_$(date +%Y%m%d_%H%M%S)"
python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag "$NEW_RUN_TAG" \
  --arm C \
  --mode FINAL \
  --stage both
```

---

## 테스트 결과

### 테스트 실행 (2-card policy 검증)
- Run Tag: (실행 대기 중)
- 목적: 2-card policy 및 이미지 최적화 검증

### 예상 결과
- ✅ Entity당 정확히 2개 카드 (Q1, Q2)
- ✅ Q1 front에 "영상 요약:" 포함
- ✅ Q1, Q2 모두 image_hint REQUIRED
- ✅ Q1, Q2 이미지 모두 Back-only
- ✅ 이미지 파일 크기 ≤ 100KB (대부분)
- ✅ Q3 관련 참조 없음

---

## 관련 문서

### 구현 로그
- `0_Protocol/00_Governance/Implementation_Change_Log_2025-12-20.md` (이전 로그)
- `0_Protocol/04_Step_Contracts/Step02_S2/S2_Implementation_Update_Log_2025-12-20.md` (v7 로그)

### 프롬프트 파일
- `3_Code/prompt/S2_SYSTEM__v8.md`
- `3_Code/prompt/S2_USER_ENTITY__v8.md`
- `3_Code/prompt/_registry.json`

### 스키마 문서
- `0_Protocol/04_Step_Contracts/Step02_S2/S2_Contract_and_Schema_Canonical.md` (업데이트 필요)
- `0_Protocol/04_Step_Contracts/Step02_S2/S2_Cardset_Image_Placement_Policy_Canonical.md` (업데이트 필요)

### 인지적 정렬 문서
- `0_Protocol/00_Governance/supporting/Prompt_governance/Yaacoub_2025_Lightweight_Prompt_Engineering_Review.md`
- `0_Protocol/00_Governance/supporting/Prompt_governance/archived/S2_v8_2Card_Policy_with_Cognitive_Alignment.md`

---

## 변경 이력

- **2025-12-26**: S2 프롬프트 v8 개선 및 2-card policy 전환
  - 3-card → 2-card policy 전환
  - Cognitive Alignment 적용 (Yaacoub 2025)
  - Q1 Front 형식 변경 (영상 요약 추가)
  - 이미지 규격 최적화 (Anki 앱 호환성)
  - validate_stage2() 함수 수정
  - S3, Anki Export, PDF Builder 업데이트

