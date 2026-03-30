# AppSheet Image Path 설정 문제 해결 프롬프트 (ChatGPT MCP용)

## 문제 상황

AppSheet 앱에서 Google Drive의 이미지 파일을 표시하려고 하는데, 이미지가 보이지 않습니다.

## 현재 설정 상태

1. **데이터 소스**: Google Sheets (Google Drive에 위치)
   - Sheet 파일명: `qa_appsheet_db` (또는 사용자가 지정한 이름)
   - Sheet 위치: `/내 드라이브/Research/MeducAI/QA_AppSheet_MVP/DEV_armG_mm_S5R0_before_rerun_preFix_20251229_195130__rep1/`

2. **이미지 파일 위치**:
   - Drive 폴더: `/내 드라이브/Research/MeducAI/QA_AppSheet_MVP/DEV_armG_mm_S5R0_before_rerun_preFix_20251229_195130__rep1/images/`
   - 이미지 파일 수: 330개
   - 파일명 예시: `IMG__DEV_armG_mm_S5R0_before_rerun_preFix_20251229_195130__rep1__grp_cbcba66e24__DERIVED_2474fe1efffb__Q1.jpg`

3. **AppSheet 설정**:
   - 테이블: `Cards`
   - 컬럼: `image_filename` (Type: Image)
   - 컬럼 값: 파일명만 저장됨 (예: `IMG__DEV_armG_mm_S5R0_before_rerun_preFix_20251229_195130__rep1__grp_cbcba66e24__DERIVED_2474fe1efffb__Q1.jpg`)
   - "Image/File folder path" 필드: 현재 비어있거나 시도한 값이 작동하지 않음

## 원하는 결과

- AppSheet 앱에서 `Cards` 테이블의 각 행을 열었을 때, `image_filename` 컬럼에 해당하는 이미지가 정상적으로 표시되어야 합니다.

## 질문

1. **"Image/File folder path" 필드에 정확히 무엇을 입력해야 하나요?**
   - Sheet와 images 폴더가 같은 Drive 폴더에 있는 경우
   - Sheet와 images 폴더가 다른 위치에 있는 경우
   - 각각의 정확한 경로 형식 (상대 경로 vs 절대 경로)

2. **Google Drive 권한 설정이 필요한가요?**
   - images 폴더의 공유 설정은 어떻게 해야 하나요?
   - "Anyone with the link can view" vs "Specific people" 중 어떤 것이 AppSheet에서 작동하나요?

3. **AppSheet의 데이터 소스 연결 방식**
   - AppSheet가 Google Drive 폴더를 어떻게 인식하나요?
   - Sheet 파일과 같은 폴더를 기준으로 상대 경로를 사용하나요, 아니면 절대 경로가 필요한가요?

4. **대안 방법이 있나요?**
   - image_filename 컬럼에 전체 Drive URL을 저장하는 방법이 더 나을까요?
   - 다른 접근 방식이 있나요?

## 추가 정보

- AppSheet 버전: 최신 버전 (2025년 기준)
- 데이터 소스: Google Sheets (Google Drive)
- 이미지 형식: JPG
- 이미지 파일명: Cards.csv의 `image_filename` 컬럼에 파일명만 저장됨 (경로 없음)

## 요청

위 문제를 해결하기 위한 **구체적이고 단계별로 실행 가능한 해결 방법**을 제공해주세요. 특히 "Image/File folder path" 필드에 입력할 정확한 값과 그 이유를 설명해주세요.

