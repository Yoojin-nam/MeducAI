아래는 **“FINAL Over-generate + Shortfall Guard”**를 표준으로 고정하는 계획입니다.

T1. FINAL 생성량 정책 확정: Over-generate + Shortfall Guard (권장)
목표

FINAL에서 03_5_select_deck.py가 quota를 적용할 때 부족으로 실패하지 않도록, Step01(Anki 생성)이 group별로 충분한 후보 카드를 생성하도록 만든다.

동시에 비용 폭발 방지(상한/버퍼)와 재현성(Seed/Manifest)을 유지한다.

설계 원칙 (확정)

FINAL에서 group별 목표 quota q_i가 있으면, Step01(Anki)은 그 group에 대해 최소 ceil(q_i * OVERGEN_FACTOR) + OVERGEN_ADD 만큼 “후보 카드”를 생성한다.

group 후보 생성 상한 MAX_CANDIDATES_PER_GROUP를 둔다(비용/시간 가드레일).

생성 실패/필터링/중복제거 등으로 유효 카드가 줄 수 있으므로, Step01이 끝난 뒤 04_5_check_deck_stats.py 또는 별도 validate 단계에서 **“후보≥quota”**를 검사하고 부족 그룹이 있으면 그 그룹만 재생성(재시도)한다.

“sample”은 스모크 테스트에서 처리할 그룹 수 제한(또는 목표 subset 크기)으로 의미를 고정하고, FINAL에서는 기본적으로 sample을 쓰지 않거나(=all groups) 매우 제한적으로만 사용한다.

T1-0. .env 변수 추가 (DoD)
추가/확정 env

FINAL_OVERGEN_FACTOR=1.6 (권장 시작값 1.4~2.0)

FINAL_OVERGEN_ADD=2 (최소 여유분)

MAX_CANDIDATES_PER_GROUP=30 (비용 상한, 프로젝트에 맞게 20~60 조정)

FINAL_RETRY_ROUNDS=2 (부족 그룹 재생성 라운드 수)

FINAL_RETRY_EXTRA=3 (재시도 시 추가 생성량)

DoD:

.env Canonical에 주석으로 “왜 필요한지(Shortfall 방지/비용 상한)” 포함.

T1-1. allocation 결과를 Step01에서 읽을 수 있게 저장 경로 고정 (DoD)

이미 03_5_select_deck.py가 저장:

target_cards_per_group_<RUN_TAG>__armX.json

이를 Step01(Anki)가 읽어서 group별 생성량을 결정할 수 있도록 한다.

DoD:

Step01(Anki)에서 해당 파일을 자동 탐색하여 읽음

없으면:

S0면 무시

FINAL이면 경고 후 “fallback 생성량 정책”으로 동작하거나(권장), hard error(더 엄격)

T1-2. Step01(Anki 생성) 쪽 생성량 정책 반영

당신 프로젝트는 Step01을 “테이블용 / 카드용”으로 분리하려는 상태였으므로, 아래는 카드 생성 엔트리(예: 01_generate_anki_json.py) 기준 티켓입니다.
(현재 파일명이 01_generate_json.py 하나라면, 우선 그 내부에서 Anki 생성 루프에만 아래 정책을 삽입하면 됩니다.)

수정 파일 (우선순위 순)

3_Code/src/01_generate_anki_json.py (있으면)
또는

3_Code/src/01_generate_json.py (현재 단일 파일이면 여기)

핵심 구현 포인트

group별로 “생성해야 하는 후보 카드 수” n_candidates_i를 계산

LLM 호출 시, 프롬프트에 n_candidates_i를 명시 (“Generate exactly N flashcards … output JSON array length N”)

저장되는 카드 CSV/JSONL에 group_id/record_id가 유지되도록 함 (03_5에서 group별 선택에 필수)

함수 시그니처 (필수)
# 3_Code/src/generation_policy.py (신설 권장)
from dataclasses import dataclass
from typing import Dict

@dataclass(frozen=True)
class CandidateGenPolicy:
    overgen_factor: float
    overgen_add: int
    max_candidates_per_group: int
    retry_rounds: int
    retry_extra: int

def compute_candidate_count(q: int, pol: CandidateGenPolicy) -> int: ...
def load_target_quota(path: str) -> Dict[str, int]: ...

compute_candidate_count 규칙 (확정)

n = ceil(q * overgen_factor) + overgen_add

n = min(n, max_candidates_per_group)

하한은 n >= q를 기본 보장(단, max cap이 q보다 낮으면 cap이 우선이므로 이 경우는 config error로 간주하고 hard error)

DoD:

max_candidates_per_group < max(q_i) 인 경우 FINAL에서 hard error (설정 문제)

T1-3. FINAL 재시도 루프: “부족 그룹만 추가 생성” (DoD)
목표

1차 생성 후에도 후보가 quota보다 적으면, 그 그룹만 다시 생성해서 후보 풀을 보강한다.

수정 파일

3_Code/src/01_generate_anki_json.py 또는 01_generate_json.py

DoD

1차 생성 완료 후:

group별 생성된 카드 수를 집계

count_i < q_i 인 그룹 리스트를 만들고

라운드별로 q_i - count_i + FINAL_RETRY_EXTRA 만큼 추가 생성

최대 FINAL_RETRY_ROUNDS 라운드 후에도 부족이면 hard error + 부족 리포트 저장

함수 시그니처 (필수)
def count_cards_by_group(cards_jsonl_path: str) -> Dict[str, int]: ...
def regenerate_missing_groups(missing: Dict[str, int], ...) -> None: ...

T1-4. run_arm_full.py 실행 순서 재배치 (중요)

현재 흐름은:
Step01 → Step02 → Step03.5(선택/할당) → …

하지만 Step01에서 quota 기반 후보 생성량을 적용하려면, Step03.5의 할당 결과를 Step01이 미리 알아야 합니다.

따라서 FINAL 모드에서는 “Allocation 계획”을 Step01 전에 수행해야 합니다.

가장 깔끔한 방법(권장):

(A) 신규 Step: 03_4_plan_allocation.py 신설

입력: group_weights / curriculum metadata

출력: target_cards_per_group_<RUN_TAG>__armX.json

그리고 FINAL 흐름:
Plan Allocation(03_4) → Step01(Anki 후보 생성) → Step02 → Step03_5(선택/검증)

DoD:

FINAL에서 run_arm_full.py가 Step01 전에 03_4_plan_allocation.py를 실행

S0에서는 실행하지 않음

시그니처
# 3_Code/src/03_4_plan_allocation.py
# reads group weights, writes target_cards_per_group json
def main(): ...

(B) 차선책

03_5_select_deck.py에서 quota를 계산하는 로직을 분리해 “plan-only” 모드로 재사용
(하지만 지금 03_5는 cards_csv 의존성이 있어 Step01 전에 쓰기 어렵습니다.)

T1-5. 비용 절약 가드레일 (필수)

DoD:

FINAL에서 sum(n_candidates_i)가 예상치를 넘으면(예: TOTAL_CARDS * 2.0 초과) 경고 또는 hard error

run_manifest.json에 다음 기록:

total_cards_requested

total_candidates_planned

overgen_factor/add/max_candidates

retry rounds 결과

권장 기준:

total_candidates_planned <= total_cards * 1.8 (초기)

이 수치는 S0 결과(편집시간/정확도) 보고 조정

지금 바로 진행 순서 (코딩 액션)

.env에 FINAL overgen 변수 추가

generation_policy.py 신설 + compute_candidate_count 구현

03_4_plan_allocation.py 신설 (혹은 기존 EDA weight를 기반으로 JSON 작성)

Step01(Anki)에:

quota json 로드

group별 후보 생성량 계산

부족 그룹 재시도

run_arm_full.py에서 FINAL일 때:

03_4 → Step01 → Step02 → 03_5 … 순서로 변경