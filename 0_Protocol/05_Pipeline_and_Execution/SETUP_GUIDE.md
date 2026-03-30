# MeducAI 프로젝트 세팅 가이드

이 문서는 MeducAI 프로젝트와 함께 작업하기 위해 필요한 환경 설정을 안내합니다.

---

## 1. 필수 요구사항

### 1.1 Python 버전
- **Python 3.10 이상, 3.13 미만** (권장: 3.10, 3.11, 3.12)
- 확인 방법:
  ```bash
  python3 --version
  ```

### 1.2 시스템 요구사항
- macOS / Linux (Windows는 WSL 권장)
- Git
- 터미널 접근 권한

---

## 2. 프로젝트 환경 설정

### 2.1 가상환경 생성 및 활성화

```bash
# 프로젝트 루트 디렉토리로 이동
cd /path/to/workspace/workspace/MeducAI

# 가상환경 생성 (Python 3.10+)
python3 -m venv .venv

# 가상환경 활성화
source .venv/bin/activate  # macOS/Linux
# 또는
.venv/bin/activate

# 활성화 확인 (프롬프트에 (.venv) 표시됨)
which python3
```

### 2.2 의존성 설치

```bash
# 가상환경이 활성화된 상태에서
pip install --upgrade pip
pip install -r requirements.txt

# 또는 3_Code/requirements.txt 사용 (버전이 다를 수 있음)
pip install -r 3_Code/requirements.txt
```

**설치되는 주요 패키지:**
- `pandas`, `numpy` - 데이터 처리
- `pydantic`, `jsonschema` - 데이터 검증
- `openai`, `google-genai` - LLM API 클라이언트
- `python-dotenv` - 환경 변수 관리
- `tqdm`, `rich` - 진행 표시 및 로깅

---

## 3. 환경 변수 설정 (.env 파일)

### 3.1 .env 파일 생성

프로젝트 루트에 `.env` 파일을 생성합니다:

```bash
# 프로젝트 루트에서
touch .env
```

### 3.2 필수 API 키 설정

`.env` 파일에 다음 내용을 추가하세요:

```bash
# ============================================
# LLM Provider API Keys (필수)
# ============================================

# Google Gemini API Key
GOOGLE_API_KEY=your_google_api_key_here

# OpenAI API Key (Arm F 사용 시 필요)
OPENAI_API_KEY=your_openai_api_key_here

# DeepSeek API Key (선택사항)
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# Anthropic Claude API Key (선택사항)
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# ============================================
# 실행 설정 (선택사항)
# ============================================

# 기본 시드 (재현성)
SEED=42

# 기본 RUN_TAG (실행 식별자)
# RUN_TAG=S0_QA_$(date +%Y%m%d_%H%M%S)

# ============================================
# 카드 타입/이미지 비율 (FINAL 모드용, 선택사항)
# ============================================

# CARD_TYPE_RATIOS=Basic_QA:0.34,Cloze_Finding:0.33,MCQ_Vignette:0.33
# IMAGE_NECESSITY_RATIOS=IMG_REQ:0.40,IMG_OPT:0.40,IMG_NONE:0.20
```

**중요:**
- `.env` 파일은 `.gitignore`에 포함되어 있어 Git에 커밋되지 않습니다
- API 키는 절대 공개 저장소에 업로드하지 마세요
- 최소한 `GOOGLE_API_KEY`는 필수입니다 (Arm A-E 사용 시)

### 3.3 API 키 획득 방법

1. **Google Gemini API Key:**
   - https://aistudio.google.com/app/apikey 접속
   - 새 API 키 생성

2. **OpenAI API Key:**
   - https://platform.openai.com/api-keys 접속
   - 새 API 키 생성

---

## 4. 프로젝트 구조 이해

### 4.1 핵심 디렉토리

```
MeducAI/
├── 0_Protocol/          # Canonical 문서 (헌법)
├── 2_Data/              # 데이터 (Git 제외)
│   ├── raw/            # 원본 데이터
│   └── metadata/       # 메타데이터
├── 3_Code/              # 소스 코드
│   ├── src/            # 메인 스크립트
│   ├── prompt/         # 프롬프트 템플릿
│   └── configs/        # 설정 파일
└── 6_Distributions/    # 배포용 산출물
```

### 4.2 실행 정책

**중요:** 모든 스크립트는 **프로젝트 루트 디렉토리**에서 실행해야 합니다:

```bash
# ✅ 올바른 방법
cd /path/to/workspace/workspace/MeducAI
python3 3_Code/src/01_generate_json.py --mode S0 --arm A --run_tag TEST

# ❌ 잘못된 방법
cd 3_Code/src
python3 01_generate_json.py --mode S0 --arm A --run_tag TEST
```

---

## 5. 기본 실행 테스트

### 5.1 API 키 확인

```bash
# 가상환경 활성화 후
python3 3_Code/src/tools/check_models.py
```

이 스크립트는 각 Provider의 API 키가 올바른지 확인하고 사용 가능한 모델을 나열합니다.

### 5.2 Smoke Test (최소 실행)

```bash
# 프로젝트 루트에서
python3 3_Code/src/01_generate_json.py \
  --mode S0 \
  --base_dir . \
  --run_tag TEST_SMOKE_$(date +%Y%m%d_%H%M%S) \
  --arm A \
  --sample 1 \
  --seed 42
```

**예상 결과:**
- `2_Data/metadata/generated/<RUN_TAG>/` 디렉토리 생성
- `output_*.jsonl` 파일 생성
- 에러 없이 완료

---

## 6. 개발 워크플로우

### 6.1 코드 수정 전 체크리스트

1. **가상환경 활성화 확인**
   ```bash
   which python3  # .venv/bin/python3 경로 확인
   ```

2. **의존성 동기화**
   ```bash
   pip install -r requirements.txt
   ```

3. **문법 검사**
   ```bash
   python3 -m compileall 3_Code/src
   ```

### 6.2 파일 수정 후 검증

프로젝트의 **Fail-Fast 원칙**에 따라:

```bash
# 1. 컴파일 확인
python3 -m compileall 3_Code/src

# 2. Smoke 테스트 (짧은 그룹)
python3 3_Code/src/01_generate_json.py \
  --mode S0 \
  --run_tag DEV_SMOKE_$(date +%Y%m%d_%H%M%S) \
  --arm A \
  --sample 1

# 3. S1 Gate 검증 (해당되는 경우)
# (S1 Gate 스크립트 실행)
```

### 6.3 Git 작업 전 확인

```bash
# .env 파일이 커밋되지 않았는지 확인
git status | grep .env

# 변경사항 확인
git diff

# 의도하지 않은 파일 제외 확인
git status
```

---

## 7. 문제 해결

### 7.1 일반적인 오류

**오류: `ModuleNotFoundError`**
```bash
# 해결: 가상환경 활성화 및 의존성 재설치
source .venv/bin/activate
pip install -r requirements.txt
```

**오류: `Missing API key: env GOOGLE_API_KEY is not set`**
```bash
# 해결: .env 파일 확인 및 API 키 설정
cat .env | grep GOOGLE_API_KEY
```

**오류: `Output directory not writable`**
```bash
# 해결: 디렉토리 권한 확인
ls -la 2_Data/metadata/generated/
chmod -R u+w 2_Data/metadata/generated/
```

### 7.2 디버깅 팁

1. **로그 확인:**
   ```bash
   # 실행 로그 확인
   tail -f logs/<RUN_TAG>/*.log
   ```

2. **디버그 아티팩트 확인:**
   ```bash
   # S1 디버그 출력 확인
   ls -la 2_Data/metadata/generated/<RUN_TAG>/debug_raw/
   ```

3. **환경 변수 확인:**
   ```bash
   # .env 로드 확인
   python3 -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('GOOGLE_API_KEY', 'NOT SET')[:10])"
   ```

---

## 8. 다음 단계

환경 설정이 완료되면:

1. **프로젝트 문서 읽기:**
   - `README.md` - 프로젝트 개요
   - `0_Protocol/00_Governance/` - Canonical 문서 시스템
   - `0_Protocol/01_Execution_Safety/` - 실행 안전 규칙

2. **파이프라인 이해:**
   - `0_Protocol/05_Pipeline_and_Execution/` - 파이프라인 실행 계획
   - `3_Code/README.md` - 코드 구조

3. **실험 설계 이해:**
   - `0_Protocol/02_Arms_and_Models/` - Arm 설정
   - `0_Protocol/06_QA_and_Study/` - QA 프레임워크

---

## 9. 빠른 참조

### 9.1 자주 사용하는 명령어

```bash
# 가상환경 활성화
source .venv/bin/activate

# 의존성 업데이트
pip install --upgrade -r requirements.txt

# Smoke 테스트
python3 3_Code/src/01_generate_json.py --mode S0 --arm A --run_tag TEST --sample 1

# 실행 상태 확인
ls -la 2_Data/metadata/generated/
```

### 9.2 중요한 파일 위치

- **환경 변수:** `.env` (프로젝트 루트)
- **의존성:** `requirements.txt` (프로젝트 루트)
- **메인 스크립트:** `3_Code/src/01_generate_json.py`
- **Arm 설정:** `3_Code/src/01_generate_json.py` (ARM_CONFIGS)
- **프롬프트:** `3_Code/prompt/`

---

## 10. 도움말

추가 도움이 필요하면:
- 프로젝트 문서: `0_Protocol/` 디렉토리
- 실행 가이드: `0_Protocol/05_Pipeline_and_Execution/README_run.md`
- 안정화 로그: `0_Protocol/01_Execution_Safety/stabilization/`

