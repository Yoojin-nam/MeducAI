# Legacy Configs

## 개요

이 폴더에는 현재 사용하지 않는 legacy 설정 파일들이 보관되어 있습니다.

**이동 일시**: 2025-12-22

---

## 이동된 파일들

### 1. `tagging_rules_v1.0.json` (~1.8 KB)

- **용도**: Tagging 규칙 v1.0 (구버전)
- **대체 파일**: `tagging_rules_v1.1.json` (현재 사용 중)
- **차이점**:
  - v1.0: 간단한 구조 (part, category만 정의)
  - v1.1: 상세한 구조 (rules 배열, 각 rule에 specialty/anatomy/topic 계층 포함)
- **상태**: ❌ 미사용 (v1.1로 대체됨)

### 2. `Tagging_Standard_v1.0.md` (~4.1 KB)

- **용도**: Tagging 표준 문서 v1.0
- **상태**: ⚠️ 참고용 문서 (현재 코드에서 직접 참조 안 함)
- **참고**: 문서는 유지할 수도 있으나, 최신 표준이 변경되었을 수 있음

---

## 현재 사용 중인 파일들

- **`tagging_rules_v1.1.json`** (962 KB): 현재 사용 중인 tagging 규칙
- **`styles.json`** (2.3 KB): 스타일 정의 (현재 사용 중)

---

## 참고

- 현재 tagging 규칙: `tagging_rules_v1.1.json`
- 사용 노트북: `RaB-LLM_06_tag_autogenerator.ipynb` (v1.0을 참조할 수 있으나, v1.1 사용 권장)

