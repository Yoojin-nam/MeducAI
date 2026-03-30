---
marp: true
theme: default
paginate: true
backgroundColor: #1a1a2e
color: #fff
style: |
  section {
    font-family: 'Noto Sans KR', sans-serif;
    background-size: cover;
    background-position: center;
  }
  h1 {
    font-size: 3em;
    margin-bottom: 0.5em;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
  h2 {
    font-size: 2em;
    color: #667eea;
    border-bottom: 2px solid #667eea;
    padding-bottom: 0.3em;
  }
  h3 {
    font-size: 1.5em;
    color: #764ba2;
  }
  table {
    border-collapse: collapse;
    width: 100%;
    margin: 1em 0;
  }
  th {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 0.5em 1em;
    text-align: left;
  }
  td {
    border: 1px solid #ddd;
    padding: 0.5em 1em;
    background: rgba(255,255,255,0.1);
  }
  pre {
    background: #2d2d3a;
    padding: 1em;
    border-radius: 8px;
    overflow-x: auto;
  }
  code {
    color: #f39c12;
  }
  strong {
    color: #667eea;
  }
  hr {
    border: none;
    height: 2px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    margin: 2em 0;
  }
  ul, ol {
    margin-left: 1.5em;
  }
  li {
    margin: 0.5em 0;
  }
---

# MeducAI 연구 개요<br>및 발전 가능성 분석

<div style="text-align: center; margin-top: 2em;">
  <div style="display: inline-block; padding: 1em 2em; background: rgba(102, 126, 234, 0.2); border-radius: 10px; border: 2px solid #667eea;">
    <strong>2026년 1월 12일</strong><br>
    <span style="font-size: 0.9em; opacity: 0.9;">GLM-4.7 연구 분석 기반</span>
  </div>
</div>

---

# 목차

<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1em; margin-top: 2em;">
  <div style="background: rgba(102, 126, 234, 0.15); padding: 1em; border-radius: 8px; border-left: 4px solid #667eea;">
    <strong>1. 연구 개요</strong>
  </div>
  <div style="background: rgba(102, 126, 234, 0.15); padding: 1em; border-radius: 8px; border-left: 4px solid #667eea;">
    <strong>2. 파이프라인 구조</strong>
  </div>
  <div style="background: rgba(102, 126, 234, 0.15); padding: 1em; border-radius: 8px; border-left: 4px solid #667eea;">
    <strong>3. 3편 논문 포트폴리오</strong>
  </div>
  <div style="background: rgba(118, 75, 162, 0.15); padding: 1em; border-radius: 8px; border-left: 4px solid #764ba2;">
    <strong>4. 현재 상태 및 일정</strong>
  </div>
  <div style="background: rgba(118, 75, 162, 0.15); padding: 1em; border-radius: 8px; border-left: 4px solid #764ba2;">
    <strong>5. 발전 가능성 분석</strong>
  </div>
  <div style="background: rgba(118, 75, 162, 0.15); padding: 1em; border-radius: 8px; border-left: 4px solid #764ba2;">
    <strong>6. 우선순위 및 향후 계획</strong>
  </div>
</div>

---

# 1. 연구 개요

## MeducAI란?

<div style="background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%); padding: 2em; border-radius: 15px; margin-top: 1.5em;">
  
  <h2 style="font-size: 2em; color: #667eea; border: none;">AI 기반 의료 교육 플랫폼</h2>

  <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 2em; margin-top: 1.5em;">
    <div>
      <ul style="list-style: none; padding: 0;">
        <li style="background: rgba(102, 126, 234, 0.15); padding: 0.8em; border-radius: 8px; margin-bottom: 0.8em;">
          <strong>🎯 목표</strong><br>
          영상의학과 전문의 시험 준비
        </li>
        <li style="background: rgba(118, 75, 162, 0.15); padding: 0.8em; border-radius: 8px; margin-bottom: 0.8em;">
          <strong>⚡ 핵심</strong><br>
          AI가 생성한 플래시카드 + 이미지
        </li>
        <li style="background: rgba(102, 126, 234, 0.15); padding: 0.8em; border-radius: 8px;">
          <strong>🔄 프로세스</strong><br>
          교육 목표 → AI 파이프라인 → 학습자
        </li>
      </ul>
    </div>

    <div style="background: rgba(255, 255, 255, 0.1); padding: 1.5em; border-radius: 10px; border: 2px solid #667eea; text-align: center;">
      <strong style="color: #667eea; font-size: 1.2em;">데이터 흐름</strong><br><br>
      <span style="font-size: 1.1em;">Curriculum Objectives</span><br>
      <strong style="color: #f39c12; font-size: 2em;">↓</strong><br>
      <span style="font-size: 1.1em;">AI Pipeline</span><br>
      <strong style="color: #f39c12; font-size: 2em;">↓</strong><br>
      <span style="font-size: 1.1em;">Flashcards</span><br>
      <strong style="color: #f39c12; font-size: 2em;">↓</strong><br>
      <span style="font-size: 1.1em;">Learners</span>
    </div>
  </div>
</div>

---

# 2. 파이프라인 구조

## S1 → S6 6단계 파이프라인

<div style="background: rgba(255, 255, 255, 0.1); padding: 2em; border-radius: 15px; margin-top: 1.5em;">
  
  <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1.5em;">
    
    <div style="background: rgba(102, 126, 234, 0.15); padding: 1em; border-radius: 10px; border-left: 5px solid #667eea;">
      <strong style="font-size: 1.3em; color: #667eea;">S1</strong><br>
      <span>구조화 (Entity 추출)</span>
      <strong style="color: #f39c12; font-size: 2em; display: block; text-align: center; margin: 0.5em 0;">↓</strong>
    </div>

    <div style="background: rgba(118, 75, 162, 0.15); padding: 1em; border-radius: 10px; border-left: 5px solid #764ba2;">
      <strong style="font-size: 1.3em; color: #764ba2;">S2</strong><br>
      <span>카드 생성 (Q1/Q2)</span>
      <strong style="color: #f39c12; font-size: 2em; display: block; text-align: center; margin: 0.5em 0;">↓</strong>
    </div>

    <div style="background: rgba(102, 126, 234, 0.15); padding: 1em; border-radius: 10px; border-left: 5px solid #667eea;">
      <strong style="font-size: 1.3em; color: #667eea;">S3</strong><br>
      <span>정책 해결 (이미지 스펙)</span>
      <strong style="color: #f39c12; font-size: 2em; display: block; text-align: center; margin: 0.5em 0;">↓</strong>
    </div>

    <div style="background: rgba(118, 75, 162, 0.15); padding: 1em; border-radius: 10px; border-left: 5px solid #764ba2;">
      <strong style="font-size: 1.3em; color: #764ba2;">S4</strong><br>
      <span>이미지 생성 (Illustration + Realistic)</span>
      <strong style="color: #f39c12; font-size: 2em; display: block; text-align: center; margin: 0.5em 0;">↓</strong>
    </div>

    <div style="background: rgba(102, 126, 234, 0.15); padding: 1em; border-radius: 10px; border-left: 5px solid #667eea;">
      <strong style="font-size: 1.3em; color: #667eea;">S5</strong><br>
      <span>검증 & 재작성 (PASS/REGEN)</span>
      <strong style="color: #f39c12; font-size: 2em; display: block; text-align: center; margin: 0.5em 0;">↓</strong>
    </div>

    <div style="background: rgba(118, 75, 162, 0.15); padding: 1em; border-radius: 10px; border-left: 5px solid #764ba2;">
      <strong style="font-size: 1.3em; color: #764ba2;">S6</strong><br>
      <span>패키징 (PDF, Anki 덱)</span>
    </div>

  </div>

  <div style="background: rgba(243, 156, 18, 0.15); padding: 1em; border-radius: 8px; margin-top: 1.5em; border: 2px solid #f39c12;">
    <strong style="color: #f39c12;">✨ 핵심 특징</strong>
    <ul style="margin-top: 0.5em;">
      <li><strong>2-card 정책</strong>: 각 엔티티당 정확히 2개 카드 (Q1, Q2)</li>
      <li><strong>Back-only 인포그래픽</strong>: 모든 Q1/Q2 카드</li>
      <li><strong>Q1/Q2 독립 이미지</strong>: 각각 별도 이미지 생성</li>
    </ul>
  </div>
</div>

---

# 3. 3편 논문 포트폴리오

## 연구 로직 흐름

<div style="display: flex; justify-content: space-between; align-items: center; background: rgba(255, 255, 255, 0.1); padding: 2em; border-radius: 15px; margin-top: 1.5em;">
  
  <div style="background: linear-gradient(135deg, rgba(102, 126, 234, 0.2) 0%, rgba(118, 75, 162, 0.2) 100%); padding: 1.5em; border-radius: 10px; width: 30%; text-align: center;">
    <strong style="font-size: 1.5em; color: #667eea;">Paper 1</strong><br>
    <span style="font-size: 0.9em;">S5 시스템 신뢰도</span><br><br>
    <div style="background: rgba(255, 255, 255, 0.2); padding: 0.5em; border-radius: 5px; font-size: 0.9em;">
      "AI 검증 시스템이 정확한가?"
    </div>
  </div>

  <strong style="color: #f39c12; font-size: 3em;">→</strong>

  <div style="background: linear-gradient(135deg, rgba(118, 75, 162, 0.2) 0%, rgba(102, 126, 234, 0.2) 100%); padding: 1.5em; border-radius: 10px; width: 30%; text-align: center;">
    <strong style="font-size: 1.5em; color: #764ba2;">Paper 2</strong><br>
    <span style="font-size: 0.9em;">이미지 신뢰도</span><br><br>
    <div style="background: rgba(255, 255, 255, 0.2); padding: 0.5em; border-radius: 5px; font-size: 0.9em;">
      "AI 이미지가 임상적으로 정확한가?"
    </div>
  </div>

  <strong style="color: #f39c12; font-size: 3em;">→</strong>

  <div style="background: linear-gradient(135deg, rgba(102, 126, 234, 0.2) 0%, rgba(118, 75, 162, 0.2) 100%); padding: 1.5em; border-radius: 10px; width: 30%; text-align: center;">
    <strong style="font-size: 1.5em; color: #667eea;">Paper 3</strong><br>
    <span style="font-size: 0.9em;">교육 효과</span><br><br>
    <div style="background: rgba(255, 255, 255, 0.2); padding: 0.5em; border-radius: 5px; font-size: 0.9em;">
      "최종 교육자료가 시험에 도움이 되는가?"
    </div>
  </div>

</div>

---

# Paper 1: S5 Multi-agent 신뢰도 연구

<div style="display: grid; grid-template-columns: 1.5fr 1fr; gap: 2em; margin-top: 1.5em;">
  
  <div>
    <table>
      <thead>
        <tr>
          <th>항목</th>
          <th>내용</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>연구 유형</strong></td>
          <td>진단 정확도 연구 (Validation)</td>
        </tr>
        <tr>
          <td><strong>핵심 질문</strong></td>
          <td>S5 multi-agent 시스템이 인간 전문가 수준의 품질 검증을 수행할 수 있는가?</td>
        </tr>
        <tr>
          <td><strong>Primary Claim</strong></td>
          <td><strong>S5-PASS는 안전하다 (FN < 0.3%)</strong></td>
        </tr>
        <tr>
          <td><strong>데이터</strong></td>
          <td>FINAL QA (1,350 전공의 + 330 전문의)</td>
        </tr>
      </tbody>
    </table>
  </div>

  <div style="background: rgba(102, 126, 234, 0.15); padding: 1.5em; border-radius: 10px; border: 2px solid #667eea;">
    <strong style="color: #667eea; font-size: 1.3em;">📊 핵심 메트릭</strong>
    <ul style="margin-top: 1em;">
      <li style="margin-bottom: 0.8em;"><strong>False Negative Rate</strong> (PASS의 안전성)<br>
        <span style="color: #f39c12;">< 0.3% (95% CI)</span></li>
      <li style="margin-bottom: 0.8em;"><strong>Accept-as-is Rate</strong> (REGEN의 완전性)<br>
        <span style="color: #f39c12;">Census review</span></li>
      <li><strong>Pre-S5 → Post-S5 변화율</strong></li>
    </ul>
  </div>

</div>

---

# Paper 2: MLLM 이미지 신뢰도 연구

<div style="background: rgba(255, 255, 255, 0.1); padding: 2em; border-radius: 15px; margin-top: 1.5em;">
  
  <table>
    <thead>
      <tr>
        <th>항목</th>
        <th>내용</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>연구 유형</strong></td>
        <td>기술적 검증 연구 (Technical Validation)</td>
      </tr>
      <tr>
        <td><strong>핵심 질문</strong></td>
        <td>MLLM이 생성한 의료 교육 이미지가 임상적으로 정확하고 교육적으로 유용한가?</td>
      </tr>
    </tbody>
  </table>

  <h3 style="margin-top: 2em;">📸 Sub-studies</h3>

  <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5em; margin-top: 1.5em;">
    
    <div style="background: rgba(102, 126, 234, 0.15); padding: 1.5em; border-radius: 10px;">
      <strong style="color: #667eea;">2.1 Visual Modality Sub-study</strong>
      <table style="margin-top: 1em;">
        <thead>
          <tr>
            <th>평가자</th>
            <th>Illustration</th>
            <th>Realistic</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Resident</td>
            <td>1,350개</td>
            <td>330개</td>
          </tr>
          <tr>
            <td>Specialist</td>
            <td>330개</td>
            <td>330개</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div style="background: rgba(118, 75, 162, 0.15); padding: 1.5em; border-radius: 10px;">
      <strong style="color: #764ba2;">2.2 Table Infographic Evaluation</strong>
      <ul style="margin-top: 1em;">
        <li>전체 833개 인포그래픽 중 <strong>100개 (12%)</strong> 샘플링</li>
        <li>9명 전공의 평가</li>
        <li>카드 평가와 병행</li>
      </ul>
    </div>

  </div>

</div>

---

# Paper 3: 교육효과 전향적 연구

<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 2em; margin-top: 1.5em;">
  
  <div>
    <table>
      <thead>
        <tr>
          <th>항목</th>
          <th>내용</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>연구 유형</strong></td>
          <td>전향적 관찰연구 (Prospective Observational)</td>
        </tr>
        <tr>
          <td><strong>대상</strong></td>
          <td>영상의학과 4년차 전공의 (전문의 시험 응시자)</td>
        </tr>
        <tr>
          <td><strong>핵심 질문</strong></td>
          <td>MeducAI FINAL 산출물이 전문의 시험 대비에 실질적으로 도움이 되는가?</td>
        </tr>
      </tbody>
    </table>
  </div>

  <div style="background: rgba(118, 75, 162, 0.15); padding: 1.5em; border-radius: 10px;">
    <strong style="color: #764ba2; font-size: 1.3em;">🎓 Primary Outcomes</strong>
    <ul style="margin-top: 1em;">
      <li style="margin-bottom: 0.8em;"><strong>Extraneous Cognitive Load</strong><br>
        인지 부하 (Leppink et al. scale)</li>
      <li style="margin-bottom: 0.8em;"><strong>Learning Efficiency</strong><br>
        학습 효율성 (0-100% time reduction)</li>
      <li style="margin-bottom: 0.8em;"><strong>Perceived Exam Readiness</strong><br>
        시험 준비 자신감 (Change score)</li>
      <li><strong>Knowledge Retention</strong><br>
        지식 유지 (1-7 Likert)</li>
    </ul>
  </div>

</div>

---

# 4. 현재 상태 및 일정

## 연구 규모 & 상태

<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.5em; margin-top: 1.5em;">
  
  <div style="background: rgba(102, 126, 234, 0.15); padding: 1.5em; border-radius: 10px; text-align: center;">
    <strong style="font-size: 2em; color: #667eea;">6,000</strong>
    <p>총 카드</p>
  </div>

  <div style="background: rgba(118, 75, 162, 0.15); padding: 1.5em; border-radius: 10px; text-align: center;">
    <strong style="font-size: 2em; color: #764ba2;">20</strong>
    <p>평가자 (9+11)</p>
  </div>

  <div style="background: rgba(102, 126, 234, 0.15); padding: 1.5em; border-radius: 10px; text-align: center;">
    <strong style="font-size: 2em; color: #667eea;">2,340</strong>
    <p>평가량</p>
  </div>

</div>

<h3 style="margin-top: 2em;">📊 현재 상태</h3>

<table style="margin-top: 1em;">
  <thead>
    <tr>
      <th>논문</th>
      <th>상태</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>Paper 1</strong></td>
      <td style="color: #27ae60;">✅ 데이터 수집 준비 완료</td>
    </tr>
    <tr>
      <td><strong>Paper 2 - Visual</strong></td>
      <td style="color: #27ae60;">✅ 데이터 수집 준비 완료</td>
    </tr>
    <tr>
      <td><strong>Paper 2 - Table</strong></td>
      <td style="color: #f39c12;">⏳ 카드 평가와 병행 실행</td>
    </tr>
    <tr>
      <td><strong>Paper 3</strong></td>
      <td style="color: #3498db;">🔄 IRB 진행 중, 1/7 배포 예정</td>
    </tr>
  </tbody>
</table>

---

# 5. 발전 가능성 분석

## 연구 설계 차원

<div style="background: rgba(255, 255, 255, 0.1); padding: 2em; border-radius: 15px; margin-top: 1.5em;">
  
  <div style="background: linear-gradient(135deg, rgba(102, 126, 234, 0.2) 0%, rgba(118, 75, 162, 0.2) 100%); padding: 1.5em; border-radius: 10px; margin-bottom: 1.5em;">
    <strong style="color: #667eea; font-size: 1.5em;">🚀 Turing Test 연구 확장 (Paper 2.5)</strong>
    
    <div style="background: rgba(255, 255, 255, 0.15); padding: 1em; border-radius: 8px; margin-top: 1em;">
      <strong>현재 상태</strong>: 아직 실행되지 않은 제안된 연구
    </div>

    <div style="background: rgba(243, 156, 18, 0.15); padding: 1em; border-radius: 8px; margin-top: 1em;">
      <strong>발전 가능성</strong>
      <p style="margin-top: 0.5em;">Paper 2 (이미지 신뢰도) + Paper 2.5 (Turing Test)</p>
      <p><em>"품질 평가" + "구분 가능성" + "AI Reject/Accept 분석"</em></p>
    </div>
  </div>

  <div style="background: rgba(118, 75, 162, 0.15); padding: 1.5em; border-radius: 10px;">
    <strong style="color: #764ba2; font-size: 1.5em;">📐 권장 설계: 독립 논문 전략</strong>
    
    <ul style="margin-top: 1em;">
      <li style="margin-bottom: 0.8em;"><strong>Primary</strong>: "AI 생성 이미지가 실제 이미지와 구분 가능한가?"</li>
      <li><strong>Secondary</strong>: "AI 평가 시스템의 calibration은 적절한가?"</li>
    </ul>
  </div>

</div>

---

# 6. 우선순위 및 향후 계획

## 발전 가능성 우선순위

<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5em; margin-top: 1.5em;">
  
  <div>
    <table>
      <thead>
        <tr>
          <th>우선순위</th>
          <th>분야</th>
          <th>구체적 발전 방안</th>
          <th>시기</th>
        </tr>
      </thead>
      <tbody>
        <tr style="background: rgba(231, 76, 60, 0.2);">
          <td><strong style="color: #e74c3c;">P0</strong></td>
          <td>데이터 품질</td>
          <td>AppSheet 시간 계산 이슈 해결</td>
          <td style="color: #e74c3c; font-weight: bold;">즉시</td>
        </tr>
        <tr style="background: rgba(243, 156, 18, 0.1);">
          <td><strong style="color: #f39c12;">P1</strong></td>
          <td>연구 설계</td>
          <td>Turing Test Pilot Study 실행</td>
          <td>1-2월</td>
        </tr>
        <tr style="background: rgba(243, 156, 18, 0.1);">
          <td><strong style="color: #f39c12;">P1</strong></td>
          <td>연구 설계</td>
          <td>독립 논문 전략 결정</td>
          <td>1-2월</td>
        </tr>
        <tr style="background: rgba(52, 152, 219, 0.1);">
          <td><strong style="color: #3498db;">P2</strong></td>
          <td>통계 분석</td>
          <td>Sample Size 계산 강화</td>
          <td>1-2월</td>
        </tr>
        <tr style="background: rgba(52, 152, 219, 0.1);">
          <td><strong style="color: #3498db;">P2</strong></td>
          <td>언어 정책</td>
          <td>S2 프롬프트 업그레이드</td>
          <td>3월 이후</td>
        </tr>
      </tbody>
    </table>
  </div>

  <div style="background: rgba(102, 126, 234, 0.15); padding: 1.5em; border-radius: 10px;">
    <strong style="color: #667eea; font-size: 1.3em;">🎯 6개월 로드맵</strong>
    
    <div style="background: rgba(255, 255, 255, 0.1); padding: 1em; border-radius: 8px; margin-top: 1em;">
      <div style="display: grid; grid-template-columns: repeat(6, 1fr); gap: 0.5em; text-align: center;">
        <div style="background: rgba(102, 126, 234, 0.2); padding: 0.5em; border-radius: 5px;">
          <strong>1월</strong>
        </div>
        <div style="background: rgba(118, 75, 162, 0.2); padding: 0.5em; border-radius: 5px;">
          <strong>2월</strong>
        </div>
        <div style="background: rgba(102, 126, 234, 0.2); padding: 0.5em; border-radius: 5px;">
          <strong>3월</strong>
        </div>
        <div style="background: rgba(118, 75, 162, 0.2); padding: 0.5em; border-radius: 5px;">
          <strong>4월</strong>
        </div>
        <div style="background: rgba(102, 126, 234, 0.2); padding: 0.5em; border-radius: 5px;">
          <strong>5월</strong>
        </div>
        <div style="background: rgba(118, 75, 162, 0.2); padding: 0.5em; border-radius: 5px;">
          <strong>6월</strong>
        </div>
      </div>

      <ul style="margin-top: 1em; font-size: 0.9em;">
        <li style="margin-bottom: 0.5em;"><strong style="color: #667eea;">Paper 1</strong>: 투고 (3-4월)</li>
        <li style="margin-bottom: 0.5em;"><strong style="color: #764ba2;">Paper 2</strong>: 투고 (4-5월)</li>
        <li><strong style="color: #667eea;">Paper 3</strong>: 투고 (5-6월)</li>
      </ul>
    </div>
  </div>

</div>

---

# 7. 결론

## 핵심 요약

<div style="background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%); padding: 2em; border-radius: 15px; margin-top: 1.5em;">
  
  <p style="font-size: 1.2em; line-height: 1.8;">MeducAI는 현재 <strong>3편 논문 기반</strong>에서 다음과 같은 발전 가능성이 있습니다:</p>

  <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1.5em; margin-top: 1.5em;">
    
    <div style="background: rgba(102, 126, 234, 0.15); padding: 1em; border-radius: 8px; border-left: 4px solid #667eea;">
      <strong>1. 연구 설계</strong><br>
      Turing Test 연구 확장 (AI Reject/Accept 분석)
    </div>

    <div style="background: rgba(118, 75, 162, 0.15); padding: 1em; border-radius: 8px; border-left: 4px solid #764ba2;">
      <strong>2. 데이터 품질</strong><br>
      AppSheet 시간 계산 이슈 즉시 해결
    </div>

    <div style="background: rgba(102, 126, 234, 0.15); padding: 1em; border-radius: 8px; border-left: 4px solid #667eea;">
      <strong>3. 통계 분석</strong><br>
      Sample size 계산 및 Pilot study 선행
    </div>

    <div style="background: rgba(118, 75, 162, 0.15); padding: 1em; border-radius: 8px; border-left: 4px solid #764ba2;">
      <strong>4. 언어 정책</strong><br>
      S2 프롬프트 영어 우선 정책 적용
    </div>

    <div style="background: rgba(102, 126, 234, 0.15); padding: 1em; border-radius: 8px; border-left: 4px solid #667eea;">
      <strong>5. 파이프라인</strong><br>
      Code-Protocol 일관성 강화
    </div>

    <div style="background: rgba(118, 75, 162, 0.15); padding: 1em; border-radius: 8px; border-left: 4px solid #764ba2;">
      <strong>6. 논문 출판</strong><br>
      Adaptive Publication Strategy (3-Paper ↔ 4-Paper)
    </div>

  </div>

</div>

---

# 가장 큰 발전 가능성

## Turing Test 연구

<div style="background: rgba(243, 156, 18, 0.15); padding: 2em; border-radius: 15px; margin-top: 1.5em; border: 3px solid #f39c12;">
  
  <strong style="color: #f39c12; font-size: 1.5em;">🎯 AI 생성 이미지의 구분 가능성 평가</strong>

  <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 2em; margin-top: 1.5em;">
    
    <div style="background: rgba(255, 255, 255, 0.1); padding: 1.5em; border-radius: 10px;">
      <strong style="color: #667eea;">✅ 장점</strong>
      <ul style="margin-top: 1em;">
        <li style="margin-bottom: 0.5em;">AI 평가 시스템의 calibration 검증</li>
        <li style="margin-bottom: 0.5em;">Paper 1의 FN 검증과 연결</li>
        <li>새로운 연구 질문 제시</li>
      </ul>
    </div>

    <div style="background: rgba(255, 255, 255, 0.1); padding: 1.5em; border-radius: 10px;">
      <strong style="color: #764ba2;">🎓 권장 전략</strong>
      <p style="margin-bottom: 0.8em;"><strong>독립 논문으로 먼저 Submission</strong></p>
      <ul style="font-size: 0.9em;">
        <li style="margin-bottom: 0.5em;"><strong style="color: #27ae60;">Accept 시</strong>: 독립 논문으로 출판 (4-Paper 체계)</li>
        <li><strong style="color: #3498db;">Reject 시</strong>: Paper 2에 Sub-study 2로 포함 (3-Paper 체계)</li>
      </ul>
    </div>

  </div>

</div>

---

# 감사합니다!

<div style="text-align: center; margin-top: 3em;">
  
  <div style="background: linear-gradient(135deg, rgba(102, 126, 234, 0.2) 0%, rgba(118, 75, 162, 0.2) 100%); padding: 2em; border-radius: 15px; display: inline-block;">
    
    <strong style="font-size: 2em; color: #667eea;">🙏 감사합니다!</strong>
    
    <p style="margin-top: 1.5em; font-size: 1.2em;">
      본 프레젠테이션은 MeducAI 연구의 개요와 발전 가능성을 정리한 것입니다.
    </p>

    <div style="background: rgba(255, 255, 255, 0.15); padding: 1em; border-radius: 10px; margin-top: 1.5em;">
      <strong style="color: #667eea;">연구팀 문의</strong><br>
      <a href="mailto:[email-redacted]" style="color: #f39c12;">[email-redacted]</a>
    </div>

    <div style="margin-top: 1.5em; font-size: 0.9em; opacity: 0.8;">
      문서: 0_Protocol/06_QA_and_Study/
    </div>

  </div>

</div>
