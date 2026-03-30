/**
 * Google Apps Script: MeducAI Baseline 설문 Google Form 생성 스크립트
 * 
 * 사용 방법:
 * 1. Google Drive에서 새 스프레드시트 생성
 * 2. 확장 프로그램 > Apps Script 열기
 * 3. 이 스크립트를 붙여넣기
 * 4. createBaselineForm(driveFolderId, targetFolderId) 함수 실행
 *    - driveFolderId: 학습 자료가 있는 구글 드라이브 폴더 ID (선택)
 *      예: createBaselineForm('1a2b3c4d5e6f7g8h9i0j')
 *    - targetFolderId: Form 파일을 저장할 구글 드라이브 폴더 ID (선택)
 *      예: createBaselineForm('학습자료폴더ID', 'Form저장폴더ID')
 *      생략 시 Google Drive 루트에 생성됨
 * 
 * 생성된 Form 위치:
 * - 기본: Google Drive 루트 (내 드라이브)
 * - targetFolderId 제공 시: 해당 폴더 내
 * 
 * 생성된 Form 링크는 로그에 출력됩니다.
 * 
 * ⚠️ 중요: 스크립트 실행 후 Form 편집 > 설정 > 확인 메시지에서
 *          구글 드라이브 링크를 실제 폴더 링크로 업데이트하세요!
 * 
 * 기반 문서: 0_Protocol/05_Pipeline_and_Execution/Baseline_Survey_Items_Integrated_For_Current_Google_Form.md
 */

function createBaselineForm(driveFolderId, targetFolderId) {
    // 구글 드라이브 폴더 ID가 제공되지 않은 경우 기본값 사용
    driveFolderId = driveFolderId || 'YOUR_FOLDER_ID';

    // Form 생성
    const form = FormApp.create('[연구 참여 동의서] 전문의 시험 대비 MeducAI 사용자 평가 연구');

    // Form 파일을 특정 폴더로 이동 (targetFolderId가 제공된 경우)
    if (targetFolderId) {
        try {
            const formFile = DriveApp.getFileById(form.getId());
            const targetFolder = DriveApp.getFolderById(targetFolderId);
            formFile.moveTo(targetFolder);
            Logger.log('✅ Form이 지정된 폴더에 저장되었습니다.');
        } catch (e) {
            Logger.log('⚠️ 폴더 이동 실패: ' + e.toString());
            Logger.log('Form은 기본 위치(Google Drive 루트)에 생성되었습니다.');
        }
    }

    // Form 기본 설정
    // Form description에 동의서 전문 포함 (제목 아래 설명란에 표시됨)
    form.setDescription(createConsentFormDescription());
    form.setCollectEmail(false); // 이메일 자동 수집 비활성화 (수동 입력으로 대체)
    form.setLimitOneResponsePerUser(false); // 1인당 1회 응답 제한 해제 (이메일 수집 없이 제한 불가)
    form.setAllowResponseEdits(false); // 응답 수정 허용 비활성화 (중간 저장 불필요)
    form.setShowLinkToRespondAgain(false);

    // ============================================
    // Part 1: 기본정보 (Section 0)
    // ============================================
    // 동의서 본문은 Form description에 포함되어 있으므로 별도 섹션 불필요

    // Section 0: 기본정보 및 이메일 주소
    form.addPageBreakItem()
        .setTitle('Section 0: 기본정보 및 이메일 주소')
        .setHelpText('연구 참여를 위한 기본 정보를 입력해주세요.');

    // S0-0. 이메일 주소 (수동 입력)
    const emailItem = form.addTextItem();
    emailItem.setTitle('S0-0. 이메일 주소')
        .setRequired(true)
        .setHelpText('연구 참여 동의서 사본 및 학습 자료(MeducAI) 관련 안내를 발송해 드리기 위한 필수 항목입니다.\n자료 수령에 차질이 없도록 자주 사용하시는 이메일을 정확히 입력해 주세요.\n(연구 데이터 분석 시 즉시 분리 보관됩니다)')
        .setValidation(FormApp.createTextValidation()
            .requireTextMatchesPattern('^[\\w\\.-]+@[\\w\\.-]+\\.[a-zA-Z]{2,}$')
            .setHelpText('올바른 이메일 주소 형식으로 입력해주세요. (예: example@email.com)')
            .build());

    // S0-1. 이름
    const nameItem = form.addTextItem();
    nameItem.setTitle('S0-1. 이름')
        .setRequired(true)
        .setHelpText('자료 발송 및 연구 참여자 식별을 위해 수집됩니다. 연구 데이터 분석 시 즉시 분리 보관됩니다.');

    // S0-2. 병원 유형
    const hospitalItem = form.addMultipleChoiceItem();
    hospitalItem.setTitle('S0-2. 현재 수련 또는 근무 중인 병원의 유형은 무엇입니까?')
        .setRequired(true)
        .setChoiceValues(['대학병원', '2차 병원', '기타'])
        .setHelpText('병원 유형을 선택해주세요.');

    // S0-3. 연령
    const ageItem = form.addTextItem();
    ageItem.setTitle('S0-3. 현재 연령은 어떻게 되십니까?')
        .setRequired(true)
        .setHelpText('만 나이를 숫자로 입력해주세요. (예: 30)')
        .setValidation(FormApp.createTextValidation()
            .requireNumber()
            .setHelpText('숫자만 입력 가능합니다.')
            .build());

    // S0-4. 성별
    const genderItem = form.addMultipleChoiceItem();
    genderItem.setTitle('S0-4. 성별을 선택해 주십시오.')
        .setRequired(true)
        .setChoiceValues(['남성', '여성', '기타', '응답하지 않음']);

    // S0-5. 연차
    const yearItem = form.addMultipleChoiceItem();
    yearItem.setTitle('S0-5. 현재 수련 연차 또는 전문의 시험 응시 자격은 무엇입니까?')
        .setRequired(true)
        .setChoiceValues(['영상의학과 전공의 4년차', '기타 (전문의 시험 응시 자격 보유자)']);

    // S0-6. 휴대전화 번호
    const phoneItem = form.addTextItem();
    phoneItem.setTitle('S0-6. 휴대전화 번호')
        .setRequired(true)
        .setHelpText('답례품 발송을 위해 수집됩니다. 연구 데이터 분석 시 즉시 분리 보관됩니다.\n형식: 010-XXXX-XXXX');

    // S0-7. 선택정보 수집 동의
    const consentItem = form.addMultipleChoiceItem();
    consentItem.setTitle('S0-7. 선택정보 수집 동의')
        .setRequired(true)
        .setChoiceValues(['동의합니다', '동의하지 않습니다'])
        .setHelpText('본 연구에 필요한 최소한의 개인정보(이름, 연락처) 수집에 동의하시겠습니까?\n동의하지 않으실 경우 연구 참여가 제한될 수 있습니다.');

    // ============================================
    // Part 2: BASELINE Survey
    // ============================================

    // Baseline 설문 Intro
    form.addPageBreakItem()
        .setTitle('BASELINE 설문')
        .setHelpText('본 설문은 MeducAI 학습 자료 사용 전, 현재 학습 상태와 배경을 파악하기 위한 설문입니다.\n응답은 익명으로 처리되며, 연구 목적 외 사용되지 않습니다.\n예상 소요 시간은 약 8–10분입니다.\n\n※ 참고: 본 설문은 동의서 작성 직후 이어서 진행됩니다.');

    // Section 1: 학습/수련 컨텍스트
    form.addPageBreakItem()
        .setTitle('Section 1: 학습/수련 컨텍스트')
        .setHelpText('교란요인 보정을 위한 정보입니다.');

    // F2. 로테이션
    const rotationItem = form.addMultipleChoiceItem();
    rotationItem.setTitle('F2. 현재 로테이션은 무엇입니까?')
        .setRequired(true)
        .setChoiceValues(['흉부영상', '복부영상', '신경영상', '근골격영상', '유방영상', '응급영상', '중재영상', '기타']);

    // F3. 공부 시간
    const studyTimeItem = form.addMultipleChoiceItem();
    studyTimeItem.setTitle('F3. 최근 2주간 주당 평균 공부 시간은 어느 정도였습니까?')
        .setRequired(true)
        .setChoiceValues(['5시간 미만', '5–10시간', '10–15시간', '15–20시간', '20시간 이상']);

    // Section 3: 기존 학습 도구 사용
    form.addPageBreakItem()
        .setTitle('Section 3: 기존 학습 도구 사용');

    // F5. 학습 도구 (복수 선택)
    const learningToolsItem = form.addCheckboxItem();
    learningToolsItem.setTitle('F5. 전문의 시험 준비를 위해 사용 중인 학습 도구를 모두 선택해 주십시오.')
        .setRequired(true)
        .setChoiceValues(['교과서', '개인 정리 노트 / 요약 자료', '문제집', 'Anki 등 플래시카드 (MeducAI 외)', '스터디 그룹', '온라인 강의 / 동영상 강의', '기타']);

    // F6. Anki 숙련도 (선택)
    const ankiUsageItem = form.addMultipleChoiceItem();
    ankiUsageItem.setTitle('F6. (선택) Anki를 사용 중이라면, 하루 평균 리뷰 카드 수는 대략 어느 정도입니까?')
        .setRequired(false)
        .setChoiceValues(['Anki 미사용', '50장 미만', '50–100장', '100–200장', '200장 이상']);

    // Section 3: LLM/AI 경험
    form.addPageBreakItem()
        .setTitle('Section 3: LLM/AI 경험 (Baseline Covariates)');

    // F7. LLM 사용 경험
    const llmExperienceItem = form.addMultipleChoiceItem();
    llmExperienceItem.setTitle('F7. 생성형 AI(LLM, ChatGPT, Claude 등)를 사용해 본 경험이 있습니까?')
        .setRequired(true)
        .setChoiceValues(['예', '아니오']);

    // F8. 임상 목적 LLM 사용 (조건부, 선택)
    const clinicalLLMItem = form.addMultipleChoiceItem();
    clinicalLLMItem.setTitle('F8. (F7=예인 경우만) 임상 목적(진단 보조, 영상 판독 보조 등)으로 LLM을 사용한 경험이 있습니까?')
        .setRequired(false)
        .setChoiceValues(['예', '아니오', '해당 없음 (F7=아니오인 경우)'])
        .setHelpText('F7에서 "예"를 선택한 경우에만 응답해주세요.');

    // F9. LLM 이해 수준
    const llmKnowledgeItem = form.addScaleItem();
    llmKnowledgeItem.setTitle('F9. 생성형 AI 기술에 대한 이해 수준은 어느 정도입니까?')
        .setRequired(true)
        .setBounds(1, 5)
        .setLabels('전혀 모른다', '잘 알고 있다')
        .setHelpText('1 = 전혀 모른다, 5 = 잘 알고 있다');

    // F10. LLM 신뢰도
    const llmTrustItem = form.addScaleItem();
    llmTrustItem.setTitle('F10. LLM이 생성한 임상 설명이나 의학 정보에 대한 전반적 신뢰도는 어느 정도입니까?')
        .setRequired(true)
        .setBounds(1, 5)
        .setLabels('전혀 신뢰하지 않는다', '매우 신뢰한다')
        .setHelpText('1 = 전혀 신뢰하지 않는다, 5 = 매우 신뢰한다');

    // Section 4: 인지 부하
    form.addPageBreakItem()
        .setTitle('Section 4: 인지 부하 (현재 시점 기준)')
        .setHelpText('응답 척도: 1 = 매우 낮았다, 7 = 매우 높았다');

    // 인지 부하 문항들 (F11-1 ~ F13-3, 총 9개)
    const cognitiveLoadQuestions = [
        { id: 'F11-1', text: '학습 자료의 구성이나 표현 방식 때문에 불필요하게 머리가 복잡하다고 느낀다.' },
        { id: 'F11-2', text: '필요한 정보를 찾기 위해 자료를 이리저리 찾아보는 데 많은 노력이 든다.' },
        { id: 'F11-3', text: '학습 도구의 사용 방식이 직관적이지 않아 학습 흐름이 끊긴다고 느낀다.' },
        { id: 'F12-1', text: '학습해야 할 내용 자체가 전반적으로 복잡하고 어렵다고 느낀다.' },
        { id: 'F12-2', text: '개별 개념보다 개념들 사이의 관계를 이해하는 것이 어렵다.' },
        { id: 'F12-3', text: '새로운 주제나 개념을 이해하는 데 상당한 정신적 노력이 필요하다.' },
        { id: 'F13-1', text: '학습 내용을 구조화하고 정리하려고 적극적으로 사고한다.' },
        { id: 'F13-2', text: '학습하면서 내가 제대로 이해하고 있는지 스스로 점검한다.' },
        { id: 'F13-3', text: '학습한 내용을 실제 문제나 임상적 맥락에 적용하려 노력한다.' }
    ];

    cognitiveLoadQuestions.forEach(function (q) {
        const item = form.addScaleItem();
        item.setTitle(`${q.id}. ${q.text}`)
            .setRequired(true)
            .setBounds(1, 7)
            .setLabels('매우 낮았다', '매우 높았다')
            .setHelpText('1 = 매우 낮았다, 7 = 매우 높았다');
    });

    // Section 5: 학업적 자기효능감
    form.addPageBreakItem()
        .setTitle('Section 5: 학업적 자기효능감')
        .setHelpText('응답 척도: 1 = 전혀 그렇지 않았다, 7 = 매우 그렇다');

    const selfEfficacyQuestions = [
        { id: 'F14-1', text: '나는 이번 전문의 시험 준비에 필요한 학습 내용을 충분히 습득할 수 있다고 느낀다.' },
        { id: 'F14-2', text: '어려운 문제를 만나더라도 결국 해결할 수 있을 것이라고 느낀다.' },
        { id: 'F14-3', text: '학습 계획을 전반적으로 잘 수행할 수 있다고 느낀다.' },
        { id: 'F14-4', text: '시험에 필요한 핵심 개념을 이해하는 데 자신이 있다.' },
        { id: 'F14-5', text: '시험 준비 과정 전반에서 원하는 학습 성과를 낼 수 있을 것이라 기대한다.' }
    ];

    selfEfficacyQuestions.forEach(function (q) {
        const item = form.addScaleItem();
        item.setTitle(`${q.id}. ${q.text}`)
            .setRequired(true)
            .setBounds(1, 7)
            .setLabels('전혀 그렇지 않았다', '매우 그렇다')
            .setHelpText('1 = 전혀 그렇지 않았다, 7 = 매우 그렇다');
    });

    // Section 6: 생활·정서 요인
    form.addPageBreakItem()
        .setTitle('Section 6: 생활·정서 요인');

    // F15-1. 스트레스
    const stressItem = form.addScaleItem();
    stressItem.setTitle('F15-1. 최근 학습 관련 스트레스 수준은 어떠했습니까?')
        .setRequired(true)
        .setBounds(1, 7)
        .setLabels('매우 낮았다', '매우 높았다')
        .setHelpText('1 = 매우 낮았다, 7 = 매우 높았다');

    // F15-2. 수면 시간
    const sleepTimeItem = form.addMultipleChoiceItem();
    sleepTimeItem.setTitle('F15-2. 최근 2주간 하루 평균 수면 시간은 어느 정도였습니까?')
        .setRequired(true)
        .setChoiceValues(['4시간 미만', '4–5시간', '5–6시간', '6–7시간', '7시간 이상']);

    // F15-3. 수면의 질
    const sleepQualityItem = form.addScaleItem();
    sleepQualityItem.setTitle('F15-3. 최근 전반적인 수면의 질은 어떠했습니까?')
        .setRequired(true)
        .setBounds(1, 7)
        .setLabels('매우 나쁘다', '매우 좋다')
        .setHelpText('1 = 매우 나쁘다, 7 = 매우 좋다');

    // F15-4. 기분 상태
    const moodItem = form.addScaleItem();
    moodItem.setTitle('F15-4. 최근 전반적인 기분 상태는 어떠했습니까?')
        .setRequired(true)
        .setBounds(1, 7)
        .setLabels('매우 나쁘다', '매우 좋다')
        .setHelpText('1 = 매우 나쁘다, 7 = 매우 좋다');

    // F15-5. 운동 빈도
    const exerciseItem = form.addMultipleChoiceItem();
    exerciseItem.setTitle('F15-5. 최근 규칙적인 운동(30분 이상) 빈도는 어느 정도였습니까?')
        .setRequired(true)
        .setChoiceValues(['전혀 하지 않음', '주 1–2회', '주 3–4회', '주 5회 이상']);

    // Section 7: 선택 항목
    form.addPageBreakItem()
        .setTitle('Section 7: 선택 항목 (탐색적 분석용)')
        .setHelpText('선택 응답 항목입니다.');

    // F16. MeducAI 기대치 (선택)
    const expectationItem = form.addScaleItem();
    expectationItem.setTitle('F16. (선택) MeducAI 학습 자료가 전문의 시험 준비에 도움이 될 것이라고 기대하십니까?')
        .setRequired(false)
        .setBounds(1, 5)
        .setLabels('전혀 그렇지 않다', '매우 그렇다')
        .setHelpText('1 = 전혀 그렇지 않다, 5 = 매우 그렇다');

    // ============================================
    // 완료 메시지 (구글 드라이브 링크 포함)
    // ============================================
    const driveLink = 'https://drive.google.com/drive/folders/' + driveFolderId;
    const completionMessage = '연구 참여에 감사드립니다!\n\n' +
        'MeducAI 학습 자료를 다운로드하실 수 있습니다:\n\n' +
        driveLink + '\n\n' +
        '※ 위 링크를 클릭하시면 구글 드라이브 폴더로 이동합니다.\n' +
        '※ 학습 자료 다운로드 안내는 입력하신 이메일로도 발송됩니다.\n' +
        '※ 문의사항이 있으시면 연구 담당자에게 연락 주시기 바랍니다.';

    form.setConfirmationMessage(completionMessage);

    // Form URL 출력
    const formUrl = form.getPublishedUrl();
    const formFile = DriveApp.getFileById(form.getId());
    const formLocation = formFile.getParents().next().getName();

    Logger.log('========================================');
    Logger.log('✅ Google Form이 생성되었습니다!');
    Logger.log('========================================');
    Logger.log('📋 Form 제목: ' + form.getTitle());
    Logger.log('📁 저장 위치: ' + formLocation);
    Logger.log('🔗 Form URL (공유용): ' + formUrl);
    Logger.log('✏️ Form 편집 URL: ' + form.getEditUrl());
    Logger.log('');

    if (driveFolderId === 'YOUR_FOLDER_ID') {
        Logger.log('⚠️ 중요: 구글 드라이브 폴더 ID를 제공하지 않았습니다.');
        Logger.log('다음과 같이 실행하세요: createBaselineForm("실제_폴더_ID")');
        Logger.log('또는 Form 편집 > 설정 > 확인 메시지에서 링크를 수정하세요.');
    } else {
        Logger.log('✅ 구글 드라이브 링크가 설정되었습니다: ' + driveLink);
    }

    Logger.log('');
    Logger.log('💡 Form 파일 위치 확인 방법:');
    Logger.log('   Google Drive에서 "' + form.getTitle() + '" 검색');
    Logger.log('   또는 Form 편집 URL에서 확인');

    return formUrl;
}

/**
 * 동의서 설명문 생성 (Form description용 - 제목 아래 설명란에 표시)
 */
function createConsentFormDescription() {
    return '연구 과제명: 전문의 자격시험 대비를 위한 LLM 기반 학습 프레임워크(MeducAI)의 사용자 경험 및 전문가 자문단 기반 콘텐츠 품질 평가에 관한 전향적 관찰연구\n\n책임연구자: [PI]\n\n(Ver. 1.1 _ 2025.12.10)\n\n' +
        '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n' +
        createConsentFormBody();
}

/**
 * 동의서 본문 생성
 */
function createConsentFormBody() {
    return '안녕하십니까? 본 설명문은 2026년도 영상의학과 전문의 자격시험을 준비하시는 전공의 선생님들을 대상으로 진행되는 본 연구의 목적과 절차, 잠재적 위험 및 이익 등에 대해 설명드리기 위해 마련되었습니다.\n\n' +
        '본 연구는 삼성창원병원 영상의학과에서 수행하며, 선생님께서 본 설명문을 읽고 동의하실 경우, 연구진이 개발한 MeducAI 학습 자료(Anki Deck 등)를 다운로드하여 활용하실 수 있습니다. 연구 참여 여부는 전적으로 선생님의 자율적인 의사에 달려 있으며, 참여하지 않더라도 전공의 수련 평가나 전문의 시험 응시에 어떠한 불이익도 발생하지 않습니다.\n\n' +
        '1. 연구의 배경 및 목적\n\n' +
        '영상의학과 전문의 자격시험은 방대한 양의 지식을 짧은 기간 내에 습득해야 하는 고난도 과정입니다. 이에 본 연구진은 생성형 AI(LLM)와 간격 반복(Spaced Repetition) 알고리즘을 결합한 적응형 학습 시스템(MeducAI)을 개발하였습니다. 본 연구는 실제 수험 환경에서 이 시스템을 활용했을 때, 선생님들의 학습 효율성, 인지 부하(Cognitive Load), 학업적 자기효능감에 미치는 영향을 분석하고, 향후 AI 기반 의학 교육 시스템의 발전을 위한 기초 자료를 마련하는 것을 목적으로 합니다.\n\n' +
        '2. 연구 참여 대상 및 절차\n\n' +
        '- 대상: 2026년도 영상의학과 전문의 자격시험 응시 예정인 4년차 전공의 (또는 이에 준하는 수험생).\n' +
        '- 연구 기간: 동의 시점부터 2026년 4월(연구 종료 시)까지.\n' +
        '- 주요 절차:\n' +
        '  (1) 동의 및 자료 제공: 본 동의서에 서명(클릭)하시면 학습 패키지(교육목표 요약표, Info 슬라이드, Anki Deck) 다운로드 권한이 부여됩니다.\n' +
        '  (2) 자율 학습: 제공된 자료의 사용 여부, 빈도, 학습 방법은 전적으로 선생님의 자율에 맡깁니다. (자료를 다운로드만 하고 사용하지 않으셔도 연구 참여가 가능합니다).\n' +
        '  (3) 설문 조사 (1회): 전문의 시험 종료 후(2월 중순 예정), 온라인 설문조사를 통해 학습 만족도, 인지 부하 등을 묻습니다 (소요 시간 약 10분).\n' +
        '  (4) 학습 로그 수집 (선택): 별도의 동의가 있는 경우에 한해, Anki 활용 시 생성되는 학습 로그 파일(*.apkg 등)을 연구 참여자가 자발적으로 제출할 수 있습니다.\n\n' +
        '3. 연구 참여에 따른 이익과 잠재적 위험\n\n' +
        '- 예상 이익: 연구 참여자에게는 영상의학회 수련 목표를 기반으로 구조화된 고품질 학습 자료(MeducAI Full Package)가 무상으로 제공되어 시험 준비에 도움을 드릴 수 있습니다.\n' +
        '- 잠재적 위험 및 안전 대책: 생성형 AI의 특성상 \'환각(Hallucination)\'으로 인한 부정확한 정보가 포함될 수 있습니다. 이를 방지하기 위해 본 자료는 배포 전 전문의 및 고년차 전공의로 구성된 전문가 패널의 교차 검증을 통해 중대한 의학적 오류가 없도록 검증되었습니다.\n' +
        '- 주의 사항: 그럼에도 불구하고 미세한 오류가 존재할 수 있으므로, 본 자료는 보조적인 학습 도구로만 활용하셔야 하며, 최종적인 의학적 판단은 교과서 및 표준 가이드라인을 따르셔야 합니다.\n\n' +
        '4. 개인정보 보호 및 비밀 보장\n\n' +
        '수집된 모든 정보는 「개인정보 보호법」 및 「생명윤리 및 안전에 관한 법률」에 따라 철저히 보호됩니다.\n\n' +
        '- 비식별화: 성명, 소속 등 개인 식별 정보는 수집 즉시 난수화된 연구용 ID로 대체되어 분석됩니다.\n' +
        '- 연락처 분리 보관: 자료 발송을 위한 이메일 주소 및 답례품 발송을 위해 수집된 휴대전화 번호는 연구 데이터와 물리적으로 분리되어 보관되며, 발송 완료 후 즉시 파기됩니다.\n' +
        '- 자료 보관: 연구 종료 후 3년간 보관된 뒤 영구 삭제됩니다.\n\n' +
        '5. 손실에 대한 보상\n\n' +
        '전문의 시험 종료 후 시행되는 설문조사를 완료해 주신 선생님께는 감사의 뜻으로 소정의 모바일 쿠폰(답례품)을 제공합니다.\n\n' +
        '6. 자발적 참여 및 동의 철회\n\n' +
        '귀하는 본 연구에 참여하지 않을 자유가 있으며, 참여 도중 언제든지 중단할 수 있습니다. 중도 철회 시 수집된 데이터는 즉시 폐기하는 것을 원칙으로 하나, 이미 익명화되어 분석이 종료된 경우에는 폐기되지 않을 수 있습니다. 동의를 철회하더라도 이미 제공받은 학습 자료의 사용 권한은 유지되며, 수련 평가 등에 어떠한 불이익도 없습니다.\n\n' +
        '7. 문의처\n\n' +
        '본 연구에 대해 궁금한 점이 있거나 권리 침해가 우려되는 경우 아래로 연락 주시기 바랍니다.\n\n' +
        '- 연구 책임자: [PI] ([email-redacted], [phone-redacted])\n' +
        '- 연구 담당자: [Study Coordinator] ([email-redacted], [phone-redacted])\n' +
        '- 관할 IRB: [Institution] 임상연구윤리심의위원회 ([phone-redacted])\n\n' +
        '※ 아래의 이메일 입력란은 선생님께 \'연구 참여 동의서 사본\' 및 \'학습 자료(MeducAI) 관련 안내\'를 발송해 드리기 위한 필수 항목입니다. 자료 수령에 차질이 없도록 자주 사용하시는 이메일을 정확히 입력해 주세요.';
}

