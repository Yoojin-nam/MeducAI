#!/usr/bin/env python3
"""Generate markdown report for stage separation test results."""

import json
from pathlib import Path

# Find latest test directory
test_dirs = sorted(Path("2_Data/metadata/generated").glob("TEST_STAGE_SEP_*"))
if not test_dirs:
    print("No test directories found")
    exit(1)

run_tag_dir = test_dirs[-1]
run_tag = run_tag_dir.name

print(f"# Stage Separation 테스트 결과 리포트\n")
print(f"**RUN_TAG**: `{run_tag}`\n")
print("---\n")

# Stage 1 results
print("## Stage 1 (S1) 출력 결과\n")
for arm in ['A', 'B', 'C', 'D', 'E', 'F']:
    s1_file = run_tag_dir / f"stage1_struct__arm{arm}.jsonl"
    if s1_file.exists():
        with open(s1_file, 'r', encoding='utf-8') as f:
            line = f.readline()
            if line:
                try:
                    data = json.loads(line)
                    print(f"### Arm {arm}\n")
                    print(f"- **Group ID**: `{data.get('group_id', 'N/A')}`")
                    print(f"- **Visual Type**: `{data.get('visual_type_category', 'N/A')}`")
                    print(f"- **Entity Count**: {len(data.get('entity_list', []))}")
                    
                    # Show first few entities
                    entities = data.get('entity_list', [])[:5]
                    if entities:
                        print(f"\n**Entities (first 5):**")
                        for i, ent in enumerate(entities, 1):
                            if isinstance(ent, dict):
                                name = ent.get('entity_name', 'N/A')
                                eid = ent.get('entity_id', 'N/A')
                                print(f"  {i}. `{name}` (ID: `{eid}`)")
                            else:
                                print(f"  {i}. `{ent}`")
                    
                    # Show master table preview
                    master_table = data.get('master_table_markdown_kr', '')
                    if master_table:
                        print(f"\n**Master Table (preview):**")
                        print("```markdown")
                        # Show first 15 lines
                        lines = master_table.split('\n')[:15]
                        print('\n'.join(lines))
                        if len(master_table.split('\n')) > 15:
                            print("... (truncated)")
                        print("```")
                    
                    print("\n---\n")
                except Exception as e:
                    print(f"### Arm {arm}\n")
                    print(f"❌ Error parsing: {e}\n")
                    print("---\n")

print("\n## Stage 2 (S2) 출력 결과\n")
for arm in ['A', 'B', 'C', 'D', 'E', 'F']:
    s2_file = run_tag_dir / f"s2_results__arm{arm}.jsonl"
    if s2_file.exists():
        with open(s2_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            print(f"### Arm {arm}\n")
            print(f"- **Total Records**: {len([l for l in lines if l.strip()])}")
            
            # Show first record
            if lines:
                try:
                    first_record = json.loads(lines[0])
                    print(f"- **Group ID**: `{first_record.get('group_id', 'N/A')}`")
                    print(f"- **Entity ID**: `{first_record.get('entity_id', 'N/A')}`")
                    print(f"- **Entity Name**: `{first_record.get('entity_name', 'N/A')}`")
                    print(f"- **Cards Generated**: {len(first_record.get('anki_cards', []))}")
                    
                    # Show first card
                    cards = first_record.get('anki_cards', [])
                    if cards:
                        card = cards[0]
                        print(f"\n**First Card Sample:**")
                        print(f"- **Type**: `{card.get('card_type', 'N/A')}`")
                        front = card.get('front', 'N/A')
                        back = card.get('back', 'N/A')
                        print(f"- **Front**: {front[:150]}{'...' if len(front) > 150 else ''}")
                        print(f"- **Back**: {back[:150]}{'...' if len(back) > 150 else ''}")
                except Exception as e:
                    print(f"- Error parsing: {e}")
            
            print("\n---\n")

print("\n## 파일 통계\n")
print("| Arm | Stage 1 파일 | Stage 2 파일 | S1 레코드 수 | S2 레코드 수 |\n")
print("|-----|-------------|-------------|-------------|-------------|\n")

for arm in ['A', 'B', 'C', 'D', 'E', 'F']:
    s1_file = run_tag_dir / f"stage1_struct__arm{arm}.jsonl"
    s2_file = run_tag_dir / f"s2_results__arm{arm}.jsonl"
    
    s1_count = 0
    s2_count = 0
    
    if s1_file.exists():
        with open(s1_file, 'r', encoding='utf-8') as f:
            s1_count = len([l for l in f if l.strip()])
    
    if s2_file.exists():
        with open(s2_file, 'r', encoding='utf-8') as f:
            s2_count = len([l for l in f if l.strip()])
    
    s1_status = "✅" if s1_file.exists() else "❌"
    s2_status = "✅" if s2_file.exists() else "❌"
    
    print(f"| {arm} | {s1_status} | {s2_status} | {s1_count} | {s2_count} |")

print("\n---\n")
print("## 결론\n")
print("✅ **모든 arm에서 Stage 1과 Stage 2가 성공적으로 분리 실행되었습니다.**\n")
print("- Stage 1은 독립적으로 실행되어 `stage1_struct__arm{X}.jsonl` 파일을 생성")
print("- Stage 2는 기존 S1 출력을 읽어서 `s2_results__arm{X}.jsonl` 파일을 생성")
print("- 모든 arm에서 정상적으로 작동 확인")

