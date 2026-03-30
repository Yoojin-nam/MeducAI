# Realistic Image Filtering Policy

**Status**: Canonical  
**Version**: 1.0  
**Created**: 2026-01-05  
**Applies to**: S4 Realistic Image Generation (`--image_type realistic`)

---

## 1. Purpose

본 문서는 Realistic Image 생성 시 **그래프/다이어그램 유형의 사전 필터링 기준**을 정의한다.

### 1.1 배경

Realistic 프롬프트(`exam_prompt_profile: realistic`)를 사용해도, 원본 콘텐츠가 본질적으로 그래프나 다이어그램인 경우 **realistic 스타일로 변환되지 않는다**.

예: T2 Relaxation 곡선 → Realistic 프롬프트 적용해도 여전히 지수 감소 곡선으로 생성됨

---

## 2. Filtering Criteria (Hard Rules)

### 2.1 Realistic 생성 제외 대상 (Mandatory Exclusion)

다음 유형은 Realistic Image 생성에서 **반드시 제외**해야 한다:

| 유형 | 예시 | 제외 이유 |
|------|------|-----------|
| **MRI Physics 곡선** | T2 Relaxation (Spin-Spin), T1 Recovery | 지수 감소/증가 곡선 → 실제 영상 아님 |
| **K-space 다이어그램** | K-space Center, K-space Trajectory | 수학적 개념도 → 실제 영상 아님 |
| **핵의학 시간-활성도 그래프** | Diuretic Renogram, Time-Activity Curve | 정량 그래프 → 실제 스캔 영상 아님 |
| **플로우차트/알고리즘** | 진단 알고리즘, 치료 프로토콜 | 절차 도식 → 영상 아님 |
| **통계/도표** | ROC Curve, Dose-Response Curve | 통계 시각화 → 영상 아님 |

### 2.2 Realistic 생성 적합 대상 (Keep)

다음 유형은 Realistic Image 생성에 **적합**하다:

| 유형 | 예시 |
|------|------|
| **초음파 영상** | Nipple Shadowing, Gallstone |
| **CT/MRI 단면 영상** | Axial CT of liver, Brain MRI T2 |
| **X-ray 영상** | Chest PA, Lateral decubitus |
| **핵의학 스캔 영상** | Thyroid Scan, Bone Scan (그래프 아님) |
| **혈관조영술** | DSA, CTA/MRA |

---

## 3. Implementation

### 3.1 Pre-Generation Filtering (Recommended)

S3 Image Spec 컴파일 단계에서 `visual_type_category`를 기반으로 필터링:

```python
REALISTIC_EXCLUDED_CATEGORIES = [
    "physics_graph",
    "physics_diagram",
    "flowchart",
    "algorithm",
    "statistical_graph",
    "time_curve",
]

def should_generate_realistic(image_spec):
    """Returns False if the spec should be excluded from realistic generation."""
    category = image_spec.get("visual_type_category", "")
    return category not in REALISTIC_EXCLUDED_CATEGORIES
```

### 3.2 Post-Generation Filtering (Fallback)

생성 후 수동 필터링이 필요한 경우:

```bash
# 부적합 이미지를 별도 폴더로 이동
mkdir -p images_realistic_excluded/
mv [부적합_이미지] images_realistic_excluded/
```

---

## 4. AppSheet Integration

`AppSheet_Realistic_Image_Evaluation_Design.md` (v4.0)에 따라:

- `Cards` 테이블의 `realistic_image_filename`이 **없으면** 평가 건너뜀
- 필터링된 카드는 자동으로 Realistic Image 평가 대상에서 제외됨
- 평가자 워크플로우에 영향 없음

---

## 5. Statistical Considerations

### 5.1 Sample Size Impact

| 항목 | 값 |
|------|-----|
| 원본 spec | 293개 |
| 필터링 후 | 286개 |
| 감소율 | 2.4% |

### 5.2 Statistical Validity

- **결론: 통계적 유의성에 문제 없음**
- n=286은 이미지 품질 평가에 충분한 샘플 크기
- 부적합 유형 제외는 methodologically sound
- Primary Analysis (S0 Non-Inferiority)에 영향 없음

---

## 6. Lessons Learned

1. **프롬프트 내용 ≠ 이미지 유형**: Realistic 프롬프트를 사용해도 원본 콘텐츠가 그래프면 그래프가 생성됨
2. **사전 필터링 필요**: 이미지 생성 전에 그래프/다이어그램 유형을 spec에서 제외하는 것이 효율적
3. **AppSheet 조건부 표시 활용**: 이미지가 없으면 자동으로 평가 건너뜀 (설계가 잘 되어 있음)

---

## 7. Related Documents

- `0_Protocol/06_QA_and_Study/QA_Operations/AppSheet_Realistic_Image_Evaluation_Design.md` (v4.0)
- `0_Protocol/04_Step_Contracts/S3_to_S4_Input_Contract_Canonical.md`
- `5_Meeting/HANDOFF_2026-01-05_Realistic_Image_Generation_Complete.md`

---

**작성자**: AI Assistant  
**작성일**: 2026-01-05

