/**
 * Google Apps Script: S0 QA Google Form 생성 스크립트
 * 
 * 사용 방법:
 * 1. Google Drive에서 새 스프레드시트 생성
 * 2. 확장 프로그램 > Apps Script 열기
 * 3. 이 스크립트를 붙여넣기
 * 4. createQAForm() 함수 실행
 * 
 * 생성된 Form 링크는 로그에 출력됩니다.
 */

function createQAForm() {
  // Form 생성
  const form = FormApp.create('MeducAI S0 QA 평가 설문');
  
  // Form 기본 설정
  form.setDescription('MeducAI S0 QA 평가를 위한 설문입니다. 각 Set(Q01~Q12)에 대해 평가해주세요.');
  form.setCollectEmail(true); // 이메일 수집
  form.setLimitOneResponsePerUser(true); // 1인당 1회 응답 제한
  form.setAllowResponseEdits(true); // 응답 수정 허용 (중간 저장)
  form.setShowLinkToRespondAgain(false);
  
  // ============================================
  // Section 1: 평가자 정보
  // ============================================
  form.addPageBreakItem()
    .setTitle('Section 1: 평가자 정보')
    .setHelpText('평가자 정보를 입력해주세요.');
  
  // 평가자 구분
  const roleItem = form.addMultipleChoiceItem();
  roleItem.setTitle('평가자 구분')
    .setRequired(true)
    .setChoiceValues(['전문의 (Attending)', '전공의 (Resident)'])
    .setHelpText('평가자 역할을 선택해주세요.');
  
  // ============================================
  // Section 2~13: Q01~Q12 평가 섹션
  // ============================================
  const qNumbers = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12'];
  
  qNumbers.forEach((qNum, index) => {
    const sectionNumber = index + 2; // Section 2부터 시작
    
    // 페이지 구분
    form.addPageBreakItem()
      .setTitle(`Section ${sectionNumber}: Q${qNum} 평가`)
      .setHelpText(`Q${qNum} Set에 대한 평가입니다. PDF 파일을 확인한 후 평가해주세요.`);
    
    // ============================================
    // Part B: 카드 평가 (Primary Endpoint)
    // ============================================
    
    // B1. Blocking Error
    const blockingErrorItem = form.addMultipleChoiceItem();
    blockingErrorItem.setTitle(`[Q${qNum}] B1. Blocking Error`)
      .setRequired(true)
      .setChoiceValues(['No (blocking error 없음)', 'Yes (blocking error 있음)'])
      .setHelpText('Blocking Error란: 임상 판단 또는 시험 정답을 직접적으로 잘못 유도할 가능성이 큰 오류입니다.');
    
    // B1-1. Blocking Error 설명 (조건부)
    const blockingErrorCommentItem = form.addParagraphTextItem();
    blockingErrorCommentItem.setTitle(`[Q${qNum}] B1-1. Blocking Error 설명 (Yes 선택 시 필수)`)
      .setRequired(false)
      .setHelpText('Blocking Error가 있는 경우, 구체적인 설명을 1줄 이내로 입력해주세요.');
    
    // B2. Overall Card Quality (Primary Endpoint)
    const qualityItem = form.addScaleItem();
    qualityItem.setTitle(`[Q${qNum}] B2. Overall Card Quality (필수, Primary Endpoint)`)
      .setRequired(true)
      .setBounds(1, 5)
      .setLabels('매우 나쁨', '매우 좋음')
      .setHelpText('이 Set의 카드 전반적 품질을 평가하세요. 정확성, 가독성, 교육 목표 부합성을 종합적으로 고려합니다. (1=매우 나쁨, 5=매우 좋음)');
    
    // B3. Evidence Comment (조건부)
    const evidenceCommentItem = form.addParagraphTextItem();
    evidenceCommentItem.setTitle(`[Q${qNum}] B3. Evidence Comment (조건부)`)
      .setRequired(false)
      .setHelpText('B1=Yes 또는 B2≤2인 경우에만 작성해주세요. 문제가 있는 카드에 대한 구체적 근거를 1-2줄 이내로 입력하세요.');
    
    // ============================================
    // Part C: 테이블 및 인포그래픽 안전성 게이트
    // ============================================
    
    // C1. Critical Error
    const criticalErrorItem = form.addMultipleChoiceItem();
    criticalErrorItem.setTitle(`[Q${qNum}] C1. Critical Error (테이블/인포그래픽)`)
      .setRequired(true)
      .setChoiceValues(['No (치명 오류 없음)', 'Yes (치명 오류 있음)'])
      .setHelpText('테이블 또는 인포그래픽에 치명 오류가 있는지 평가하세요.');
    
    // C1-1. Critical Error 설명 (조건부)
    const criticalErrorCommentItem = form.addParagraphTextItem();
    criticalErrorCommentItem.setTitle(`[Q${qNum}] C1-1. Critical Error 설명 (Yes 선택 시 필수)`)
      .setRequired(false)
      .setHelpText('Critical Error가 있는 경우, 구체적인 설명을 1줄 이내로 입력해주세요.');
    
    // C2. Scope Failure
    const scopeFailureItem = form.addMultipleChoiceItem();
    scopeFailureItem.setTitle(`[Q${qNum}] C2. Scope Failure (테이블/인포그래픽)`)
      .setRequired(true)
      .setChoiceValues(['No (불일치 없음)', 'Yes (불일치 있음)'])
      .setHelpText('테이블 또는 인포그래픽이 Group Path/objectives와 명백히 불일치하는지 평가하세요.');
    
    // C2-1. Scope Failure 설명 (조건부)
    const scopeFailureCommentItem = form.addParagraphTextItem();
    scopeFailureCommentItem.setTitle(`[Q${qNum}] C2-1. Scope Failure 설명 (Yes 선택 시 필수)`)
      .setRequired(false)
      .setHelpText('Scope Failure가 있는 경우, 구체적인 설명을 1줄 이내로 입력해주세요.');
    
    // ============================================
    // Part D: 보조 평가 항목 (Secondary Outcomes)
    // ============================================
    
    // D1. Clarity & Readability (선택)
    const clarityItem = form.addScaleItem();
    clarityItem.setTitle(`[Q${qNum}] D1. Clarity & Readability (선택)`)
      .setRequired(false)
      .setBounds(1, 5)
      .setLabels('혼란·오해 가능성 높음', '매우 명확, 학습 친화적')
      .setHelpText('이 Set의 카드가 학습자 관점에서 얼마나 명확하고 읽기 쉬운가? (1=혼란, 5=매우 명확)');
    
    // D2. Clinical/Exam Relevance (선택)
    const relevanceItem = form.addScaleItem();
    relevanceItem.setTitle(`[Q${qNum}] D2. Clinical/Exam Relevance (선택)`)
      .setRequired(false)
      .setBounds(1, 5)
      .setLabels('시험과 거의 무관', '핵심 고빈도 시험 주제')
      .setHelpText('이 Set의 카드가 영상의학과 전문의 시험 및 수련 목표에 얼마나 부합하는가? (1=무관, 5=핵심 주제)');
    
    // D3. Editing Time (필수, Secondary Outcome)
    const editingTimeItem = form.addTextItem();
    editingTimeItem.setTitle(`[Q${qNum}] D3. Editing Time (필수, 분 단위)`)
      .setRequired(true)
      .setHelpText('이 Set을 "배포 가능한 수준"으로 만드는 데 필요한 편집 시간을 분 단위로 입력하세요. (예: 0, 1, 2.5, 3, 5, 10)');
    
    // ============================================
    // Part E: 평가 시간 (선택, 운영 검증용)
    // ============================================
    
    const actualTimeItem = form.addMultipleChoiceItem();
    actualTimeItem.setTitle(`[Q${qNum}] E. 실제 평가 시간 (선택)`)
      .setRequired(false)
      .setChoiceValues(['5분 미만', '5-7분', '7-10분', '10분 초과'])
      .setHelpText('본 Set 평가에 실제로 소요된 시간을 선택해주세요. (운영 검증용)');
    
    // ============================================
    // 자유 의견 (선택)
    // ============================================
    
    const freeCommentItem = form.addParagraphTextItem();
    freeCommentItem.setTitle(`[Q${qNum}] 자유 의견 (선택)`)
      .setRequired(false)
      .setHelpText('추가 의견이나 제안사항이 있으시면 입력해주세요.');
  });
  
  // ============================================
  // 완료 메시지
  // ============================================
  form.setConfirmationMessage('평가에 참여해주셔서 감사합니다!');
  
  // Form URL 출력
  const formUrl = form.getPublishedUrl();
  Logger.log('Google Form이 생성되었습니다!');
  Logger.log('Form URL: ' + formUrl);
  Logger.log('Form 편집 URL: ' + form.getEditUrl());
  
  return formUrl;
}
