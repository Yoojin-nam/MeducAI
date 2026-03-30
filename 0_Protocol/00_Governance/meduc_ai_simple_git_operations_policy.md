# MeducAI 전용 초간단 Git 운영 규칙 (Canonical)

**Status:** Canonical  
**Applies to:** MeducAI 로컬 작업 폴더(단일 사용자/소규모 협업)  
**Effective date:** 2025-12-15  

---

## 0. 목적

본 문서는 MeducAI 프로젝트에서 **복잡한 Git 기능(브랜치, PR, rebase 등)을 사용하지 않고도**
문서/코드 변경 이력을 안정적으로 추적하기 위한 **최소 운영 규칙**을 정의한다.

핵심 목표:
- “최신본이 무엇인지” 혼란 제거
- 실수로 덮어쓴 파일의 복구 가능성 확보
- IRB/논문 대응을 위한 스냅샷(tag) 제공

---

## 1. 운영 원칙 (최소 규칙)

### Rule 1) 브랜치는 `main` 하나만 쓴다
- 브랜치 생성 금지(원칙)
- 예외: 대규모 리팩터링이 필요할 때만 `wip/<topic>` 임시 브랜치 허용

### Rule 2) 작업 단위는 “짧은 주기 커밋”
- 하루 1–3회 커밋(권장)
- 한 번 커밋은 “하나의 의미 있는 변경 묶음”

### Rule 3) 태그(tag)로 중요한 시점을 고정한다
- Protocol freeze, S0 시작/종료 등 **의사결정 시점**은 tag로 남긴다.

---

## 2. Google Drive에서 작업할 때 안전 수칙

> Git은 버전 관리, Drive는 동기화/백업이다.

### 권장 안전 규칙
- 동일 폴더를 **2대 이상**에서 동시에 편집하지 않는다.
- 대량 파일 이동/리네임 직후에는 Drive 동기화가 끝난 뒤 다음 작업을 한다.
- 가능하면 “한 컴퓨터에서만” 작업한다.

### (선택) 가장 안정적인 방식
- 로컬(비동기화 폴더)에서 git 운영 → 일정 주기로 Drive에 복사/백업

---

## 3. 최초 1회 설정 (초기화)

프로젝트 루트(README.md가 있는 폴더)에서 실행:

```bash
cd /path/to/MeducAI

git init

git config user.name "<YOUR_NAME>"
git config user.email "<YOUR_EMAIL>"

# 첫 상태 확인
ls
git status
```

---

## 4. 매일 쓰는 3단계 루틴 (핵심)

### Step 1) 변경 확인
```bash
git status
```

### Step 2) 스테이징
- 전체를 올릴 때:
```bash
git add .
```
- 특정 폴더만 올릴 때(권장):
```bash
git add 0_Protocol/ 3_Code/src/ 1_Instruments/
```

### Step 3) 커밋
```bash
git commit -m "<message>"
```

---

## 5. 커밋 메시지 규칙 (MeducAI 전용)

형식(권장):

```
<AREA>: <what changed> (<why/impact>)
```

예시:
- `PROTOCOL: freeze QA Framework v2.0 (S0 start)`
- `MODELSEL: update plan to v2.0 (6-arm factorial + NI)`
- `OPS: add Gemini usage guide (stable JSON output)`
- `CODE: fix F-arm model name mapping (gpt-5.2-pro)`
- `DOCS: canonicalize document versioning policy`

금지(비권장):
- `update` / `fix`처럼 의미 없는 메시지 단독 사용

---

## 6. 태그(tag) 운영 (강력 추천)

### 언제 태그를 찍나
- Protocol vX Freeze
- S0 시작/종료
- Deployment model 선정/고정
- IRB 제출본 생성

### 태그 규칙
- 형식: `milestone_<topic>_YYYY-MM-DD`

예시:
```bash
git tag milestone_protocol_v2_frozen_2025-12-15
```

태그 목록 확인:
```bash
git tag
```

---

## 7. 가장 유용한 조회/복구 명령 6개

1) 최근 커밋 보기
```bash
git log --oneline -n 20
```

2) 특정 파일 변경 이력
```bash
git log -- <path/to/file>
```

3) 변경 내용(diff) 확인
```bash
git diff
```

4) 마지막 커밋으로 되돌리기(커밋 전 변경 폐기)
```bash
git restore .
```

5) 특정 파일만 되돌리기
```bash
git restore -- <path/to/file>
```

6) 커밋된 파일을 과거 버전으로 되돌리기(주의)
```bash
git checkout <commit_hash> -- <path/to/file>
```

---

## 8. .gitignore 최소 세트 (권장)

프로젝트 루트에 `.gitignore` 파일 생성:

```gitignore
# Python
__pycache__/
*.pyc
.venv/
venv/

# Jupyter
.ipynb_checkpoints/

# OS
.DS_Store

# Secrets
.env
*.key

# Large outputs (예: 결과물/이미지/대규모 데이터)
2_Data/**
4_Results/**
```

> 주의: `2_Data/`와 `4_Results/`를 git으로 추적해야 한다면, 하위 폴더 정책을 별도로 설계한다.

---

## 9. 운영 체크리스트 (5분)

- [ ] `git status`가 깨끗한가?
- [ ] 커밋 메시지가 의미를 가지는가?
- [ ] Protocol/QA milestone이면 tag를 찍었는가?
- [ ] `.env` 등 민감정보가 커밋 대상에 포함되지 않았는가?

---

## 10. 원칙 문장

> **브랜치 하나, 루틴 3단계(add/commit/tag), milestone만 태그로 고정한다.**

---

**End of Document**
