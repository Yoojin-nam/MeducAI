# MeducAI Cover Image Generation Prompt

## 이미지 사양

- **파일명**: `cover_base.jpg`
- **해상도**: 최소 1920 × 1080 px (고해상도 권장, 자동 center-crop됨)
- **비율**: 16:9 (landscape)
- **저장 위치**: `3_Code/src/tools/assets/cover_base.jpg`
- **⚠️ 중요**: 이미지에 텍스트 없이 순수 배경/그래픽만 생성 (MeducAI 제목과 분과명은 PDF 생성 시 오버레이)

---

## 🎨 복사해서 바로 사용하세요

### Gemini / ChatGPT용 (복사 후 바로 붙여넣기)

```
Generate an image: Professional medical radiology textbook cover design. Dark navy blue to ocean blue gradient background. Abstract floating CT scan slices and MRI brain images in artistic arrangement. NO TEXT AT ALL. Clean empty space at top center for title overlay. Clean empty space at bottom third for subtitle. 16:9 landscape ratio. Modern minimalist academic style. High resolution.
```

### Midjourney용 (복사 후 /imagine에 붙여넣기)

```
professional medical radiology textbook cover, dark navy blue to ocean blue gradient, abstract floating CT and MRI brain scan slices, NO TEXT, empty top center for title, empty bottom third area, modern minimalist academic design, no watermarks, high resolution --ar 16:9 --v 6 --q 2
```

### DALL-E 3 / ChatGPT 이미지용 (간결 버전)

```
Medical textbook cover with navy-to-blue gradient. Floating abstract CT and MRI brain scan visualizations. NO TEXT OR LETTERS. Empty space at top and bottom for text overlay. Landscape 16:9, minimalist professional style, high resolution.
```

### 초간단 버전 (안될 경우 이것만 사용)

```
Medical radiology textbook cover, navy blue gradient, floating brain MRI scans, NO TEXT, minimalist, 16:9 landscape, high resolution
```

---

## 디자인 참고

- **배경**: Deep Navy `#1B3A5F` → Ocean Blue `#4A90D9` 그라데이션
- **이미지 내용**: CT/MRI 영상의 추상적 시각화
- **⚠️ 텍스트 없음**: 모든 텍스트는 PDF 생성 시 오버레이됨

```
┌──────────────────────────────────────────────────────────────┐
│    ← MeducAI 제목 오버레이 영역 (PDF에서 추가) →            │
│                                                              │
│          (추상적 CT/MRI 영상 시각화)                         │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│    ← 분과명 텍스트 오버레이 영역 (PDF에서 추가) →           │
└──────────────────────────────────────────────────────────────┘
```

### PDF 렌더링 시 추가되는 요소

1. **상단**: "MeducAI" 대형 타이틀 (반투명 배경 위 흰색 텍스트)
2. **하단 1/3**: 분과명 영문 텍스트 (예: "Neuro & Head-Neck Imaging")

---

## 생성 후 처리

1. 이미지 다운로드 (고해상도 유지)
2. **리사이즈 불필요** - PDF 생성 시 자동 center-crop 처리
3. `cover_base.jpg`로 저장 → 이 폴더(`assets/`)에 배치

---

## 체크리스트

- [ ] AI 도구로 이미지 생성
- [ ] **텍스트가 전혀 없는지** 확인
- [ ] 16:9 가로 비율 확인
- [ ] 상단과 하단에 오버레이 공간 있는지 확인
- [ ] `cover_base.jpg`로 저장 완료

