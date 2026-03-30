#!/bin/bash
# 원격 서버(EC2, VPS 등)에서 MeducAI 파이프라인을 실행하기 위한 초기 설정 스크립트
# 사용법: bash setup_remote_server.sh

set -e

echo "=========================================="
echo "🚀 MeducAI 원격 서버 설정 스크립트"
echo "=========================================="
echo ""

# 1. 시스템 업데이트
echo ">>> [1/6] 시스템 업데이트 중..."
sudo apt-get update -qq
sudo apt-get upgrade -y -qq

# 2. 필수 패키지 설치
echo ">>> [2/6] 필수 패키지 설치 중..."
sudo apt-get install -y -qq \
    python3 \
    python3-pip \
    python3-venv \
    git \
    screen \
    tmux \
    htop \
    curl \
    wget

# 3. Python 가상환경 확인
echo ">>> [3/6] Python 가상환경 확인 중..."
if [ ! -d "venv" ]; then
    echo "가상환경이 없습니다. 생성 중..."
    python3 -m venv venv
fi

# 4. 가상환경 활성화 및 패키지 설치
echo ">>> [4/6] Python 패키지 설치 중..."
source venv/bin/activate
pip install --upgrade pip -q
if [ -f "3_Code/requirements.txt" ]; then
    pip install -r 3_Code/requirements.txt -q
else
    echo "⚠️  경고: 3_Code/requirements.txt를 찾을 수 없습니다."
fi

# 5. .env 파일 확인
echo ">>> [5/6] 환경 변수 파일 확인 중..."
if [ ! -f ".env" ]; then
    echo "⚠️  경고: .env 파일이 없습니다."
    echo "   다음 내용을 포함하는 .env 파일을 생성해주세요:"
    echo "   - GOOGLE_API_KEY=your-key"
    echo "   - 기타 필요한 API 키들"
    echo ""
    echo "   예시:"
    echo "   nano .env"
else
    echo "✅ .env 파일이 존재합니다."
    # 보안을 위해 권한 제한
    chmod 600 .env
fi

# 6. 디렉토리 구조 확인
echo ">>> [6/6] 디렉토리 구조 확인 중..."
mkdir -p logs
mkdir -p 2_Data/metadata/generated
mkdir -p 6_Distributions/QA_Packets
mkdir -p 6_Distributions/anki

echo ""
echo "=========================================="
echo "✅ 설정 완료!"
echo "=========================================="
echo ""
echo "다음 단계:"
echo "1. .env 파일에 API 키 설정 (필요한 경우)"
echo "2. screen 또는 tmux로 세션 시작:"
echo "   screen -S meducai"
echo "   # 또는"
echo "   tmux new -s meducai"
echo ""
echo "3. 파이프라인 실행:"
echo "   source venv/bin/activate"
echo "   RUN_TAG=\"REMOTE_RUN_\$(date +%Y%m%d_%H%M%S)\""
echo "   python3 3_Code/src/run_arm_full.py \\"
echo "     --base_dir . \\"
echo "     --provider gemini \\"
echo "     --run_tag_base \"\$RUN_TAG\" \\"
echo "     --arms A,B,C,D,E,F \\"
echo "     --parallel \\"
echo "     --max_workers 2 \\"
echo "     --sample 1 \\"
echo "     --target_total 12"
echo ""
echo "4. screen/tmux에서 분리:"
echo "   screen: Ctrl+A, D"
echo "   tmux: Ctrl+B, D"
echo ""
echo "5. 재접속:"
echo "   screen -r meducai"
echo "   # 또는"
echo "   tmux attach -t meducai"
echo "=========================================="

