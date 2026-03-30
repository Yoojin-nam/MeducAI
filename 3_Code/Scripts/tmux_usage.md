실행
chmod +x run_s0_6arm_tmux.sh
./run_s0_6arm_tmux.sh

2) 사용 방법 (운영)

tmux에서 빠져나가기(분리): Ctrl+b → d

다시 들어가기:

tmux attach -t meducai_s0_6arm


세션 목록:

tmux ls

B) 결과 확인 커맨드 (추천)
1) arm별 로그 tail
tail -f 2_Data/metadata/generated/<RUN_TAG>/logs/run_*_arm*.log

2) output JSONL 파일 존재 확인
ls -lt 2_Data/metadata/generated/<RUN_TAG>/output_*__arm*.jsonl

3) 성공/실패 빠른 집계
grep -R "DONE" -n 2_Data/metadata/generated/<RUN_TAG>/logs
grep -R "group failed" -n 2_Data/metadata/generated/<RUN_TAG>/logs

C) 실험 비용 안전장치 (강권)

S0에서는 아래를 추천합니다.

export LLM_RETRY_MAX=0
export S0_FIXED_PAYLOAD_CARDS=12
export TIMEOUT_S=120


그리고 처음엔 SAMPLE=1로 시작 → 성공 확인 후 SAMPLE 비우고 전체 실행.

SAMPLE=1 ./run_s0_6arm_tmux.sh
# OK면
SAMPLE= ./run_s0_6arm_tmux.sh

D) 주의: “동시에 6개 창”은 API rate-limit/429 위험

동시 실행이 429를 유발하면 비용과 시간이 더 나빠질 수 있습니다.
그럴 경우:

동시 실행 대신 순차 실행(arm을 하나씩)로 바꾸거나

provider별로 분리(예: gemini 5개 병렬, gpt 1개 단독)하거나

간단한 sleep 삽입

원하시면 “rate-limit 안전한 순차 실행 버전”도 바로 드리겠습니다.