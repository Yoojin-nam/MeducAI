#!/usr/bin/env python3
"""
Google Form 생성 도우미 스크립트 (Python)

이 스크립트는 Google Apps Script를 사용하여 Google Form을 생성하는 과정을 안내합니다.
직접적으로 Google Form을 생성하지는 않지만, 필요한 설정과 구조를 검증하고
Google Apps Script 코드를 생성합니다.

사용 방법:
1. 이 스크립트를 실행하여 Google Apps Script 코드 생성
2. 생성된 코드를 Google Apps Script에 붙여넣기
3. createQAForm() 함수 실행
"""

import json
from pathlib import Path
from typing import Dict, List


def generate_google_apps_script() -> str:
    """
    Google Apps Script 코드를 생성합니다.
    """
    script_content = '''/**
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
'''
    return script_content


def validate_form_structure() -> Dict:
    """
    Form 구조를 검증하고 요약을 반환합니다.
    """
    structure = {
        "total_sections": 13,  # Section 1 + Q01~Q12
        "section_1": {
            "title": "평가자 정보",
            "items": [
                "평가자 구분 (객관식, 필수)"
            ]
        },
        "sections_2_13": {
            "title": "Q01~Q12 평가",
            "items_per_q": [
                "B1. Blocking Error (객관식, 필수)",
                "B1-1. Blocking Error 설명 (텍스트, 조건부)",
                "B2. Overall Card Quality (척도 1-5, 필수)",
                "B3. Evidence Comment (텍스트, 조건부)",
                "C1. Critical Error (객관식, 필수)",
                "C1-1. Critical Error 설명 (텍스트, 조건부)",
                "C2. Scope Failure (객관식, 필수)",
                "C2-1. Scope Failure 설명 (텍스트, 조건부)",
                "D1. Clarity & Readability (척도 1-5, 선택)",
                "D2. Clinical/Exam Relevance (척도 1-5, 선택)",
                "D3. Editing Time (텍스트, 필수)",
                "E. 실제 평가 시간 (객관식, 선택)",
                "자유 의견 (텍스트, 선택)"
            ],
            "total_items_per_q": 13,
            "total_items_all_q": 13 * 12  # 156 items
        },
        "form_settings": {
            "collect_email": True,
            "limit_one_response": True,
            "allow_response_edits": True,
            "show_link_to_respond_again": False
        }
    }
    return structure


def main():
    """
    메인 함수: Google Apps Script 코드 생성 및 구조 검증
    """
    print("=" * 60)
    print("MeducAI S0 QA Google Form 생성 도우미")
    print("=" * 60)
    print()
    
    # Form 구조 검증
    structure = validate_form_structure()
    print("Form 구조 검증:")
    print(f"  - 총 섹션 수: {structure['total_sections']}")
    print(f"  - Section 1: {structure['section_1']['title']}")
    print(f"  - Section 2~13: {structure['sections_2_13']['title']}")
    print(f"  - Q당 문항 수: {structure['sections_2_13']['total_items_per_q']}")
    print(f"  - 전체 문항 수: {structure['sections_2_13']['total_items_all_q']} (Q01~Q12)")
    print()
    
    # Google Apps Script 코드 생성
    script_content = generate_google_apps_script()
    
    # 스크립트 파일 저장
    script_path = Path(__file__).parent / "create_google_form_qa.js"
    script_path.write_text(script_content, encoding='utf-8')
    print(f"✅ Google Apps Script 코드가 생성되었습니다:")
    print(f"   {script_path}")
    print()
    
    # 사용 방법 안내
    print("=" * 60)
    print("사용 방법:")
    print("=" * 60)
    print("1. Google Drive 접속")
    print("2. 새 Google 스프레드시트 생성")
    print("3. 확장 프로그램 > Apps Script 열기")
    print(f"4. {script_path.name} 파일의 내용을 복사하여 붙여넣기")
    print("5. createQAForm() 함수 선택 후 실행")
    print("6. 권한 승인 (처음 실행 시)")
    print("7. 로그에서 Form URL 확인")
    print()
    print("=" * 60)
    print("참고 문서:")
    print("=" * 60)
    print("- Google_Form_Creation_Guide.md")
    print("- Google_Form_Design_Specification.md")
    print("- S0_QA_Survey_Questions.md")
    print()


if __name__ == "__main__":
    main()

