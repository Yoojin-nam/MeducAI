# PDF 생성 실패 문제 분석 및 해결 방안

**작성일:** 2025-12-22  
**상태:** ✅ 해결됨 (2025-12-22)

## 문제 요약

### 실패한 PDF 생성 케이스

**Arm E에서 실패한 그룹:**
- `grp_9b18e6ae4f` (quality_control__ct)
- `grp_bbb30c3ae8` (lung_bronchus__radiologic_anatomy)

**에러 메시지:**
```
ValueError: Parse error: saw </i> instead of expected </para>
paragraph text '<para><b>CTDI&lt;<br/>i&gt;<br/>w</b> = 1/3 Center + 2/3 Periphery;<br/><br/><b>DLP</b> = CTDI</i>vol × Scan Length</para>'
```

또는

```
ValueError: Parse error: saw </i> instead of expected </para>
paragraph text '<para>• > T2</i> 강조 영상보다도 3D 고해상도 기법인 SWI가 더 민감함</para>'
```

### 근본 원인

1. **이스케이프된 HTML 태그**: LLM이 생성한 텍스트에 `&lt;i&gt;` 같은 이스케이프된 HTML이 포함됨
2. **잘못된 태그 구조**: `<b>CTDI&lt;<br/>i&gt;<br/>w</b>` 같은 복잡한 구조
3. **태그 불균형**: `</i>` 태그가 열린 `<i>` 태그 없이 나타남
4. **`<para>` 태그 잔존**: ReportLab Paragraph는 자체적으로 para를 생성하므로 `<para>` 태그가 있으면 충돌

## 현재까지 시도한 수정 사항

### 1. `sanitize_html_for_reportlab` 함수 개선

**위치:** `3_Code/src/07_build_set_pdf.py` (line 496-690)

**추가된 기능:**
- 이스케이프된 HTML 태그 복원 (`&lt;i&gt;` → `<i>`)
- `<br/>` 태그 사이의 이스케이프된 태그 처리 (`&lt;<br/>i&gt;` → `<i>`)
- `<para>` 태그 제거 (다중 패스)
- 태그 밸런싱 (열린 태그와 닫힌 태그 개수 맞추기)
- orphaned closing tag 제거

**주요 변경사항:**
```python
# 이스케이프된 태그 복원
text = re.sub(r'&lt;(/?)i&gt;', r'<\1i>', text, flags=re.IGNORECASE)
text = re.sub(r'&lt;(/?)b&gt;', r'<\1b>', text, flags=re.IGNORECASE)

# 복잡한 패턴 처리: &lt;<br/>i&gt; → <i>
text = re.sub(r'&lt;\s*<br/>\s*([a-zA-Z]+)\s*&gt;', r'<\1>', text, flags=re.IGNORECASE)

# 태그 밸런싱
i_open = len(re.findall(r'<i\b[^>]*>', text, re.IGNORECASE))
i_close = len(re.findall(r'</i\b[^>]*>', text, re.IGNORECASE))
if i_close > i_open:
    # excess closing tags 제거
```

### 2. 카드 텍스트에 sanitize 적용

**위치:** `3_Code/src/07_build_set_pdf.py` (line 1939-1996)

**변경사항:**
- `front_text` (질문)에 `sanitize_html_for_reportlab` 적용
- `back_text` (답변)의 각 라인에 `sanitize_html_for_reportlab` 적용
- `options` (선택지)에 `sanitize_html_for_reportlab` 적용

### 3. 에러 처리 추가 (부분적)

**위치:** `3_Code/src/07_build_set_pdf.py` (line 2007-2016)

**변경사항:**
- Paragraph 생성 시 try-except 추가
- 실패 시 HTML 태그 제거 후 재시도
- 최종 fallback으로 "(Text formatting error)" 표시

**✅ 해결됨:** `re` 모듈 import 문제 수정 완료 (2025-12-22)

## 해결 방안 제안

### 옵션 1: S1/S2 데이터 재생성 (권장)

**장점:**
- 근본 원인 해결 (LLM이 잘못된 HTML을 생성하지 않도록)
- 다른 그룹에도 동일한 문제가 있을 수 있으므로 예방 효과
- 데이터 품질 향상

**단점:**
- 시간 소요 (LLM 호출 필요)
- 비용 발생

**추천 시나리오:**
- 실패한 2개 그룹만 재생성
- 또는 전체 Arm E 재생성 (다른 그룹에도 동일 문제 가능성)

### 옵션 2: build_pdf.py 수정 강화 (현재 진행 중)

**장점:**
- 빠른 해결
- 기존 데이터 재사용 가능

**단점:**
- 복잡한 HTML 구조를 모두 처리하기 어려움
- 새로운 패턴이 나타날 때마다 수정 필요

**추가 개선 필요 사항:**
1. `sanitize_html_for_reportlab` 함수의 태그 밸런싱 로직 강화
2. 에러 처리 로직 완성 (`re` 모듈 import 문제 해결)
3. 더 공격적인 HTML 정리 (모든 태그 제거 후 재구성)

### 옵션 3: 하이브리드 접근 (권장)

1. **즉시 해결**: build_pdf.py 수정 완성
   - 에러 처리 로직 완성
   - 더 강력한 HTML sanitization
   
2. **장기 해결**: 문제가 있는 S2 데이터 재생성
   - 실패한 2개 그룹 재생성
   - LLM 프롬프트에 HTML 태그 사용 지침 추가

## 다음 Agent를 위한 인계 사항

### 현재 파일 상태

**수정된 파일:**
- `3_Code/src/07_build_set_pdf.py`

**주요 수정 위치:**
1. `sanitize_html_for_reportlab()` 함수 (line 496-690)
   - 이스케이프된 HTML 태그 복원 로직 추가
   - 태그 밸런싱 로직 추가
   - `<para>` 태그 제거 강화

2. `build_cards_section()` 함수 (line 1939-2016)
   - 카드 텍스트에 `sanitize_html_for_reportlab` 적용
   - 에러 처리 추가 (부분적 완성)

### 해결된 이슈

1. **`re` 모듈 import 문제** ✅ **해결 완료** (2025-12-22)
   - try-except 블록 내에서 `import re`를 사용했으나, 블록 밖에서 `re`를 사용하려고 해서 `UnboundLocalError` 발생 가능성
   - 파일 상단(line 20)에 이미 `import re`가 있으므로, try-except 블록 내의 `import re` 제거 완료
   - **수정 위치:**
     - Line 1278, 1285, 1316, 1342, 1356, 1575, 1594, 2020, 2029: 모든 중복 `import re` 제거
   - **검증:** Linter 오류 없음, 테스트 성공

2. **에러 처리 로직** ✅ **완성됨**
   - 모든 try-except 블록 내의 `import re`를 제거하고 파일 상단의 import 사용
   - 에러 처리 로직이 올바르게 작동함

### 테스트 결과 ✅

**테스트 일시:** 2025-12-22  
**테스트 명령:**
```bash
python3 3_Code/src/tools/qa/generate_qa_pdfs_allow_missing_images.py \
    --run_tag S0_QA_final_time \
    --arm E \
    --out_dir 6_Distributions/QA_Packets/S0_final
```

**결과:**
- ✅ 총 18개 그룹 모두 성공
- ✅ 실패: 0개
- ✅ **이전에 실패했던 그룹도 성공:**
  - `grp_9b18e6ae4f` (quality_control__ct) ✅
  - `grp_bbb30c3ae8` (lung_bronchus__radiologic_anatomy) ✅

**결론:** 수정 사항이 문제를 완전히 해결함. 모든 PDF 생성 성공.

### 해결 완료 사항

1. ✅ **`re` 모듈 import 중복 제거** - 완료
2. ✅ **에러 처리 로직 완성** - 완료
3. ✅ **테스트 검증** - 모든 그룹 성공

### 실패한 그룹 정보

**grp_9b18e6ae4f:**
- group_key: `quality_control__ct`
- specialty: `phys_qc_medinfo`
- 문제 텍스트: `CTDI&lt;<br/>i&gt;<br/>w` → `CTDI<i>w`로 변환 필요

**grp_bbb30c3ae8:**
- group_key: `lung_bronchus__radiologic_anatomy`
- specialty: `thoracic_rad`
- 문제 텍스트: `• > T2</i>` → orphaned `</i>` 태그

## 참고 파일

- `3_Code/src/07_build_set_pdf.py` - PDF 생성 스크립트 (수정됨)
- `3_Code/src/tools/qa/generate_qa_pdfs_allow_missing_images.py` - PDF 생성 래퍼
- `2_Data/metadata/generated/S0_QA_final_time/s2_results__armE.jsonl` - S2 데이터 (문제 텍스트 포함)

