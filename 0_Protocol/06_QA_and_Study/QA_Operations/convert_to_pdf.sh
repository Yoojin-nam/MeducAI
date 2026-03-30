#!/bin/bash
# HTML을 PDF로 변환하는 스크립트
# macOS에서 사용

HTML_FILE="FINAL_QA_Evaluation_Guide_for_Participants.html"
PDF_FILE="FINAL_QA_Evaluation_Guide_for_Participants.pdf"

echo "HTML 파일을 PDF로 변환합니다..."
echo "HTML 파일: $HTML_FILE"

# 방법 1: macOS의 기본 브라우저 사용 (Safari 또는 Chrome)
if command -v python3 &> /dev/null; then
    python3 << PYTHON_EOF
import webbrowser
import os
import time

html_path = os.path.abspath("${HTML_FILE}")
print(f"브라우저에서 열기: {html_path}")
print("\n다음 단계:")
print("1. 브라우저에서 파일이 열립니다")
print("2. Cmd+P (인쇄)를 누릅니다")
print("3. 하단의 'PDF로 저장'을 클릭합니다")
print(f"4. 파일명을 '${PDF_FILE}'로 저장합니다")
print("\n5초 후 브라우저가 열립니다...")
time.sleep(5)
webbrowser.open(f"file://{html_path}")
PYTHON_EOF
else
    # 브라우저로 직접 열기
    open "$HTML_FILE"
    echo ""
    echo "브라우저에서 파일이 열렸습니다."
    echo "다음 단계를 따라주세요:"
    echo "1. Cmd+P (인쇄)를 누르세요"
    echo "2. 하단의 'PDF로 저장'을 클릭하세요"
    echo "3. 파일명을 '$PDF_FILE'로 저장하세요"
fi

