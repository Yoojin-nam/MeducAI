# FINAL QA 할당 시스템 구현 인계장

**작성일**: 2026-01-01  
**상태**: 구현 준비 완료  
**목적**: 새로운 agent가 FINAL QA 할당 시스템을 구현할 수 있도록 모든 배경 정보와 결정사항 전달

---

## 1. 배경 및 목적

### 1.1 연구 목적
- **Paper 1 (Validation)**: S5 멀티에이전트 시스템의 신뢰성 검증 (Audit Study)
  - 목표: "S5-PASS는 안전하다(FN < 0.3%)" & "S5-REGEN은 쓸만하다(Accept-as-is)" 증명
- **Paper 2 (Education)**: 검증된 문항의 교육적 효과
- **Sub-study (Visual Modality)**: 일러스트(S5 정제) vs 실사(MLLM Raw)의 임상적 정확도 및 선호도 비교

### 1.2 데이터 현황
- **모집단**: 생성된 문항 총 6,000~8,000개 (전수 S5 처리 완료)
- **전공의 (Residents)**: 9명 (Audit 및 Safety 검증 주력)
- **전문의 (Specialists)**: 10명 (Reference Standard 제공 및 Visual Sub-study 주력)

### 1.3 핵심 발견
- **FLAG 그룹이 없고, REGEN도 매우 적음** → 모델(S5)의 초기 생성 품질이 매우 높음
- 연구 성격이 '결함 찾기'에서 **'압도적 품질 확증'**으로 변경 필요

---

## 2. 통계학 교수의 조언 요약

### 2.1 핵심 전략: "선택과 집중"

1. **FLAG 그룹 폐기**: 0건으로 처리, 로직에서 완전 제외
   - 이유: FLAG 설정 시 자동으로 REGEN이 트리거되므로 별도 그룹 불필요

2. **REGEN 전수 조사 (Census)**: 
   - REGEN이 적을 때(≤200개): **전수 조사** - "발생한 모든 REGEN 문항을 다 본다"
   - REGEN이 많을 때(>200개): **200개로 제한** - 무작위 샘플링
   - 논문 문구: *"AI가 수정한 문항(REGEN)은 전수 검토(exhaustively reviewed)하였으며..."*

3. **PASS 그룹에 할당량 집중**:
   - 나머지 할당량 전부 PASS에 몰아주기
   - 안전성 상한(Upper Bound)을 0%에 가깝게 수렴
   - 예: 1,300개 PASS 검사 시 오류율 상한 **0.23%**

### 2.2 통계적 근거

- **PASS 그룹 n=1,300개, 오류 0건**:
  - 95% 신뢰구간 상한: 0.23% (Clopper-Pearson)
  - 99% 신뢰구간 상한: 0.35%
- **REGEN 전수 조사**: "100% 검증"이라는 강력한 결론 제공

---

## 3. S5 판정 정의 (사전 정의, S5 실행 전 고정)

### 3.1 판정 기준

**중요**: 이 정의는 **S5 실행 전에 사전 정의**되어야 하며, S5 결과가 나온 후 변경 금지 (연구 설계 무결성)

```python
def determine_s5_decision(s5_record: Dict[str, Any]) -> str:
    """
    S5 판정 결정 로직 (PASS/REGEN만, FLAG 제외)
    
    Returns: 'PASS' | 'REGEN'
    """
    # REGEN 판정
    trigger_score = s5_record.get("s5_regeneration_trigger_score")
    if trigger_score is not None and trigger_score < 70.0:
        return "REGEN"
    
    if _as_bool(s5_record.get("s5_was_regenerated")) is True:
        return "REGEN"
    
    # Default: PASS
    return "PASS"
```

### 3.2 판정 기준 명시

- **PASS**: 
  - `regeneration_trigger_score >= 70.0` AND 
  - `s5_was_regenerated == False`
  
- **REGEN**: 
  - `regeneration_trigger_score < 70.0` OR 
  - `s5_was_regenerated == True`
  
- **FLAG**: 제외 (REGEN에 포함됨)

### 3.3 관련 코드 위치

- `3_Code/src/tools/multi_agent/score_calculator.py`: `calculate_s5_regeneration_trigger_score()` 함수
- `3_Code/src/tools/final_qa/export_appsheet_tables.py`: S5 데이터 export 로직

---

## 4. 할당 로직 상세

### 4.1 전공의 할당 (총 1,350건, 인당 150건)

#### Step 1: REGEN 처리 (핵심 로직)

```python
total_regen_count = len(regen_cards)

if total_regen_count <= 200:
    # Case A: 전수 조사 (Census)
    assigned_regen = all_regen_cards  # 전부 할당
    regen_assigned_count = total_regen_count
    regen_census = True
else:
    # Case B: 200개로 제한 (Cap)
    assigned_regen = random_sample(regen_cards, n=200, seed=seed)
    regen_assigned_count = 200
    regen_census = False
```

#### Step 2: Calibration 처리 (Specialty-Stratified)
- **99건** (33문항 × 3명/문항)
- **11분과 × 3문제 = 33문제**: 모든 분과 균등 대표
- 각 전공의가 **11개** calibration 문항 평가 (균형 배정)
- **전문의 330에서 선택**: Realistic 이미지 포함 보장
- 목적: ICC 정밀도 확보 (95% CI 폭 ≈ 0.30)
- 위치 랜덤화: 150개 내에서 랜덤 분산 (학습효과/피로효과 방지)

#### Step 3: PASS 처리
```python
pass_needed = 1350 - 99 - regen_assigned_count  # 99 = calibration slots (33 × 3)
assigned_pass = random_sample(pass_cards, n=pass_needed, seed=seed)

# 예시: REGEN=100일 때
# pass_needed = 1350 - 99 - 100 = 1151
```

#### Step 4: 균등 분배
- 9명 전공의에게 균등 분배
- Cluster(Objective) 고려한 Shuffle (통계적 독립성 확보)

### 4.2 전문의 할당 (총 300건, 인당 30건)

#### 전략: 전공의 할당분에서 서브샘플링 (100% 오버랩)

```python
resident_assigned_cards = set(assigned_regen + assigned_pass + assigned_calibration)

# REGEN 우선 포함
specialist_regen = []
if len(assigned_regen) <= 200:
    specialist_regen = assigned_regen  # 전부 포함
else:
    specialist_regen = random_sample(assigned_regen, n=200, seed=seed)

# PASS에서 나머지 채우기
specialist_pass_needed = 300 - len(specialist_regen)
specialist_pass = random_sample(
    [c for c in assigned_pass if c in resident_assigned_cards],
    n=specialist_pass_needed,
    seed=seed
)
```

#### 할당 비율
- **S5-PASS**: 100건 (전공의 할당분에서 추출)
- **S5-REGEN**: 200건 (전공의 할당분에서 추출, 우선 포함)
- **Visual Modality Sub-study**: 이 300건 안에서 수행

---

## 5. 구현 계획 요약

### 5.1 필수 구현 파일

1. **`3_Code/src/tools/qa/generate_final_qa_assignments.py`** (신규)
   - 핵심 할당 스크립트
   - REGEN 전수 조사 vs Cap 로직 구현
   - 전공의/전문의 할당 생성

2. **`3_Code/src/tools/final_qa/export_appsheet_tables.py`** (업데이트)
   - `s5_decision` 필드 추가 (PASS/REGEN만)
   - `determine_s5_decision()` 함수 구현

3. **`0_Protocol/05_Pipeline_and_Execution/S5_Decision_Definition_Canonical.md`** (신규)
   - S5 판정 기준 사전 정의 문서

4. **`0_Protocol/06_QA_and_Study/FINAL_QA_Research_Design_Spec.md`** (신규)
   - 연구 설계 사양서 (FLAG 폐기, REGEN 전수 조사 전략)

5. **`0_Protocol/06_QA_and_Study/QA_Operations/FINAL_QA_Assignment_Guide.md`** (신규)
   - 할당 알고리즘 상세 가이드

### 5.2 구현 순서

1. **P0 (필수)**: S5 판정 기준 문서화 및 함수 구현
2. **P0 (필수)**: 할당 스크립트 구현 (`generate_final_qa_assignments.py`)
3. **P1 (중요)**: 연구 설계 사양서 문서화
4. **P1 (중요)**: 할당 가이드 문서 작성

---

## 6. 데이터 구조 및 스키마

### 6.1 입력 데이터

- **Cards.csv**: 전체 문항 정보
  - 필수 필드: `card_uid`, `card_id`, `group_id`
  
- **S5.csv**: S5 검증 결과
  - 필수 필드: `card_uid`, `s5_regeneration_trigger_score`, `s5_was_regenerated`
  - 추가 필요: `s5_decision` (PASS/REGEN)

- **reviewer_master.csv**: 평가자 정보
  - 필수 필드: `reviewer_email`, `role` (resident/attending)

### 6.2 출력 데이터

- **Assignments.csv**: 할당 결과
  - 필드: `assignment_id`, `rater_email`, `card_uid`, `card_id`, `assignment_order`, `batch_id`, `status`
  - `s5_decision` 포함 (PASS/REGEN)

### 6.3 평가 레코드 스키마

```python
class EvaluationRecord:
    # 기본 정보
    question_id: str
    user_id: str
    user_role: str  # 'resident' | 'specialist'
    
    # S5 메타데이터
    s5_decision: str  # 'PASS' | 'REGEN' (FLAG 제외)
    cluster_id: str  # Objective ID 또는 질환 그룹
    
    # 1. 텍스트/논리 평가 (Paper 1 Main)
    blocking_error: bool
    error_category: str  # 임상오류, 논리오류, 환각 등
    
    # 2. REGEN 평가 (s5_decision == 'REGEN'인 경우)
    accept_as_is: bool  # 수정본 수용 가능 여부
    improvement_scale: str  # 'Better', 'Same', 'Worse'
    
    # 3. 이미지 평가 (Specialist Only)
    photo_hallucination: bool  # 실사 이미지 오류 여부
    preferred_modality: str  # 'Illustration', 'Photo', 'Neutral'
```

---

## 7. 검증 체크리스트

구현 완료 후 다음을 확인:

- [ ] S5 판정(PASS/REGEN)이 모든 문항에 대해 계산됨 (FLAG 제외)
- [ ] REGEN ≤ 200개일 때 전수 조사 수행
- [ ] REGEN > 200개일 때 200개로 제한
- [ ] **Calibration (Specialty-Stratified)**: 33개 문항 × 3명 = 99 slots (11분과 × 3문제)
- [ ] 각 전공의가 정확히 **11개** calibration 문항 평가
- [ ] **전문의 330에서 선택**: Realistic 이미지 포함 보장
- [ ] Calibration 문항이 150개 내에서 **랜덤 위치**에 분산
- [ ] 전공의 할당: 총 1,350건, 인당 150건 (Calibration 11 + REGEN + PASS ~139)
- [ ] 전문의 할당: 총 330건, 전공의 할당분에서 서브샘플링, REGEN 우선 포함
- [ ] PASS 그룹에 나머지 할당량 전부 몰아주기
- [ ] 통계 분석: 안전성 상한 계산 (예: 1,200개 PASS → 0.25% 상한)
- [ ] **Realistic 평가**: 전공의 330개 (Calibration 중복 유지), 전문의 330개

---

## 8. 참고 문서

### 8.1 관련 프로토콜 문서

- `0_Protocol/06_QA_and_Study/FINAL_QA_Form_Design.md`: 평가 폼 설계
- `0_Protocol/05_Pipeline_and_Execution/QA_Metric_Definitions.md`: QA 지표 정의
- `0_Protocol/04_Step_Contracts/Step05_S5/S5_Validation_Contract_Canonical.md`: S5 계약 정의

### 8.2 관련 코드

- `3_Code/src/tools/final_qa/generate_assignments.py`: 기존 할당 스크립트 (참고용)
- `3_Code/src/tools/multi_agent/score_calculator.py`: S5 점수 계산 로직
- `3_Code/src/tools/final_qa/export_appsheet_tables.py`: S5 데이터 export

### 8.3 계획 문서

- `/path/to/workspace/.cursor/plans/s5-stratified_assignment_(flag_폐기,_regen_전수_조사)_f9fedeb4.plan.md`: 상세 구현 계획

---

## 9. 주요 결정사항 요약

1. ✅ **FLAG 그룹 폐기**: 0건 처리, 로직에서 완전 제외
2. ✅ **REGEN 전수 조사 전략**: ≤200개는 전수, >200개는 200개 Cap
3. ✅ **PASS 그룹 할당량 집중**: 나머지 전부 PASS에 몰아주기
4. ✅ **S5 판정 정의**: PASS/REGEN만 (FLAG 제외)
5. ✅ **전문의 할당**: 전공의 할당분에서 서브샘플링, REGEN 우선 포함
6. ✅ **고정 시드**: `SEED=20260101` (프로토콜에 명시)
7. ✅ **Calibration Specialty-Stratified**: 33개×3명 (11분과×3문제, 전문의 330에서 선택)
8. ✅ **전공의 Realistic 평가**: 330개 (Calibration 중복 유지, 시나리오 A)
9. ✅ **위치 랜덤화**: Calibration 10개를 150개 내에서 랜덤 분산

---

## 10. 다음 단계

1. S5 판정 기준 문서 작성 (`S5_Decision_Definition_Canonical.md`)
2. `export_appsheet_tables.py`에 `s5_decision` 필드 추가
3. `generate_final_qa_assignments.py` 스크립트 구현
4. 연구 설계 사양서 문서화
5. 할당 가이드 문서 작성

---

**문의사항이 있으면 이 문서를 참고하여 구현을 진행하세요.**

