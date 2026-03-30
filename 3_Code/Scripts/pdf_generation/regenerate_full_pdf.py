#!/usr/bin/env python3
"""
전체 평가 기준이 포함된 완전한 PDF 생성
"""

import subprocess
import os
import time
import shutil

def create_full_markdown():
    """상세한 평가 기준이 모두 포함된 마크다운 생성"""
    
    # 이 부분에는 원래 작성했던 전체 마크다운 내용이 들어가야 합니다
    # 파일이 너무 크므로 Git에서 복구하거나 다시 작성해야 합니다
    
    print("⚠️  상세 마크다운 복구 필요")
    print()
    print("Git에서 복구를 시도합니다...")
    
    # Git에서 복구 시도
    try:
        # 삭제된 파일 복구
        result = subprocess.run(
            ['git', 'log', '--all', '--full-history', '--', 
             'FINAL_QA_평가_가이드_전공의용.md'],
            capture_output=True,
            text=True,
            cwd='/path/to/workspace/workspace/MeducAI/6_Distributions/Final_QA/Evaluation_Guide'
        )
        
        if result.returncode == 0 and result.stdout.strip():
            print("✓ Git 히스토리 발견")
            # 최근 커밋에서 복구
            commit = result.stdout.split('\n')[0].split()[1] if result.stdout else None
            if commit:
                print(f"  커밋: {commit}")
                # TODO: 파일 복구
        else:
            print("✗ Git 히스토리 없음")
            return False
            
    except Exception as e:
        print(f"✗ Git 복구 실패: {e}")
        return False
    
    return False

def main():
    os.chdir('/path/to/workspace/workspace/MeducAI/6_Distributions/Final_QA/Evaluation_Guide')
    
    print("=" * 70)
    print("전체 평가 기준 포함 PDF 재생성")
    print("=" * 70)
    print()
    
    # Cursor AI에게 원본 마크다운 재생성 요청 필요
    print("📝 원본 마크다운 파일이 필요합니다.")
    print()
    print("해결 방법:")
    print("1. Cursor AI에게 원래 작성했던 전체 마크다운을 다시 생성 요청")
    print("2. 또는 Git에서 복구")
    print()
    
    create_full_markdown()

if __name__ == '__main__':
    main()

