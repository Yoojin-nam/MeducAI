# PDF 생성 문제 수정 검토 및 진행 방안

**작성일:** 2025-12-22  
**검토자:** AI Agent  
**기반 문서:** `PDF_GENERATION_ISSUE_REPORT.md`

## 수정 완료 사항

### 1. `re` 모듈 import 중복 제거 ✅

**문제:**
- 파일 상단(line 20)에 `import re`가 있음에도 불구하고, try-except 블록 내부에 중복 `import re`가 9곳에 존재
- 이는 `UnboundLocalError`를 발생시킬 수 있음

**수정 위치:**
- Line 1278: `get_text_length` 함수 내부
- Line 1285: `measure_text_width` 함수 내부
- Line 1316: `find_longest_word` 함수 내부
- Line 1342: `calculate_column_min_width` 함수 내부
- Line 1356: `calculate_column_min_width` 함수 내부 (중첩)
- Line 1575: `build_master_table_section` 함수 내부
- Line 1594: `build_master_table_section` 함수 내부 (중첩)
- Line 2020: `build_cards_section` 함수 내부 (에러 처리)
- Line 2029: `build_cards_section` 함수 내부 (에러 처리)

**검증:**
- 모든 중복 `import re` 제거 완료
- 파일 상단의 `import re`만 사용하도록 통일
- Linter 오류 없음

## 코드 검토 결과

### 2. `sanitize_html_for_reportlab` 함수 로직 분석

#### 현재 처리 순서

1. **Markdown 파싱** (line 513)
   - `parse_markdown_formatting()` 호출

2. **`<para>` 태그 제거** (line 517-518)
   - 3번 반복하여 중첩/잘못된 para 태그 제거

3. **이스케이프된 HTML 태그 복원** (line 525-555)
   - `&lt;br/&gt;` → `<br/>`
   - `&lt;i&gt;` → `<i>`, `&lt;/i&gt;` → `</i>`
   - `&lt;b&gt;` → `<b>`, `&lt;/b&gt;` → `</b>`
   - 복잡한 패턴: `&lt;<br/>i&gt;` → `<i>`
   - 특수 패턴: `text&lt;<br/>tag&gt;<br/>text` → `text<tag>text`

4. **태그 밸런싱 (1차)** (line 574-576)
   - `i`, `b`, `para` 태그 밸런싱

5. **`fix_tag_content` 함수 실행** (line 663)
   - 태그 내용 내부의 잘못된 `<`, `>` 이스케이프
   - ⚠️ **잠재적 문제점**: 이미 복원된 태그를 다시 이스케이프할 수 있음

6. **최종 `<para>` 태그 제거** (line 668-676)
   - 5번 반복하여 완전히 제거

7. **최종 태그 밸런싱** (line 681-708)
   - `i`, `b` 태그의 orphaned closing tag 제거

8. **`<br>` 태그 정규화** (line 710-714)
   - `<br>` → `<br/>` 변환

#### 인계장 문제 케이스 처리 분석

**케이스 1: `CTDI&lt;<br/>i&gt;<br/>w` → `CTDI<i>w`**

현재 로직으로 처리 가능:
- Line 537: `&lt;<br/>i&gt;` → `<i>` 패턴 처리
- Line 552: `text&lt;<br/>tag&gt;<br/>text` 패턴 처리
- Line 548: `<br/>` 태그 제거

**예상 처리 흐름:**
```
CTDI&lt;<br/>i&gt;<br/>w
→ (line 537) CTDI<i><br/>w
→ (line 552) CTDI<i>w  (fix_split_escaped_tags가 <br/> 제거)
```

**케이스 2: `• > T2</i>` → orphaned `</i>` 태그 제거**

현재 로직으로 처리 가능:
- Line 681-695: orphaned `</i>` 태그 제거 로직
- Opening tag가 없으면 closing tag 제거

#### 잠재적 문제점

1. **`fix_tag_content` 함수의 과도한 이스케이프**
   - Line 597-600에서 태그 내용 내부의 `<`, `>`를 이스케이프
   - 이미 복원된 태그(`<i>`, `<b>`)가 다시 이스케이프될 수 있음
   - 예: `<b>CTDI<i>w</b>` → `fix_tag_content` 실행 시 → `<b>CTDI&lt;i&gt;w</b>`로 변환될 수 있음

2. **순서 문제**
   - 이스케이프된 태그를 복원한 후 `fix_tag_content`가 실행되면, 복원된 태그가 다시 이스케이프될 수 있음
   - 하지만 `fix_tag_content`의 패턴(line 607)은 `<tag>content</tag>` 형태만 처리하므로, 실제로는 문제가 없을 수 있음

3. **복잡도**
   - `fix_tag_content` 함수가 매우 복잡함 (line 582-661)
   - 여러 단계의 정규식 처리와 중첩된 함수로 인해 디버깅이 어려움

## 권장 사항

### 즉시 조치 (완료)

1. ✅ **`re` 모듈 import 중복 제거** - 완료
2. ✅ **에러 처리 로직 일관성 확인** - 모든 에러 처리에서 `re` 모듈 올바르게 사용

### 단기 조치 (권장)

1. **테스트 실행**
   ```bash
   python3 3_Code/src/tools/qa/generate_qa_pdfs_allow_missing_images.py \
       --run_tag S0_QA_final_time \
       --arm E \
       --out_dir 6_Distributions/QA_Packets/S0_final
   ```
   - 실패했던 2개 그룹(`grp_9b18e6ae4f`, `grp_bbb30c3ae8`)이 이제 성공하는지 확인

2. **실패 시 추가 디버깅**
   - 실패한 경우, 실제 입력 텍스트와 `sanitize_html_for_reportlab` 출력 비교
   - `fix_tag_content` 함수가 문제를 일으키는지 확인

### 중기 조치 (선택적)

1. **`fix_tag_content` 함수 개선**
   - 현재 로직이 너무 복잡하고, 일부 케이스에서 오히려 문제를 만들 수 있음
   - 더 단순하고 안전한 로직으로 리팩토링 고려
   - 또는 `fix_tag_content` 실행 전에 이미 복원된 태그를 보호하는 로직 추가

2. **단위 테스트 추가**
   - 인계장에서 언급한 문제 케이스에 대한 단위 테스트 작성
   - `sanitize_html_for_reportlab` 함수의 다양한 입력에 대한 테스트

### 장기 조치 (근본 해결)

1. **S2 데이터 재생성**
   - 실패한 2개 그룹의 S2 데이터 재생성
   - LLM 프롬프트에 HTML 태그 사용 지침 추가
   - "HTML 태그를 올바르게 사용하라"는 명시적 지침

2. **프롬프트 개선**
   - LLM이 이스케이프된 HTML을 생성하지 않도록 프롬프트 개선
   - 예: "HTML 태그를 사용할 때는 `&lt;` 대신 `<`를 직접 사용하라"

## 테스트 결과 ✅

**테스트 일시:** 2025-12-22  
**결과:** ✅ **성공**

```
Total groups: 18
Successfully generated: 18
Failed: 0
```

**특히 이전에 실패했던 그룹도 성공:**
- `grp_9b18e6ae4f` (quality_control__ct) ✅
- `grp_bbb30c3ae8` (lung_bronchus__radiologic_anatomy) ✅

**결론:** 수정 사항이 문제를 완전히 해결함. 모든 PDF 생성 성공.

## 해결 완료

1. ✅ **`re` 모듈 import 중복 제거** - 완료
2. ✅ **에러 처리 로직 완성** - 완료
3. ✅ **테스트 검증** - 모든 그룹 성공
4. ✅ **인계장 업데이트** - 완료

## 참고

- 수정된 파일: `3_Code/src/07_build_set_pdf.py`
- 검토 기준: `3_Code/src/tools/qa/PDF_GENERATION_ISSUE_REPORT.md`
- 관련 스크립트: `3_Code/src/tools/qa/generate_qa_pdfs_allow_missing_images.py`

