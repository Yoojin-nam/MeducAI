#!/usr/bin/env python3
"""
fix_s2_mcq_answer_format.py

S2 MCQ 카드의 정답 형식 오류 수정 후처리 스크립트

문제: MCQ back 텍스트의 "정답:" 필드가 잘못된 형식으로 생성됨
  - 숫자 사용: "정답: 4" (correct_index 값을 그대로 사용)
  - 선지 첫 단어: "정답: Petersen's" (정답 선지 텍스트의 첫 단어)

해결: correct_index를 사용하여 정답 문자(A-E)로 정규화

MI-CLEAR-LLM 준수:
  - 의미론적 변경 없음 (correct_index, options[] 그대로 유지)
  - 형식 정규화만 수행 (포맷팅 후처리)
  - 원본 백업 + 변경 diff 기록

Usage:
  python3 fix_s2_mcq_answer_format.py --input <s2_results.jsonl> [--dry-run]
"""

import argparse
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path


CORRECT_LETTERS = ['A', 'B', 'C', 'D', 'E']
ANSWER_PATTERN = re.compile(r'정답:\s*\S+')


def fix_mcq_back_text(back_text: str, correct_index: int) -> tuple[str, bool]:
    """
    MCQ back 텍스트의 "정답:" 필드를 correct_letter로 정규화.
    
    Returns:
        tuple: (fixed_text, was_modified)
    """
    if correct_index < 0 or correct_index >= len(CORRECT_LETTERS):
        raise ValueError(f"Invalid correct_index: {correct_index}. Must be 0-4.")
    
    correct_letter = CORRECT_LETTERS[correct_index]
    expected_format = f"정답: {correct_letter}"
    
    match = ANSWER_PATTERN.search(back_text)
    if not match:
        return back_text, False
    
    current_value = match.group(0)
    
    # 이미 올바른 형식인지 확인
    if current_value == expected_format:
        return back_text, False
    
    # 단일 문자 A-E로만 이루어진 경우 이미 올바른 형식
    answer_val = current_value.replace("정답:", "").strip()
    if answer_val in CORRECT_LETTERS:
        if answer_val == correct_letter:
            return back_text, False
        # 정답 문자는 있지만 correct_index와 다름 - 이는 데이터 불일치
        # 이 경우에도 correct_index 기반으로 수정 (correct_index가 ground truth)
    
    # 수정 수행
    fixed_text = ANSWER_PATTERN.sub(expected_format, back_text, count=1)
    return fixed_text, True


def process_line(line: str) -> tuple[str, list[dict]]:
    """
    단일 JSONL 라인 처리.
    
    Returns:
        tuple: (fixed_json_line, list_of_changes)
    """
    data = json.loads(line)
    changes = []
    modified = False
    
    for i, card in enumerate(data.get('anki_cards', [])):
        if card.get('card_type', '').upper() != 'MCQ':
            continue
        
        back_text = card.get('back', '')
        correct_index = card.get('correct_index')
        
        if correct_index is None:
            continue
        
        try:
            fixed_back, was_modified = fix_mcq_back_text(back_text, correct_index)
        except ValueError as e:
            changes.append({
                'entity_id': data.get('entity_id'),
                'entity_name': data.get('entity_name'),
                'card_index': i,
                'error': str(e)
            })
            continue
        
        if was_modified:
            # 원본 값 추출
            match = ANSWER_PATTERN.search(back_text)
            original_value = match.group(0) if match else "N/A"
            
            changes.append({
                'entity_id': data.get('entity_id'),
                'entity_name': data.get('entity_name'),
                'card_index': i,
                'original': original_value,
                'fixed': f"정답: {CORRECT_LETTERS[correct_index]}",
                'correct_index': correct_index
            })
            card['back'] = fixed_back
            modified = True
    
    if modified:
        return json.dumps(data, ensure_ascii=False), changes
    return line.rstrip('\n'), changes


def main():
    parser = argparse.ArgumentParser(
        description='S2 MCQ 정답 형식 오류 수정'
    )
    parser.add_argument(
        '--input', '-i',
        required=True,
        help='입력 S2 results JSONL 파일'
    )
    parser.add_argument(
        '--output', '-o',
        help='출력 파일 (기본: 입력 파일 덮어쓰기)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='실제 수정 없이 변경 사항만 출력'
    )
    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='백업 생성 안 함'
    )
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: 입력 파일이 존재하지 않음: {input_path}", file=sys.stderr)
        sys.exit(1)
    
    output_path = Path(args.output) if args.output else input_path
    
    # 모든 라인 처리
    fixed_lines = []
    all_changes = []
    total_lines = 0
    
    print(f"Processing: {input_path}")
    
    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            if not line:
                fixed_lines.append(line)
                continue
            
            total_lines += 1
            fixed_line, changes = process_line(line)
            fixed_lines.append(fixed_line)
            all_changes.extend(changes)
    
    # 결과 출력
    print(f"\n=== 처리 결과 ===")
    print(f"총 라인 수: {total_lines}")
    print(f"수정된 MCQ 카드 수: {len(all_changes)}")
    
    if all_changes:
        print(f"\n--- 변경 상세 (처음 10건) ---")
        for change in all_changes[:10]:
            if 'error' in change:
                print(f"  [ERROR] {change['entity_name']}: {change['error']}")
            else:
                print(f"  {change['entity_name']} (card {change['card_index']}): "
                      f"{change['original']} → {change['fixed']}")
        if len(all_changes) > 10:
            print(f"  ... 외 {len(all_changes) - 10}건")
    
    if args.dry_run:
        print(f"\n[DRY-RUN] 실제 파일은 수정되지 않았습니다.")
        return
    
    if not all_changes:
        print(f"\n수정할 항목이 없습니다.")
        return
    
    # 백업 생성
    if not args.no_backup and output_path == input_path:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = input_path.parent / 'archive'
        backup_dir.mkdir(exist_ok=True)
        backup_path = backup_dir / f"{input_path.stem}__backup_{timestamp}{input_path.suffix}"
        shutil.copy2(input_path, backup_path)
        print(f"\n백업 생성: {backup_path}")
    
    # 파일 쓰기
    with open(output_path, 'w', encoding='utf-8') as f:
        for line in fixed_lines:
            f.write(line + '\n')
    
    print(f"\n출력 파일: {output_path}")
    
    # 변경 로그 생성
    log_path = output_path.parent / f"{output_path.stem}__fix_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    log_data = {
        'timestamp': datetime.now().isoformat(),
        'input_file': str(input_path),
        'output_file': str(output_path),
        'total_lines': total_lines,
        'changes_count': len(all_changes),
        'changes': all_changes
    }
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)
    
    print(f"변경 로그: {log_path}")
    print(f"\n✅ 완료: {len(all_changes)}건 수정됨")


if __name__ == '__main__':
    main()

