# 컴퓨터를 꺼도 프로세스가 계속 실행되도록 하는 방법

## 개요
MeducAI 파이프라인은 S1→S2→S3→S4 단계를 거치며 시간이 오래 걸릴 수 있습니다. 
컴퓨터를 꺼도 계속 실행되도록 하는 방법들을 정리했습니다.

---

## 방법 1: 클라우드 서버 사용 (권장)

### 1.1 AWS EC2
**장점:**
- 24/7 실행 가능
- 비용: t3.micro (무료 티어) 또는 t3.small (~$15/월)
- 스토리지 확장 용이

**설정 방법:**
```bash
# 1. EC2 인스턴스 생성 (Ubuntu 22.04 LTS 권장)
# 2. SSH 접속
ssh -i your-key.pem ubuntu@your-ec2-ip

# 3. 프로젝트 클론/업로드
git clone your-repo-url
# 또는 scp로 업로드

# 4. 환경 설정
cd MeducAI
python3 -m venv venv
source venv/bin/activate
pip install -r 3_Code/requirements.txt

# 5. .env 파일 설정 (API 키 등)

# 6. screen 또는 tmux로 실행
screen -S meducai
# 또는
tmux new -s meducai

# 7. 파이프라인 실행
RUN_TAG="CLOUD_RUN_$(date +%Y%m%d_%H%M%S)"
python3 3_Code/src/run_arm_full.py --base_dir . --provider gemini --run_tag_base "$RUN_TAG" --arms A,B,C,D,E,F --parallel --max_workers 2 --sample 1 --target_total 12

# 8. screen/tmux에서 분리: Ctrl+A, D (screen) 또는 Ctrl+B, D (tmux)
# 재접속: screen -r meducai 또는 tmux attach -t meducai
```

**비용 예상:**
- t3.micro (1 vCPU, 1GB RAM): 무료 티어 또는 ~$7/월
- t3.small (2 vCPU, 2GB RAM): ~$15/월
- 스토리지: EBS 20GB ~$2/월

### 1.2 Google Cloud Platform (GCP)
**장점:**
- $300 무료 크레딧 제공
- Compute Engine 사용

**설정 방법:**
```bash
# 1. GCP 콘솔에서 VM 인스턴스 생성
# 2. SSH 접속 (브라우저 또는 gcloud CLI)
gcloud compute ssh your-instance-name --zone=your-zone

# 3. 이후는 EC2와 동일
```

### 1.3 Azure
**장점:**
- $200 무료 크레딧 제공
- 한국 리전 사용 가능

---

## 방법 2: 원격 서버/VPS 사용

### 2.1 저렴한 VPS 제공업체
- **DigitalOcean**: $6/월부터 (1GB RAM)
- **Linode**: $5/월부터
- **Vultr**: $6/월부터
- **한국 서버**: 카페24, 가비아 등 (비용 높음)

### 2.2 설정 (EC2와 동일)
```bash
# SSH 접속 후
screen -S meducai
# 파이프라인 실행
```

---

## 방법 3: macOS에서 백그라운드 실행 (컴퓨터 켜져 있을 때만)

### ⚠️ 중요: macOS Sleep 방지

**tmux/screen만으로는 sleep을 막을 수 없습니다!** macOS가 sleep 모드로 들어가면 프로세스가 일시 중지됩니다.

**해결 방법:**

#### 3.0.1 caffeinate 사용 (권장)

```bash
# tmux 세션에서 caffeinate로 sleep 방지
tmux new -s meducai

# caffeinate로 sleep 방지하면서 파이프라인 실행
caffeinate -i python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag Final_S1_armC_test \
  --arm C \
  --stage 1 \
  --resume

# 또는 특정 프로세스 ID에 대해 sleep 방지
caffeinate -w <PID>
```

**caffeinate 옵션:**
- `-i`: 시스템이 idle 상태여도 sleep 방지
- `-w <PID>`: 특정 프로세스가 실행 중일 때만 sleep 방지
- `-d`: 디스플레이가 켜져 있을 때만 sleep 방지
- `-s`: 시스템이 sleep하지 않도록 방지 (가장 강력)

**예시:**
```bash
# 가장 강력한 방법 (시스템 sleep 완전 차단)
caffeinate -s python3 3_Code/src/01_generate_json.py ...

# 또는 tmux와 함께
tmux new -s meducai
caffeinate -s python3 3_Code/src/01_generate_json.py ...
# Ctrl+B, D로 분리
```

#### 3.0.2 시스템 설정에서 sleep 방지

```bash
# 터미널에서 sleep 방지 (시스템 설정)
# 시스템 설정 → 에너지 절약 → "컴퓨터가 절전 모드로 전환되지 않도록 방지" 체크

# 또는 명령어로 (일시적)
sudo pmset -a sleep 0
sudo pmset -a disablesleep 1

# 원래대로 복구
sudo pmset -a sleep 10
sudo pmset -a disablesleep 0
```

**주의:** 시스템 설정 변경은 모든 앱에 영향을 줍니다. 작업 완료 후 복구하세요.

#### 3.0.3 tmux + caffeinate 조합 (권장)

```bash
# 1. tmux 세션 생성
tmux new -s meducai

# 2. caffeinate로 sleep 방지하면서 실행
caffeinate -s python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag Final_S1_armC_test \
  --arm C \
  --stage 1 \
  --resume

# 3. Ctrl+B, D로 분리 (프로세스는 계속 실행)
# 4. 재접속: tmux attach -t meducai
```

### 3.1 nohup 사용 (간단)
```bash
# 터미널에서
nohup python3 3_Code/src/run_arm_full.py \
  --base_dir . \
  --provider gemini \
  --run_tag_base "$RUN_TAG" \
  --arms A,B,C,D,E,F \
  --parallel \
  --max_workers 2 \
  --sample 1 \
  --target_total 12 \
  > logs/nohup_${RUN_TAG}.log 2>&1 &

# 프로세스 ID 확인
echo $!

# 로그 확인
tail -f logs/nohup_${RUN_TAG}.log
```

**주의:** 
- 컴퓨터를 끄면 프로세스가 종료됩니다. 컴퓨터는 켜둬야 합니다.
- **sleep 방지가 필요합니다!** `caffeinate` 명령어를 함께 사용하세요.

### 3.2 launchd 사용 (macOS 서비스)
**장점:** 컴퓨터가 켜져 있을 때 자동 재시작 가능

**설정:**
```bash
# ~/Library/LaunchAgents/com.meducai.pipeline.plist 생성
```

파일 내용:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.meducai.pipeline</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>/path/to/workspace/workspace/MeducAI/3_Code/src/run_arm_full.py</string>
        <string>--base_dir</string>
        <string>/path/to/workspace/workspace/MeducAI</string>
        <string>--provider</string>
        <string>gemini</string>
        <string>--run_tag_base</string>
        <string>LAUNCHD_RUN</string>
        <string>--arms</string>
        <string>A,B,C,D,E,F</string>
        <string>--parallel</string>
        <string>--max_workers</string>
        <string>2</string>
        <string>--sample</string>
        <string>1</string>
        <string>--target_total</string>
        <string>12</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/path/to/workspace/workspace/MeducAI</string>
    <key>StandardOutPath</key>
    <string>/path/to/workspace/workspace/MeducAI/logs/launchd_stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/path/to/workspace/workspace/MeducAI/logs/launchd_stderr.log</string>
    <key>RunAtLoad</key>
    <false/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
```

**사용:**
```bash
# 로드
launchctl load ~/Library/LaunchAgents/com.meducai.pipeline.plist

# 시작
launchctl start com.meducai.pipeline

# 상태 확인
launchctl list | grep meducai

# 중지
launchctl stop com.meducai.pipeline

# 언로드
launchctl unload ~/Library/LaunchAgents/com.meducai.pipeline.plist
```

**주의:** 컴퓨터를 끄면 실행이 중단됩니다.

---

## ⚠️ 중요: 와이파이/네트워크 연결 끊김 시 동작

### 현재 동작 방식

MeducAI 파이프라인은 **네트워크 오류에 대한 재시도 로직**이 있습니다:

1. **자동 재시도:**
   - 네트워크 오류 발생 시 최대 **2번 재시도** (총 3번 시도)
   - 재시도 간격: 지수 백오프 (2초, 4초, ... 최대 30초)
   - 감지되는 오류: `connection error`, `connection reset`, `timeout`, `502`, `503`, `504` 등

2. **재시도 실패 시:**
   - 해당 그룹이 **실패 처리**됨
   - 프로세스는 **다음 그룹으로 계속 진행**
   - 실패한 그룹은 `--resume` 옵션으로 나중에 재실행 가능

### 문제점

**와이파이가 오래 끊겨 있으면:**
- 재시도 3번 모두 실패 → 그룹 실패 처리
- 와이파이 재연결 후에도 **자동으로 재시도하지 않음**
- 프로세스는 이미 다음 그룹으로 넘어감

### 해결 방법

#### 방법 1: `--resume` 옵션 사용 (권장)

와이파이 재연결 후 실패한 그룹만 다시 실행:

```bash
# 와이파이 재연결 후
python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag Final_S1_armC_test \
  --arm C \
  --stage 1 \
  --resume
```

**장점:**
- 이미 성공한 그룹은 스킵
- 실패한 그룹만 재실행
- 시간 절약

#### 방법 2: 재시도 횟수 증가

환경변수로 재시도 횟수 늘리기:

```bash
# 재시도 횟수를 5번으로 증가 (기본값: 2)
export LLM_RETRY_MAX=5

# 파이프라인 실행
python3 3_Code/src/01_generate_json.py ...
```

**주의:** 재시도 횟수를 너무 늘리면 와이파이가 오래 끊겨 있을 때 대기 시간이 길어집니다.

#### 방법 3: 안정적인 네트워크 환경 사용

**권장:**
- **유선 인터넷** 사용 (와이파이보다 안정적)
- **클라우드 서버** 사용 (AWS EC2, GCP 등) - 네트워크가 안정적
- **모바일 핫스팟** 대비 - 유선 인터넷이 더 안정적

#### 방법 4: 네트워크 모니터링 스크립트

와이파이 연결 상태를 모니터링하고 자동으로 재연결:

```bash
# 네트워크 연결 확인 스크립트 (별도 터미널에서 실행)
while true; do
  if ! ping -c 1 8.8.8.8 > /dev/null 2>&1; then
    echo "$(date): 네트워크 연결 끊김 감지"
    # 자동 재연결 시도 (macOS)
    networksetup -setairportpower en0 off
    sleep 2
    networksetup -setairportpower en0 on
  fi
  sleep 10
done
```

### 실제 시나리오

**시나리오 1: 와이파이가 1-2분 끊김**
- ✅ 재시도 로직으로 대부분 자동 복구
- 문제 없음

**시나리오 2: 와이파이가 5분 이상 끊김**
- ❌ 재시도 모두 실패 → 그룹 실패 처리
- 해결: 와이파이 재연결 후 `--resume` 옵션으로 재실행

**시나리오 3: 와이파이가 계속 불안정**
- ❌ 여러 그룹이 실패할 수 있음
- 해결: 유선 인터넷 사용 또는 클라우드 서버 사용 권장

### 모니터링

실패한 그룹 확인:

```bash
# 로그에서 실패한 그룹 찾기
grep -r "group failed" logs/

# 또는 출력 파일 확인
# stage1_struct__armC.jsonl에서 누락된 그룹 확인
```

---

## 방법 4: screen/tmux 사용 (원격 서버에서)

### 4.1 screen
```bash
# 세션 생성
screen -S meducai

# 파이프라인 실행
RUN_TAG="SCREEN_RUN_$(date +%Y%m%d_%H%M%S)"
python3 3_Code/src/run_arm_full.py ...

# 분리: Ctrl+A, D
# 재접속: screen -r meducai
# 목록: screen -ls
# 종료: screen 내에서 exit 또는 screen -X -S meducai quit
```

### 4.2 tmux (screen보다 기능이 많음)
```bash
# 세션 생성
tmux new -s meducai

# 파이프라인 실행
RUN_TAG="TMUX_RUN_$(date +%Y%m%d_%H%M%S)"
python3 3_Code/src/run_arm_full.py ...

# 분리: Ctrl+B, D
# 재접속: tmux attach -t meducai
# 목록: tmux ls
# 종료: tmux kill-session -t meducai
```

---

## 방법 5: 프로세스 매니저 사용

### 5.1 supervisor (Linux/서버)
```bash
# 설치 (Ubuntu/Debian)
sudo apt-get install supervisor

# 설정 파일 생성: /etc/supervisor/conf.d/meducai.conf
[program:meducai]
command=/path/to/venv/bin/python3 /path/to/MeducAI/3_Code/src/run_arm_full.py --base_dir /path/to/MeducAI --provider gemini --run_tag_base SUPERVISOR_RUN --arms A,B,C,D,E,F --parallel --max_workers 2 --sample 1 --target_total 12
directory=/path/to/MeducAI
user=your-user
autostart=true
autorestart=true
stderr_logfile=/path/to/MeducAI/logs/supervisor_stderr.log
stdout_logfile=/path/to/MeducAI/logs/supervisor_stdout.log

# 재로드
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start meducai
```

### 5.2 PM2 (Node.js 기반, Python도 지원)
```bash
# 설치
npm install -g pm2

# 실행
pm2 start 3_Code/src/run_arm_full.py \
  --name meducai \
  --interpreter python3 \
  -- --base_dir . --provider gemini --run_tag_base PM2_RUN --arms A,B,C,D,E,F --parallel --max_workers 2 --sample 1 --target_total 12

# 상태 확인
pm2 status

# 로그
pm2 logs meducai

# 재시작
pm2 restart meducai

# 종료
pm2 stop meducai
```

---

## 추천 방법 비교

| 방법 | 컴퓨터 꺼도 실행 | 비용 | 설정 난이도 | 추천도 |
|------|----------------|------|------------|--------|
| **AWS EC2** | ✅ | $7-15/월 | 중 | ⭐⭐⭐⭐⭐ |
| **GCP/Azure** | ✅ | 무료 크레딧 | 중 | ⭐⭐⭐⭐ |
| **VPS** | ✅ | $5-10/월 | 중 | ⭐⭐⭐⭐ |
| **nohup (macOS)** | ❌ | 무료 | 쉬움 | ⭐⭐ |
| **launchd (macOS)** | ❌ | 무료 | 중 | ⭐⭐ |
| **tmux + caffeinate (macOS)** | ⚠️* | 무료 | 쉬움 | ⭐⭐⭐ |
| **screen/tmux (서버)** | ✅ | 서버 비용 | 쉬움 | ⭐⭐⭐⭐⭐ |

*컴퓨터는 켜둬야 하지만 sleep은 방지됨

---

## 실제 사용 예시: AWS EC2 설정

### 1단계: EC2 인스턴스 생성
1. AWS 콘솔 → EC2 → Launch Instance
2. Ubuntu 22.04 LTS 선택
3. t3.micro 또는 t3.small 선택
4. 키 페어 생성/다운로드
5. 보안 그룹: SSH (22), 필요시 HTTP/HTTPS 추가

### 2단계: 초기 설정
```bash
# SSH 접속
ssh -i your-key.pem ubuntu@your-ec2-ip

# 시스템 업데이트
sudo apt-get update
sudo apt-get upgrade -y

# 필수 패키지 설치
sudo apt-get install -y python3-pip python3-venv git screen

# 프로젝트 클론 (또는 scp로 업로드)
git clone your-repo-url
cd MeducAI

# 가상환경 설정
python3 -m venv venv
source venv/bin/activate
pip install -r 3_Code/requirements.txt

# .env 파일 설정 (nano 또는 vim 사용)
nano .env
# API 키 등 입력

# screen 세션 시작
screen -S meducai
```

### 3단계: 파이프라인 실행
```bash
# screen 내에서
RUN_TAG="EC2_RUN_$(date +%Y%m%d_%H%M%S)"
python3 3_Code/src/run_arm_full.py \
  --base_dir . \
  --provider gemini \
  --run_tag_base "$RUN_TAG" \
  --arms A,B,C,D,E,F \
  --parallel \
  --max_workers 2 \
  --sample 1 \
  --target_total 12

# Ctrl+A, D로 분리
```

### 4단계: 재접속 및 모니터링
```bash
# SSH 재접속 후
screen -r meducai

# 로그 확인
tail -f logs/$RUN_TAG/${RUN_TAG}__armA.log
```

---

## 주의사항

1. **API 키 보안**
   - `.env` 파일을 Git에 커밋하지 않기
   - 서버에서도 `.env` 권한 제한: `chmod 600 .env`

2. **비용 관리**
   - 사용하지 않을 때는 인스턴스 중지 (EC2: Stop Instance)
   - 스토리지 비용도 확인

3. **데이터 백업**
   - 중요한 결과물은 정기적으로 다운로드
   - S3나 다른 스토리지에 자동 백업 설정 고려

4. **모니터링**
   - 로그 파일 정기 확인
   - 디스크 공간 모니터링: `df -h`
   - 메모리 사용량: `free -h`

---

## 빠른 시작 가이드

**가장 빠른 방법 (EC2 사용):**
```bash
# 1. EC2 인스턴스 생성 (Ubuntu 22.04, t3.micro)
# 2. SSH 접속
ssh -i key.pem ubuntu@your-ip

# 3. 한 번에 설정
sudo apt-get update && sudo apt-get install -y python3-pip python3-venv git screen
git clone your-repo && cd MeducAI
python3 -m venv venv && source venv/bin/activate
pip install -r 3_Code/requirements.txt
# .env 설정 후
screen -S meducai
# 파이프라인 실행
```

---

**작성일**: 2025-12-23  
**목적**: MeducAI 파이프라인을 컴퓨터를 꺼도 계속 실행하기 위한 가이드

