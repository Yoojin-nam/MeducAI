# Gemini API 키 테스트 가이드

## 개요

`test_gemini_api_key.py` 스크립트는 새로 발급받은 Gemini API 키가 정상 작동하는지 확인하고, `gemini-3-pro-image-preview` 모델의 사용 가능 여부를 테스트합니다.

## 사용 방법

```bash
# 프로젝트 루트에서 실행
cd /path/to/workspace/workspace/MeducAI
python3 3_Code/src/tools/test_gemini_api_key.py
```

## 테스트 내용

1. **API 키 확인**: `GOOGLE_API_KEY` 환경 변수가 설정되어 있는지 확인
2. **API 연결 테스트**: Gemini API에 연결하여 모델 목록 조회
3. **이미지 생성 테스트**: `gemini-3-pro-image-preview` 모델로 간단한 이미지 생성 (1K, 1:1 비율)

## 예상 출력

```
======================================================================
Gemini API 키 및 gemini-3-pro-image 모델 테스트
======================================================================

======================================================================
1. API 키 확인
======================================================================
✅ API 키 확인됨 (길이: 39자)
   키 앞부분: AIzaSyDjwo...lrEk

======================================================================
2. Gemini API 연결 테스트 (모델 목록 조회)
======================================================================
✅ API 연결 성공! 총 XX개 모델 발견

📸 이미지 생성 모델 (X개):
   - models/gemini-2.5-flash-image
   - models/gemini-3-pro-image-preview
   - ...

✅ gemini-3-pro-image-preview 모델 사용 가능:
   - models/gemini-3-pro-image-preview

======================================================================
3. 이미지 생성 테스트
======================================================================
테스트 프롬프트: A simple geometric shape: a blue circle on a white background
모델: models/gemini-3-pro-image-preview

이미지 생성 중... (10-30초 소요될 수 있습니다)
✅ 이미지 생성 성공!
   생성된 이미지: 2_Data/metadata/temp/test_api_key_image.jpg
   이미지 크기: 45,234 bytes (44.2 KB)

======================================================================
테스트 결과 요약
======================================================================
✅ API 키: 설정됨
✅ API 연결: 성공
✅ 이미지 생성: 성공

🎉 모든 테스트 통과! API 키가 정상 작동하며 이미지 생성이 가능합니다.
   gemini-3-pro-image 모델을 사용할 수 있습니다.
======================================================================
```

## 에러 상황 및 해결 방법

### Rate Limit / Quota 에러

```
❌ Rate Limit / Quota 에러 발생!
   에러 메시지: 429 Resource exhausted: Quota exceeded
```

**의미**: API 키는 정상이지만 일일 요청 제한(RPD)이 초과되었거나 부족합니다.

**해결 방법**:
- Google Cloud Console에서 할당량 확인
- 더 낮은 tier의 모델 사용 고려 (예: `gemini-2.5-flash-image`)
- 다음날 다시 시도

### 권한 에러 (403)

```
❌ 권한 에러 발생!
   에러 메시지: 403 Permission denied
```

**의미**: API 키에 `gemini-3-pro-image-preview` 모델 사용 권한이 없습니다.

**해결 방법**:
- Google Cloud Console에서 "Generative Language API" 활성화 확인
- API 키에 적절한 권한이 있는지 확인

### 인증 에러 (401)

```
❌ 인증 에러 발생!
   에러 메시지: 401 Invalid API key
```

**의미**: API 키가 유효하지 않거나 만료되었습니다.

**해결 방법**:
- 새로운 API 키 발급
- `.env` 파일에 올바른 키 설정

## RPD (Rate Per Day) 예상 사용량

### S4 이미지 생성 시 예상 사용량

**per arm 기준**:
- 카드 이미지: 18 그룹 × 4 엔티티 × 3 카드 = **216개** (1K 해상도, 각각 ~1,120 토큰)
- 테이블 비주얼: 18 그룹 × 1 = **18개** (4K 해상도, 각각 ~2,000 토큰)
- **총 이미지 수**: 234개 per arm

**6 arms 기준**:
- **총 이미지 수**: 234 × 6 = **1,404개**
- **예상 토큰 사용량**: 
  - 카드 이미지: 216 × 6 × 1,120 = 1,451,520 토큰
  - 테이블 이미지: 18 × 6 × 2,000 = 216,000 토큰
  - **총 예상 토큰**: ~1,667,520 토큰

**참고**: 
- gemini-3-pro-image-preview의 RPD 제한은 Google Cloud Console에서 확인 가능
- Preview 모델은 일반적으로 제한이 더 낮을 수 있음
- 실제 실행 시 rate limit 에러가 발생하면 할당량 증가를 요청하거나 배치 처리 고려

## 관련 문서

- [Gemini Pricing](0_Protocol/00_Governance/supporting/LLM-operation/Gemini_price.md)
- [S4 Image Generator Documentation](3_Code/src/04_s4_image_generator.py)

