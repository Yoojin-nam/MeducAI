#!/bin/bash
# Translate Korean medical terms to English in Anki cards

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/../src/tools/anki/translate_medical_terms.py"

# Default values
INPUT_FILE=""
OUTPUT_FILE=""
MODEL="gemini-3-flash-preview"
MAX_CARDS=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --input)
            INPUT_FILE="$2"
            shift 2
            ;;
        --output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        --model)
            MODEL="$2"
            shift 2
            ;;
        --max_cards)
            MAX_CARDS="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 --input <input.jsonl> --output <output.jsonl> [options]"
            echo ""
            echo "Options:"
            echo "  --input <file>     Input S2 JSONL file (required)"
            echo "  --output <file>     Output JSONL file (required)"
            echo "  --model <name>      Gemini model name (default: gemini-3-flash-preview)"
            echo "  --max_cards <n>     Maximum number of records to process (for testing)"
            echo ""
            echo "Example:"
            echo "  $0 \\"
            echo "    --input 2_Data/metadata/generated/FINAL_DISTRIBUTION/s2_results__s1armG__s2armG.jsonl \\"
            echo "    --output 2_Data/metadata/generated/FINAL_DISTRIBUTION/s2_results__translated.jsonl"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Validate required arguments
if [[ -z "$INPUT_FILE" ]] || [[ -z "$OUTPUT_FILE" ]]; then
    echo "Error: --input and --output are required"
    echo "Use --help for usage information"
    exit 1
fi

# Convert to absolute paths
INPUT_FILE_ABS="$(cd "$(dirname "$INPUT_FILE")" && pwd)/$(basename "$INPUT_FILE")"
OUTPUT_FILE_ABS="$(cd "$(dirname "$OUTPUT_FILE")" && pwd)/$(basename "$OUTPUT_FILE")"

# Change to project root
cd "$PROJECT_ROOT"

# Build command
CMD="python3 $PYTHON_SCRIPT --input \"$INPUT_FILE_ABS\" --output \"$OUTPUT_FILE_ABS\" --model \"$MODEL\""

if [[ -n "$MAX_CARDS" ]]; then
    CMD="$CMD --max_cards $MAX_CARDS"
fi

# Execute
echo "Translating medical terms in Anki cards..."
echo "Input:  $INPUT_FILE_ABS"
echo "Output: $OUTPUT_FILE_ABS"
echo "Model:  $MODEL"
echo ""

eval $CMD

echo ""
echo "✅ Translation complete!"

