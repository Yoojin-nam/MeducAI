# 07_build_set_pdf.py 함수 파라미터 정리

## Path Utilities

### `get_generated_dir(base_dir: Path, run_tag: str) -> Path`
- `base_dir`: 프로젝트 기본 디렉토리
- `run_tag`: 실행 태그 (예: "TEST_S2_V7_20251220_105343")

### `get_images_dir(base_dir: Path, run_tag: str) -> Path`
- `base_dir`: 프로젝트 기본 디렉토리
- `run_tag`: 실행 태그

---

## Data Loading Functions

### `load_s1_struct(s1_path: Path, group_id: str) -> Optional[Dict[str, Any]]`
- `s1_path`: S1 구조 파일 경로
- `group_id`: 그룹 ID (예: "G0123")

### `load_s2_results(s2_path: Path, group_id: str) -> List[Dict[str, Any]]`
- `s2_path`: S2 결과 파일 경로
- `group_id`: 그룹 ID

### `load_s3_policy_manifest(manifest_path: Path, group_id: str) -> Dict[Tuple[str, str], Dict[str, Any]]`
- `manifest_path`: S3 정책 매니페스트 파일 경로
- `group_id`: 그룹 ID
- **반환**: `(entity_id, card_role) -> policy_entry` 매핑

### `load_s4_image_manifest(manifest_path: Path, group_id: str, base_dir: Path, run_tag: str) -> Dict[Tuple[str, Optional[str], Optional[str]], str]`
- `manifest_path`: S4 이미지 매니페스트 파일 경로
- `group_id`: 그룹 ID
- `base_dir`: 프로젝트 기본 디렉토리
- `run_tag`: 실행 태그
- **반환**: `(spec_kind, entity_id, card_role) -> image_path` 매핑

### `load_surrogate_map(csv_path: Path) -> Dict[Tuple[str, str], str]`
- `csv_path`: 대체 ID 매핑 CSV 파일 경로
- **반환**: `(group_id, arm) -> surrogate_set_id` 매핑

---

## Text Processing Functions

### `parse_markdown_formatting(text: str) -> str`
- `text`: 마크다운 형식이 포함된 텍스트

### `sanitize_html_for_reportlab(text: str) -> str`
- `text`: HTML 태그가 포함된 텍스트

**Operational note (ReportLab hard-fail prevention):**
- ReportLab `paraparser` will hard-fail on malformed tags such as `"<br/<b>..."` (i.e., `<br/` immediately
  followed by a new tag opener).
- The PDF builder MUST sanitize such malformed sequences before feeding into ReportLab Paragraph parsing.
- Implementation reference: `3_Code/src/07_build_set_pdf.py` (look for `sanitize_html_for_reportlab()` and the
  specific fix that rewrites `<br/<` to `<br/><`).

### `bold_important_terms(text: str) -> str`
- `text`: 의학 용어가 포함된 텍스트

### `parse_markdown_table(md_table: str) -> Tuple[List[str], List[List[str]]]`
- `md_table`: 마크다운 테이블 문자열
- **반환**: `(headers, rows)` 튜플

---

## PDF Generation Functions

### `register_korean_font() -> Tuple[str, str]`
- 파라미터 없음
- **반환**: `(korean_font_name, korean_font_bold_name)` 튜플

### `create_pdf_styles() -> Tuple[Any, Dict[str, ParagraphStyle], str, str]`
- 파라미터 없음
- **반환**: `(styles, custom_styles, korean_font, korean_font_bold)` 튜플

### `parse_group_path_from_s1(s1_record: Dict[str, Any]) -> Tuple[str, str, Optional[str]]`
- `s1_record`: S1 레코드 딕셔너리 (group_path 또는 group_key 포함)
- **반환**: `(subspecialty, region, category)` 튜플
- **동작**: 
  - 우선 `group_path` 파싱 (형식: "specialty > anatomy > modality > category")
  - `group_path`가 없으면 `group_key` 파싱 (형식: "subspecialty__region__category")

### `build_master_table_section(...) -> None`
- `story: List` - PDF 스토리 리스트 (출력용)
- `master_table_md: str` - 마스터 테이블 마크다운
- `custom_styles: Dict[str, ParagraphStyle]` - 커스텀 스타일 딕셔너리
- `page_width: float` - 페이지 너비
- `page_height: float` - 페이지 높이
- `korean_font: str` - 한글 폰트 이름
- `korean_font_bold: str` - 한글 볼드 폰트 이름
- `s1_record: Optional[Dict[str, Any]] = None` - S1 레코드 (헤더 생성용, group_path/group_key 포함)
- `specialty: Optional[str] = None` - 전문과 (결합 PDF 모드용)

### `build_infographic_section(...) -> None`
- `story: List` - PDF 스토리 리스트
- `image_path: Optional[str]` - 인포그래픽 이미지 경로
- `custom_styles: Dict[str, ParagraphStyle]` - 커스텀 스타일 딕셔너리
- `allow_missing: bool = False` - 이미지 누락 허용 여부
- `page_width: Optional[float] = None` - 페이지 너비
- `page_height: Optional[float] = None` - 페이지 높이

### `build_cards_section(...) -> None`
- `story: List` - PDF 스토리 리스트
- `s2_records: List[Dict[str, Any]]` - S2 결과 레코드 리스트
- `policy_mapping: Dict[Tuple[str, str], Dict[str, Any]]` - 정책 매핑 `(entity_id, card_role) -> policy`
- `image_mapping: Dict[Tuple[str, Optional[str], Optional[str]], str]` - 이미지 매핑 `(spec_kind, entity_id, card_role) -> image_path`
- `custom_styles: Dict[str, ParagraphStyle]` - 커스텀 스타일 딕셔너리
- `page_width: float` - 페이지 너비
- `page_height: float` - 페이지 높이
- `allow_missing_images: bool = False` - 이미지 누락 허용 여부

### `build_set_pdf(...) -> Path`
- `base_dir: Path` - 프로젝트 기본 디렉토리 (키워드 전용)
- `run_tag: str` - 실행 태그 (키워드 전용)
- `arm: str` - Arm 식별자 (A-F) (키워드 전용)
- `group_id: str` - 그룹 ID (키워드 전용)
- `out_dir: Path` - 출력 디렉토리 (키워드 전용)
- `blinded: bool = False` - 블라인드 모드 활성화 여부 (키워드 전용)
- `surrogate_map: Optional[Dict[Tuple[str, str], str]] = None` - 대체 ID 매핑 (키워드 전용)
- `allow_missing_images: bool = False` - 이미지 누락 허용 여부 (키워드 전용)
- **반환**: 생성된 PDF 파일 경로

---

## CLI Function

### `main() -> None`
- 파라미터 없음 (argparse로 CLI 인자 파싱)

### CLI Arguments (argparse)
- `--base_dir` (str, default=".") - 프로젝트 기본 디렉토리
- `--run_tag` (str, required) - 실행 태그
- `--arm` (str, required) - Arm 식별자 (A-F)
- `--group_id` (str, required) - 그룹 ID
- `--out_dir` (str, default="6_Distributions/QA_Packets") - 출력 디렉토리
- `--blinded` (flag) - 블라인드 모드 활성화
- `--set_surrogate_csv` (str, default="0_Protocol/06_QA_and_Study/QA_Operations/surrogate_map.csv") - 대체 ID 매핑 CSV 경로
- `--allow_missing_images` (flag) - 이미지 누락 허용 (**미리보기/디버그용**; 최종 배포는 upstream(S4)에서 이미지 누락을 해결하고 이 옵션 없이 생성)

---

## 주요 데이터 구조

### Policy Mapping
```python
Dict[Tuple[str, str], Dict[str, Any]]
# 키: (entity_id, card_role)
# 값: {
#     "image_placement": "FRONT" | "BACK" | "NONE",
#     "card_type": "BASIC" | "MCQ" | "MCQ_VIGNETTE",
#     "image_required": bool,
#     ...
# }
```

### Image Mapping
```python
Dict[Tuple[str, Optional[str], Optional[str]], str]
# 키: (spec_kind, entity_id, card_role)
# 값: image_path (절대 경로 문자열)
# 예: ("S2_CARD_IMAGE", "DERIVED_123", "Q1") -> "/path/to/image.png"
```

### Surrogate Map
```python
Dict[Tuple[str, str], str]
# 키: (group_id, arm)
# 값: surrogate_set_id
```


