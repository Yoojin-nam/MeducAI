"""
list_all_models.py
- Prints available models per provider: Google(Gemini), OpenAI, DeepSeek, Anthropic(Claude)
- Uses .env for API keys

Required env vars:
- GOOGLE_API_KEY
- OPENAI_API_KEY
- DEEPSEEK_API_KEY
- ANTHROPIC_API_KEY

Optional:
- DEEPSEEK_BASE_URL (default: https://api.deepseek.com)
"""

import os
from dotenv import load_dotenv


def print_header(title: str):
    print("\n" + "=" * 88)
    print(title)
    print("=" * 88)


def list_gemini_models():
    try:
        from google import genai
    except ImportError:
        print("❌ google.genai가 설치되어 있지 않습니다.  pip install -U google-genai")
        return

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ GOOGLE_API_KEY가 없습니다.")
        return

    print_header("✅ Google Gemini: 사용 가능한 모델 목록 (google.genai SDK)")
    try:
        client = genai.Client(api_key=api_key)
        
        # List all available models
        models = client.models.list()
        
        # Filter and display models
        image_models = []
        text_models = []
        all_models = []
        
        # Iterate through models
        for model in models:
            # Extract model name (could be a string or object with .name attribute)
            if isinstance(model, str):
                model_name = model
            elif hasattr(model, 'name'):
                model_name = model.name
            elif hasattr(model, 'display_name'):
                model_name = model.display_name
            else:
                model_name = str(model)
            
            all_models.append(model_name)
            
            # Check if it's an image generation model
            model_lower = model_name.lower()
            if 'image' in model_lower or 'banana' in model_lower or 'imagen' in model_lower:
                image_models.append(model_name)
            else:
                text_models.append(model_name)
        
        if image_models:
            print("\n📸 Image Generation Models:")
            for m in sorted(set(image_models)):
                print(f"  - {m}")
        
        if text_models:
            print("\n💬 Text Generation Models:")
            for m in sorted(set(text_models)):
                print(f"  - {m}")
        
        if not image_models and not text_models:
            # Fallback: just list all models
            print("\n모든 모델:")
            for m in sorted(set(all_models)):
                print(f"  - {m}")
        
        total = len(set(all_models))
        print(f"\n총 {total}개 (이미지: {len(set(image_models))}개, 텍스트: {len(set(text_models))}개)")
        
    except Exception as e:
        print(f"❌ Gemini 모델 목록 조회 실패: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


def list_openai_models():
    try:
        from openai import OpenAI
    except ImportError:
        print("❌ openai가 설치되어 있지 않습니다.  pip install -U openai")
        return

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY가 없습니다.")
        return

    client = OpenAI(api_key=api_key)

    print_header("✅ OpenAI: 사용 가능한 모델 목록 (/v1/models)")
    try:
        models = client.models.list()
        ids = sorted([m.id for m in models.data])
        for mid in ids:
            print(f" - {mid}")
        print(f"\n총 {len(ids)}개")
    except Exception as e:
        print(f"❌ OpenAI 모델 목록 조회 실패: {type(e).__name__}: {e}")


def list_deepseek_models():
    # DeepSeek는 OpenAI-compatible models endpoint를 제공합니다.
    try:
        from openai import OpenAI
    except ImportError:
        print("❌ openai가 설치되어 있지 않습니다.  pip install -U openai")
        return

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("❌ DEEPSEEK_API_KEY가 없습니다.")
        return

    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    client = OpenAI(api_key=api_key, base_url=base_url)

    print_header(f"✅ DeepSeek: 사용 가능한 모델 목록 ({base_url}/models)")
    try:
        models = client.models.list()
        ids = sorted([m.id for m in models.data])
        for mid in ids:
            print(f" - {mid}")
        print(f"\n총 {len(ids)}개")
    except Exception as e:
        print(f"❌ DeepSeek 모델 목록 조회 실패: {type(e).__name__}: {e}")


def list_anthropic_models():
    # Anthropic은 환경/SDK 버전에 따라 models.list 지원 여부가 다를 수 있어
    # 1) 가능하면 models.list로 전부 출력
    # 2) 불가하면 후보 모델을 실제 호출(ping)하여 사용 가능 여부 출력(fallback)
    try:
        import anthropic
    except ImportError:
        print("❌ anthropic이 설치되어 있지 않습니다.  pip install -U anthropic")
        return

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY가 없습니다.")
        return

    client = anthropic.Anthropic(api_key=api_key)

    print_header("✅ Anthropic (Claude): 사용 가능한 모델 목록")

    # (1) models.list 시도
    try:
        if hasattr(client, "models") and hasattr(client.models, "list"):
            resp = client.models.list()
            # resp.data: list of model objects with .id
            ids = [m.id for m in resp.data]
            for mid in ids:
                print(f" - {mid}")
            print(f"\n총 {len(ids)}개 (models.list)")
            return
    except Exception as e:
        print(f"ℹ️ models.list 미지원 또는 실패: {type(e).__name__}: {e}")
        print("ℹ️ fallback: 후보 모델 ping 테스트로 사용 가능 모델을 확인합니다.")

    # (2) fallback: 후보 모델 ping
    # 필요 시 여기 후보 리스트를 최신으로 업데이트해서 쓰세요.
    candidate_models = [
        # Claude 3.x / 3.5 계열(예시)
        "claude-3-5-sonnet-20241022",
        "claude-3-5-opus-20241022",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
    ]

    available = []
    for model in candidate_models:
        try:
            client.messages.create(
                model=model,
                max_tokens=1,
                temperature=0,
                messages=[{"role": "user", "content": "ping"}],
            )
            available.append(model)
        except Exception:
            pass

    if available:
        for mid in available:
            print(f" - {mid}")
        print(f"\n총 {len(available)}개 (ping-based availability)")
    else:
        print("❌ 후보 리스트 기준으로 호출 가능한 모델을 확인하지 못했습니다.")
        print("   - 계정 권한/요금제/리전 제한 또는 모델명 변경 가능성이 있습니다.")


def main():
    load_dotenv()

    # 회사별 “전부 출력” (가능한 경우 전부, 불가능한 경우 best-effort)
    list_gemini_models()
    list_openai_models()
    list_deepseek_models()
    list_anthropic_models()

    print("\n" + "-" * 88)
    print("완료")
    print("-" * 88)


if __name__ == "__main__":
    main()
