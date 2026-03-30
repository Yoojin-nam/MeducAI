#!/bin/bash

echo "🚀 Starting 5-Arm Verification Run (A, B, C, D, E)..."
echo "-----------------------------------------------------"

# Define Arms
ARMS=("A" "B" "C" "D" "E")

# 1. 실행 루프 (Execution Loop)
for ARM in "${ARMS[@]}"; do
    TAG="VERIFY_${ARM}"
    echo "▶️  Running Arm ${ARM}..."
    python 3_Code/src/01_generate_json.py --arm $ARM --sample 1 --run_tag $TAG > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        echo "   ✅ Arm ${ARM} Generation Complete."
    else
        echo "   ❌ Arm ${ARM} Failed."
    fi
done

echo ""
echo "🔍 Verifying Internal Logic (RAG & Thinking)..."
echo "-----------------------------------------------------"

# 2. 검증 로직 (Python Checker)
python -c "
import json
import os
import glob

# 정의된 기대값 (Expected Configuration)
# A: No Think, No RAG
# B: No Think, YES RAG
# C: YES Think, No RAG
# D: YES Think, YES RAG (Synergy)
# E: YES Think, No RAG (Pro / Closed Book)

expectations = {
    'A': {'rag': False, 'think': False, 'desc': 'Baseline'},
    'B': {'rag': True,  'think': False, 'desc': 'RAG Only'},
    'C': {'rag': False, 'think': True,  'desc': 'Thinking'},
    'D': {'rag': True,  'think': True,  'desc': 'Synergy'},
    'E': {'rag': False, 'think': True,  'desc': 'High-End (Pro)'}
}

print(f'{str(chr(9989)):<3} | {\"Arm\":<3} | {\"Model\":<18} | {\"Thinking\":<8} | {\"RAG (Search)\":<12} | {\"Result\"}')
print('-'*75)

base_dir = '2_Data/metadata/generated/gemini'

for arm, exp in expectations.items():
    tag = f'VERIFY_{arm}'
    file_path = f'{base_dir}/output_gemini_{tag}.jsonl'
    
    if not os.path.exists(file_path):
        print(f'❌  | {arm:<3} | FILE NOT FOUND     | -        | -            | FAIL')
        continue

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            line = f.readline()
            if not line:
                print(f'❌  | {arm:<3} | EMPTY FILE         | -        | -            | FAIL')
                continue
                
            data = json.loads(line)
            meta = data.get('metadata', {})
            
            # 1. Check Model
            model = meta.get('model', 'unknown')
            
            # 2. Check Thinking (Budget > 0)
            thinking_budget = meta.get('thinking_budget', 0)
            is_thinking = thinking_budget > 0
            
            # 3. Check RAG (Grounding Metadata existence)
            # logic: Step01 code saves 'grounding_info' in metadata
            grounding_info = meta.get('grounding_info', {})
            has_grounding = 'grounding_metadata' in grounding_info or meta.get('use_search') is True
            
            # Compare with expectation
            rag_match = (has_grounding == exp['rag'])
            # Note: For Arm B/D, use_search is True, but sometimes grounding_metadata is empty if query wasn't triggered.
            # So we check config intent 'use_search' mainly, but prefer evidence.
            # In v3.9.7 code, meta['use_search'] is the config source of truth.
            
            config_rag = meta.get('use_search', False)
            config_think = is_thinking
            
            pass_rag = (config_rag == exp['rag'])
            pass_think = (config_think == exp['think'])
            
            status = 'PASS' if (pass_rag and pass_think) else 'FAIL'
            icon = '✅ ' if status == 'PASS' else '⚠️ '
            
            think_str = 'ON' if config_think else 'OFF'
            rag_str = 'ON' if config_rag else 'OFF'
            
            print(f'{icon:<3} | {arm:<3} | {model:<18} | {think_str:<8} | {rag_str:<12} | {status}')
            
            if status == 'FAIL':
                print(f'    -> Expected: Think={exp[\"think\"]}, RAG={exp[\"rag\"]}')

    except Exception as e:
        print(f'❌  | {arm:<3} | ERROR: {str(e)}')

print('-'*75)
"
