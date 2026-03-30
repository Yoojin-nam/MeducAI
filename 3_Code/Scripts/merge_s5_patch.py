#!/usr/bin/env python3
"""
S5 패치 파일 병합 스크립트
- 기존 S5 validation 파일에서 패치된 그룹을 교체
"""

import json
import shutil
from datetime import datetime
from pathlib import Path

BASE_DIR = Path("/path/to/workspace/workspace/MeducAI")
RUN_TAG = "FINAL_DISTRIBUTION"

MAIN_FILE = BASE_DIR / "2_Data/metadata/generated" / RUN_TAG / "s5_validation__armG.jsonl"
PATCH_FILE = BASE_DIR / "2_Data/metadata/generated" / RUN_TAG / "s5_validation__armG__patch_29groups.jsonl"


def main():
    print("=" * 60)
    print("S5 패치 파일 병합")
    print("=" * 60)
    
    if not PATCH_FILE.exists():
        print(f"Error: 패치 파일 없음: {PATCH_FILE}")
        return
    
    if not MAIN_FILE.exists():
        print(f"Error: 메인 파일 없음: {MAIN_FILE}")
        return
    
    # 1. 백업 생성
    backup_file = MAIN_FILE.with_suffix(f".jsonl.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    shutil.copy(MAIN_FILE, backup_file)
    print(f"백업 생성: {backup_file.name}")
    
    # 2. 패치 파일 로드 (group_id -> record)
    patch_records = {}
    with open(PATCH_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            record = json.loads(line)
            group_id = record.get('group_id')
            if group_id:
                patch_records[group_id] = record
    
    print(f"패치 그룹: {len(patch_records)}개")
    
    # 3. 메인 파일 로드 및 병합
    merged_records = []
    replaced_count = 0
    
    with open(MAIN_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            record = json.loads(line)
            group_id = record.get('group_id')
            
            if group_id in patch_records:
                # 패치된 레코드로 교체
                merged_records.append(patch_records[group_id])
                replaced_count += 1
                del patch_records[group_id]  # 사용된 패치 제거
            else:
                # 기존 레코드 유지
                merged_records.append(record)
    
    # 4. 남은 패치 레코드 추가 (메인에 없던 그룹)
    for group_id, record in patch_records.items():
        merged_records.append(record)
        print(f"  새 그룹 추가: {group_id}")
    
    # 5. 병합된 파일 저장
    with open(MAIN_FILE, 'w', encoding='utf-8') as f:
        for record in merged_records:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    print(f"\n결과:")
    print(f"  - 교체된 그룹: {replaced_count}개")
    print(f"  - 총 레코드: {len(merged_records)}개")
    print(f"  - 저장: {MAIN_FILE}")
    
    print("\n✓ 병합 완료!")


if __name__ == "__main__":
    main()

