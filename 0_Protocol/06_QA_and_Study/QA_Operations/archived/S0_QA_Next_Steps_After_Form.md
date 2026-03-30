# S0 QA 다음 단계 가이드 (Google Form 생성 후)

**Date:** 2025-12-20  
**Status:** 실행 가이드  
**Prerequisites:** 
- ✅ S1/S2 실행 중 또는 완료
- ✅ Google Form 생성 완료

---

## 📋 현재 상태 확인

### 1. S1/S2 실행 상태 확인

```bash
# S1 출력 확인
ls -lh 2_Data/metadata/generated/S0_QA_*/stage1_struct__arm*.jsonl

# S2 출력 확인
ls -lh 2_Data/metadata/generated/S0_QA_*/s2_results__arm*.jsonl

# 각 arm별 레코드 수 확인
for arm in A B C D E F; do
  echo "Arm $arm:"
  wc -l 2_Data/metadata/generated/S0_QA_*/stage1_struct__arm${arm}.jsonl 2>/dev/null || echo "  S1: 아직 생성 안됨"
  wc -l 2_Data/metadata/generated/S0_QA_*/s2_results__arm${arm}.jsonl 2>/dev/null || echo "  S2: 아직 생성 안됨"
done
```

**예상 결과:**
- S1: 각 arm당 18개 레코드 (18 groups)
- S2: 각 arm당 약 216개 레코드 (18 groups × 12 cards)

---

## 🎯 다음 단계 (순서대로)

### Phase 1: S1/S2 완료 대기 및 검증

#### ✅ 체크리스트

- [ ] S1 출력 확인 (각 arm당 18개)
- [ ] S1 Gate 통과 확인
- [ ] Allocation 생성 확인
- [ ] S2 출력 확인 (각 arm당 약 216개)
- [ ] 모든 arm (A-F) 완료 확인

---

### Phase 2: S3 실행 (이미지 스펙 생성)

#### 목적
- 이미지 정책 해석 및 이미지 스펙 컴파일
- 이미지 생성은 하지 않음 (스펙만 생성)

#### 실행 명령어

```bash
cd /path/to/workspace/workspace/MeducAI

# Run tag 확인 (S1/S2 실행 시 사용한 것과 동일해야 함)
RUN_TAG="S0_QA_20251220"  # 실제 run_tag로 변경

# S3 실행 (모든 arm)
for arm in A B C D E F; do
  echo "Running S3 for Arm $arm..."
  python3 3_Code/src/03_s3_policy_resolver.py \
    --base_dir . \
    --run_tag $RUN_TAG \
    --arm $arm
done
```

#### 검증

```bash
# S3 출력 확인
ls -lh 2_Data/metadata/generated/$RUN_TAG/image_policy_manifest__arm*.jsonl
ls -lh 2_Data/metadata/generated/$RUN_TAG/s3_image_spec__arm*.jsonl

# 레코드 수 확인
for arm in A B C D E F; do
  echo "Arm $arm:"
  wc -l 2_Data/metadata/generated/$RUN_TAG/image_policy_manifest__arm${arm}.jsonl
  wc -l 2_Data/metadata/generated/$RUN_TAG/s3_image_spec__arm${arm}.jsonl
done
```

---

### Phase 3: S4 실행 (이미지 생성)

#### 목적
- S3 스펙 기반으로 이미지 생성
- 모든 카드 및 테이블 이미지 생성

#### 실행 명령어

```bash
# S4 실행 (모든 arm)
for arm in A B C D E F; do
  echo "Running S4 for Arm $arm..."
  python3 3_Code/src/04_s4_image_generator.py \
    --base_dir . \
    --run_tag $RUN_TAG \
    --arm $arm
done
```

#### 검증

```bash
# 이미지 파일 확인
ls -lh 2_Data/metadata/generated/$RUN_TAG/images/ | head -20

# 이미지 개수 확인
find 2_Data/metadata/generated/$RUN_TAG/images/ -name "IMG__*.png" | wc -l

# S4 manifest 확인
ls -lh 2_Data/metadata/generated/$RUN_TAG/s4_image_manifest__arm*.jsonl
```

**예상 결과:**
- 각 arm당 약 216개 이미지 (18 groups × 12 cards)
- 총 약 1,296개 이미지 (6 arms × 216)

---

### Phase 4: PDF 생성 및 배포 준비

#### 4.1 PDF 생성

```bash
# 전체 실행 (PDF 생성 + 폴더 구성 + zip)
python3 3_Code/src/tools/qa/distribute_qa_packets.py \
    --base_dir . \
    --run_tag $RUN_TAG \
    --skip_email  # 이메일은 나중에 발송
```

#### 4.2 단계별 실행 (테스트용)

```bash
# 1. PDF만 생성 (테스트)
python3 3_Code/src/tools/qa/distribute_qa_packets.py \
    --base_dir . \
    --run_tag $RUN_TAG \
    --skip_organize --skip_zip --skip_email \
    --dry_run

# 2. PDF 생성 (실제)
python3 3_Code/src/tools/qa/distribute_qa_packets.py \
    --base_dir . \
    --run_tag $RUN_TAG \
    --skip_organize --skip_zip --skip_email

# 3. PDF 생성 + 폴더 구성
python3 3_Code/src/tools/qa/distribute_qa_packets.py \
    --base_dir . \
    --run_tag $RUN_TAG \
    --skip_zip --skip_email

# 4. 압축까지
python3 3_Code/src/tools/qa/distribute_qa_packets.py \
    --base_dir . \
    --run_tag $RUN_TAG \
    --skip_email
```

#### 4.3 출력 구조 확인

```bash
# PDF 개수 확인
ls -1 6_Distributions/QA_Packets/SET_*.pdf | wc -l
# 예상: 108개

# Reviewer별 폴더 확인
ls -d 6_Distributions/QA_Packets/by_reviewer/rev_* | wc -l
# 예상: 18개

# 각 reviewer의 PDF 개수 확인
for rev in rev_001 rev_002 rev_003; do
  echo "$rev: $(ls -1 6_Distributions/QA_Packets/by_reviewer/$rev/*.pdf 2>/dev/null | wc -l) PDFs"
done
# 예상: 각 12개

# Zip 파일 확인
ls -lh 6_Distributions/QA_Packets/zip/*.zip
# 예상: 18개 zip 파일
```

---

### Phase 5: Google Drive 설정

#### 5.1 Google Drive 폴더 구조 생성

**권장 구조:**
```
Google Drive/
└── S0_QA_Reviewers/
    ├── Reviewer_A_Email@example.com/
    │   ├── Q01.pdf
    │   ├── Q02.pdf
    │   ├── ...
    │   └── Q12.pdf
    ├── Reviewer_B_Email@example.com/
    │   └── ...
    └── ...
```

#### 5.2 수동 설정 방법

1. **Google Drive 접속**
2. **새 폴더 생성**: "S0_QA_Reviewers"
3. **평가자별 개인 폴더 생성**
   - 각 평가자 이메일 주소로 폴더명 생성
   - 예: `reviewer_a@example.com`
4. **PDF 파일 업로드**
   - `6_Distributions/QA_Packets/by_reviewer/rev_XXX/` 폴더의 PDF를
   - 해당 평가자의 Google Drive 폴더에 업로드
   - 파일명: `Q01.pdf`, `Q02.pdf`, ..., `Q12.pdf`
5. **폴더 공유 설정**
   - 각 평가자 폴더를 해당 평가자 이메일로 공유
   - 권한: "뷰어" 또는 "편집자" (필요시)

#### 5.3 자동화 스크립트 (선택)

Google Drive API를 사용하여 자동화할 수 있습니다. (별도 구현 필요)

---

### Phase 6: 이메일 발송

#### 6.1 이메일 템플릿 준비

**템플릿 예시:**

```
제목: MeducAI S0 QA 평가 요청

안녕하세요 [평가자 이름]님,

MeducAI S0 QA 평가에 참여해 주셔서 감사합니다.

평가 자료:
- Google Drive 폴더: [개인 폴더 링크]
- Google Form: [Form 링크]

평가 가이드:
1. Google Drive 폴더에서 Q01~Q12 PDF 파일을 확인하세요.
2. Google Form에서 각 Q 섹션을 순차적으로 평가하세요.
3. 중간 저장 후 이어서 응답 가능합니다.

평가 기간: [시작일] ~ [종료일]

문의사항이 있으시면 연락 주세요.

감사합니다.
MeducAI 팀
```

#### 6.2 이메일 발송 (자동화)

```bash
# distribute_qa_packets.py로 이메일 발송
python3 3_Code/src/tools/qa/distribute_qa_packets.py \
    --base_dir . \
    --run_tag $RUN_TAG \
    --skip_pdf --skip_organize --skip_zip \
    --smtp_server smtp.gmail.com \
    --smtp_port 587 \
    --smtp_user your_email@gmail.com \
    --smtp_password your_app_password \
    --from_email your_email@gmail.com
```

**Gmail 앱 비밀번호 설정:**
1. Google 계정에서 "2단계 인증" 활성화
2. "앱 비밀번호" 생성
3. 생성된 앱 비밀번호를 `--smtp_password`에 사용

#### 6.3 수동 이메일 발송

`reviewer_master.csv`를 확인하여 각 평가자에게 개별 이메일 발송:

```bash
# 평가자 목록 확인
cat 1_Secure_Participant_Info/reviewer_master.csv
```

---

### Phase 7: Google Form 설정 확인

#### 7.1 Form 설정 검증

- [ ] 이메일 수집 활성화 확인
- [ ] 1인당 1회 응답 제한 확인
- [ ] 응답 수정 허용 확인
- [ ] Section 1~13 모두 생성 확인
- [ ] 필수 문항 설정 확인

#### 7.2 Form 테스트

1. **테스트 응답 제출**
   - 본인 이메일로 테스트 응답 제출
   - 모든 섹션 입력 테스트
   - 중간 저장 테스트

2. **응답 확인**
   - Form 편집 화면 > 응답 탭에서 확인
   - CSV 다운로드 테스트

---

### Phase 8: 데이터 수집 준비

#### 8.1 assignment_map.csv 확인

```bash
# assignment_map 확인
head -20 0_Protocol/06_QA_and_Study/QA_Operations/assignment_map.csv

# reviewer_email 컬럼 확인
cut -d',' -f1,2 0_Protocol/06_QA_and_Study/QA_Operations/assignment_map.csv | head -20
```

#### 8.2 데이터 결합 스크립트 준비

Google Form 응답 CSV와 `assignment_map.csv`를 결합하는 스크립트를 준비합니다.

**Join key:**
- `reviewer_email` (Form 응답) + `reviewer_email` (assignment_map)
- `section` (Q01~Q12) + `local_qid` (assignment_map)

---

## 📊 진행 상황 추적

### 체크리스트

- [ ] Phase 1: S1/S2 완료 및 검증
- [ ] Phase 2: S3 실행 완료
- [ ] Phase 3: S4 실행 완료
- [ ] Phase 4: PDF 생성 및 배포 준비 완료
  - [ ] 108개 PDF 생성 확인
  - [ ] Reviewer별 폴더 구성 확인
  - [ ] 18개 zip 파일 생성 확인
- [ ] Phase 5: Google Drive 설정 완료
  - [ ] 평가자별 폴더 생성
  - [ ] PDF 업로드 완료
  - [ ] 폴더 공유 설정 완료
- [ ] Phase 6: 이메일 발송 완료
- [ ] Phase 7: Google Form 설정 확인 완료
- [ ] Phase 8: 데이터 수집 준비 완료

---

## 🚨 주의사항

### 1. Run Tag 일관성
모든 단계에서 동일한 `--run_tag`를 사용해야 합니다.

### 2. 이미지 없이 PDF 생성
S4 실행 전에 **미리보기/디버그용** PDF를 생성하려면 `--allow_missing_images` 옵션이 필요합니다. `distribute_qa_packets.py`는 운영상(초기/부분 산출물) 이 옵션을 기본 사용합니다.

**정책:** 최종 QA 배포용 PDF는 **S4 완료 후** `--allow_missing_images` 없이 생성해야 합니다. 콘텐츠 품질 판정/게이트는 PDF 생성기가 아니라 **Option C(S5 triage → S6 export gate)** 에서 수행합니다.

### 3. 블라인딩 확인
- PDF에는 블라인딩된 Set ID만 표시
- Google Form에는 arm 정보가 노출되지 않음
- `assignment_map.csv`와 `surrogate_map.csv`로만 실제 매핑 가능

### 4. 데이터 보안
- `assignment_map.csv`와 `reviewer_master.csv`는 보안 폴더에 보관
- Google Drive 공유 설정 시 권한 확인

---

## 📚 참고 문서

- `S0_QA_Execution_Workflow.md` - 전체 워크플로우
- `Google_Form_Design_Specification.md` - Google Form 설계
- `Google_Form_Creation_Guide.md` - Google Form 생성 가이드
- `PDF_Packet_Builder_README.md` - PDF 생성 가이드
- `QA_Framework.md` - QA 프레임워크

---

**Last Updated:** 2025-12-20

