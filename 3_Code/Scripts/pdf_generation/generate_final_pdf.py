#!/usr/bin/env python3
"""
상세 마크다운을 깨끗한 PDF로 변환
"""

import subprocess
import os
import time

def md_to_html_to_pdf(md_file, pdf_file):
    """마크다운 → HTML → PDF (헤더/푸터 없이)"""
    
    html_file = md_file.replace('.md', '.html')
    
    # 1. Pandoc: MD → HTML
    print(f"[1/2] HTML 생성: {md_file} → {html_file}")
    cmd_pandoc = [
        'pandoc',
        md_file,
        '-o', html_file,
        '--standalone',
        '--metadata', 'title=MeducAI QA 평가 가이드',
        '--self-contained'
    ]
    
    try:
        subprocess.run(cmd_pandoc, check=True, capture_output=True)
        print(f"  ✓ HTML 생성 완료")
    except Exception as e:
        print(f"  ✗ HTML 생성 실패: {e}")
        return False
    
    # 스타일 추가
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    style = """
<style>
@page { margin: 20mm; size: A4; }
body {
    font-family: 'AppleSDGothicNeo-Regular', 'Nanum Gothic', 'Malgun Gothic', sans-serif;
    font-size: 11pt;
    line-height: 1.6;
    max-width: 900px;
    margin: 0 auto;
    padding: 20px;
    color: #333;
}
h1 {
    font-size: 24pt;
    color: #2c3e50;
    border-bottom: 3px solid #3498db;
    padding-bottom: 10px;
    margin-top: 30px;
    page-break-after: avoid;
}
h2 {
    font-size: 18pt;
    color: #34495e;
    border-bottom: 2px solid #e0e0e0;
    padding-bottom: 8px;
    margin-top: 25px;
    page-break-after: avoid;
}
h3 {
    font-size: 14pt;
    color: #555;
    margin-top: 20px;
    page-break-after: avoid;
}
h4 {
    font-size: 12pt;
    color: #666;
    margin-top: 15px;
}
p {
    margin: 10px 0;
    orphans: 3;
    widows: 3;
}
table {
    border-collapse: collapse;
    width: 100%;
    margin: 15px 0;
    page-break-inside: avoid;
}
th, td {
    border: 1px solid #ddd;
    padding: 10px;
    text-align: left;
}
th {
    background-color: #f2f2f2;
    font-weight: bold;
}
tr:nth-child(even) {
    background-color: #f9f9f9;
}
pre {
    background-color: #f5f5f5;
    padding: 15px;
    border-left: 4px solid #3498db;
    overflow-x: auto;
    page-break-inside: avoid;
}
code {
    background-color: #f5f5f5;
    padding: 2px 6px;
    border-radius: 3px;
    font-family: 'Courier New', monospace;
    font-size: 10pt;
}
ul, ol {
    margin: 10px 0;
    padding-left: 30px;
}
li {
    margin: 5px 0;
}
strong {
    font-weight: bold;
    color: #2c3e50;
}
@media print {
    body {
        font-size: 10pt;
    }
    h1 {
        page-break-before: always;
    }
    h1:first-of-type {
        page-break-before: avoid;
    }
}
</style>
"""
    
    if '</head>' in content:
        content = content.replace('</head>', style + '\n</head>')
    else:
        content = style + '\n' + content
    
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"  ✓ 스타일 적용 완료")
    
    # 2. Chrome: HTML → PDF (헤더/푸터 없이!)
    print(f"[2/2] PDF 생성: {html_file} → {pdf_file}")
    
    chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    html_path = f"file://{os.path.abspath(html_file)}"
    
    cmd_chrome = [
        chrome_path,
        '--headless',
        '--disable-gpu',
        '--no-pdf-header-footer',  # 핵심!
        '--print-to-pdf=' + pdf_file,
        html_path
    ]
    
    try:
        subprocess.run(cmd_chrome, check=True, capture_output=True, timeout=30)
        
        if os.path.exists(pdf_file):
            size = os.path.getsize(pdf_file) // 1024
            print(f"  ✓ PDF 생성 완료 ({size}KB)")
            return True
        else:
            print(f"  ✗ PDF 파일 생성 실패")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"  ✗ 타임아웃")
        return False
    except Exception as e:
        print(f"  ✗ PDF 생성 실패: {e}")
        return False

def main():
    os.chdir('/path/to/workspace/workspace/MeducAI/6_Distributions/Final_QA/Evaluation_Guide')
    
    print("=" * 70)
    print("전체 평가 기준 포함 PDF 생성 (헤더/푸터 없음)")
    print("=" * 70)
    print()
    
    files = [
        ('FINAL_QA_평가_가이드_전공의용_FULL.md', 'FINAL_QA_평가_가이드_전공의용.pdf'),
        ('FINAL_QA_평가_가이드_전문의용_FULL.md', 'FINAL_QA_평가_가이드_전문의용.pdf')
    ]
    
    for md_file, pdf_file in files:
        print(f"처리 중: {md_file}")
        print()
        if md_to_html_to_pdf(md_file, pdf_file):
            print(f"✅ 완료: {pdf_file}")
        else:
            print(f"❌ 실패: {pdf_file}")
        print()
        time.sleep(2)  # Chrome 안정화
    
    # 정리
    print("정리 중...")
    for md_file, _ in files:
        html_file = md_file.replace('.md', '.html')
        if os.path.exists(html_file):
            os.remove(html_file)
            print(f"  ✓ 삭제: {html_file}")
        if os.path.exists(md_file):
            os.remove(md_file)
            print(f"  ✓ 삭제: {md_file}")
    
    # 간단 버전도 삭제
    for f in ['FINAL_QA_평가_가이드_전공의용_simple.pdf', 'FINAL_QA_평가_가이드_전문의용_simple.pdf', 'regenerate_full_pdf.py']:
        if os.path.exists(f):
            os.remove(f)
            print(f"  ✓ 삭제: {f}")
    
    print()
    print("=" * 70)
    print("✅ 모든 작업 완료!")
    print("=" * 70)
    print()
    print("최종 파일:")
    for _, pdf_file in files:
        if os.path.exists(pdf_file):
            size = os.path.getsize(pdf_file) // 1024
            print(f"  ✓ {pdf_file} ({size}KB)")
    print()
    print("🎉 전체 평가 기준 포함 + 하단 파일 경로 제거 완료!")

if __name__ == '__main__':
    main()

