#!/usr/bin/env python3
"""
MeducAI Anki 사용 설명서 PDF 생성기

Generates a comprehensive Anki usage guide PDF in Korean.

Contents:
1. Anki 설치 방법 (Windows/Mac/iOS/Android)
2. 덱 가져오기 방법
3. 추천 학습 설정 (하루 200문제, 랜덤 순서)
4. 분과별 덱 활용법 (약한 파트 집중 학습)
5. 통계 확인 및 학습 진도 관리

Usage:
    python 3_Code/src/tools/docs/generate_anki_guide_pdf.py --out_dir 6_Distributions
"""

import argparse
import os
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    ListFlowable,
    ListItem,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# =========================
# Font Registration (reused from 07_build_set_pdf.py)
# =========================

def register_korean_font():
    """Register Korean font for PDF generation."""
    home_dir = os.path.expanduser("~")
    
    korean_font_candidates = [
        # 나눔고딕 (Nanum Gothic) - preferred
        (f"{home_dir}/Library/Fonts/NanumGothic.ttf", f"{home_dir}/Library/Fonts/NanumGothicExtraBold.ttf"),
        ("/Library/Fonts/NanumGothic.ttf", "/Library/Fonts/NanumGothicExtraBold.ttf"),
        (f"{home_dir}/Library/Fonts/NanumGothic.ttf", f"{home_dir}/Library/Fonts/NanumGothicBold.ttf"),
        ("/Library/Fonts/NanumGothic.ttf", "/Library/Fonts/NanumGothicBold.ttf"),
        # Noto Sans KR
        (f"{home_dir}/Library/Fonts/NotoSansKR-Regular.ttf", f"{home_dir}/Library/Fonts/NotoSansKR-Bold.ttf"),
        ("/Library/Fonts/NotoSansKR-Regular.ttf", "/Library/Fonts/NotoSansKR-Bold.ttf"),
        # Apple SD Gothic Neo
        ("/System/Library/Fonts/Supplemental/AppleSDGothicNeo-Regular.otf", "/System/Library/Fonts/Supplemental/AppleSDGothicNeo-Bold.otf"),
        ("/System/Library/Fonts/AppleSDGothicNeo.ttc", "/System/Library/Fonts/AppleSDGothicNeo.ttc"),
        # AppleGothic fallback
        ("/System/Library/Fonts/Supplemental/AppleGothic.ttf", "/System/Library/Fonts/Supplemental/AppleGothic.ttf"),
        ("/Library/Fonts/AppleGothic.ttf", "/Library/Fonts/AppleGothic.ttf"),
    ]
    
    korean_font_name = "KoreanFont"
    korean_font_bold_name = "KoreanFont-Bold"
    
    for normal_path, bold_path in korean_font_candidates:
        if os.path.exists(normal_path):
            try:
                pdfmetrics.registerFont(TTFont(korean_font_name, normal_path))
                
                bold_registered = False
                if os.path.exists(bold_path) and bold_path != normal_path:
                    try:
                        pdfmetrics.registerFont(TTFont(korean_font_bold_name, bold_path))
                        bold_registered = True
                    except Exception:
                        pass
                
                if not bold_registered:
                    try:
                        pdfmetrics.registerFont(TTFont(korean_font_bold_name, normal_path))
                    except Exception:
                        korean_font_bold_name = korean_font_name
                
                pdfmetrics.registerFontFamily(
                    korean_font_name,
                    normal=korean_font_name,
                    bold=korean_font_bold_name
                )
                return korean_font_name, korean_font_bold_name
            except Exception:
                continue
    
    # Fallback to Variable Font
    variable_font_paths = [
        f"{home_dir}/Library/Fonts/NotoSansKR-VariableFont_wght.ttf",
        "/Library/Fonts/NotoSansKR-VariableFont_wght.ttf",
    ]
    
    for font_path in variable_font_paths:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont(korean_font_name, font_path))
                pdfmetrics.registerFont(TTFont(korean_font_bold_name, font_path))
                pdfmetrics.registerFontFamily(
                    korean_font_name,
                    normal=korean_font_name,
                    bold=korean_font_bold_name
                )
                return korean_font_name, korean_font_bold_name
            except Exception:
                continue
    
    # Final fallback: Helvetica
    print("[WARNING] Korean font not found, using Helvetica (Korean characters may not display)", file=sys.stderr)
    return "Helvetica", "Helvetica-Bold"


def create_styles(korean_font: str, korean_font_bold: str):
    """Create PDF styles for the guide."""
    styles = getSampleStyleSheet()
    
    custom_styles = {
        "title": ParagraphStyle(
            "CustomTitle",
            parent=styles["Title"],
            fontSize=24,
            textColor=colors.HexColor("#1a365d"),
            spaceAfter=30,
            spaceBefore=20,
            alignment=TA_CENTER,
            fontName=korean_font_bold,
        ),
        "subtitle": ParagraphStyle(
            "CustomSubtitle",
            parent=styles["Normal"],
            fontSize=12,
            textColor=colors.HexColor("#4a5568"),
            spaceAfter=40,
            alignment=TA_CENTER,
            fontName=korean_font,
        ),
        "h1": ParagraphStyle(
            "CustomH1",
            parent=styles["Heading1"],
            fontSize=18,
            textColor=colors.HexColor("#2c5282"),
            spaceAfter=12,
            spaceBefore=24,
            fontName=korean_font_bold,
        ),
        "h2": ParagraphStyle(
            "CustomH2",
            parent=styles["Heading2"],
            fontSize=14,
            textColor=colors.HexColor("#2d3748"),
            spaceAfter=8,
            spaceBefore=16,
            fontName=korean_font_bold,
        ),
        "h3": ParagraphStyle(
            "CustomH3",
            parent=styles["Heading3"],
            fontSize=12,
            textColor=colors.HexColor("#4a5568"),
            spaceAfter=6,
            spaceBefore=12,
            fontName=korean_font_bold,
        ),
        "body": ParagraphStyle(
            "CustomBody",
            parent=styles["Normal"],
            fontSize=11,
            textColor=colors.black,
            spaceAfter=8,
            alignment=TA_JUSTIFY,
            fontName=korean_font,
            leading=16,
        ),
        "bullet": ParagraphStyle(
            "CustomBullet",
            parent=styles["Normal"],
            fontSize=11,
            textColor=colors.black,
            spaceAfter=4,
            leftIndent=20,
            fontName=korean_font,
            leading=15,
        ),
        "sub_bullet": ParagraphStyle(
            "CustomSubBullet",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#4a5568"),
            spaceAfter=3,
            leftIndent=40,
            fontName=korean_font,
            leading=14,
        ),
        "tip": ParagraphStyle(
            "CustomTip",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#2f855a"),
            spaceAfter=8,
            spaceBefore=8,
            leftIndent=15,
            rightIndent=15,
            fontName=korean_font,
            backColor=colors.HexColor("#f0fff4"),
            borderPadding=8,
            leading=14,
        ),
        "warning": ParagraphStyle(
            "CustomWarning",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#c53030"),
            spaceAfter=8,
            spaceBefore=8,
            leftIndent=15,
            rightIndent=15,
            fontName=korean_font,
            backColor=colors.HexColor("#fff5f5"),
            borderPadding=8,
            leading=14,
        ),
        "footer": ParagraphStyle(
            "CustomFooter",
            parent=styles["Normal"],
            fontSize=9,
            textColor=colors.HexColor("#718096"),
            alignment=TA_CENTER,
            fontName=korean_font,
        ),
        "code": ParagraphStyle(
            "CustomCode",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#2d3748"),
            spaceAfter=6,
            leftIndent=20,
            fontName="Courier",
            backColor=colors.HexColor("#edf2f7"),
            leading=14,
        ),
        "table_header": ParagraphStyle(
            "CustomTableHeader",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.white,
            alignment=TA_CENTER,
            fontName=korean_font_bold,
        ),
        "table_cell": ParagraphStyle(
            "CustomTableCell",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.black,
            alignment=TA_LEFT,
            fontName=korean_font,
            leading=13,
        ),
    }
    
    return styles, custom_styles


def build_title_page(story, styles):
    """Build the title page."""
    story.append(Spacer(1, 3 * cm))
    
    story.append(Paragraph("MeducAI", styles["title"]))
    story.append(Paragraph("Anki 사용 설명서", styles["title"]))
    
    story.append(Spacer(1, 1 * cm))
    
    story.append(Paragraph(
        "영상의학과 전공의를 위한<br/>스마트 학습 가이드",
        styles["subtitle"]
    ))
    
    story.append(Spacer(1, 3 * cm))
    
    # Table of contents preview
    toc_items = [
        "1. Anki란?",
        "2. Anki 설치 방법",
        "3. 덱 가져오기 방법",
        "4. 추천 학습 설정",
        "5. 분과별 덱 활용법",
        "6. 통계 및 학습 진도 관리",
        "7. 자주 묻는 질문 (FAQ)",
    ]
    
    for item in toc_items:
        story.append(Paragraph(item, styles["body"]))
    
    story.append(Spacer(1, 2 * cm))
    story.append(Paragraph("MeducAI Research Team", styles["footer"]))
    
    # Page break after title page (Section 1 starts on new page)
    story.append(PageBreak())


def build_section_intro(story, styles):
    """Build Section 1: Introduction to Anki."""
    story.append(Paragraph("1. Anki란?", styles["h1"]))
    
    story.append(Paragraph(
        "Anki는 과학적으로 검증된 <b>간격 반복(Spaced Repetition)</b> 알고리즘을 사용하는 "
        "무료 오픈소스 플래시카드 프로그램입니다. 의학교육에서 널리 사용되며, "
        "특히 영상의학과 전공의 학습에 매우 효과적입니다.",
        styles["body"]
    ))
    
    story.append(Paragraph("1.1 왜 Anki인가?", styles["h2"]))
    
    benefits = [
        "<b>망각 곡선 극복</b>: 에빙하우스 망각 곡선에 기반하여 최적의 복습 시점을 자동 계산",
        "<b>개인화된 학습</b>: 각 카드에 대한 본인의 이해도에 따라 복습 주기가 조절됨",
        "<b>멀티 플랫폼</b>: PC, Mac, iOS, Android 모든 기기에서 동기화하여 사용 가능",
        "<b>무료 & 오픈소스</b>: 완전 무료로 사용 가능 (AnkiMobile iOS는 유료)",
        "<b>이미지 지원</b>: 영상의학과 학습에 필수적인 이미지 기반 카드 완벽 지원",
    ]
    
    for benefit in benefits:
        story.append(Paragraph(f"• {benefit}", styles["bullet"]))
    
    story.append(Spacer(1, 0.5 * cm))
    
    story.append(Paragraph(
        "💡 <b>Tip</b>: 매일 꾸준히 10-20분씩 학습하는 것이 한 번에 몰아서 공부하는 것보다 "
        "기억 정착에 훨씬 효과적입니다.",
        styles["tip"]
    ))
    
    # Section divider
    story.append(Spacer(1, 1.5 * cm))


def build_section_installation(story, styles):
    """Build Section 2: Installation Guide."""
    story.append(Paragraph("2. Anki 설치 방법", styles["h1"]))
    
    story.append(Paragraph(
        "Anki는 모든 주요 플랫폼에서 사용할 수 있습니다. 아래 플랫폼별 설치 가이드를 따라주세요.",
        styles["body"]
    ))
    
    # Windows
    story.append(Paragraph("2.1 Windows", styles["h2"]))
    steps_windows = [
        "공식 웹사이트 접속: <b>https://apps.ankiweb.net</b>",
        "'Download' 버튼 클릭 후 Windows 버전 다운로드",
        "다운로드된 설치 파일(.exe) 실행",
        "설치 마법사의 안내에 따라 설치 완료",
        "바탕화면 또는 시작 메뉴에서 Anki 실행",
    ]
    for i, step in enumerate(steps_windows, 1):
        story.append(Paragraph(f"{i}. {step}", styles["bullet"]))
    
    # Mac
    story.append(Paragraph("2.2 macOS", styles["h2"]))
    steps_mac = [
        "공식 웹사이트 접속: <b>https://apps.ankiweb.net</b>",
        "'Download' 버튼 클릭 후 macOS 버전 다운로드 (Intel 또는 Apple Silicon 선택)",
        "다운로드된 .dmg 파일 열기",
        "Anki 아이콘을 Applications 폴더로 드래그",
        "Launchpad 또는 Applications에서 Anki 실행",
    ]
    for i, step in enumerate(steps_mac, 1):
        story.append(Paragraph(f"{i}. {step}", styles["bullet"]))
    
    story.append(Paragraph(
        "⚠️ <b>주의</b>: macOS에서 처음 실행 시 '확인되지 않은 개발자' 경고가 나올 수 있습니다. "
        "'시스템 환경설정 > 보안 및 개인정보 보호'에서 '확인 없이 열기'를 클릭하세요.",
        styles["warning"]
    ))
    
    # iOS
    story.append(Paragraph("2.3 iOS (iPhone/iPad)", styles["h2"]))
    steps_ios = [
        "App Store에서 'AnkiMobile Flashcards' 검색",
        "앱 구매 및 다운로드 (유료: $24.99)",
        "앱 실행 후 AnkiWeb 계정으로 로그인 (동기화용)",
    ]
    for i, step in enumerate(steps_ios, 1):
        story.append(Paragraph(f"{i}. {step}", styles["bullet"]))
    
    story.append(Paragraph(
        "💡 <b>Tip</b>: iOS 앱은 유료이지만, Anki 개발 지원과 함께 가장 안정적인 모바일 경험을 제공합니다. "
        "무료 대안으로 AnkiWeb(웹 브라우저)도 사용 가능합니다.",
        styles["tip"]
    ))
    
    # Android
    story.append(Paragraph("2.4 Android", styles["h2"]))
    steps_android = [
        "Google Play Store에서 'AnkiDroid Flashcards' 검색",
        "무료 다운로드 및 설치",
        "앱 실행 후 AnkiWeb 계정으로 로그인 (동기화용)",
    ]
    for i, step in enumerate(steps_android, 1):
        story.append(Paragraph(f"{i}. {step}", styles["bullet"]))
    
    story.append(Spacer(1, 0.5 * cm))
    
    # AnkiWeb Account
    story.append(Paragraph("2.5 AnkiWeb 계정 생성 (필수)", styles["h2"]))
    story.append(Paragraph(
        "여러 기기에서 학습 진도를 동기화하려면 AnkiWeb 계정이 필요합니다.",
        styles["body"]
    ))
    
    steps_web = [
        "<b>https://ankiweb.net</b> 접속",
        "'Sign Up' 클릭하여 무료 계정 생성",
        "이메일 인증 완료",
        "Anki 앱에서 '동기화' 버튼 클릭 후 로그인",
    ]
    for i, step in enumerate(steps_web, 1):
        story.append(Paragraph(f"{i}. {step}", styles["bullet"]))
    
    # Section divider
    story.append(Spacer(1, 1.5 * cm))


def build_section_import(story, styles):
    """Build Section 3: Importing Decks."""
    story.append(Paragraph("3. 덱 가져오기 방법", styles["h1"]))
    
    story.append(Paragraph(
        "MeducAI에서 제공하는 .apkg 파일을 Anki로 가져오는 방법입니다.",
        styles["body"]
    ))
    
    # Desktop
    story.append(Paragraph("3.1 PC/Mac에서 가져오기", styles["h2"]))
    steps_desktop = [
        "Anki 프로그램 실행",
        "메뉴에서 '파일(File)' → '가져오기(Import)' 클릭",
        "MeducAI에서 제공받은 .apkg 파일 선택",
        "'열기(Open)' 클릭",
        "가져오기 완료 메시지 확인",
    ]
    for i, step in enumerate(steps_desktop, 1):
        story.append(Paragraph(f"{i}. {step}", styles["bullet"]))
    
    story.append(Paragraph(
        "💡 <b>Tip</b>: .apkg 파일을 더블클릭하면 자동으로 Anki가 열리면서 가져오기가 됩니다.",
        styles["tip"]
    ))
    
    # Mobile
    story.append(Paragraph("3.2 모바일에서 가져오기", styles["h2"]))
    
    story.append(Paragraph("<b>iOS (AnkiMobile):</b>", styles["h3"]))
    steps_ios = [
        ".apkg 파일을 이메일, 클라우드 등으로 iPhone/iPad에 전송",
        "파일 앱에서 .apkg 파일 탭",
        "'공유' → 'AnkiMobile에서 열기' 선택",
        "가져오기 완료 확인",
    ]
    for i, step in enumerate(steps_ios, 1):
        story.append(Paragraph(f"{i}. {step}", styles["sub_bullet"]))
    
    story.append(Paragraph("<b>Android (AnkiDroid):</b>", styles["h3"]))
    steps_android = [
        ".apkg 파일을 기기의 Downloads 폴더에 저장",
        "AnkiDroid 앱 실행",
        "메뉴 (≡) → '가져오기' 선택",
        ".apkg 파일 선택 후 가져오기",
    ]
    for i, step in enumerate(steps_android, 1):
        story.append(Paragraph(f"{i}. {step}", styles["sub_bullet"]))
    
    # Available Decks
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph("3.3 제공되는 덱 목록", styles["h2"]))
    story.append(Paragraph(
        "MeducAI에서는 다음과 같은 덱을 제공합니다:",
        styles["body"]
    ))
    
    # Create a table for decks
    deck_data = [
        [Paragraph("<b>덱 이름</b>", styles["table_header"]),
         Paragraph("<b>카드 수</b>", styles["table_header"]),
         Paragraph("<b>설명</b>", styles["table_header"])],
        [Paragraph("MeducAI_FINAL_ALL", styles["table_cell"]),
         Paragraph("6,000", styles["table_cell"]),
         Paragraph("전체 통합 덱", styles["table_cell"])],
        [Paragraph("MeducAI_thoracic", styles["table_cell"]),
         Paragraph("~550", styles["table_cell"]),
         Paragraph("흉부영상의학", styles["table_cell"])],
        [Paragraph("MeducAI_abdominal", styles["table_cell"]),
         Paragraph("~550", styles["table_cell"]),
         Paragraph("복부영상의학", styles["table_cell"])],
        [Paragraph("MeducAI_neuro", styles["table_cell"]),
         Paragraph("~550", styles["table_cell"]),
         Paragraph("신경영상의학", styles["table_cell"])],
        [Paragraph("MeducAI_musculoskeletal", styles["table_cell"]),
         Paragraph("~550", styles["table_cell"]),
         Paragraph("근골격영상의학", styles["table_cell"])],
        [Paragraph("... (총 11개 분과)", styles["table_cell"]),
         Paragraph("-", styles["table_cell"]),
         Paragraph("분과별 개별 덱 제공", styles["table_cell"])],
    ]
    
    deck_table = Table(deck_data, colWidths=[5.5*cm, 2.5*cm, 6*cm])
    deck_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2c5282")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e0")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7fafc")]),
    ]))
    story.append(deck_table)
    
    # Section divider
    story.append(Spacer(1, 1.5 * cm))


def build_section_settings(story, styles):
    """Build Section 4: Recommended Settings."""
    story.append(Paragraph("4. 추천 학습 설정", styles["h1"]))
    
    story.append(Paragraph(
        "효과적인 학습을 위해 다음 설정을 권장합니다.",
        styles["body"]
    ))
    
    # Daily limits
    story.append(Paragraph("4.1 일일 학습량 설정", styles["h2"]))
    story.append(Paragraph(
        "덱 옵션에서 일일 학습량을 설정할 수 있습니다.",
        styles["body"]
    ))
    
    story.append(Paragraph("<b>설정 방법:</b>", styles["h3"]))
    steps_settings = [
        "메인 화면에서 덱 이름 옆 톱니바퀴 아이콘 클릭",
        "'옵션(Options)' 선택",
        "'새 카드(New Cards)' 탭에서 설정 조정",
    ]
    for i, step in enumerate(steps_settings, 1):
        story.append(Paragraph(f"{i}. {step}", styles["bullet"]))
    
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("<b>권장 설정값:</b>", styles["h3"]))
    
    settings_data = [
        [Paragraph("<b>설정 항목</b>", styles["table_header"]),
         Paragraph("<b>권장값</b>", styles["table_header"]),
         Paragraph("<b>설명</b>", styles["table_header"])],
        [Paragraph("새 카드/일", styles["table_cell"]),
         Paragraph("50~100", styles["table_cell"]),
         Paragraph("하루에 학습할 새로운 카드 수", styles["table_cell"])],
        [Paragraph("최대 복습/일", styles["table_cell"]),
         Paragraph("200~300", styles["table_cell"]),
         Paragraph("하루 최대 복습 카드 수", styles["table_cell"])],
        [Paragraph("학습 단계", styles["table_cell"]),
         Paragraph("1 10 60", styles["table_cell"]),
         Paragraph("1분, 10분, 60분 간격으로 반복", styles["table_cell"])],
        [Paragraph("졸업 간격", styles["table_cell"]),
         Paragraph("1일", styles["table_cell"]),
         Paragraph("첫 복습까지의 간격", styles["table_cell"])],
        [Paragraph("쉬움 간격", styles["table_cell"]),
         Paragraph("4일", styles["table_cell"]),
         Paragraph("'쉬움' 선택 시 간격", styles["table_cell"])],
    ]
    
    settings_table = Table(settings_data, colWidths=[4*cm, 3*cm, 7*cm])
    settings_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2c5282")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e0")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7fafc")]),
    ]))
    story.append(settings_table)
    
    # Random order
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph("4.2 랜덤 순서 학습", styles["h2"]))
    story.append(Paragraph(
        "카드를 랜덤 순서로 학습하면 더 효과적입니다.",
        styles["body"]
    ))
    
    random_steps = [
        "덱 옵션에서 '새 카드(New Cards)' 탭 선택",
        "'삽입 순서(Insertion Order)' → '무작위(Random)' 설정",
        "또는 '새 카드 순서' → '무작위' 설정",
    ]
    for i, step in enumerate(random_steps, 1):
        story.append(Paragraph(f"{i}. {step}", styles["bullet"]))
    
    # Answer buttons
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph("4.3 답변 버튼 이해하기", styles["h2"]))
    story.append(Paragraph(
        "카드를 복습할 때 4가지 버튼 중 하나를 선택합니다:",
        styles["body"]
    ))
    
    buttons_data = [
        [Paragraph("<b>버튼</b>", styles["table_header"]),
         Paragraph("<b>의미</b>", styles["table_header"]),
         Paragraph("<b>언제 선택?</b>", styles["table_header"])],
        [Paragraph("다시 (Again)", styles["table_cell"]),
         Paragraph("틀렸거나 기억 안남", styles["table_cell"]),
         Paragraph("전혀 기억이 나지 않을 때", styles["table_cell"])],
        [Paragraph("어려움 (Hard)", styles["table_cell"]),
         Paragraph("어렵게 기억함", styles["table_cell"]),
         Paragraph("힌트가 필요했거나 오래 걸렸을 때", styles["table_cell"])],
        [Paragraph("좋음 (Good)", styles["table_cell"]),
         Paragraph("적절하게 기억함", styles["table_cell"]),
         Paragraph("약간의 노력으로 기억했을 때", styles["table_cell"])],
        [Paragraph("쉬움 (Easy)", styles["table_cell"]),
         Paragraph("즉시, 확실히 기억", styles["table_cell"]),
         Paragraph("전혀 고민 없이 바로 알았을 때", styles["table_cell"])],
    ]
    
    buttons_table = Table(buttons_data, colWidths=[3.5*cm, 4*cm, 6.5*cm])
    buttons_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2c5282")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e0")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7fafc")]),
    ]))
    story.append(buttons_table)
    
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(
        "💡 <b>Tip</b>: '쉬움'을 너무 자주 누르면 복습 간격이 급격히 늘어나서 "
        "나중에 잊어버릴 수 있습니다. 정말 확실할 때만 사용하세요.",
        styles["tip"]
    ))
    
    # Section divider
    story.append(Spacer(1, 1.5 * cm))


def build_section_specialty(story, styles):
    """Build Section 5: Using Specialty Decks."""
    story.append(Paragraph("5. 분과별 덱 활용법", styles["h1"]))
    
    story.append(Paragraph(
        "MeducAI는 11개 분과별 개별 덱을 제공하여 "
        "약한 파트에 집중적으로 학습할 수 있습니다.",
        styles["body"]
    ))
    
    # Strategy 1
    story.append(Paragraph("5.1 약한 파트 집중 학습", styles["h2"]))
    story.append(Paragraph(
        "전체 덱으로 학습하다가 특정 분과의 정답률이 낮으면, "
        "해당 분과 덱만 따로 집중 학습하세요.",
        styles["body"]
    ))
    
    focus_steps = [
        "통계에서 정답률이 낮은 분과 파악 (5.6 참조)",
        "해당 분과의 개별 덱 가져오기",
        "일일 새 카드 수를 늘려서 집중 학습",
        "정답률이 개선되면 다시 전체 덱 위주로 복귀",
    ]
    for i, step in enumerate(focus_steps, 1):
        story.append(Paragraph(f"{i}. {step}", styles["bullet"]))
    
    # Strategy 2
    story.append(Paragraph("5.2 순차적 분과별 정복", styles["h2"]))
    story.append(Paragraph(
        "한 분과씩 완전히 마스터한 후 다음 분과로 넘어가는 전략입니다.",
        styles["body"]
    ))
    
    sequential_steps = [
        "첫 번째 분과 덱으로 시작 (예: 흉부영상의학)",
        "해당 덱의 모든 새 카드 학습 완료",
        "복습 카드가 안정화되면 (일일 복습 < 50) 다음 분과 추가",
        "점진적으로 분과를 확장",
    ]
    for i, step in enumerate(sequential_steps, 1):
        story.append(Paragraph(f"{i}. {step}", styles["bullet"]))
    
    # Specialties list
    story.append(Paragraph("5.3 분과 목록", styles["h2"]))
    
    specialties = [
        ("흉부영상의학", "thoracic", "폐, 심장, 종격동"),
        ("복부영상의학", "abdominal", "간담췌, 위장관, 비뇨생식"),
        ("신경영상의학", "neuro", "뇌, 척추, 두경부"),
        ("근골격영상의학", "musculoskeletal", "골관절, 연부조직"),
        ("유방영상의학", "breast", "유방초음파, 유방촬영"),
        ("소아영상의학", "pediatric", "소아특이질환"),
        ("혈관중재영상의학", "interventional", "혈관조영, 시술"),
        ("핵의학", "nuclear_medicine", "PET, SPECT, 갑상선"),
        ("응급영상의학", "emergency", "응급상황 영상판독"),
        ("종양영상의학", "oncology", "암 병기결정, 반응평가"),
        ("심장영상의학", "cardiac", "심장CT, 심장MRI"),
    ]
    
    spec_data = [
        [Paragraph("<b>분과명</b>", styles["table_header"]),
         Paragraph("<b>덱 접미사</b>", styles["table_header"]),
         Paragraph("<b>주요 내용</b>", styles["table_header"])],
    ]
    for kr_name, suffix, topics in specialties:
        spec_data.append([
            Paragraph(kr_name, styles["table_cell"]),
            Paragraph(f"_{suffix}", styles["table_cell"]),
            Paragraph(topics, styles["table_cell"]),
        ])
    
    spec_table = Table(spec_data, colWidths=[4.5*cm, 3.5*cm, 6*cm])
    spec_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2c5282")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
        ('TOPPADDING', (0, 1), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e0")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7fafc")]),
    ]))
    story.append(spec_table)
    
    # Section divider
    story.append(Spacer(1, 1.5 * cm))


def build_section_statistics(story, styles):
    """Build Section 6: Statistics and Progress."""
    story.append(Paragraph("6. 통계 및 학습 진도 관리", styles["h1"]))
    
    story.append(Paragraph(
        "Anki는 강력한 통계 기능을 제공합니다. 정기적으로 통계를 확인하여 "
        "학습 효율을 최적화하세요.",
        styles["body"]
    ))
    
    # Accessing stats
    story.append(Paragraph("6.1 통계 화면 접근", styles["h2"]))
    stats_access = [
        "<b>PC/Mac</b>: 메뉴 → 도구(Tools) → 통계(Statistics) 또는 단축키 <b>Shift+S</b>",
        "<b>iOS</b>: 덱 선택 → 우측 상단 그래프 아이콘",
        "<b>Android</b>: 덱 선택 → 메뉴(⋮) → 통계",
    ]
    for item in stats_access:
        story.append(Paragraph(f"• {item}", styles["bullet"]))
    
    # Key metrics
    story.append(Paragraph("6.2 핵심 지표 이해", styles["h2"]))
    
    metrics = [
        ("<b>정답률(Correct %)</b>", "복습 시 정답을 맞힌 비율. 80% 이상 유지가 이상적"),
        ("<b>성숙 카드(Mature)</b>", "21일 이상 간격의 카드. 장기기억으로 정착된 카드"),
        ("<b>젊은 카드(Young)</b>", "21일 미만 간격. 아직 정착 중인 카드"),
        ("<b>새 카드(New)</b>", "아직 학습하지 않은 카드"),
        ("<b>일일 학습량</b>", "오늘 복습한 카드 수와 소요 시간"),
        ("<b>예측(Forecast)</b>", "향후 며칠간 예상 복습량"),
    ]
    for metric, desc in metrics:
        story.append(Paragraph(f"• {metric}: {desc}", styles["bullet"]))
    
    # Progress tracking
    story.append(Paragraph("6.3 학습 진도 추적", styles["h2"]))
    story.append(Paragraph(
        "효과적인 진도 관리를 위한 지표들입니다:",
        styles["body"]
    ))
    
    progress_items = [
        "<b>Streak (연속 학습일)</b>: 하루도 빠지지 않고 학습한 연속 일수",
        "<b>총 복습 횟수</b>: 지금까지 복습한 카드의 총 횟수",
        "<b>평균 학습 시간</b>: 하루 평균 학습에 소요된 시간",
        "<b>리텐션(Retention)</b>: 장기기억 정착률 (성숙 카드 정답률)",
    ]
    for item in progress_items:
        story.append(Paragraph(f"• {item}", styles["bullet"]))
    
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(
        "💡 <b>Tip</b>: 통계에서 '월간(Month)' 또는 '연간(Year)' 뷰로 전환하면 "
        "장기적인 학습 패턴을 확인할 수 있습니다.",
        styles["tip"]
    ))
    
    # Ideal targets
    story.append(Paragraph("6.4 이상적인 목표치", styles["h2"]))
    
    targets_data = [
        [Paragraph("<b>지표</b>", styles["table_header"]),
         Paragraph("<b>목표</b>", styles["table_header"]),
         Paragraph("<b>의미</b>", styles["table_header"])],
        [Paragraph("일일 학습량", styles["table_cell"]),
         Paragraph("150~250 카드", styles["table_cell"]),
         Paragraph("새 카드 + 복습 카드 합계", styles["table_cell"])],
        [Paragraph("정답률", styles["table_cell"]),
         Paragraph("≥ 80%", styles["table_cell"]),
         Paragraph("전체 정답률 기준", styles["table_cell"])],
        [Paragraph("성숙 카드 정답률", styles["table_cell"]),
         Paragraph("≥ 90%", styles["table_cell"]),
         Paragraph("장기기억 정착 기준", styles["table_cell"])],
        [Paragraph("일일 학습 시간", styles["table_cell"]),
         Paragraph("20~40분", styles["table_cell"]),
         Paragraph("집중력 유지 최적 시간", styles["table_cell"])],
    ]
    
    targets_table = Table(targets_data, colWidths=[4.5*cm, 3.5*cm, 6*cm])
    targets_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2c5282")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e0")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7fafc")]),
    ]))
    story.append(targets_table)
    
    # Section divider
    story.append(Spacer(1, 1.5 * cm))


def build_section_faq(story, styles):
    """Build Section 7: FAQ."""
    story.append(Paragraph("7. 자주 묻는 질문 (FAQ)", styles["h1"]))
    
    faqs = [
        (
            "Q: 하루를 빼먹으면 어떻게 되나요?",
            "밀린 복습 카드가 쌓이지만, Anki가 자동으로 우선순위를 조정합니다. "
            "가장 급한 카드부터 보여주므로 다음 날 평소보다 조금 더 학습하면 됩니다. "
            "한 번 빼먹었다고 포기하지 마세요!"
        ),
        (
            "Q: 카드가 너무 많아서 부담됩니다. 어떻게 하나요?",
            "새 카드 학습을 일시 중단하고 복습에만 집중하세요. "
            "덱 옵션에서 '새 카드/일'을 0으로 설정하면 됩니다. "
            "복습 카드가 줄어들면 다시 새 카드를 추가하세요."
        ),
        (
            "Q: 동기화가 안 됩니다.",
            "1) 인터넷 연결 확인<br/>"
            "2) AnkiWeb 로그인 상태 확인<br/>"
            "3) '동기화 충돌' 시 한쪽을 선택해야 합니다. 최신 데이터가 있는 쪽을 선택하세요."
        ),
        (
            "Q: 카드를 수정할 수 있나요?",
            "네! 카드 학습 중 '편집(Edit)' 버튼을 누르거나, "
            "브라우저(도구 → 찾아보기)에서 카드를 검색하여 수정할 수 있습니다."
        ),
        (
            "Q: 특정 카드만 다시 학습하고 싶어요.",
            "브라우저에서 해당 카드를 찾아 우클릭 → '학습 재설정(Forget)' 또는 "
            "'카드 일정 변경(Reschedule)'을 선택하세요."
        ),
        (
            "Q: 이미지가 안 보입니다.",
            "1) 이미지 파일이 미디어 폴더에 있는지 확인<br/>"
            "2) 도구 → 미디어 확인(Check Media)으로 누락 파일 점검<br/>"
            "3) 동기화 후 '미디어 동기화'까지 완료되었는지 확인"
        ),
        (
            "Q: 백업은 어떻게 하나요?",
            "Anki는 자동으로 백업합니다. 수동 백업은 파일 → 내보내기(Export)에서 "
            "'Anki 덱 패키지(.apkg)'로 저장하면 됩니다."
        ),
    ]
    
    for question, answer in faqs:
        story.append(Paragraph(question, styles["h3"]))
        story.append(Paragraph(f"A: {answer}", styles["body"]))
        story.append(Spacer(1, 0.3 * cm))
    
    # Final tips
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph("마무리 Tips", styles["h2"]))
    
    final_tips = [
        "🎯 <b>매일 조금씩</b>: 10분이라도 매일 하는 것이 주 1회 2시간보다 효과적",
        "📱 <b>자투리 시간 활용</b>: 출퇴근, 점심시간에 모바일로 복습",
        "🔄 <b>꾸준한 동기화</b>: 학습 후 항상 동기화 버튼 클릭",
        "📊 <b>주간 통계 점검</b>: 매주 통계를 확인하여 학습 패턴 개선",
        "💪 <b>포기하지 않기</b>: 밀리더라도 조금씩 따라잡으면 됩니다",
    ]
    for tip in final_tips:
        story.append(Paragraph(tip, styles["bullet"]))
    
    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph(
        "문의사항이 있으시면 MeducAI 연구팀으로 연락해 주세요.",
        styles["footer"]
    ))
    story.append(Paragraph(
        "MeducAI Research Team | https://meducai.io",
        styles["footer"]
    ))


def generate_anki_guide_pdf(out_dir: Path) -> Path:
    """Generate the Anki Guide PDF."""
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = out_dir / "Anki_Guide.pdf"
    
    # Register fonts
    korean_font, korean_font_bold = register_korean_font()
    print(f"[Anki Guide] Using fonts: {korean_font}, {korean_font_bold}")
    
    # Create styles
    _, custom_styles = create_styles(korean_font, korean_font_bold)
    
    # Create document
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    
    story = []
    
    # Build sections
    print("[Anki Guide] Building title page...")
    build_title_page(story, custom_styles)
    
    print("[Anki Guide] Building Section 1: Introduction...")
    build_section_intro(story, custom_styles)
    
    print("[Anki Guide] Building Section 2: Installation...")
    build_section_installation(story, custom_styles)
    
    print("[Anki Guide] Building Section 3: Import...")
    build_section_import(story, custom_styles)
    
    print("[Anki Guide] Building Section 4: Settings...")
    build_section_settings(story, custom_styles)
    
    print("[Anki Guide] Building Section 5: Specialty Decks...")
    build_section_specialty(story, custom_styles)
    
    print("[Anki Guide] Building Section 6: Statistics...")
    build_section_statistics(story, custom_styles)
    
    print("[Anki Guide] Building Section 7: FAQ...")
    build_section_faq(story, custom_styles)
    
    # Build PDF
    print(f"[Anki Guide] Generating PDF: {pdf_path}")
    doc.build(story)
    
    print(f"[Anki Guide] ✓ Successfully created: {pdf_path}")
    return pdf_path


def main():
    parser = argparse.ArgumentParser(
        description="Generate MeducAI Anki Usage Guide PDF",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
    python 3_Code/src/tools/docs/generate_anki_guide_pdf.py --out_dir 6_Distributions

Output:
    6_Distributions/Anki_Guide.pdf
        """,
    )
    
    parser.add_argument(
        "--out_dir",
        type=str,
        default="6_Distributions/MeducAI_Final_Share",
        help="Output directory for the PDF (default: 6_Distributions/MeducAI_Final_Share)",
    )
    parser.add_argument(
        "--base_dir",
        type=str,
        default=".",
        help="Project base directory (default: current directory)",
    )
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir).resolve()
    out_dir = base_dir / args.out_dir if not Path(args.out_dir).is_absolute() else Path(args.out_dir)
    
    pdf_path = generate_anki_guide_pdf(out_dir)
    print(f"\n[Anki Guide] PDF generated at: {pdf_path}")


if __name__ == "__main__":
    main()

