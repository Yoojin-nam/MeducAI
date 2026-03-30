#!/bin/bash

# MeducAI: Run all models for comparison
# Usage: ./run_all.sh

PROVIDERS=("gemini" "gpt" "deepseek" "claude")
SAMPLE_SIZE=10

echo "=========================================="
echo " Starting Multi-Model Experiment (n=$SAMPLE_SIZE)"
echo "=========================================="

for p in "${PROVIDERS[@]}"; do
    echo ""
    echo "▶ Processing Provider: $p"
    echo "------------------------------------------"
    
    # 파이썬 스크립트 실행
    python 3_Code/src/01_generate_json.py --provider "$p" --sample "$SAMPLE_SIZE"
    
    # 에러 체크
    if [ $? -eq 0 ]; then
        echo "✅ $p finished successfully."
    else
        echo "❌ $p failed. Check API Keys or Logs."
    fi
    
    # API Rate Limit 방지를 위한 짧은 휴식 (선택 사항)
    sleep 2
done

echo ""
echo "🎉 All experiments completed."