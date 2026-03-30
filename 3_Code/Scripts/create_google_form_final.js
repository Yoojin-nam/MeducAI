/**
 * Google Apps Script: MeducAI FINAL(시험 후) 설문 Google Form 생성 스크립트
 *
 * 기반 문서:
 * - 0_Protocol/05_Pipeline_and_Execution/meduc_ai_final_survey_form.md
 *
 * 사용 방법:
 * 1. Google Drive에서 새 스프레드시트 생성
 * 2. 확장 프로그램 > Apps Script 열기
 * 3. 이 스크립트를 붙여넣기
 * 4. createFinalForm(targetFolderId) 함수 실행
 *    - targetFolderId: Form 파일을 저장할 구글 드라이브 폴더 ID (선택)
 *      예: createFinalForm('Form저장폴더ID')
 *
 * 생성된 Form 링크는 로그에 출력됩니다.
 * 
 * 섹션 흐름:
 * - A1=예: A1 → A-사용자(A2-A5) → B-H(평가, H3에서 Z로 분기) → Z(공통) → 제출
 * - A1=아니오: A1 → N(비사용자, N3에서 Z로 분기) → Z(공통) → 제출
 */

function createFinalForm(targetFolderId) {
  const form = FormApp.create('[FINAL 설문] MeducAI 사용자 경험 및 학습 효과 평가 (시험 후)');

  // Form 파일을 특정 폴더로 이동
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

  // 기본 설정
  form.setDescription(
    '본 설문은 영상의학과 전문의 자격시험 준비 과정에서 MeducAI 학습 자료(Anki 덱, 요약 표, 슬라이드 등)를 사용한 경험에 대해 묻는 설문입니다.\n\n' +
    '※ 본 설문은 BASELINE 설문 응답과의 일관된 분석(연결/비교)을 위해 Google 계정 로그인이 필요하며, 응답자의 이메일 주소가 인증된 형태로 수집됩니다.\n' +
    '※ 자료 수령/안내 및 분석 연결에 문제가 없도록, BASELINE 설문에 사용했던 것과 동일한 Google 계정으로 로그인해 주세요.\n\n' +
    '- 설문 참여는 자발적이며, 응답 도중 언제든지 중단할 수 있습니다.\n' +
    '- 예상 소요 시간은 약 8–10분입니다.'
  );

  form.setCollectEmail(true);
  form.setLimitOneResponsePerUser(true);
  form.setAllowResponseEdits(false);
  form.setShowLinkToRespondAgain(false);

  // 공통 유틸
  const likert5 = function (item, title, helpText) {
    item.setTitle(title).setRequired(true).setBounds(1, 5).setLabels('전혀 그렇지 않았다', '매우 그렇다');
    if (helpText) item.setHelpText(helpText);
  };

  const numberTextItem = function (title, helpText, min, max) {
    const item = form.addTextItem();
    item.setTitle(title).setRequired(true);
    if (helpText) item.setHelpText(helpText);
    const v = FormApp.createTextValidation().requireNumber();
    if (typeof min === 'number' && typeof max === 'number') {
      v.requireNumberBetween(min, max);
    }
    item.setValidation(v.build());
    return item;
  };

  // ============================================
  // SECTION 1: A1 분기점
  // ============================================
  form.addPageBreakItem()
    .setTitle('A1. MeducAI 사용 여부')
    .setHelpText('아래 문항은 MeducAI 사용 여부를 확인합니다. 응답에 따라 다음 섹션이 달라집니다.');

  const a1 = form.addMultipleChoiceItem();
  a1.setTitle('A1. 이번 전문의 시험 준비 과정에서 MeducAI 학습 자료를 실제로 사용하였습니까? (필수)')
    .setRequired(true);

  // ============================================
  // SECTION 2: USER PATH - A2-A5 사용 요약
  // ============================================
  const pageUser = form.addPageBreakItem()
    .setTitle('A. MeducAI 사용 요약 (사용자만)')
    .setHelpText('A1에서 "예"를 선택한 경우에만 응답합니다.');

  form.addMultipleChoiceItem()
    .setTitle('A2. MeducAI 사용 기간 (필수)')
    .setRequired(true)
    .setChoiceValues(['1주 미만', '1–2주', '2–3주', '3–4주', '4주 이상']);

  form.addMultipleChoiceItem()
    .setTitle('A3. MeducAI 사용 빈도 (필수)')
    .setRequired(true)
    .setChoiceValues(['거의 매일', '주 4–6회', '주 2–3회', '주 1회 이하']);

  form.addCheckboxItem()
    .setTitle('A4. 사용한 구성 요소 (필수, 복수 선택)')
    .setRequired(true)
    .setChoiceValues(['Anki 덱(플래시카드)', '요약 표(Table)', '슬라이드(Info slide)', '기타 (자유 기입)'])
    .setHelpText('MeducAI 패키지 중 실제로 사용한 구성 요소를 모두 선택해 주십시오.');

  numberTextItem(
    'A5. 사용량(대략) – 총 사용 시간 (필수, hour)',
    '시험 준비 기간 동안 MeducAI 학습 자료를 사용한 총 시간을 대략 입력해 주세요. 예: 0, 1, 5, 12.5',
    0,
    1000
  );

  // ============================================
  // SECTION 3-8: B-H (사용자 전용 평가)
  // ============================================
  form.addPageBreakItem()
    .setTitle('B. Educational Quality / Exam Utility')
    .setHelpText('아래 문항은 교육적 질/시험 유용성에 대한 평가입니다. (1–5)');

  likert5(form.addScaleItem(), 'B1. MeducAI 학습 자료는 전문의 시험 대비에 직접적으로 도움이 되었다.');
  likert5(form.addScaleItem(), 'B2. 각 토픽에서 시험에 중요한 핵심 개념(core)을 잘 짚어주었다.');
  likert5(form.addScaleItem(), 'B3. 불필요하거나 시험과 직접적 관련이 적은 정보는 많지 않았다.');
  likert5(form.addScaleItem(), 'B4. 설명의 구조와 분량은 학습에 적절하였다.');

  form.addPageBreakItem()
    .setTitle('C. Technical Accuracy (체감)')
    .setHelpText('아래 문항은 기술적 정확성(체감)에 대한 질문입니다. (1–5)');

  likert5(form.addScaleItem(), 'C1. MeducAI 학습 자료에서 명백한 사실 오류를 경험한 적이 있다.');
  likert5(form.addScaleItem(), 'C2. 그럴듯하지만 틀린 설명으로 인해 혼란을 느낀 적이 있다.');

  form.addMultipleChoiceItem()
    .setTitle('C3. 오류 또는 부정확한 정보가 학습에 부정적인 영향을 주었다. (필수)')
    .setRequired(true)
    .setChoiceValues(['예', '아니오']);

  form.addMultipleChoiceItem()
    .setTitle('C4. 명백한 오류 경험 "횟수(대략)" (필수)')
    .setRequired(true)
    .setChoiceValues(['0회', '1–2회', '3–5회', '6회 이상']);

  form.addParagraphTextItem()
    .setTitle('(선택) 오류 경험이 있었다면 간단히 서술해 주십시오.')
    .setRequired(false)
    .setHelpText('1–2문장 이내로 작성해 주세요.');

  form.addPageBreakItem()
    .setTitle('D. Efficiency (학습 효율성)')
    .setHelpText('아래 문항은 "시험 준비 기간 동안"의 대략적 총합(회상치)을 묻습니다. 단위는 분(min)입니다.');

  numberTextItem('D1. MeducAI를 활용하여 학습 자료를 이해·정리하는 데 실제로 소요된 시간 (필수, 분)', '예: 0, 30, 120, 450', 0, 100000);
  numberTextItem('D2. 동일 학습을 기존 방식으로 했다면 필요했을 것으로 예상되는 시간 (필수, 분)', '예: 0, 60, 300, 1000', 0, 100000);
  numberTextItem('D3. 오류 확인/표현 수정(검증 포함)에 소요된 시간 (필수, 분; 0 가능)', '예: 0, 10, 60', 0, 100000);
  likert5(form.addScaleItem(), 'D4. MeducAI 사용으로 학습 시간이 절감되었다고 느꼈습니다.');

  form.addPageBreakItem()
    .setTitle('E. Trust & Calibration')
    .setHelpText('아래 문항은 MeducAI 산출물에 대한 신뢰/사용 태도(automation bias 포함)를 묻습니다. (1–5)');

  likert5(form.addScaleItem(), 'E1. MeducAI가 제공한 학습 자료는 전반적으로 신뢰할 수 있었다.');
  likert5(form.addScaleItem(), 'E2. 별도의 교재나 가이드라인 확인 없이 MeducAI 내용을 그대로 암기한 경우가 있었다.');
  likert5(form.addScaleItem(), 'E3. MeducAI 자료를 사용할 때 오류 가능성을 염두에 두고 비판적으로 검토하였다.');

  form.addPageBreakItem()
    .setTitle('G. Learning Satisfaction / Technology Acceptance (TAM)')
    .setHelpText('아래 문항은 만족도 및 기술 수용(TAM)을 묻습니다. (1–5)');

  likert5(form.addScaleItem(), 'G1. (Satisfaction) MeducAI 학습 자료 전반에 만족한다.');
  likert5(form.addScaleItem(), 'G2. (Satisfaction) MeducAI는 시험 준비에 유용한 학습 경험을 제공했다.');
  likert5(form.addScaleItem(), 'G3. (TAM-Usefulness) MeducAI는 내가 공부해야 할 내용을 더 효율적으로 학습하도록 도와주었다.');
  likert5(form.addScaleItem(), 'G4. (TAM-Ease of use) MeducAI 학습 자료는 사용 방법을 익히기 쉬웠다.');
  likert5(form.addScaleItem(), 'G5. (TAM-Intention) 향후 다른 시험이나 학습 상황에서도 MeducAI와 유사한 학습 도구를 사용하고 싶다.');

  form.addPageBreakItem()
    .setTitle('H. 종합 평가 / 운영 개선')
    .setHelpText('마지막으로 종합 평가 및 개선 포인트를 묻습니다.');

  numberTextItem(
    'H1. 동료에게 MeducAI 사용을 권하고 싶습니까? (필수, 0–10)',
    '0–10 점수로 입력해 주세요. (0=전혀 권하지 않음, 10=강력 추천)',
    0,
    10
  );

  const h2 = form.addScaleItem();
  h2.setTitle('H2. (선택) MeducAI 사용으로 "시험 준비 자신감"이 향상되었다고 느꼈습니까?')
    .setRequired(false)
    .setBounds(1, 7)
    .setLabels('전혀 그렇지 않았다', '매우 그렇다');

  form.addParagraphTextItem()
    .setTitle('H3. (선택) 가장 도움이 되었던 점 / 개선이 필요하다고 느낀 점을 자유롭게 작성해 주십시오.')
    .setRequired(false)
    .setHelpText('1–3문장 이내로 작성해 주세요.');

  // H4: 개선 영역 (MultipleChoice) → 사용자 경로의 마지막 분기점
  const h4 = form.addMultipleChoiceItem();
  h4.setTitle('H4. (필수) 개선이 가장 필요하다고 느낀 영역은 무엇입니까?')
    .setRequired(true);

  // ============================================
  // SECTION 9: NON-USER PATH - N1-N4
  // ============================================
  const pageNonUser = form.addPageBreakItem()
    .setTitle('A-0. 미사용자 섹션')
    .setHelpText('A1에서 "아니오"를 선택한 분만 응답합니다. 비사용 원인을 파악하기 위한 문항입니다.');

  form.addMultipleChoiceItem()
    .setTitle('N1. MeducAI 학습 자료를 "받거나(전달/링크) 접한" 적이 있습니까? (필수)')
    .setRequired(true)
    .setChoiceValues(['예 (다운로드/전달/링크를 받음)', '아니오 (받은 적 없음/모름)']);

  form.addCheckboxItem()
    .setTitle('N2. MeducAI를 사용하지 않은 가장 큰 이유(들)는 무엇입니까? (필수, 복수 선택)')
    .setRequired(true)
    .setChoiceValues([
      '자료를 받지 못했거나 접근 경로를 몰랐다',
      '시간이 부족했다',
      '기존에 쓰던 학습 방식/도구로 충분했다',
      'Anki(플래시카드) 학습 방식이 나와 맞지 않았다',
      '사용 방법/온보딩이 어렵게 느껴졌다',
      '콘텐츠 정확성(오류 가능성)이 걱정되었다',
      '콘텐츠 분량/구성이 부담스러웠다',
      '기술적 문제(접속/다운로드/기기)로 사용이 어려웠다',
      '기타 (자유 기입)',
    ]);

  form.addParagraphTextItem()
    .setTitle('N3. (선택) 사용을 가능하게 했을 "개선/지원"이 있다면 무엇입니까?')
    .setRequired(false)
    .setHelpText('1–2문장 이내로 작성해 주세요.');

  // N4: 향후 의향 (MultipleChoice) → 비사용자 경로의 마지막 분기점
  const n4 = form.addMultipleChoiceItem();
  n4.setTitle('N4. (필수) 향후(다른 시험/학습 상황) 유사한 도구를 사용할 의향이 있습니까?')
    .setRequired(true)
    .setChoiceValues([
      '1 - 전혀 없다',
      '2',
      '3',
      '4',
      '5 - 매우 있다',
    ]);

  // ============================================
  // SECTION 10: Z. Common (모든 응답자)
  // ============================================
  const pageCommon = form.addPageBreakItem()
    .setTitle('Z. 공통 섹션 (모든 응답자)')
    .setHelpText('아래 문항은 MeducAI 사용 여부와 무관하게 모두 응답해 주세요. (Baseline 대비 변화량 해석용)');

  // Z1-3: Extraneous CL
  form.addScaleItem()
    .setTitle('Z1. 시험 준비 기간 동안 사용한 학습 자료/도구(전체)의 구성이나 표현 방식 때문에 불필요하게 머리가 복잡하다고 느꼈다.')
    .setRequired(true)
    .setBounds(1, 7)
    .setLabels('매우 낮았다', '매우 높았다')
    .setHelpText('MeducAI 포함 "전체 학습 자료/도구(교재, 강의, 노트 등)"를 기준으로 응답해 주세요.');

  form.addScaleItem()
    .setTitle('Z2. 시험 준비 기간 동안 필요한 정보를 찾기 위해 자료를 이리저리 찾아보는 데 많은 노력이 들었다.')
    .setRequired(true)
    .setBounds(1, 7)
    .setLabels('매우 낮았다', '매우 높았다');

  form.addScaleItem()
    .setTitle('Z3. 시험 준비 기간 동안 학습 도구의 사용 방식이 직관적이지 않아 학습 흐름이 끊긴다고 느꼈다.')
    .setRequired(true)
    .setBounds(1, 7)
    .setLabels('매우 낮았다', '매우 높았다');

  // Z4-8: Behavioral/emotional
  form.addScaleItem()
    .setTitle('Z4. 최근 학습 관련 스트레스 수준은 어떠했습니까?')
    .setRequired(true)
    .setBounds(1, 7)
    .setLabels('매우 낮았다', '매우 높았다');

  form.addMultipleChoiceItem()
    .setTitle('Z5. 최근 2주간 하루 평균 수면 시간은 어느 정도였습니까?')
    .setRequired(true)
    .setChoiceValues(['4시간 미만', '4–5시간', '5–6시간', '6–7시간', '7시간 이상']);

  form.addScaleItem()
    .setTitle('Z6. 최근 전반적인 수면의 질은 어떠했습니까?')
    .setRequired(true)
    .setBounds(1, 7)
    .setLabels('매우 나쁘다', '매우 좋다');

  form.addScaleItem()
    .setTitle('Z7. 최근 전반적인 기분 상태는 어떠했습니까?')
    .setRequired(true)
    .setBounds(1, 7)
    .setLabels('매우 나쁘다', '매우 좋다');

  form.addMultipleChoiceItem()
    .setTitle('Z8. 최근 규칙적인 운동(30분 이상) 빈도는 어느 정도였습니까?')
    .setRequired(true)
    .setChoiceValues(['전혀 하지 않음', '주 1–2회', '주 3–4회', '주 5회 이상']);

  // Z9-10: Self-efficacy
  form.addScaleItem()
    .setTitle('Z9. 나는 학습 계획을 전반적으로 잘 수행할 수 있다고 느낀다.')
    .setRequired(true)
    .setBounds(1, 7)
    .setLabels('전혀 그렇지 않았다', '매우 그렇다');

  form.addScaleItem()
    .setTitle('Z10. 나는 시험에 필요한 핵심 개념을 이해하는 데 자신이 있다.')
    .setRequired(true)
    .setBounds(1, 7)
    .setLabels('전혀 그렇지 않았다', '매우 그렇다');

  // ============================================
  // 분기 설정 (모든 섹션 생성 후)
  // ============================================

  // A1 분기
  a1.setChoices([
    a1.createChoice('예', pageUser),
    a1.createChoice('아니오 (사용하지 않음)', pageNonUser),
  ]);

  // H4: 사용자 경로의 모든 선택지 → pageCommon
  h4.setChoices([
    h4.createChoice('사실 오류/정확성', pageCommon),
    h4.createChoice('설명의 명확성/가독성', pageCommon),
    h4.createChoice('시험 적합성(핵심성/불필요 정보)', pageCommon),
    h4.createChoice('분량/구성(너무 길거나 짧음)', pageCommon),
    h4.createChoice('요약 표(Table) 품질', pageCommon),
    h4.createChoice('슬라이드(Info slide) 품질', pageCommon),
    h4.createChoice('Anki 덱 구성(카드 구성/표현)', pageCommon),
    h4.createChoice('기타', pageCommon),
  ]);

  // N4: 비사용자 경로의 모든 선택지 → pageCommon
  n4.setChoices([
    n4.createChoice('1 - 전혀 없다', pageCommon),
    n4.createChoice('2', pageCommon),
    n4.createChoice('3', pageCommon),
    n4.createChoice('4', pageCommon),
    n4.createChoice('5 - 매우 있다', pageCommon),
  ]);

  // 완료 메시지
  form.setConfirmationMessage(
    '설문에 참여해 주셔서 진심으로 감사드립니다.\n' +
    '귀하의 응답은 향후 AI 기반 전문의 교육 도구 개선을 위한 중요한 자료로 활용될 예정입니다.'
  );

  // URL 출력
  const formUrl = form.getPublishedUrl();
  Logger.log('========================================');
  Logger.log('✅ FINAL Google Form이 생성되었습니다!');
  Logger.log('========================================');
  Logger.log('📋 Form 제목: ' + form.getTitle());
  Logger.log('🔗 Form URL (공유용): ' + formUrl);
  Logger.log('✏️ Form 편집 URL: ' + form.getEditUrl());
  Logger.log('');
  Logger.log('📊 흐름 확인:');
  Logger.log('  - A1=예 → A2-A5 → B-H(H4에서 Z로) → Z → 제출');
  Logger.log('  - A1=아니오 → N1-N4(N4에서 Z로) → Z → 제출');

  return formUrl;
}
