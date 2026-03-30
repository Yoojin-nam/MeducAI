#!/usr/bin/env python3
"""
Gemini API 키 및 gemini-3-pro-image 모델 테스트 스크립트

이 스크립트는:
1. GOOGLE_API_KEY 환경 변수가 설정되어 있는지 확인
2. Gemini API 연결 테스트 (모델 목록 조회)
3. gemini-3-pro-image-preview 모델로 간단한 이미지 생성 테스트
4. Rate limit 에러 확인

사용법:
    python3 3_Code/src/tools/test_gemini_api_key.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def print_header(title: str):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def test_api_key_presence():
    """API 키가 환경 변수에 설정되어 있는지 확인"""
    print_header("1. API 키 확인")
    
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not api_key:
        print("❌ GOOGLE_API_KEY 환경 변수가 설정되어 있지 않습니다.")
        print("   .env 파일에 GOOGLE_API_KEY를 추가하거나 환경 변수를 설정해주세요.")
        return None
    
    # API 키 형식 확인 (일반적으로 길이가 39자 이상)
    if len(api_key) < 20:
        print(f"⚠️  API 키 길이가 짧습니다 ({len(api_key)}자). 올바른 키인지 확인해주세요.")
    else:
        print(f"✅ API 키 확인됨 (길이: {len(api_key)}자)")
        print(f"   키 앞부분: {api_key[:10]}...{api_key[-4:]}")
    
    return api_key


def test_model_listing(api_key: str):
    """모델 목록 조회를 통한 API 연결 테스트"""
    print_header("2. Gemini API 연결 테스트 (모델 목록 조회)")
    
    try:
        from google import genai
    except ImportError:
        print("❌ google.genai가 설치되어 있지 않습니다.")
        print("   설치: pip install -U google-genai")
        return False, []
    
    try:
        client = genai.Client(api_key=api_key)
        models = client.models.list()
        
        model_names = []
        image_models = []
        
        for model in models:
            if isinstance(model, str):
                model_name = model
            elif hasattr(model, 'name'):
                model_name = model.name
            elif hasattr(model, 'display_name'):
                model_name = model.display_name
            else:
                model_name = str(model)
            
            model_names.append(model_name)
            if 'image' in model_name.lower() or 'banana' in model_name.lower():
                image_models.append(model_name)
        
        print(f"✅ API 연결 성공! 총 {len(model_names)}개 모델 발견")
        
        if image_models:
            print(f"\n📸 이미지 생성 모델 ({len(image_models)}개):")
            for m in sorted(set(image_models)):
                print(f"   - {m}")
        
        # gemini-3-pro-image-preview 확인
        target_model = "gemini-3-pro-image-preview"
        target_models = [m for m in model_names if target_model in m.lower()]
        
        if target_models:
            print(f"\n✅ {target_model} 모델 사용 가능:")
            for m in target_models:
                print(f"   - {m}")
            return True, target_models
        else:
            print(f"\n⚠️  {target_model} 모델을 찾을 수 없습니다.")
            print("   사용 가능한 이미지 모델:")
            for m in sorted(set(image_models)):
                print(f"   - {m}")
            return True, []
        
    except Exception as e:
        print(f"❌ API 연결 실패: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False, []


def test_image_generation(api_key: str, model_name: str = "models/gemini-3-pro-image-preview"):
    """간단한 이미지 생성 테스트"""
    print_header("3. 이미지 생성 테스트")
    
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        print("❌ google.genai가 설치되어 있지 않습니다.")
        return False
    
    try:
        client = genai.Client(api_key=api_key)
        
        # 간단한 테스트 프롬프트
        test_prompt = "A simple geometric shape: a blue circle on a white background"
        print(f"테스트 프롬프트: {test_prompt}")
        print(f"모델: {model_name}")
        print("\n이미지 생성 중... (10-30초 소요될 수 있습니다)")
        
        # 이미지 생성 요청
        response = client.models.generateContent(
            model_name,
            test_prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                image_config=types.ImageConfig(
                    aspect_ratio="1:1",
                    image_size="1K",  # 1024x1024
                ),
            ),
        )
        
        # 이미지 추출
        image_bytes = None
        try:
            # response.candidates[0].content.parts에서 이미지 추출
            if hasattr(response, 'candidates') and len(response.candidates) > 0:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                    for part in candidate.content.parts:
                        if hasattr(part, 'inline_data'):
                            inline_data = part.inline_data
                            if hasattr(inline_data, 'data'):
                                import base64
                                image_bytes = base64.b64decode(inline_data.data)
                                break
                        elif hasattr(part, 'inlineData'):
                            inline_data = part.inlineData
                            if hasattr(inline_data, 'data'):
                                import base64
                                image_bytes = base64.b64decode(inline_data.data)
                                break
        except Exception as e:
            print(f"⚠️  이미지 추출 중 오류: {e}")
        
        if image_bytes:
            # 테스트 이미지 저장
            test_output_dir = Path(".") / "2_Data" / "metadata" / "temp"
            test_output_dir.mkdir(parents=True, exist_ok=True)
            test_image_path = test_output_dir / "test_api_key_image.jpg"
            
            with open(test_image_path, "wb") as f:
                f.write(image_bytes)
            
            print(f"✅ 이미지 생성 성공!")
            print(f"   생성된 이미지: {test_image_path}")
            print(f"   이미지 크기: {len(image_bytes):,} bytes ({len(image_bytes) / 1024:.1f} KB)")
            
            # 이미지 삭제 제안
            print(f"\n💡 테스트 이미지는 {test_image_path}에 저장되었습니다.")
            print("   필요 없으면 삭제해도 됩니다.")
            
            return True
        else:
            print("⚠️  응답은 받았지만 이미지를 추출할 수 없습니다.")
            print(f"   응답 타입: {type(response)}")
            return False
        
    except Exception as e:
        error_msg = str(e).lower()
        
        # Rate limit 에러 확인
        if "rate limit" in error_msg or "quota" in error_msg or "429" in error_msg:
            print(f"❌ Rate Limit / Quota 에러 발생!")
            print(f"   에러 메시지: {e}")
            print(f"\n💡 이는 API 키는 정상이지만 RPD(일일 요청 제한)가 부족하거나 초과했을 수 있습니다.")
            print(f"   Google Cloud Console에서 할당량을 확인하거나 더 낮은 tier의 모델을 사용해보세요.")
            return False
        elif "403" in error_msg or "permission" in error_msg or "forbidden" in error_msg:
            print(f"❌ 권한 에러 발생!")
            print(f"   에러 메시지: {e}")
            print(f"\n💡 API 키에 gemini-3-pro-image-preview 모델 사용 권한이 없을 수 있습니다.")
            print(f"   Google Cloud Console에서 API 활성화 및 권한을 확인해주세요.")
            return False
        elif "401" in error_msg or "unauthorized" in error_msg or "invalid" in error_msg:
            print(f"❌ 인증 에러 발생!")
            print(f"   에러 메시지: {e}")
            print(f"\n💡 API 키가 유효하지 않거나 만료되었을 수 있습니다.")
            print(f"   새로운 API 키를 발급받아 .env 파일에 업데이트해주세요.")
            return False
        else:
            print(f"❌ 이미지 생성 실패: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    # Try to load .env file, but continue if it doesn't exist or can't be read
    try:
        load_dotenv()
    except Exception as e:
        print(f"⚠️  .env 파일 로드 실패 (계속 진행): {e}")
        print("   환경 변수에서 직접 GOOGLE_API_KEY를 읽습니다.")
    
    print("=" * 70)
    print("Gemini API 키 및 gemini-3-pro-image 모델 테스트")
    print("=" * 70)
    
    # 1. API 키 확인
    api_key = test_api_key_presence()
    if not api_key:
        print("\n" + "=" * 70)
        print("❌ 테스트 중단: API 키가 없습니다.")
        print("=" * 70)
        return 1
    
    # 2. 모델 목록 조회
    api_works, image_models = test_model_listing(api_key)
    if not api_works:
        print("\n" + "=" * 70)
        print("❌ 테스트 중단: API 연결 실패")
        print("=" * 70)
        return 1
    
    # 3. 이미지 생성 테스트
    # 사용 가능한 이미지 모델이 있으면 사용
    model_to_test = "models/gemini-3-pro-image-preview"
    if image_models:
        # 정확한 모델 이름 사용
        for m in image_models:
            if "gemini-3-pro-image" in m.lower():
                model_to_test = m
                break
    
    image_success = test_image_generation(api_key, model_to_test)
    
    # 최종 결과
    print("\n" + "=" * 70)
    print("테스트 결과 요약")
    print("=" * 70)
    print(f"✅ API 키: 설정됨")
    print(f"{'✅' if api_works else '❌'} API 연결: {'성공' if api_works else '실패'}")
    print(f"{'✅' if image_success else '❌'} 이미지 생성: {'성공' if image_success else '실패'}")
    
    if api_works and image_success:
        print("\n🎉 모든 테스트 통과! API 키가 정상 작동하며 이미지 생성이 가능합니다.")
        print("   gemini-3-pro-image 모델을 사용할 수 있습니다.")
    elif api_works:
        print("\n⚠️  API 연결은 성공했지만 이미지 생성에 실패했습니다.")
        print("   위의 에러 메시지를 확인하여 문제를 해결해주세요.")
    else:
        print("\n❌ API 연결에 실패했습니다.")
        print("   API 키가 올바른지, 인터넷 연결이 정상인지 확인해주세요.")
    
    print("=" * 70)
    
    return 0 if (api_works and image_success) else 1


if __name__ == "__main__":
    sys.exit(main())

