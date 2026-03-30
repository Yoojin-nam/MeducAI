# S5R2 실행 전 체크리스트

**Status**: Pre-execution Checklist  
**Last Updated**: 2025-12-30  
**Purpose**: S5R2 실행 전 필수 확인 사항

---

## ✅ 준비 완료 항목

- [x] `temp_selected_groups.txt` 파일 존재 (11개 그룹)
- [x] Run tag 형식 확인: `DEV_armG_mm_S5R2_after_postFix_YYYYMMDD_HHMMSS__rep1` 및 `__rep2`

---

## ⚠️ 실행 전 확인 필요 항목

### 1. S5R2 프롬프트 파일 준비 상태

**확인 필요**:
- [ ] `S1_SYSTEM__S5R2__v14.md` 파일 존재 여부
- [ ] `S2_SYSTEM__S5R2__v11.md` 파일 존재 여부 (확인됨: ✓ 존재)
- [ ] 레지스트리 업데이트 여부

**현재 상태** (확인됨):
- `S2_SYSTEM__S5R2__v11.md`: ✓ 존재
- `S1_SYSTEM__S5R2__v14.md`: ❌ **없음** (S5R1만 존재: `S1_SYSTEM__S5R1__v13.md`)
- 레지스트리: `S1_SYSTEM`은 `S1_SYSTEM__S5R1__v13.md`를 가리킴
- 레지스트리: `S2_SYSTEM`은 `S2_SYSTEM__S5R1__v10.md`를 가리킴

**⚠️ 중요**: 
- 현재 레지스트리는 S5R1 프롬프트를 가리키고 있음
- S5R2로 실행하려면 레지스트리 업데이트 필요하거나, S1_SYSTEM__S5R2__v14.md 파일 생성 필요
- **현재 상태로 실행하면 S5R1 프롬프트로 실행됨** (의도 확인 필요)

### 2. 실행 순서 확인

**전체 실행 순서** (rep1 완료 후 rep2 실행):

1. **S1/S2 생성** (rep1)
   ```bash
   RUN_TAG_REP1="DEV_armG_mm_S5R2_after_postFix_20251230_185052__rep1"
   python3 3_Code/src/01_generate_json.py \
     --base_dir . \
     --run_tag "$RUN_TAG_REP1" \
     --arm G \
     --mode FINAL \
     --stage both \
     --only_group_keys_file temp_selected_groups.txt
   ```

2. **S3 실행** (rep1)
   ```bash
   python3 3_Code/src/03_s3_policy_resolver.py \
     --base_dir . \
     --run_tag "$RUN_TAG_REP1" \
     --arm G
   ```

3. **S4 실행** (rep1)
   ```bash
   python3 3_Code/src/04_s4_image_generator.py \
     --base_dir . \
     --run_tag "$RUN_TAG_REP1" \
     --arm G
   ```

4. **S5 검증** (rep1)
   ```bash
   python3 3_Code/src/05_s5_validator.py \
     --base_dir . \
     --run_tag "$RUN_TAG_REP1" \
     --arm G
   ```

5. **S5 리포트** (rep1)
   ```bash
   python3 3_Code/src/tools/s5/s5_report.py \
     --base_dir . \
     --run_tag "$RUN_TAG_REP1" \
     --arm G
   ```

6. **rep2도 동일한 순서로 실행** (S1/S2 → S3 → S4 → S5 → 리포트)

---

## 실행 명령어 (완전한 형태)

### rep1 전체 실행

```bash
# Run tag 설정
RUN_TAG_REP1="DEV_armG_mm_S5R2_after_postFix_20251230_185052__rep1"
echo "Run tag: $RUN_TAG_REP1"

# 1. S1/S2 생성
python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag "$RUN_TAG_REP1" \
  --arm G \
  --mode FINAL \
  --stage both \
  --only_group_keys_file temp_selected_groups.txt

# 2. S3 실행
python3 3_Code/src/03_s3_policy_resolver.py \
  --base_dir . \
  --run_tag "$RUN_TAG_REP1" \
  --arm G

# 3. S4 실행
python3 3_Code/src/04_s4_image_generator.py \
  --base_dir . \
  --run_tag "$RUN_TAG_REP1" \
  --arm G

# 4. S5 검증
python3 3_Code/src/05_s5_validator.py \
  --base_dir . \
  --run_tag "$RUN_TAG_REP1" \
  --arm G

# 5. S5 리포트
python3 3_Code/src/tools/s5/s5_report.py \
  --base_dir . \
  --run_tag "$RUN_TAG_REP1" \
  --arm G
```

### rep2 전체 실행 (rep1 완료 후)

```bash
# Run tag 설정
RUN_TAG_REP2="DEV_armG_mm_S5R2_after_postFix_20251230_185052__rep2"
echo "Run tag: $RUN_TAG_REP2"

# (rep1과 동일한 순서로 실행)
```

---

## 주의사항

1. **프롬프트 레지스트리 확인**: S5R2 프롬프트가 레지스트리에 등록되어 있는지 확인
2. **같은 그룹 사용**: `temp_selected_groups.txt` 파일이 Phase 1과 동일한지 확인
3. **FINAL mode 필수**: 모든 Entity에 대해 카드를 생성해야 함
4. **실행 순서 준수**: S1/S2 → S3 → S4 → S5 → 리포트 순서로 실행

---

## 참고 문서

- `S5R_Execution_Commands_Template.md`: 전체 실행 명령어 템플릿
- `S5R_Run_Tags_Reference.md`: Run tag 참조 가이드

