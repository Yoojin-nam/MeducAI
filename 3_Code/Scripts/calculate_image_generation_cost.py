#!/usr/bin/env python3
"""
Gemini 3 Pro Image Preview 유료 계정 비용 계산 스크립트

이미지 생성 비용 계산:
- 카드 이미지 (2K): Q1, Q2 per entity
- 테이블 비주얼 (4K): 1 per group

가격 (유료 계정 기준):
- 입력: $2.00 per 1M tokens (텍스트/이미지), 이미지당 약 $0.0011
- 출력 (2K 이미지): $0.134 per 1,000/2,000 이미지
- 출력 (4K 이미지): $0.24 per 4,000 이미지
또는
- 출력 (이미지): $120.00 per 1M tokens

참고: 실제 비용은 토큰 기반 계산과 이미지 단위 계산 중 더 저렴한 방식을 사용할 수 있습니다.
"""

import argparse
from pathlib import Path
import json
from typing import Dict, Tuple


# Gemini 3 Pro Image Preview 가격 (유료 계정)
# 참고: 가격표에서 "$0.134 per 1,000/2,000 images"는 1,000개 또는 2,000개 당 $0.134를 의미
# "$0.24 per 4,000 images"는 4,000개 당 $0.24를 의미
PRICING = {
    "input_per_million_tokens": 2.00,  # $2.00 per 1M tokens (텍스트/이미지)
    "input_per_image_approx": 0.0011,  # 약 $0.0011 per image (프롬프트 포함)
    
    # 출력 비용 (이미지) - Google 가격표 기준
    # "$0.134 per 1,000/2,000 images" = $0.134 per 1,000 images 또는 per 2,000 images
    # 보수적으로 1,000개 기준으로 계산
    "output_2k_per_1000_images": 0.134,  # $0.134 per 1,000 images (2K 해상도)
    "output_2k_per_image": 0.134 / 1000,  # 이미지당 약 $0.000134
    "output_4k_per_4000_images": 0.24,   # $0.24 per 4,000 images (4K 해상도)
    "output_4k_per_image": 0.24 / 4000,  # 이미지당 약 $0.00006
    "output_per_million_tokens": 120.00, # $120.00 per 1M tokens (이미지 출력)
}


def estimate_tokens_per_image(prompt_length_chars: int = 500) -> Tuple[int, int]:
    """
    이미지 생성당 대략적인 토큰 수 추정
    
    Args:
        prompt_length_chars: 프롬프트 길이 (문자 수)
    
    Returns:
        (입력 토큰 수, 출력 토큰 수 추정)
    """
    # 입력: 프롬프트 토큰 (대략 1 문자 = 0.25 토큰)
    input_tokens = int(prompt_length_chars * 0.25)
    
    # 출력: 이미지 생성은 토큰으로 측정하기 어려우므로 이미지 단위 가격 사용
    # 2K 이미지: 약 500-1000 토큰, 4K 이미지: 약 2000-4000 토큰 (대략)
    output_tokens_2k = 750  # 2K 이미지 평균
    output_tokens_4k = 3000  # 4K 이미지 평균
    
    return input_tokens, output_tokens_2k, output_tokens_4k


def calculate_cost_from_entity_count(
    total_entities: int,
    total_groups: int,
    prompt_length_chars: int = 500
) -> Dict[str, float]:
    """
    엔티티 수와 그룹 수로부터 총 비용 계산
    
    Args:
        total_entities: 전체 엔티티 수
        total_groups: 전체 그룹 수
        prompt_length_chars: 평균 프롬프트 길이 (문자 수)
    
    Returns:
        비용 세부 정보 딕셔너리
    """
    # 이미지 개수 계산
    # 카드 이미지: 엔티티당 2개 (Q1, Q2) - 2K 해상도
    card_images_2k = total_entities * 2
    
    # 테이블 비주얼: 그룹당 1개 - 4K 해상도
    table_images_4k = total_groups
    
    total_images = card_images_2k + table_images_4k
    
    # 토큰 추정
    input_tokens_per_card, output_tokens_2k, output_tokens_4k = estimate_tokens_per_image(prompt_length_chars)
    
    total_input_tokens = (
        card_images_2k * input_tokens_per_card +
        table_images_4k * input_tokens_per_card
    )
    
    total_output_tokens = (
        card_images_2k * output_tokens_2k +
        table_images_4k * output_tokens_4k
    )
    
    # 비용 계산 방법 1: 이미지 단위 가격 사용 (더 간단하고 정확)
    # 2K 이미지 비용 ($0.134 per 1,000 images)
    card_image_cost_2k = (card_images_2k / 1000) * PRICING["output_2k_per_1000_images"]
    
    # 4K 이미지 비용 ($0.24 per 4,000 images)
    table_image_cost_4k = (table_images_4k / 4000) * PRICING["output_4k_per_4000_images"]
    
    # 또는 이미지당 단가로 계산 (더 정확할 수 있음)
    card_image_cost_2k_alt = card_images_2k * PRICING["output_2k_per_image"]
    table_image_cost_4k_alt = table_images_4k * PRICING["output_4k_per_image"]
    
    # 입력 비용 (이미지당 약 $0.0011)
    input_cost = total_images * PRICING["input_per_image_approx"]
    
    # 총 비용 (이미지 단위 가격 방식)
    total_cost_image_based = input_cost + card_image_cost_2k + table_image_cost_4k
    
    # 비용 계산 방법 2: 토큰 기반 가격 사용
    input_cost_token_based = (total_input_tokens / 1_000_000) * PRICING["input_per_million_tokens"]
    output_cost_token_based = (total_output_tokens / 1_000_000) * PRICING["output_per_million_tokens"]
    total_cost_token_based = input_cost_token_based + output_cost_token_based
    
    # 더 저렴한 방법 선택
    total_cost = min(total_cost_image_based, total_cost_token_based)
    
    return {
        "total_entities": total_entities,
        "total_groups": total_groups,
        "card_images_2k": card_images_2k,
        "table_images_4k": table_images_4k,
        "total_images": total_images,
        "costs": {
            "input_cost_image_based": input_cost,
            "output_cost_2k_images": card_image_cost_2k,
            "output_cost_4k_images": table_image_cost_4k,
            "total_cost_image_based": total_cost_image_based,
            "input_cost_token_based": input_cost_token_based,
            "output_cost_token_based": output_cost_token_based,
            "total_cost_token_based": total_cost_token_based,
            "total_cost_estimate": total_cost,
        },
        "tokens": {
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
        }
    }


def calculate_from_s3_specs(s3_spec_file: Path) -> Dict[str, float]:
    """
    S3 image spec 파일로부터 실제 이미지 개수와 비용 계산
    
    Args:
        s3_spec_file: s3_image_spec__arm{X}.jsonl 파일 경로
    
    Returns:
        비용 세부 정보 딕셔너리
    """
    card_images_2k = 0
    table_images_4k = 0
    
    with open(s3_spec_file, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            spec = json.loads(line)
            spec_kind = spec.get('spec_kind', '').strip()
            
            if spec_kind == 'S1_TABLE_VISUAL':
                table_images_4k += 1
            elif spec_kind in ('S2_CARD_IMAGE', 'S2_CARD_CONCEPT'):
                card_images_2k += 1
    
    total_groups = table_images_4k
    total_entities = card_images_2k // 2  # Q1, Q2 두 개씩
    
    return calculate_cost_from_entity_count(total_entities, total_groups)


def calculate_from_manifest(s4_manifest_file: Path) -> Dict[str, float]:
    """
    S4 image manifest 파일로부터 실제 생성된 이미지 개수와 비용 계산
    
    Args:
        s4_manifest_file: s4_image_manifest__arm{X}.jsonl 파일 경로
    
    Returns:
        비용 세부 정보 딕셔너리
    """
    card_images_2k = 0
    table_images_4k = 0
    
    with open(s4_manifest_file, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            entry = json.loads(line)
            spec_kind = entry.get('spec_kind', '').strip()
            generation_success = entry.get('generation_success', False)
            
            if not generation_success:
                continue  # 실패한 이미지는 비용 계산에서 제외
            
            if spec_kind == 'S1_TABLE_VISUAL':
                table_images_4k += 1
            elif spec_kind in ('S2_CARD_IMAGE', 'S2_CARD_CONCEPT'):
                card_images_2k += 1
    
    total_groups = table_images_4k
    total_entities = card_images_2k // 2  # Q1, Q2 두 개씩
    
    return calculate_cost_from_entity_count(total_entities, total_groups)


def main():
    parser = argparse.ArgumentParser(
        description="Gemini 3 Pro Image Preview 유료 계정 비용 계산",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
  # 엔티티 수와 그룹 수로 계산
  python calculate_image_generation_cost.py --entities 500 --groups 100
  
  # S3 spec 파일로 계산
  python calculate_image_generation_cost.py --s3_spec 2_Data/metadata/generated/RUN_TAG/s3_image_spec__armA.jsonl
  
  # S4 manifest 파일로 계산
  python calculate_image_generation_cost.py --s4_manifest 2_Data/metadata/generated/RUN_TAG/s4_image_manifest__armA.jsonl
        """
    )
    
    parser.add_argument(
        '--entities',
        type=int,
        help='전체 엔티티 수'
    )
    parser.add_argument(
        '--groups',
        type=int,
        help='전체 그룹 수'
    )
    parser.add_argument(
        '--s3_spec',
        type=Path,
        help='S3 image spec 파일 경로 (s3_image_spec__arm{X}.jsonl)'
    )
    parser.add_argument(
        '--s4_manifest',
        type=Path,
        help='S4 image manifest 파일 경로 (s4_image_manifest__arm{X}.jsonl)'
    )
    parser.add_argument(
        '--prompt-length',
        type=int,
        default=500,
        help='평균 프롬프트 길이 (문자 수, 기본값: 500)'
    )
    
    args = parser.parse_args()
    
    if args.s3_spec:
        if not args.s3_spec.exists():
            print(f"❌ 파일을 찾을 수 없습니다: {args.s3_spec}")
            return
        result = calculate_from_s3_specs(args.s3_spec)
    elif args.s4_manifest:
        if not args.s4_manifest.exists():
            print(f"❌ 파일을 찾을 수 없습니다: {args.s4_manifest}")
            return
        result = calculate_from_manifest(args.s4_manifest)
    elif args.entities and args.groups:
        result = calculate_cost_from_entity_count(
            args.entities,
            args.groups,
            args.prompt_length
        )
    else:
        parser.print_help()
        return
    
    # 결과 출력
    print("=" * 60)
    print("Gemini 3 Pro Image Preview 유료 계정 비용 계산")
    print("=" * 60)
    print()
    print(f"📊 이미지 생성 개수:")
    print(f"  - 전체 엔티티: {result['total_entities']:,}개")
    print(f"  - 전체 그룹: {result['total_groups']:,}개")
    print(f"  - 카드 이미지 (2K): {result['card_images_2k']:,}개")
    print(f"  - 테이블 비주얼 (4K): {result['table_images_4k']:,}개")
    print(f"  - 총 이미지: {result['total_images']:,}개")
    print()
    
    costs = result['costs']
    print(f"💰 비용 계산 (USD):")
    print()
    print(f"  방법 1: 이미지 단위 가격")
    print(f"    - 입력 비용: ${costs['input_cost_image_based']:.4f}")
    print(f"    - 출력 비용 (2K 이미지): ${costs['output_cost_2k_images']:.4f}")
    print(f"    - 출력 비용 (4K 이미지): ${costs['output_cost_4k_images']:.4f}")
    print(f"    - 총 비용: ${costs['total_cost_image_based']:.2f}")
    print()
    print(f"  방법 2: 토큰 기반 가격")
    print(f"    - 입력 토큰: {result['tokens']['total_input_tokens']:,} tokens")
    print(f"    - 출력 토큰: {result['tokens']['total_output_tokens']:,} tokens")
    print(f"    - 입력 비용: ${costs['input_cost_token_based']:.4f}")
    print(f"    - 출력 비용: ${costs['output_cost_token_based']:.4f}")
    print(f"    - 총 비용: ${costs['total_cost_token_based']:.2f}")
    print()
    print(f"  🎯 예상 총 비용 (더 저렴한 방법): ${costs['total_cost_estimate']:.2f} USD")
    print()
    print("=" * 60)
    print()
    print("참고:")
    print("- 실제 비용은 Google이 토큰 기반과 이미지 단위 가격 중 적용하는 방식에 따라 달라질 수 있습니다.")
    print("- 입력 비용은 프롬프트 길이에 따라 달라질 수 있습니다.")
    print("- 재시도/실패한 이미지는 비용에 포함되지 않습니다 (성공한 이미지만 계산).")


if __name__ == '__main__':
    main()

