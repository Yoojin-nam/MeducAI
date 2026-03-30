#!/usr/bin/env python3
"""
Download FINAL_DISTRIBUTION batches that are completed.

This script reads batch tracking metadata and downloads result files for SUCCEEDED
batches, then saves decoded images into:
  2_Data/metadata/generated/FINAL_DISTRIBUTION/images/

Note:
- Requires valid GOOGLE_API_KEY_XX entries in `.env`
- Generated outputs are intentionally excluded from git by `.gitignore`
"""
import base64
import json
from pathlib import Path

from dotenv import dotenv_values
from google import genai


BASE_DIR = Path(".")
TRACKING_FILE = BASE_DIR / "2_Data/metadata/.batch_tracking.json"
IMAGES_DIR = BASE_DIR / "2_Data/metadata/generated/FINAL_DISTRIBUTION/images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

env = dotenv_values(".env")

with open(TRACKING_FILE) as f:
    tracking = json.load(f)

print("=== 배치 다운로드 시작 ===\n")
total_saved = 0
total_skipped = 0

for api_key_label, data in tracking.get("batches", {}).items():
    run_tag = data.get("run_tag", "FINAL_DISTRIBUTION")

    for chunk in data.get("chunks", []):
        batch_id = chunk.get("batch_id", "")
        api_key_number = chunk.get("api_key_number")
        prompts_metadata = chunk.get("prompts_metadata", [])
        num_requests = chunk.get("num_requests", 0)

        api_key_name = f"GOOGLE_API_KEY_{api_key_number:02d}"
        api_key = env.get(api_key_name, "")

        if not api_key:
            print(f"❌ {api_key_name} 없음, 스킵")
            continue

        short_id = batch_id.split("/")[-1][:25] if "/" in batch_id else batch_id[:25]
        print(f"📦 배치 {short_id}... ({num_requests}개)", end=" ", flush=True)

        try:
            client = genai.Client(api_key=api_key)
            batch = client.batches.get(name=batch_id)
            state = str(batch.state)

            if state != "JobState.JOB_STATE_SUCCEEDED":
                print("⏳")
                continue

            # 결과 파일 다운로드
            result_file = batch.dest.file_name if hasattr(batch.dest, "file_name") else str(batch.dest)
            print("다운로드 중...", end=" ", flush=True)

            result_content = client.files.download(file=result_file)
            if hasattr(result_content, "text"):
                lines = result_content.text.strip().split("\n")
            elif hasattr(result_content, "decode"):
                lines = result_content.decode().strip().split("\n")
            else:
                # bytes인 경우
                lines = result_content.strip().decode("utf-8").split("\n")

            # 이미지 저장
            saved = 0
            skipped = 0
            for line in lines:
                if not line.strip():
                    continue
                result = json.loads(line)

                # 이미지 데이터 추출
                resp = result.get("response", {})
                candidates = resp.get("candidates", [])
                if not candidates:
                    continue

                parts = candidates[0].get("content", {}).get("parts", [])
                image_data = None
                for part in parts:
                    if "inline_data" in part:
                        image_data = part["inline_data"].get("data", "")
                        break

                if not image_data:
                    continue

                # 파일명 결정
                custom_id = result.get("custom_id", "")
                pm = next((p for p in prompts_metadata if p.get("prompt_hash") == custom_id), None)

                if pm:
                    group_id = pm.get("group_id", "")
                    spec_kind = pm.get("spec_kind", "")
                    if spec_kind == "S1_TABLE_VISUAL":
                        filename = f"IMG__{run_tag}__{group_id}__TABLE.jpg"
                    else:
                        entity_id = pm.get("entity_id", "")
                        card_role = pm.get("card_role", "")
                        filename = f"IMG__{run_tag}__{group_id}__DERIVED_{entity_id}__{card_role}.jpg"
                else:
                    filename = f"IMG__{run_tag}__unknown_{custom_id[:8]}.jpg"

                filepath = IMAGES_DIR / filename
                if filepath.exists():
                    skipped += 1
                    continue

                filepath.write_bytes(base64.b64decode(image_data))
                saved += 1

            print(f"✅ 저장: {saved}개, 스킵: {skipped}개")
            total_saved += saved
            total_skipped += skipped

        except Exception as e:
            print(f"❌ 에러: {str(e)[:80]}")
            continue

print(f"\n=== 완료: 총 {total_saved}개 새로 저장, {total_skipped}개 스킵 ===")


