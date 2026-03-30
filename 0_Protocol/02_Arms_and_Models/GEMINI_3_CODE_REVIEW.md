# Gemini 3 코드 검토 결과

**Status:** Reference (Code Review)  
**Last Updated:** 2025-12-20  
**Purpose:** Gemini 3 가이드라인 준수 여부 및 코드 구현 검토

## 검토 기준
- Gemini 3 개발 가이드라인 (`Gemini_3_develop.md`)
- 현재 코드 구현 (`01_generate_json.py`)

## 주요 발견 사항

### ✅ 올바르게 구현된 부분

1. **Thinking Level 지원**
   - Gemini 3에서 `thinking_level` 파라미터 사용 (line 985-998)
   - Gemini 2.5와의 하위 호환성 유지 (`thinking_budget` 지원)

2. **ARM 설정과 Thinking Level 매핑**
   - ARM A: `thinking_level="minimal"` ✅
   - ARM C, D: `thinking_level="high"` ✅

### ⚠️ 주의가 필요한 부분

#### 1. **max_output_tokens 제한 (Line 887-913) ✅ 수정 완료**

**가이드라인 명시값:**
- Gemini 3 Pro: **64k output tokens**
- Gemini 3 Flash: **64k output tokens**

**현재 코드 설정:**
```python
# Gemini 3 Flash Stage1
if thinking_enabled:
    max_out_stage1 = min(base_max_out_stage1, 768)  # 매우 낮음
else:
    max_out_stage1 = min(base_max_out_stage1, 1024)  # 낮음

# Gemini 3 Flash Stage2
if thinking_enabled and rag_enabled:
    max_out_stage2 = min(base_max_out_stage2, 24576)  # 64k의 38%
elif thinking_enabled or rag_enabled:
    max_out_stage2 = min(base_max_out_stage2, 32768)  # 64k의 50%
else:
    max_out_stage2 = min(base_max_out_stage2, 32768)  # 64k의 50%

# Gemini 3 Pro Stage2
max_out_stage2 = min(base_max_out_stage2, 49152)  # 64k의 75%
```

**이슈:**
- Stage1 제한(768/1024)이 가이드라인의 64k보다 훨씬 낮음
- 코드 주석에 "tested: 1024 still fails"라고 되어 있어 실제 테스트 결과 반영된 것으로 보임
- **권장사항**: 가이드라인과 실제 동작의 차이를 명확히 문서화

**검토 의견:**
- Stage1 출력이 짧은 경우라면 낮은 제한도 합리적일 수 있음
- 하지만 가이드라인과 불일치하므로, 실제 API 제약인지 테스트 환경 이슈인지 확인 필요

#### 2. **Thinking Level 기본값 처리 (Line 989-998)**

**가이드라인 명시:**
> If `thinking_level` is not specified, Gemini 3 will default to `high`.

**현재 코드:**
```python
elif thinking_enabled:
    # Default to "high" if thinking is enabled but level not specified
    config_kwargs["thinking_config"] = genai_types.ThinkingConfig(
        thinking_level="high"
    )
else:
    # Default to "minimal" if thinking is disabled
    config_kwargs["thinking_config"] = genai_types.ThinkingConfig(
        thinking_level="minimal"
    )
```

**이슈:**
- `thinking_enabled=False`일 때 명시적으로 `"minimal"`을 설정
- 가이드라인에서는 파라미터를 아예 지정하지 않으면 자동으로 `"high"`가 됨
- **현재 코드는 의도적으로 `"minimal"`을 강제하므로, 이는 의도된 동작으로 보임**

**검토 의견:**
- ARM A (thinking_enabled=False)에서 `"minimal"` 사용은 명시적 설정이므로 문제 없음
- 하지만 가이드라인의 기본 동작과 다르므로, 주석으로 이유를 명확히 하는 것이 좋음

#### 3. **Temperature 설정 (Line 256-260, Line 2828-2829)**

**가이드라인 권장:**
> For Gemini 3, we strongly recommend keeping the temperature parameter at its default value of `1.0`.
> Changing the temperature (setting it below 1.0) may lead to unexpected behavior, such as looping or degraded performance.

**현재 코드:**
```python
temp_stage1 = float(arm_cfg.get("temp_stage1", env_float("TEMPERATURE_STAGE1", 0.2)))
temp_stage2 = float(arm_cfg.get("temp_stage2", env_float("TEMPERATURE_STAGE2", 0.2)))
```

**이슈:**
- 기본값이 `0.2`로 설정됨 (가이드라인 권장값 1.0과 다름)
- ARM F만 `temp_stage1=0.2, temp_stage2=0.2`로 명시적으로 설정
- **다른 ARM들은 ARM_CONFIGS에서 temperature를 명시하지 않아 기본값 0.2 사용**

**검토 의견:**
- 가이드라인 권장사항과 불일치
- 실제 테스트에서 0.2가 잘 동작한다면 문제 없을 수 있음
- 하지만 가이드라인에서 "looping or degraded performance" 경고를 하고 있으므로, 이 부분을 검증 필요

#### 4. **Media Resolution (미구현)**

**가이드라인 기능:**
- `media_resolution` 파라미터 지원 (이미지/PDF/비디오 해상도 제어)
- 현재 코드에서는 미사용 (Step01은 TEXT-only이므로 정상)

**검토 의견:**
- Step01은 텍스트만 처리하므로 이 기능은 필요 없음
- 향후 이미지 처리 단계에서 도입 검토

### ✅ 기타 정상 동작

1. **Thought Signatures**: 코드에서 SDK를 사용하므로 자동 처리됨 (가이드라인 line 273 참고)
2. **RAG (Google Search)**: 올바르게 구현됨 (line 1006-1011)
3. **Response MIME Type**: JSON 모드 올바르게 설정 (line 979)
4. **API 버전**: v1beta 사용 (가이드라인과 일치)

## 권장사항

### 높은 우선순위

1. **Temperature 기본값 검토**
   - 가이드라인 권장값(1.0)과의 차이 검증
   - 실제 프로덕션에서 looping이나 성능 저하 발생 여부 모니터링
   - 문제가 있다면 1.0으로 변경 검토

2. ~~**max_output_tokens Stage1 제한 문서화**~~ ✅ **완료**
   - ✅ 가이드라인(64k)에 맞춰 Stage1 8192, Stage2 61440으로 수정 완료
   - ✅ 가이드라인 참조 주석 추가 완료

### 중간 우선순위

3. **Thinking Level 기본값 동작 명확화**
   - `thinking_enabled=False`일 때 `"minimal"` 사용하는 이유 주석 추가
   - 가이드라인 기본값(`"high"`)과의 차이 설명

4. ~~**모델별 토큰 제한 상수화**~~ ✅ **부분 완료**
   - ✅ `GEMINI_3_MAX_OUTPUT_TOKENS = 64000` 상수 추가 완료
   - ✅ Stage1/Stage2 값들은 가이드라인에 맞춰 통일된 값 사용

### 낮은 우선순위

5. **마이그레이션 가이드 준수 여부 검토**
   - 가이드라인의 "Migrating from Gemini 2.5" 섹션 확인
   - 현재 코드가 모든 권장사항을 따르는지 점검

## 결론

전반적으로 Gemini 3 가이드라인을 잘 따르고 있으며, 주요 기능(thinking_level, RAG)이 올바르게 구현되어 있습니다.

**✅ 완료된 개선사항:**
- **max_output_tokens 제한**: 가이드라인의 64k output tokens에 맞춰 조정 완료
  - Stage1: 768/1024 → 8192
  - Stage2: 24576~49152 → 61440 (Pro/Flash 통일)

**⚠️ 남은 검토 사항:**
- **temperature 기본값**: 가이드라인 권장값(1.0)과 현재 코드(0.2)의 차이 검증 필요

