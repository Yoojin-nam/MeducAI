# Stage Separation 테스트 결과 리포트

**RUN_TAG**: `TEST_STAGE_SEP_20251219_155318`

---

## Stage 1 (S1) 출력 결과

### Arm A

- **Group ID**: `d2da903bffbe2cd6`
- **Visual Type**: `Pathology_Pattern`
- **Entity Count**: 14

**Entities (first 5):**
  1. `Bone Destruction Patterns` (ID: `DERIVED:dfb0a9b7e48f`)
  2. `Enchondroma` (ID: `DERIVED:a1990fad058f`)
  3. `Osteochondroma` (ID: `DERIVED:36d795361cc8`)
  4. `Chondroblastoma` (ID: `DERIVED:f6d5a00b970b`)
  5. `Conventional Chondrosarcoma` (ID: `DERIVED:46fd429aa278`)

**Master Table (preview):**
```markdown
| Entity name | 질환/개념 | 영상 소견 키워드 | 모달리티별 핵심 소견 | 병리·기전/특징 | 감별 질환 | 시험포인트 |
|---|---|---|---|---|---|---|
| Bone Destruction Patterns | 골 파괴 양상 | Geographic, Moth-eaten, Permeative | X-ray: 경계, 전이대; CT: 피질골/골수강 침범; MRI: 연부조직 침범 | 종양 성장 속도 및 침윤성 반영; 양성/악성 감별 중요 지표 | 양성 종양, 악성 종양, 감염, 외상 | 각 패턴의 특징적 소견 및 의미; 악성도 예측 |
| Enchondroma | 내연골종 | 연골성 석회화, 엽상 경계, 골수강 내 병변 | X-ray: 팝콘/고리형 석회화, 골수강 확장; MRI: T2 고신호, 석회화 저신호 | 양성 연골성 종양; 수지골/장골 간부 흔함; Ollier/Maffucci 증후군 다발성 | 저등급 연골육종, 골경색 | 석회화 양상; 악성 변화 감별 (통증, 크기 증가, 피질골 파괴) |
| Osteochondroma | 골연골종 | 골수강 연속성, 연골모자, 외골성 성장 | X-ray: 골수강과 연속된 골성 돌출; MRI: 연골모자 두께 측정 (악성 변화 지표) | 가장 흔한 양성 골종양; 성장판에서 기원; 연골모자 두께 2cm 이상 시 악성 변화 의심 | 골막 반응, 연골육종 (악성 변화 시) | 골수강 연속성; 연골모자 두께; 악성 변화 소견 |
| Chondroblastoma | 연골모세포종 | 골단부 병변, 석회화, 경화성 경계 | X-ray: 골단부 투과성 병변, 경화성 경계, 석회화; MRI: T2 고신호, 부종 | 양성 연골성 종양; 10-20대 호발; 골단부에 위치 | 거대세포종, 감염, 무혈성 괴사 | 특징적인 골단부 위치; 석회화 유무 |
| Conventional Chondrosarcoma | 연골육종 (재래형) | 엽상 종괴, 연골성 석회화, 피질골 파괴 | X-ray: 불규칙한 연골성 석회화, 골 파괴; CT: 석회화, 피질골 침범; MRI: T2 고신호, 엽상 패턴, 연부조직 침범 | 악성 연골성 종양; 40대 이상 호발; 골수강 내/외 발생; 통증 동반 | 내연골종 (악성 변화), 골경색 | 악성 변화 소견 (통증, 크기 증가, 피질골 파괴, 연부조직 침범) |
| Osteoma | 골종 | 치밀골성 병변, 부비동/두개골 | X-ray/CT: 균일한 고밀도 치밀골 병변, 주변 피질골과 연속성 | 양성 골 형성 종양; 주로 두개골, 부비동, 안와에 발생; Gardner 증후군과 연관 | 골성 골종, 골모세포종 (크기/위치 차이) | 특징적인 위치 (두개골, 부비동); 치밀골성 소견 |
| Osteoid Osteoma/Osteoblastoma | 유골골종/골모세포종 | Nidus, 반응성 경화, 통증 (야간 통증) | X-ray: Nidus (투과성/석회화), 주변 반응성 경화; CT: Nidus 명확히 확인; MRI: Nidus 주변 골수 부종 | 양성 골 형성 종양; 유골골종은 작고 통증 심함 (NSAIDs 반응); 골모세포종은 크고 척추 호발 | 골수염, 스트레스 골절, 골육종 (초기) | Nidus의 존재; 반응성 경화; 통증 양상; 크기 및 위치 차이 |
| Osteosarcoma (Conventional) | 골육종 (재래형) | Codman 삼각, Sunburst, Spiculated, 골막 반응 | X-ray: 골 파괴, 골막 반응 (Codman, Sunburst), 연부조직 종괴, 종양성 골 형성; CT: 골화 정도, 피질골 파괴; MRI: 골수강/연부조직 침범 범위 | 가장 흔한 원발성 악성 골종양; 10-20대 호발; 장골의 골간단부; 폐 전이 흔함 | Ewing 육종, 골수염, 골모세포종 (악성 변화) | 특징적인 골막 반응; 종양성 골 형성; 폐 전이 유무 |
| Fibrous Cortical Defect/Nonossifying Fibroma | 섬유성 피질 결손/비골화성 섬유종 | 피질골 편심성, 다엽성, 경화성 경계 | X-ray: 장골의 골간단부, 피질골에 위치한 투과성 병변, 경화성 경계; MRI: T1 저신호, T2 고신호 | 양성 섬유성 병변; 소아/청소년 호발; 대부분 무증상, 자연 소실; 비골화성 섬유종은 섬유성 피질 결손의 큰 형태 | 골수염, 골육종 (초기) | 특징적인 위치 (장골 골간단부 피질골); 자연 소실 경향 |
| Giant Cell Tumor | 거대세포종 | 골단부/골간단부, 피질골 팽창, 경계 불분명 | X-ray: 장골의 골단부/골간단부, 편심성 투과성 병변, 피질골 팽창, 경화성 경계 없음; MRI: T1 저신호, T2 고신호, 출혈 소견 | 국소적으로 공격적인 양성 종양; 20-40대 호발; 폐 전이 가능성; 재발률 높음 | 연골모세포종, 동맥류성 골낭종 | 특징적인 골단부 위치; 경계 불분명; 피질골 팽창 |
| Simple Bone Cyst (SBC) | 단순 골낭종 | Falling fragment sign, 중심성, 얇은 경계 | X-ray: 장골의 골간단부, 중심성 투과성 병변, 얇은 경화성 경계, 피질골 팽창; CT/MRI: 균일한 액체 신호, 얇은 벽 | 양성 골낭종; 소아/청소년 호발; 상완골/대퇴골 근위부; 병적 골절 흔함 | 동맥류성 골낭종, 섬유성 이형성증 | Falling fragment sign; 중심성 위치; 병적 골절 |
| Aneurysmal Bone Cyst (ABC) | 동맥류성 골낭종 | Fluid-fluid level, 팽창성, 다방성 | X-ray: 팽창성 투과성 병변, 얇은 피질골; MRI: Fluid-fluid level (가장 특징적), 다방성, T2 고신호 | 양성 골낭종; 10-20대 호발; 척추, 장골 골간단부; 혈액으로 채워진 공간 | 거대세포종, 단순 골낭종, 모세혈관 확장성 골육종 | Fluid-fluid level; 팽창성 병변; 다방성 |
| Ewing Sarcoma | 유잉 육종 | Onion skin, Hair-on-end, 골막 반응, 골수강 침범 | X-ray: 골수강 침범, 골막 반응 (onion skin, hair-on-end), 골 파괴; MRI: 광범위한 골수강 침범, 연부조직 종괴 | 악성 소원형세포 종양; 10-20대 호발; 장골 골간부/골간단부, 편평골; 전신 증상 동반 | 골수염, 골육종, 림프종 | 특징적인 골막 반응; 광범위한 골수강 침범; 연부조직 종괴; 전신 증상 |
... (truncated)
```

---

### Arm B

- **Group ID**: `d2da903bffbe2cd6`
- **Visual Type**: `Pathology_Pattern`
- **Entity Count**: 12

**Entities (first 5):**
  1. `Bone Destruction Patterns` (ID: `DERIVED:dfb0a9b7e48f`)
  2. `Osteochondroma` (ID: `DERIVED:36d795361cc8`)
  3. `Enchondroma` (ID: `DERIVED:a1990fad058f`)
  4. `Chondroblastoma` (ID: `DERIVED:f6d5a00b970b`)
  5. `Osteoid Osteoma/Osteoblastoma` (ID: `DERIVED:95c9938d118f`)

**Master Table (preview):**
```markdown
| Entity name | 질환/개념 | 영상 소견 키워드 | 모달리티별 핵심 소견 | 병리·기전/특징 | 감별 질환 | 시험포인트 |
|:---|:---|:---|:---|:---|:---|:---|
| Bone Destruction Patterns | 골 파괴 양상 | Geographic, Moth-eaten, Permeative | X-ray: 경계/전이대/피질 파괴 정도; CT: 피질 파괴 및 연부조직 침범 상세 | 양성/저악성도(Geographic), 중등도 악성(Moth-eaten), 고악성도(Permeative) 시사 | 양성 종양, 악성 종양, 감염, 대사성 질환 | 각 패턴의 특징 및 악성도 예측 |
| Osteochondroma | 골연골종 | Pedunculated/Sessile, Cartilage cap, Cortex/Medulla continuity | X-ray: 골수강과 연속성; MRI: 연골모자 두께 측정 (악성 변화) | 성장판에서 기원, 가장 흔한 양성 골종양. 연골모자 두께 2cm 이상 시 악성 변화 의심 | Parosteal osteosarcoma, Myositis ossificans | 골수강 연속성, 연골모자 두께, 악성 변화 소견 |
| Enchondroma | 내연골종 | Chondroid matrix, Popcorn/Arcs and rings calcification, Lobulated | X-ray: 골내 병변, 석회화; MRI: T2 고신호, 석회화에 의한 저신호 | 골수강 내 연골 형성 종양. 수지골/족지골 호발. Ollier/Maffucci 증후군 다발성 | Low-grade chondrosarcoma, Bone infarct | 석회화 양상, 위치, 악성 변화 감별 (통증, 피질 파괴, 연부조직 침범) |
| Chondroblastoma | 연골모세포종 | Epiphyseal/Apophyseal, Geographic, Sclerotic rim, Chondroid matrix | X-ray: 골단/골단판 병변, 석회화; MRI: T2 고신호, 주변 부종 | 드문 양성 연골 종양. 10-20대 호발. 관절 연골에 인접 | Giant cell tumor, Infection, Aneurysmal bone cyst | 특징적인 골단 위치, 주변 부종 |
| Osteoid Osteoma/Osteoblastoma | 유골골종/골모세포종 | Nidus, Sclerosis, Pain (nocturnal/aspirin-responsive for OO) | X-ray/CT: Nidus (중심부 투명대)와 주변 경화성 반응. CT가 Nidus 확인에 우수 | 유사한 병리, 크기 차이 (OO < 1.5-2cm, OB > 2cm). OO는 야간통/아스피린 반응 | Chronic osteomyelitis, Stress fracture, Brodie's abscess | Nidus의 특징, 크기 차이, 임상 증상 (특히 OO) |
| Conventional Osteosarcoma | 골육종 (재래형) | Sunburst/Codman triangle, Spiculated periosteal reaction, Osteoid matrix, Soft tissue mass | X-ray: 골형성/골파괴 혼합, 피질 파괴, 연부조직 침범; MRI: 골수 침범, 연부조직 범위 평가 | 가장 흔한 원발성 악성 골종양. 10-20대 호발. 골모세포에서 기원. 폐 전이 흔함 | Ewing sarcoma, Osteomyelitis, Chondrosarcoma | 특징적인 골막 반응, 골수강/연부조직 침범 범위, 폐 전이 |
| Ewing Sarcoma | 유잉 육종 | Onion skin periosteal reaction, Permeative destruction, Large soft tissue mass | X-ray: 양파껍질 골막 반응, 골파괴; MRI: 광범위한 골수 침범, 큰 연부조직 종괴 | 10대 이하 소아/청소년 호발. 신경외배엽 기원. 전이 흔함 | Osteomyelitis, Lymphoma, Neuroblastoma metastasis | 양파껍질 골막 반응, 광범위한 골수 침범, 큰 연부조직 종괴 |
| Giant Cell Tumor | 거대세포종 | Epiphyseal/Metaphyseal, Subarticular, Non-sclerotic margin, Expansile | X-ray: 골단/골간단 병변, 경화 변연 없음, 피질 팽창; MRI: T2 이질적 고신호, 출혈/액체-액체층 | 20-40대 호발. 국소 재발률 높음. 양성이나 공격적 행동 | Chondroblastoma, Aneurysmal bone cyst, Brown tumor | 특징적인 골단 위치, 경화 변연 없음, 재발 경향 |
| Simple Bone Cyst/Aneurysmal Bone Cyst | 단순골낭종/동맥류성골낭종 | Fluid-fluid levels (ABC), Fallen fragment sign (SBC), Expansile (ABC) | X-ray: 투명한 골내 병변; MRI: ABC에서 액체-액체층, SBC에서 Fallen fragment sign | SBC: 무증상, 병적 골절 후 발견; ABC: 혈액으로 채워진 낭종, 팽창성 | Chondroblastoma, Giant cell tumor, Telangiectatic osteosarcoma | 액체-액체층 (ABC), Fallen fragment sign (SBC), 위치 (SBC: 근위 상완골/대퇴골) |
| Langerhans Cell Histiocytosis | 랑게르한스세포 조직구증 | Beveled edge, Button sequestrum, Geographic destruction | X-ray: 천공성/지리적 골파괴, 두개골의 Beveled edge; MRI: 골수 부종, 연부조직 침범 | 소아 호발. 단일/다발성 병변. 염증성/종양성 특징 혼합 | Osteomyelitis, Ewing sarcoma, Metastasis | 두개골의 Beveled edge/Button sequestrum, 소아 호발, 다발성 병변 가능성 |
| Conventional Chondrosarcoma | 연골육종 (재래형) | Chondroid matrix, Popcorn/Arcs and rings calcification, Cortical destruction, Soft tissue mass | X-ray: 불규칙한 석회화, 피질 파괴; CT: 석회화 양상, 피질 파괴; MRI: T2 고신호, 연부조직 침범 | 40대 이상 호발. 연골에서 기원한 악성 종양. 내연골종의 악성 변화 가능 | Enchondroma, Bone infarct, Osteosarcoma | 내연골종과의 감별 (통증, 피질 파괴, 연부조직 침범, 병변 크기) |
| Fibrous Cortical Defect/Nonossifying Fibroma | 섬유성 피질 결손/비골화성 섬유종 | Eccentric, Sclerotic margin, Lobulated, Metaphyseal | X-ray: 장골의 편심성, 피질 병변, 경화성 변연 | 소아/청소년 흔한 양성 병변. 대부분 무증상, 자연 소실. FCD는 작은 형태, NOF는 큰 형태 | Chondromyxoid fibroma, Fibrous dysplasia | 특징적인 위치 (장골 골간단), 무증상, 자연 소실 |
```

---

### Arm C

- **Group ID**: `d2da903bffbe2cd6`
- **Visual Type**: `Pathology_Pattern`
- **Entity Count**: 12

**Entities (first 5):**
  1. `골 파괴 양상` (ID: `DERIVED:15c91ce38434`)
  2. `연골종 (Enchondroma)` (ID: `DERIVED:46461584e737`)
  3. `골연골종 (Osteochondroma)` (ID: `DERIVED:5de4be9b6d1c`)
  4. `연골모세포종 (Chondroblastoma)` (ID: `DERIVED:5682838b4f1e`)
  5. `골육종 (Osteosarcoma)` (ID: `DERIVED:74c3621ca944`)

**Master Table (preview):**
```markdown
| Entity name | 질환/개념 | 영상 소견 키워드 | 모달리티별 핵심 소견 | 병리·기전/특징 | 감별 질환 | 시험포인트 |
|:---|:---|:---|:---|:---|:---|:---|
| 골 파괴 양상 | 골 파괴 패턴 | Geographic/Moth-eaten/Permeative | X-ray: 경계 명확성, 전이대 | 종양의 침습성/성장 속도 반영 | 골수염, 낭종 | 악성도 예측 |
| 연골종 (Enchondroma) | 양성 연골성 종양 | 연골성 기질 석회화, lobulated | X-ray: 팝콘/고리형 석회화; MRI: 고신호 T2 | 성숙 연골 세포; 골수 내 위치 | 저등급 연골육종 | 악성 변환 감별 |
| 골연골종 (Osteochondroma) | 양성 골성 연골성 종양 | 피질골-골수 연속성, 연골모자 | X-ray: 골 외측 돌출; MRI: 연골모자 두께 | 성장판 연골의 이탈; 연골모자 | 골막 반응, 골화성 근염 | 연골모자 두께에 따른 악성 변환 |
| 연골모세포종 (Chondroblastoma) | 양성 연골성 종양 | 골단부, 편심성, 석회화 | X-ray: 골단부 투과성 병변; MRI: T2 저신호 | 미성숙 연골모세포; 골단부 호발 | 감염, 거대세포종 | 골단부 병변, T2 저신호 |
| 골육종 (Osteosarcoma) | 악성 골 형성 종양 | 조골성/용골성/혼합형, Codman 삼각형 | X-ray: 불규칙한 골막 반응, Sunburst; MRI: 골수 침범 | 미성숙 조골세포의 악성 증식 | Ewing 육종, 골수염 | 다양한 아형별 특징 |
| 섬유성 피질 결손/비골화성 섬유종 | 양성 섬유성 병변 | 피질골 내 투과성, 경화성 경계 | X-ray: 장골 피질골 내 타원형; MRI: T1/T2 저신호 | 섬유모세포 증식; 성장판 근처 | 골수염, 섬유성 이형성증 | 자연 소실 경향 |
| 거대세포종 (Giant Cell Tumor) | 양성/국소적 공격성 종양 | 골단-골간단, 비경화성 경계 | X-ray: 골단부 투과성, 피질골 팽창; MRI: T2 이질적 고신호 | 다핵 거대세포; 골단부 호발 | ABC, 갈색종 | 골단부, 비경화성, 국소 재발 |
| 단순 골낭종 (Simple Bone Cyst) | 양성 골 낭종 | 단방성, 얇은 경화성 경계 | X-ray: 장골 골간단부, Fallen fragment sign; MRI: T1 저/T2 고신호 | 액체 저류; 성장판 근처 | ABC, 섬유성 이형성증 | Fallen fragment sign, 무증상 |
| 동맥류성 골낭종 (Aneurysmal Bone Cyst) | 양성 골 낭종 | 다방성, fluid-fluid level | X-ray: 팽창성 투과성; MRI: T2 고신호, fluid-fluid level | 혈액 저류; 골막하/골수 내 | GCT, 혈관종 | Fluid-fluid level, 팽창성 |
| 랑게르한스세포 조직구증 (LCH) | 조직구 증식성 질환 | 용골성, Beveled edge, Floating tooth | X-ray: 천공성/지도형 용골성; MRI: T2 고신호, 조영 증강 | 랑게르한스세포 증식; 소아 호발 | 골수염, Ewing 육종 | Beveled edge, 다발성 병변 |
| Ewing 육종 | 악성 소원형세포 종양 | 양파껍질 골막 반응, 골수 침범 | X-ray: 골막 반응, 골수 침범; MRI: 광범위한 골수 부종 | 미분화 소원형세포; 골간단/골간부 | 골수염, 림프종 | 소아/청소년, 광범위한 골수 침범 |
| 골 림프종 | 악성 림프구 증식 | 용골성, 골막 반응, 골수 침범 | X-ray: 지도형/침윤성 용골성; MRI: T2 고신호, 조영 증강 | 림프구의 악성 증식; 고령 호발 | 골수염, Ewing 육종 | 고령, 다발성 병변, 골수 부종 |
```

---

### Arm D

- **Group ID**: `d2da903bffbe2cd6`
- **Visual Type**: `Pathology_Pattern`
- **Entity Count**: 10

**Entities (first 5):**
  1. `Bone Destruction Patterns` (ID: `DERIVED:dfb0a9b7e48f`)
  2. `Bone Tumor Location Patterns` (ID: `DERIVED:f520e2d728f6`)
  3. `Osteochondroma` (ID: `DERIVED:36d795361cc8`)
  4. `Enchondroma vs Chondrosarcoma` (ID: `DERIVED:bf6c96b02dbd`)
  5. `Osteoid Osteoma / Osteoblastoma` (ID: `DERIVED:78d969fa88be`)

**Master Table (preview):**
```markdown
| Entity name | 질환/개념 | 영상 소견 키워드 | 모달리티별 핵심 소견 | 병리·기전/특징 | 감별 질환 | 시험포인트 |
|:---|:---|:---|:---|:---|:---|:---|
| Bone Destruction Patterns | 골 파괴 양상 | Geographic, Moth-eaten, Permeative | X-ray: 경계 명확/불명확, 천공성 | 종양의 성장 속도 및 침윤성 반영 | 감염, 골수염, 대사성 질환 | 파괴 양상별 악성도 예측 |
| Bone Tumor Location Patterns | 골 종양 발생 위치/연령 패턴 | 장골의 종적/횡적 위치, 연령별 호발 | X-ray: 골단/골간단/골간, 피질/수질/골막 | 종양의 기원 세포 및 성장 특성 | 유사 연령/위치 호발 종양 | 연령, 위치 기반 감별 진단 |
| Osteochondroma | 골연골종 및 악성 변화 | 골수 연속성, 연골모자, Pedunculated/Sessile | X-ray: 피질골/수질골 연속성; MRI: 연골모자 두께 | 가장 흔한 양성 골종양, 연골모자 두꺼워지면 악성 변화 의심 | 골막 반응, 골화성 근염 | 연골모자 두께 측정, 악성 변화 감별 |
| Enchondroma vs Chondrosarcoma | 내연골종 vs 연골육종 (Conventional) | 팝콘 석회화, 고리/호 석회화, 피질골 미란/파괴 | X-ray: 내연골종(명확 경계), 연골육종(불명확 경계); MRI: T2 고신호, 조영 증강 | 내연골종은 양성, 연골육종은 악성 연골 형성 종양 | 골경색, 섬유성 이형성증 | 악성 변화 시사 소견 (통증, 크기 증가, 피질 파괴) |
| Osteoid Osteoma / Osteoblastoma | 유골골종 / 골모세포종 | Nidus, 반응성 경화, 통증 | X-ray: Nidus 내 석회화, 주변 경화; CT: Nidus 명확; MRI: 주변 부종 | Nidus 크기, 통증 양상 차이 (야간통/아스피린 반응) | 만성 골수염, 스트레스 골절 | Nidus 확인, 크기 및 주변 반응 |
| Osteosarcoma (Conventional) | 골육종 (Conventional) | Codman 삼각형, Sunburst, Hair-on-end, 종괴 형성 | X-ray: 골막 반응, 골 파괴; CT: 골화 정도; MRI: 골수 침범, 연부조직 확장 | 가장 흔한 원발성 악성 골종양, 조골세포 기원 | Ewing 육종, 골수염 | 골막 반응, 연부조직 침범 범위 |
| Ewing Sarcoma | Ewing 육종 | Onion skin, 골수 침범, 연부조직 종괴 | X-ray: 다층성 골막 반응, 골 파괴; MRI: 광범위한 골수 침범, 연부조직 종괴 | 소아/청소년 호발, 신경외배엽 기원 | 골수염, 림프종, 골육종 | 광범위한 골수 침범, 연부조직 종괴 |
| Giant Cell Tumor | 거대세포종 | 골단/골간단, 비경화성 경계, 피질골 팽창 | X-ray: 편심성, 비경화성 경계, 골단 침범; MRI: T2 저신호 (출혈/헤모시데린) | 성인 호발, 국소 재발률 높음, 악성 변화 가능 | 동맥류성 골낭종, 갈색종 | 골단 침범, 비경화성 경계 |
| Simple Bone Cyst / Aneurysmal Bone Cyst | 단순골낭종 / 동맥류성 골낭종 | Falling fragment sign, Fluid-fluid level, 팽창성 병변 | X-ray: 단순골낭종(중심성, 얇은 피질), 동맥류성 골낭종(팽창성); MRI: Fluid-fluid level | 단순골낭종(무증상, 병적 골절), 동맥류성 골낭종(혈액 저류) | 섬유성 이형성증, 거대세포종 | Fluid-fluid level 유무, 병변 내부 특성 |
| Langerhans Cell Histiocytosis | 랑게르한스 세포 조직구증 | Beveled edge, Button sequestrum, Vertebra plana | X-ray: 천공성 골 파괴, 골막 반응; CT: 골 파괴 양상; MRI: 골수 침범, 연부조직 종괴 | 소아 호발, 단일/다발성 병변, 염증성/종양성 특성 | 골수염, Ewing 육종, 전이암 | 두개골/척추 병변, Beveled edge sign |
```

---

### Arm E

- **Group ID**: `d2da903bffbe2cd6`
- **Visual Type**: `Pathology_Pattern`
- **Entity Count**: 14

**Entities (first 5):**
  1. `Bone Tumor Analysis Approach` (ID: `DERIVED:ad8e3b6a4d9f`)
  2. `Osteochondroma` (ID: `DERIVED:36d795361cc8`)
  3. `Enchondroma` (ID: `DERIVED:a1990fad058f`)
  4. `Chondrosarcoma` (ID: `DERIVED:6010ab5640e8`)
  5. `Chondroblastoma` (ID: `DERIVED:f6d5a00b970b`)

**Master Table (preview):**
```markdown
| Entity name | 질환/개념 | 영상 소견 키워드 | 모달리티별 핵심 소견 | 병리·기전/특징 | 감별 질환 | 시험포인트 |
|---|---|---|---|---|---|---|
| Bone Tumor Analysis Approach | 골종양 진단 접근 | Lodwick 분류; 골파괴 양상 | XR: 변연부/이행대 평가; MRI: 골수 침범 범위 | 나이/위치/매트릭스가 진단 핵심 | 감염; 대사성 질환 | Geographic vs Permeative; 나이별 호발 질환 |
| Osteochondroma | 골연골종 | 피질골/골수강 연결; 연골모(Cartilage cap) | XR: 줄기(Stalk) 확인; MRI: 연골모 두께 측정 | 성장판의 골간단부 이탈(Metaplasia) | Parosteal osteosarcoma | 모골(Parent bone)과의 연결성; 악성 변화 시사 소견(두께 >1.5cm) |
| Enchondroma | 내연골종 | Rings and arcs; 석회화 매트릭스 | XR: 중심성/석회화; MRI: T2 고신호/Lobulated | 투명 연골(Hyaline cartilage) 구성 | Bone infarct; Low-grade Chondrosarcoma | 손/발의 단골 호발; 통증 없어야 함(통증 시 악성 의심) |
| Chondrosarcoma | 연골육종 | Endosteal scalloping; 연부조직 종괴 | XR: 피질골 침식 깊이; MRI: 조영증강 패턴 | 성인 원발성 골암 2-3위 | Enchondroma | Scalloping > 2/3 두께; 통증; 연부조직 종괴 형성 |
| Chondroblastoma | 연골모세포종 | 골단(Epiphysis) 발생; 경화성 테두리 | XR: 얇은 경화 띠; MRI: 광범위한 골수 부종 | 미성숙 연골세포; Chicken-wire 석회화 | GCT; Clear cell chondrosarcoma | 골단판 닫히기 전 호발; 주위 부종 심함 |
| Osteoid Osteoma & Osteoblastoma | 유골골종 및 골모세포종 | Nidus(핵); 주변부 경화 | CT: 저음영 Nidus 확인; Bone Scan: Double density | 야간 통증(NSAID 반응); Prostaglandin | Stress fracture; Abscess | Nidus 크기 기준(1.5cm); 통증 양상 |
| Osteosarcoma | 골육종 | 구름 모양(Cloud-like) 골형성; Codman triangle | XR: Sunburst 골막반응; MRI: Skip metastasis | 10대 호발; 골모세포의 유골 형성 | Ewing sarcoma; Myositis ossificans | 골막 반응 양상; 전형적 골형성 매트릭스 |
| Giant Cell Tumor | 거대세포종 | 관절면 접촉(Abutting); 비경화성 변연 | XR: 편심성/비누거품 모양; MRI: T2 저신호(Hemosiderin) | 파골세포 유사 거대세포; 폐전이 가능 | ABC; Chondroblastoma | 골단판 폐쇄 후 발생; 관절면 침범 여부 |
| Simple Bone Cyst | 단순골낭종 | 중심성; Fallen fragment sign | XR: 골간단부 팽창성 병변; MRI: 단순 낭종 신호 | 장액성 액체 저류 | ABC | 병적 골절 후 Fallen fragment; 소아 상완골/대퇴골 |
| Aneurysmal Bone Cyst | 동맥류성골낭종 | 편심성; Fluid-fluid level | XR: 풍선 같은 팽창(Blow-out); MRI: 액체-액체 층 | 혈액 충만 공간; 1차성 또는 2차성 | Telangiectatic osteosarcoma | Fluid-fluid level(특이적이지 않음); 급격한 팽창 |
| Non-ossifying Fibroma | 비골화성 섬유종 | 편심성; 다방성(Loculated); 경화성 테두리 | XR: 골간단부에서 골간부로 이동 양상 | 저절로 경화/소실(Self-limiting) | Fibrous dysplasia | "Don't touch" lesion; 증상 없음; 나이 들며 경화 |
| Ewing Sarcoma | 유잉육종 | 투과성(Permeative); 양파껍질(Onion-skin) | XR: 광범위 골파괴; MRI: 거대 연부조직 종괴 | 소원형세포종양; t(11;22) | Osteomyelitis; LCH | 골간부(Diaphysis) 호발; 거대 종괴와 골파괴 불일치 |
| Langerhans Cell Histiocytosis | 랑게르한스세포 조직구증 | Beveled edge; Vertebra plana | XR: Punched-out 병변; CT: 두개골 내외판 침범 차이 | 호산구 육아종; 소아 호발 | Ewing sarcoma; Metastasis | 두개골/척추 특징적 소견; 부유 치아(Floating tooth) |
... (truncated)
```

---

### Arm F

- **Group ID**: `d2da903bffbe2cd6`
- **Visual Type**: `Pathology_Pattern`
- **Entity Count**: 16

**Entities (first 5):**
  1. `골파괴 패턴 Lodwick 분류` (ID: `DERIVED:234e9ead6061`)
  2. `연골종 Enchondroma` (ID: `DERIVED:4fca1347ac57`)
  3. `골연골종 Osteochondroma` (ID: `DERIVED:2403393507ae`)
  4. `골연골종 악성변형 소견` (ID: `DERIVED:526fa0749978`)
  5. `연골모세포종 Chondroblastoma` (ID: `DERIVED:5ed086d0a1e2`)

**Master Table (preview):**
```markdown
| Entity name | 질환/개념 | 영상 소견 키워드 | 모달리티별 핵심 소견 | 병리·기전/특징 | 감별 질환 | 시험포인트 |
| --- | --- | --- | --- | --- | --- | --- |
| 골파괴 패턴 Lodwick 분류 | 골파괴 패턴/공격성 평가 | geographic·moth-eaten·permeative; zone of transition; periosteal reaction; soft tissue mass | X-ray: Lodwick I~III, 전이대, 골막반응; MRI: 골수 침범 범위·연부조직 종괴; CT: 피질 파괴·기질 | 성장 속도와 상관; 넓은 전이대·침윤성 파괴는 공격성 시사 | 골수염; 스트레스 골절; 전이암·골수종 | Lodwick 패턴과 전이대·골막반응을 묶어 공격성/악성 가능성 판단 |
| 연골종 Enchondroma | 양성 연골성 종양 | ring-and-arc 석회화; endosteal scalloping; pathologic fracture | X-ray: 수질강 내 연골성 석회화; MRI: T2 고신호 소엽성·조영 증강 격벽; CT: 석회화·피질 얇아짐 | 수질강 내 유리연골; 손·발 소골 및 장관골에서 흔함 | 저등급 연골육종; 골경색; 연골모세포종 | 통증·피질 파괴·연부조직 종괴는 연골육종 쪽으로 기울게 함 |
| 골연골종 Osteochondroma | 외골종/골연골종 | exostosis; corticomedullary continuity; cartilage cap | X-ray: 골피질·수질 연속성; MRI: 연골모자 두께 평가; CT: 골성 연속성·복잡 부위 평가 | 성장판 기원; 장관골 골간단 주변; 다발성은 HME 연관 | 골막하 골육종; 부착부 골극; 연골육종 변성 | 핵심은 corticomedullary continuity 확인 |
| 골연골종 악성변형 소견 | 골연골종의 악성 변환/이차성 연골육종 | cartilage cap 비후; 통증; 성장 재개; 연부조직 종괴 | MRI: 연골모자 두께 증가·불규칙 조영; CT: 석회화 패턴 변화·피질 파괴; X-ray: 불규칙한 종괴성 음영 | 성인에서 크기 증가·통증은 경고; 연골성 악성화가 대표 | 점액성 변화; 점액낭염; 외상 후 변화 | 연골모자 두께와 피질 파괴·연부조직 종괴를 시험에서 강조 |
| 연골모세포종 Chondroblastoma | 양성 연골성 종양 | epiphyseal lesion; sclerotic rim; edema | X-ray: 골단 중심 용해성 병변·경화성 테두리; MRI: 주변 골수·연부조직 부종이 두드러짐; CT: 석회화·경계 | 청소년·젊은 성인; 골단 선호 | 거대세포종; 감염; 골단 ABC | 골단 병변에서 나이와 위치가 감별의 핵심 |
| 전형적 연골육종 Conventional chondrosarcoma | 악성 연골성 종양 | deep endosteal scalloping; cortical breach; soft tissue mass; ring-and-arc | X-ray: 공격적 용해·연골성 석회화; MRI: 소엽성 T2 고신호·연부조직 확장; CT: 석회화·피질 파괴 | 성인에서 흔함; 통증 동반; 저등급은 영상-임상 통합 필요 | 연골종; 이차성 연골육종; 골경색 | endosteal scalloping의 깊이·피질 파괴·연부조직 종괴로 양악성 구분 |
| 골양골종 Osteoid osteoma/골모세포종 Osteoblastoma | 골형성 종양 | nidus; 야간통·NSAID 반응; reactive sclerosis | X-ray: 작은 nidus와 반응성 경화; CT: nidus 확인 최강; MRI: 부종 과장 가능·nidus 조영 | 크기·위치로 구분; osteoblastoma는 더 크고 척추 후궁 등에서 흔함 | Brodie 농양; 스트레스 골절; 골육종 | CT로 nidus 찾기와 임상 통증 패턴이 단골 포인트 |
| 골육종 Osteosarcoma (주요 아형 포함) | 악성 골형성 종양 | sunburst; Codman triangle; osteoid matrix; skip lesion | X-ray: 혼합성 파괴·골형성 기질·골막반응; MRI: 골수 범위·신경혈관 침범·skip lesion; CT: 폐전이·기질 | 고등급이 대표; 골간단 선호; 아형은 conventional·telangiectatic·parosteal·periosteal 등 | Ewing 육종; 골수염; MFH of bone | 골막반응과 osteoid matrix, MRI로 범위/skip lesion 평가 |
| 섬유성 피질 결손/비골화성 섬유종 FCD/NOF | 섬유성 병변 | eccentric metaphyseal; bubbly lucency; sclerotic rim | X-ray: 피질 기반 편심성 용해·경화성 테두리; MRI: 섬유성 저신호 성분·비특이; CT: 피질 얇아짐 | 소아·청소년; 자연 소실 가능; 큰 병변은 골절 위험 | 섬유이형성증; 골낭종; LCH | 전형적 위치와 경계 명확한 양성 소견을 기억 |
| 거대세포종 Giant cell tumor | 국소 침윤성 양성/중간악성 | epiphyseal-metaphyseal; subchondral; non-sclerotic margin | X-ray: 골단-골간단 용해성·관절면 인접; MRI: 출혈·액체-액체층 동반 가능; CT: 피질 결손 | 성숙 골격에서; 국소 재발 가능 | 연골모세포종; 갈색종양; ABC | 골단 병변에서 성장판 폐쇄 여부가 핵심 감별 축 |
| 단순골낭종/동맥류성 골낭종 UBC/ABC | 낭성 골병변 | UBC: central metaphyseal; fallen fragment; ABC: expansile·fluid-fluid level | X-ray: UBC 중심성 투과성·얇은 피질; ABC 팽창성 다방성; MRI: ABC 액체-액체층, UBC 단일액체 | UBC는 소아에서 흔함; ABC는 1차 또는 2차로 발생 | 거대세포종; 텔란지엑타틱 골육종; 감염 | ABC의 fluid-fluid level은 비특이 가능·악성 감별 필요 |
| 유잉육종 Ewing sarcoma | 소원형세포 종양 | diaphyseal; onion-skin; large soft tissue mass | X-ray: 골간부 중심 파괴·층판성 골막반응; MRI: 연부조직 종괴 크고 골수 침범 광범위; CT: 폐 평가 | 소아·청소년; 전신 증상 동반 가능 | 골수염; 림프종; 골육종 | 골간부 병변+큰 연부조직 종괴 조합을 고전적으로 출제 |
| 골 림프종/골 LCH | 혈액종양/조직구 질환 | lymphoma: permeative·minimal periosteal; LCH: punched-out·vertebra plana | X-ray: 림프종은 침윤성 파괴·비특이; LCH는 천공성 용해·평평해진 척추; MRI: 골수 치환·연부조직 | 림프종은 성인에서도; LCH는 소아에서 다발 가능 | 전이암; 골수염; Ewing 육종 | LCH의 vertebra plana와 림프종의 비특이 침윤성 소견을 구분 |
... (truncated)
```

---


## Stage 2 (S2) 출력 결과

### Arm A

- **Total Records**: 4
- **Group ID**: `d2da903bffbe2cd6`
- **Entity ID**: `DERIVED:dfb0a9b7e48f`
- **Entity Name**: `Bone Destruction Patterns`
- **Cards Generated**: 3

**First Card Sample:**
- **Type**: `Recall`
- **Front**: What bone destruction pattern is characterized by a single, well-defined lytic lesion, often with a sclerotic rim?
- **Back**: Geographic bone destruction pattern, typically indicating a slow-growing or benign process.

---

### Arm B

- **Total Records**: 4
- **Group ID**: `d2da903bffbe2cd6`
- **Entity ID**: `DERIVED:dfb0a9b7e48f`
- **Entity Name**: `Bone Destruction Patterns`
- **Cards Generated**: 3

**First Card Sample:**
- **Type**: `Definition`
- **Front**: What are the three main patterns of bone destruction?
- **Back**: The three main patterns are Geographic, Moth-eaten, and Permeative.

---

### Arm C

- **Total Records**: 4
- **Group ID**: `d2da903bffbe2cd6`
- **Entity ID**: `DERIVED:15c91ce38434`
- **Entity Name**: `골 파괴 양상`
- **Cards Generated**: 3

**First Card Sample:**
- **Type**: `Basic`
- **Front**: 골 파괴 양상(Bone destruction pattern)의 세 가지 주요 유형은 무엇인가?
- **Back**: Geographic, Moth-eaten, Permeative

---

### Arm D

- **Total Records**: 4
- **Group ID**: `d2da903bffbe2cd6`
- **Entity ID**: `DERIVED:dfb0a9b7e48f`
- **Entity Name**: `Bone Destruction Patterns`
- **Cards Generated**: 3

**First Card Sample:**
- **Type**: `Basic`
- **Front**: What are the characteristics of <b>Geographic bone destruction</b> and its implication for lesion aggressiveness?
- **Back**: <b>Characteristics:</b> Large, solitary area of bone destruction with a relatively well-defined margin.<br><b>Implication:</b> If margins are scleroti...

---

### Arm E

- **Total Records**: 4
- **Group ID**: `d2da903bffbe2cd6`
- **Entity ID**: `DERIVED:ad8e3b6a4d9f`
- **Entity Name**: `Bone Tumor Analysis Approach`
- **Cards Generated**: 3

**First Card Sample:**
- **Type**: `concept_explanation`
- **Front**: What are the three primary factors (the 'diagnostic triad') used to narrow the differential diagnosis of a primary bone tumor?
- **Back**: 1. Patient Age
2. Tumor Location (e.g., epiphysis vs. metaphysis vs. diaphysis)
3. Tumor Matrix (e.g., osteoid, chondroid, fibrous)

---

### Arm F

- **Total Records**: 4
- **Group ID**: `d2da903bffbe2cd6`
- **Entity ID**: `DERIVED:234e9ead6061`
- **Entity Name**: `골파괴 패턴 Lodwick 분류`
- **Cards Generated**: 3

**First Card Sample:**
- **Type**: `Classification`
- **Front**: Lodwick 골파괴 패턴 분류의 3가지 기본 패턴은?
- **Back**: Geographic(국소적·경계 비교적 명확) / Moth-eaten(다발성 작은 용해가 군데군데) / Permeative(미세한 침윤성 용해가 광범위). 일반적으로 geographic < moth-eaten < permeative 순으로 공격성 시사.

---


## 파일 통계

| Arm | Stage 1 파일 | Stage 2 파일 | S1 레코드 수 | S2 레코드 수 |

|-----|-------------|-------------|-------------|-------------|

| A | ✅ | ✅ | 1 | 4 |
| B | ✅ | ✅ | 1 | 4 |
| C | ✅ | ✅ | 1 | 4 |
| D | ✅ | ✅ | 1 | 4 |
| E | ✅ | ✅ | 1 | 4 |
| F | ✅ | ✅ | 1 | 4 |

---

## 결론

✅ **모든 arm에서 Stage 1과 Stage 2가 성공적으로 분리 실행되었습니다.**

- Stage 1은 독립적으로 실행되어 `stage1_struct__arm{X}.jsonl` 파일을 생성
- Stage 2는 기존 S1 출력을 읽어서 `s2_results__arm{X}.jsonl` 파일을 생성
- 모든 arm에서 정상적으로 작동 확인
