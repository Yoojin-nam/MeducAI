# PDF Generation and Formatting History

**Last Updated**: 2026-01-06  
**Purpose**: PDF 생성 및 포맷팅 구현 기록  
**Scope**: FINAL_DISTRIBUTION PDF 배포 문서 생성 관련 작업

---

## 개요

본 문서는 MeducAI FINAL_DISTRIBUTION의 PDF 배포 문서 생성 및 포맷팅 작업을 시간순으로 정리합니다.

---

## Timeline

### 2026-01-06: PDF 최종 배포 구현 완료

**문서**: `HANDOFF_2026-01-06_PDF_Final_Implementation.md`

#### 요구사항 요약

**1. 목차 (TOC)**
- [x] 각 specialty의 **시작 페이지 번호만** 표시
- [x] 하이퍼링크로 해당 섹션으로 이동
- 예시:
  ```
  CONTENTS
  
  Abdominal Radiology ................... 5
  Breast Radiology ...................... 142
  ```

**2. 헤더 박스 (모든 페이지)**
- [x] 그라데이션 배경 (Deep Navy → Ocean Blue)
- [x] 경로 표시: `CONTENTS › SPECIALTY › REGION › MODALITY › CATEGORY`
- [x] 섹션 타입: `| OBJECTIVE GOAL`, `| MASTER TABLE`, `| INFOGRAPHIC`
- [x] 우측에 `MeducAI` 로고
- [x] **헤더 내용이 페이지 내용과 일치** (afterFlowable 메서드로 해결)
- [ ] 경로 각 세그먼트에 하이퍼링크 (현재 미구현 - 복잡도 높음)

**3. 학습 목표**
- [x] **한글 학습목표** 출력 (`groups_canonical.csv`의 `objective_list_kr` 사용)
- [x] 페이지 중간에서 끊기지 않도록 `KeepTogether` 적용
- [x] 9pt 폰트 크기

**4. 테이블 포맷팅**
- [x] 헤더와 셀 모두 9pt
- [x] 엔티티명 컬럼: **항상 볼드체**
- [x] 마크다운 파싱: `**볼드**` → `<b>볼드</b>`
- [x] 줄바꿈 규칙:
  - 엔티티명: `&` 뒤, `(` 앞에서 줄바꿈
  - 2번째 컬럼: `(` 앞, 세미콜론 뒤
  - 나머지: 세미콜론 뒤
- [x] 의학 약어 자동 볼드: CT, MRI, US 등

#### 핵심 구현 사항

**1. HeaderTrackingDocTemplate** ✅

**문제**: `SimpleDocTemplate`의 콜백 타이밍 문제로 헤더 정보가 페이지 내용과 불일치

**해결**: `BaseDocTemplate`의 `afterFlowable()` 메서드 활용

```python
class HeaderTrackingDocTemplate(BaseDocTemplate):
    def __init__(self, *args, **kwargs):
        self.current_header_info = {
            'group_path': '',
            'section_type': '',
            'bookmark': '',
        }
        BaseDocTemplate.__init__(self, *args, **kwargs)
    
    def afterFlowable(self, flowable):
        """Flowable이 배치된 직후 호출 - 헤더 정보 업데이트 타이밍이 완벽"""
        if isinstance(flowable, HeaderInfoFlowable):
            self.current_header_info = {
                'group_path': flowable.group_path,
                'section_type': flowable.section_type,
                'bookmark': flowable.bookmark,
            }
```

**핵심 포인트**:
- `afterFlowable()`은 Flowable이 페이지에 배치된 **직후** 호출됨
- `doc.current_header_info`는 페이지 렌더링 중에 지속됨
- 헤더 콜백에서 `doc.current_header_info`를 읽으면 항상 최신 정보

**2. HeaderInfoFlowable** ✅

**역할**:
1. 헤더 정보 전달 (group_path, section_type)
2. 북마크 앵커 생성 (TOC 하이퍼링크용)

```python
class HeaderInfoFlowable(Flowable):
    def __init__(self, group_path: str, section_type: str, bookmark: str = ""):
        Flowable.__init__(self)
        self.group_path = group_path
        self.section_type = section_type
        self.bookmark = bookmark
        self.width = 0  # 공간 차지하지 않음
        self.height = 0
    
    def draw(self):
        """북마크 앵커 등록"""
        if self.bookmark:
            self.canv.bookmarkPage(self.bookmark)
```

**사용 예시**:
```python
# Objective Goal 섹션 시작
bookmark = f"{bookmark_base}_OBJECTIVE"
story.append(HeaderInfoFlowable(group_path, "OBJECTIVE GOAL", bookmark))

# 실제 컨텐츠
for obj in objectives:
    story.append(Paragraph(f"• {obj}", styles["Objective"]))
```

**3. PageTemplate with Custom Frame** ✅

```python
def create_main_page_template(
    page_size: tuple,
    korean_font: str = "Helvetica",
    margins: Optional[Dict[str, float]] = None,
) -> PageTemplate:
    """
    커스텀 PageTemplate 생성
    - Frame으로 컨텐츠 영역 정의
    - onPage 콜백으로 헤더/푸터 그리기
    """
    if margins is None:
        margins = {
            'left': 0.75 * cm,
            'right': 0.75 * cm,
            'top': HEADER_HEIGHT + 0.5 * cm,
            'bottom': FOOTER_HEIGHT + 0.5 * cm,
        }
    
    def draw_header_footer(canvas_obj, doc):
        """헤더와 푸터 그리기 - doc.current_header_info에서 정보 읽기"""
        canvas_obj.saveState()
        draw_modern_header(canvas_obj, doc, korean_font)
        page_num = canvas_obj.getPageNumber()
        draw_modern_footer(canvas_obj, doc, page_num)
        canvas_obj.restoreState()
    
    frame = Frame(
        margins['left'], margins['bottom'],
        frame_width, frame_height,
        id='normal', showBoundary=0,
    )
    
    return PageTemplate(id='Main', frames=[frame], onPage=draw_header_footer)
```

#### 구현 파일

**Main Script**: `3_Code/src/tools/build_distribution_pdf.py`

**Features**:
- HeaderTrackingDocTemplate 클래스
- HeaderInfoFlowable 클래스
- Modern header/footer drawing functions
- Table formatting with markdown parsing
- Automatic line breaking for medical terms
- Korean font support

---

### 2026-01-06: PDF Header Fix

**문서**: `HANDOFF_2026-01-06_PDF_Header_Fix.md`

#### 문제

PDF 헤더의 specialty/region/modality 정보가 페이지 내용과 불일치하는 문제 발생

#### 원인

`SimpleDocTemplate`의 `beforeBuildDoc` 콜백이 페이지 렌더링 전에 호출되어, 헤더가 이전 페이지의 정보를 표시함

#### 해결

`BaseDocTemplate`의 `afterFlowable()` 메서드를 사용하여 Flowable이 페이지에 배치된 직후 헤더 정보를 업데이트

---

### 2026-01-06: Markdown Bold Removal

**문서**: `HANDOFF_2026-01-06_Markdown_Bold_Removal.md`, `HANDOFF_2026-01-06_Markdown_Bold_Fix.md`

#### 문제

Assignment CSV 파일에 markdown bold syntax (`**text**`)가 그대로 포함되어 AppSheet에서 표시됨

#### 해결

**스크립트**: `3_Code/src/tools/final_qa/export_appsheet_tables.py`

**수정 사항**:
```python
def remove_markdown_bold(text: str) -> str:
    """Remove **bold** markdown syntax"""
    if not text:
        return text
    return re.sub(r'\*\*(.+?)\*\*', r'\1', text)
```

**적용 필드**:
- `card_front`
- `card_back`
- `image_caption`
- All text fields in Cards.csv and Assignments.csv

---

## PDF 생성 워크플로우

### 1. Data Collection
```
groups_canonical.csv + s2_results.jsonl + images/ → build_distribution_pdf.py
```

### 2. PDF Structure
```
Cover Page
  ↓
Table of Contents (with page numbers and hyperlinks)
  ↓
For each specialty:
  ↓
  For each group:
    ↓
    [HeaderInfoFlowable] (invisible, updates header)
    Objective Goals (Korean, KeepTogether)
    Master Table (formatted, bold entities)
    Infographic (image, KeepTogether)
    Q1/Q2 Cards (if applicable)
```

### 3. Header/Footer Rendering
```
onPage callback:
  ↓
  Read doc.current_header_info (set by afterFlowable)
  ↓
  Draw gradient header with breadcrumb
  Draw footer with page number
```

---

## 생성된 파일

**Output**: `FINAL_DISTRIBUTION_armG.pdf`

**Location**: `6_Distributions/MeducAI_Final_Share/`

**Stats**:
- 321 groups
- ~500-800 pages (depending on content)
- File size: ~50-100 MB (with images)

---

## 스타일 가이드

### Colors

**Header Gradient**:
- Start: Deep Navy `#1a237e`
- End: Ocean Blue `#1e88e5`

**Text Colors**:
- Header text: White `#ffffff`
- Body text: Black `#000000`
- Footer text: Gray `#666666`

### Fonts

**Korean**:
- Primary: NanumGothic (if available)
- Fallback: Helvetica

**English**:
- Primary: Helvetica
- Bold: Helvetica-Bold

### Font Sizes

| Element | Size |
|---------|------|
| Header breadcrumb | 9pt |
| Header section type | 8pt |
| Objective goals | 9pt |
| Table header | 9pt (bold) |
| Table cells | 9pt |
| Footer page number | 8pt |

---

## 알려진 이슈

### 1. 헤더 하이퍼링크 미구현
- 현재: 헤더의 breadcrumb은 텍스트만 표시
- 향후: 각 세그먼트 클릭 시 해당 섹션으로 이동 (복잡도 높음)

### 2. 긴 테이블 분할
- 현재: 테이블이 페이지를 넘어갈 경우 자동 분할
- 이슈: 헤더 행이 다음 페이지에 반복되지 않음
- 해결: `repeatRows=1` 옵션 추가 (partially implemented)

### 3. 이미지 품질
- 현재: JPEG 품질 85로 저장
- 이슈: 고해상도 모니터에서 약간 흐릿할 수 있음
- 해결: 필요시 quality 90으로 상향

---

## 관련 스크립트

### PDF Generation
```
3_Code/src/tools/
  └── build_distribution_pdf.py      # Main PDF builder
```

### AppSheet Export
```
3_Code/src/tools/final_qa/
  └── export_appsheet_tables.py      # CSV export with markdown removal
```

---

## 참고 문서

### Protocol 문서
- `0_Protocol/06_QA_and_Study/QA_Operations/FINAL_QA_Design_and_Endpoints.md`

### 5_Meeting 원본 문서
- `HANDOFF_2026-01-06_PDF_Final_Implementation.md`
- `HANDOFF_2026-01-06_PDF_Header_Fix.md`
- `HANDOFF_2026-01-06_Markdown_Bold_Removal.md`
- `HANDOFF_2026-01-06_Markdown_Bold_Fix.md`

---

**문서 작성일**: 2026-01-06  
**최종 업데이트**: 2026-01-06  
**상태**: 통합 완료

