# SubBridge (SRT Verifier & Merger) — AI Assistant Context Document

> **이 문서의 목적**: Gemini, ChatGPT, Cursor 등 AI 어시스턴트가 이 프로젝트의 현재 상태를 빠르게 파악하고, 톤앤매너를 유지하며 새로운 기능을 추가하거나 버그를 수정할 때 참조하는 **컨텍스트 기준 문서(PRD)** 입니다.

---

## 1. 프로젝트 개요 (Project Overview)

| 항목 | 내용 |
|------|------|
| **프로그램명** | SubBridge (SRT 자막 검수 및 병합 도구) |
| **목적** | SRT 자막 파일을 로드하여 Gemini AI로 다국어 번역하고, 번역 결과를 검수·편집한 뒤 새 SRT 파일로 병합·저장하는 올인원 자막 번역 툴 |
| **주요 타겟 언어** | English, 한국어, 日本語, 中文(简), 中文(繁), Русский, Español, Français, Deutsch, Português, Italiano, Tiếng Việt, ภาษาไทย, Bahasa Indonesia, العربية, हिन्दी |
| **배포 형태** | PyInstaller 단일 exe (`SubBridgeAI.exe`) + Python 스크립트 직접 실행 |
| **소스 파일** | `srt_verifier_merger.py` (단일 파일, ~2940줄) |

---

## 2. 기술 스택 및 아키텍처 (Tech Stack & Architecture)

### 2.1 기술 스택

| 구분 | 기술 |
|------|------|
| **언어** | Python 3.14+ |
| **GUI** | Tkinter (ttk 포함) |
| **AI API** | Google Gemini (`google-genai` 라이브러리) |
| **빌드** | PyInstaller 6.18+ |
| **아이콘** | `app.ico` (Windows), `icon.png` (fallback) |

### 2.2 아키텍처 개요

```
srt_verifier_merger.py (단일 파일)
├── 상수 & 설정 (Lines 1-312)
│   ├── 경로 상수 (PREFS_PATH, GLOSSARY_PATH, LOG_HISTORY_PATH 등)
│   ├── 번역 설정 (BATCH_CHUNK_SIZE=10, QA_MAX_CHARS=45 등)
│   ├── 언어/폰트/모델 옵션 리스트
│   └── 로그 하이라이트 패턴
│
├── 유틸리티 함수 (Lines 118-455)
│   ├── write_readme()          — readme.txt 자동 갱신
│   ├── load/save_gemini_api_key() — API 키 관리
│   ├── parse_srt() / parse_txt_lines() — 파일 파싱
│   ├── merge_data() / build_srt_from_merged() — 데이터 병합/생성
│   └── _glossary_dict_to_text() / _glossary_text_to_dict() — 용어집 변환
│
├── StatsManager 클래스 (Lines 315-359)
│   └── 모델별 번역 성능 통계 관리 (model_performance.json)
│
├── LogViewer 클래스 (Lines 456-786)
│   └── 로그 창 UI + 로그 이력 관리 (log_history.json)
│
├── 번역 헬퍼 함수 (Lines 769-911)
│   ├── _map_translation_response_lines() — 응답 매핑
│   ├── _parse_json_translation_response() — JSON 파싱
│   ├── _translate_chunk_single_fallback() — 단일 행 폴백 번역
│   └── _run_qa_checks() — 45자 초과/빈줄/인코딩 QA
│
└── SrtVerifierMergerApp 클래스 (Lines 915-2940)
    ├── __init__() — 상태 초기화, UI 빌드, 설정 로드
    ├── _build_ui() — 전체 UI 레이아웃 구성
    ├── _refresh_tree() — Treeview 갱신 (경고 태그 포함)
    ├── _do_translation_work() — 배치 번역 핵심 로직 (워커 스레드)
    ├── _on_translation_done() — 번역 완료 콜백 (메인 스레드)
    ├── _on_glossary_settings() — 용어집 창 생성/관리
    └── _load/_save_preferences() — 설정 영속화
```

### 2.3 스레딩 모델

```
[메인 스레드 (Tkinter UI)]
    │
    ├── _on_ai_translate()  →  threading.Thread(daemon=True) 생성
    │                              │
    │                              ▼
    │                     [워커 스레드]
    │                     _run_translation_worker()
    │                       └── _do_translation_work()
    │                             ├── Gemini API 호출 (배치 단위)
    │                             ├── self.rows[i]["translated"] 직접 수정
    │                             └── root.after(0, callback) 으로 UI 갱신 요청
    │                                   ├── 로그 메시지 삽입
    │                                   ├── 진행률 업데이트
    │                                   ├── Treeview 갱신
    │                                   └── 45자 초과 경고 실시간 출력
    │
    ▼
[메인 스레드로 복귀]
    _on_translation_done()  ←  root.after(0, ...)
```

> **핵심 원칙**: 워커 스레드에서 UI 위젯을 직접 조작하지 않으며, 반드시 `self.root.after(0, callback)`을 통해 메인 스레드에서 실행합니다.

---

## 3. UI/UX 레이아웃 구조 (UI Structure)

### 3.1 메인 윈도우 (`SrtVerifierMergerApp._build_ui`)

```
┌─────────────────────────────────────────────────────────────────┐
│ [Header] "SRT 자막 검수 및 병합 도구"  [?] (도움말 + 빨간 배지)    │
├─────────────────────────────────────────────────────────────────┤
│ [Row 0] 원본SRT | 번역TXT | AI번역 | □모두번역 | 범위입력 |       │
│         AI모델▼ | 언어▼ | 용어집 |  (spacer)  | 병합하기 |       │
│         □작업내용 | 글자크기▼                                     │
│ [Row 1]                    추출하기 | 언어▼                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [Treeview - 3 컬럼]                                             │
│  ┌──────────────┬──────────────────┬──────────────────────┐  ▲  │
│  │ 순번/타임코드  │ 원본 텍스트       │ 번역 텍스트           │  │  │
│  │ (고정 250px)  │ (stretch)        │ (stretch)            │  │  │
│  ├──────────────┼──────────────────┼──────────────────────┤  │  │
│  │ 1 (00:00...) │ Hello world      │ 안녕하세요             │  │  │
│  │ 2 (00:01...) │ Long sentence... │ [주황색] 45자 초과 텍스트│  │  │
│  └──────────────┴──────────────────┴──────────────────────┘  ▼  │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ [Bottom] 검색: [________] [찾기 Ctrl+F] [검토 필요 찾기 (총 N건)] │
│ [Status Bar] 준비됨. 원본 SRT 또는 번역 TXT를 열어주세요.          │
│ [Progress Bar] ████████████░░░░░░░░ (번역 중에만 표시)            │
└─────────────────────────────────────────────────────────────────┘
                                          ┌──────────────────────┐
                                          │ [LogViewer 창]        │
                                          │ (메인 창 우측에 자석   │
                                          │  부착, 독립 Toplevel) │
                                          │ 폰트크기▼ | 크기초기화│
                                          │ ┌──────────────────┐ │
                                          │ │ [ScrolledText]    │ │
                                          │ │ [정보] 번역 시작...│ │
                                          │ │ [경고] Line 5 45자│ │
                                          │ │  초과.(길이:52자)  │ │
                                          │ └──────────────────┘ │
                                          └──────────────────────┘
```

### 3.2 Treeview 태그 시스템

| 태그명 | 배경색 | 글자색 | 조건 |
|--------|--------|--------|------|
| `even` | `#ffffff` | 기본 | 짝수 행 (정상) |
| `odd` | `#f5f5f5` | 기본 | 홀수 행 (정상) |
| `warning_even` | `#ffffff` | `#D35400` (주황) | 짝수 행 + 경고 |
| `warning_odd` | `#f5f5f5` | `#D35400` (주황) | 홀수 행 + 경고 |

**경고 조건**: `len(line) > 45` (45자 초과) **또는** `"빈줄" in text`

### 3.3 용어집 창 (`_on_glossary_settings`)

```
┌──────────────────────────────────────────┐
│ 용어집 설정                    [X]        │
├──────────────────────────────────────────┤
│ [언어▼ English]  [글자크기▼ 보통]         │
├──────────────────────────────────────────┤
│ ┌──────────────────┬──────────────────┐  │
│ │ 원본단어          │ 번역단어(English) │  │
│ ├──────────────────┼──────────────────┤  │
│ │ 안녕하세요        │ Hello            │  │
│ │ 감사합니다        │ Thank you        │  │
│ └──────────────────┴──────────────────┘  │
├──────────────────────────────────────────┤
│ [단어 추가/수정/삭제]                      │
│ 원본: [________]  번역: [________]        │
│ [추가/수정] [삭제 (Del)] [저장 후 닫기 (Ctrl+S)] │
└──────────────────────────────────────────┘
```

- **모달 다이얼로그** (`grab_set()`)
- 언어 전환 시 해당 언어의 용어집만 표시
- 메인 프로그램의 AI 번역 대상 언어와 **독립적**으로 관리

#### 용어집 창 전용 단축키

| 단축키 | 동작 |
|--------|------|
| `Delete` | 선택된 항목 삭제 |
| `Ctrl+S` | 저장 후 닫기 (glossary.json 반영) |
| `Escape` | 저장 후 닫기 |
| `Enter` (원본 입력창) | 번역 입력창으로 포커스 이동 |
| `Enter` (번역 입력창) | 추가/수정 실행 |

#### Treeview 선택 ↔ 입력창 자동 완성 (Auto-fill)

- `<<TreeviewSelect>>` 이벤트에 `on_select` 콜백 바인딩
- 사용자가 Treeview에서 항목을 클릭하거나 방향키로 선택을 변경하면, 해당 행의 원본/번역 텍스트가 하단 입력창에 자동으로 채워짐
- 이를 통해 리스트를 훑으면서 바로 하단에서 텍스트를 수정 → Enter로 추가/수정 가능

#### UX 안전장치: 미등록 텍스트(Uncommitted Text) 감지

- `save_and_close()` 호출 시 (Ctrl+S, Esc, X 버튼, 저장 후 닫기 버튼 모두 해당)
- 하단 입력창에 텍스트가 남아있으면 `messagebox.askyesnocancel` 팝업 표시:
  - **예**: 입력 중인 단어를 용어집에 추가/수정한 뒤 저장 후 닫기
  - **아니요**: 입력 중인 단어를 무시하고 현재 Treeview 데이터만 저장 후 닫기
  - **취소**: 저장/닫기 중단, 용어집 창 유지 (편집 계속)
- 입력창이 비어있으면 팝업 없이 즉시 저장 후 닫기

---

## 4. 핵심 기능 명세 (Core Features & Workflows)

### 4.1 배치(Batch) 번역 시스템

#### 번역 흐름

```
사용자 클릭 → _on_ai_translate()
    ├── API 키 검증
    ├── 번역 범위 파싱 (범위 모드 / 모두 번역 모드)
    ├── 배치 크기 결정 (10줄/배치)
    └── 워커 스레드 생성 → _do_translation_work()
         │
         ├── Gemini API 클라이언트 초기화
         ├── 모델 선택 (자동 / 수동)
         │    └── 자동: AI_MODEL_FALLBACKS 순서대로 시도
         │         ("gemini-2.5-pro" → "gemini-2.5-flash" → "gemini-2.5-flash-lite")
         │
         └── 배치 루프 (10줄씩):
              ├── JSON 프롬프트 구성:
              │    [{"id": "1", "text": "원본 텍스트"}, ...]
              ├── API 호출 (1차 시도)
              ├── 실패 시 → 동일 배치 재시도 (2차)
              ├── 재실패 시 → 단일 행 폴백 (_translate_chunk_single_fallback)
              ├── 응답 파싱 → id 기반 매핑 → self.rows 업데이트
              ├── QA 검사 (_run_qa_checks) → 실시간 경고 출력
              └── root.after(0, ...) → Treeview 갱신 + 진행률 업데이트
```

#### JSON 프롬프트 형식

```json
// 요청
[{"id": "1", "text": "Hello world"}, {"id": "2", "text": "Good morning"}]

// 응답 (기대 형식)
[{"id": "1", "text": "안녕하세요"}, {"id": "2", "text": "좋은 아침입니다"}]
```

#### 시스템 인스트럭션 구조

```
당신은 전문 자막 번역가입니다. ...
- 대상 언어: {target_lang}
- <br/> 태그 보존 규칙
- [선택] 용어집 포함 시:
  【필수 번역 용어집】
  원본단어:번역단어
  ...
```

#### 폴백 전략 (2단계)

| 단계 | 조건 | 동작 |
|------|------|------|
| 1차 | 배치 API 호출 | 10줄 묶어서 JSON 요청 |
| 2차 | 1차 실패 또는 ID 불일치 | 행 단위 개별 번역 (single fallback) |

- 429 (Quota Exceeded) / 503 (UNAVAILABLE) 에러 시 즉시 중단

### 4.2 용어집(Glossary) 시스템

#### 데이터 구조

```json
// glossary.json
{
  "English": {
    "안녕하세요": "Hello",
    "감사합니다": "Thank you"
  },
  "한국어": {
    "Hello": "안녕하세요"
  }
}
```

- **타입**: `Dict[str, Dict[str, str]]` (언어명 → {원본: 번역})
- **언어별 독립 관리**: 각 언어마다 별도의 용어 사전
- **메인 프로그램과의 관계**: 번역 시 AI 대상 언어에 해당하는 용어집만 프롬프트에 포함

#### 동기화 흐름

```
용어집 창에서 편집 → _save_glossary_data() → glossary.json 저장
                                                    ↓
번역 시작 → _get_glossary_text_for_lang(target_lang) → 해당 언어 용어집 텍스트 추출
                                                    ↓
                                          시스템 인스트럭션에 포함
```

### 4.3 실시간 QA 및 시각화 시스템

#### QA 검사 (`_run_qa_checks`)

| 검사 항목 | 조건 | 출력 형식 | 후속 동작 |
|-----------|------|-----------|-----------|
| 45자 초과 | `len(line.strip()) > 45` | `[경고] Line {번호} 45자 초과.(길이:{n}자)` | 주황색 강조 + 검토 카운트 포함 |
| 빈줄 감지 | 번역 결과가 비어있음 | `Line {start}-{end}: 빈 줄 {count}건 감지되어 <빈줄> 처리` | `<빈줄>` 텍스트 삽입 → 주황색 강조 + 검토 카운트 포함 |
| 인코딩 깨짐 | `\uFFFD` 포함 | `[오류] Line {idx}: 번역 결과에 깨진 문자가 감지되었습니다.` | 로그 출력만 |

> **빈줄 처리 흐름**: 번역 결과가 비어있으면 `AI_TRANSLATE_EMPTY_PLACEHOLDER = "<빈줄>"`로 자동 채워짐 → `"빈줄" in text` 경고 조건에 매칭 → **45자 초과와 동일하게** 주황색 강조 표시 + 검토 필요 카운트에 포함. 즉, 빈줄 감지와 주황색 경고는 하나의 연결된 파이프라인이다.

#### 주황색 강조 시스템 (45자 초과 + 빈줄 공통)

```
_refresh_tree() 또는 _commit_inplace_edit()
    ├── 각 행의 translated 텍스트 검사
    ├── _is_warning_text(text):
    │    └── len(line) > 45 OR "빈줄" in text → True
    │        (빈줄 감지 시 "<빈줄>" 텍스트가 들어있으므로 자동 매칭)
    └── True → warning_{even|odd} 태그 적용 (주황색 #D35400)
        False → {even|odd} 태그 적용 (기본색)
```

#### 검토 필요 찾기 버튼

```
[검토 필요 찾기 (총 N건)]
    │
    ├── _update_warning_count(): 경고 항목 수 세어 버튼 텍스트 갱신
    │    호출 시점: 파일 로드, 번역 완료, 번역 실패/중단, 셀 편집 완료, 초기화
    │
    ├── _on_warning_nav(): 다음 경고 항목으로 이동
    │    ├── 현재 선택 행 기준 다음 경고 찾기
    │    ├── tree.selection_set() + tree.see() + tree.focus()
    │    └── 마지막 도달 시 처음으로 wrap-around
    │
    └── 0건 시: 버튼 disabled + "검토할 항목이 없습니다." 상태바 표시
```

### 4.4 실시간 로그 시스템 (`LogViewer`)

- **위치**: 메인 창 우측에 자석처럼 부착 (독립 `Toplevel`)
- **토글**: 상단 "작업 내용" 체크박스로 표시/숨김
- **이력 관리**: `log_history.json`에 최대 500건 저장 (초과 시 100건씩 정리)
- **실시간 갱신**: `text.update_idletasks()` 호출로 UI 프리징 방지
- **하이라이트**: `[경고]`, `[오류]`, `[OK]` 등 패턴에 따라 색상 적용

### 4.5 전역 단축키 및 네비게이션 (Hotkeys & Navigation)

#### 전역 단축키

| 단축키 | 동작 | 바인딩 함수 |
|--------|------|-------------|
| `F4` | 검토 필요 찾기 (다음 경고 항목으로 이동) | `_on_warning_nav` |
| `F3` | 용어집 설정 창 열기 | `_on_glossary_settings` |
| `Ctrl+S` | 병합하기 (SRT 저장) | `_on_merge` |
| `Ctrl+Enter` | AI 번역 시작 | `_on_ai_translate` |
| `Ctrl+F` | 검색 입력창 포커스 | `_focus_search_entry` |

- 모든 단축키는 `self.root.bind()`로 메인 윈도우 전역에 바인딩
- 버튼 텍스트에 단축키가 표시됨 (예: `AI 번역 (Ctrl+Enter)`, `병합하기 (Ctrl+S)`)
- 바인딩 대상 함수는 `event=None` 기본 인자를 가져 버튼 클릭과 키보드 입력 모두 호환

#### Treeview 방향키 & 페이지 네비게이션

| 키 | 동작 | 이동량 |
|----|------|--------|
| `↑` (Up) | 이전 항목으로 이동 + 스크롤 | 1행 |
| `↓` (Down) | 다음 항목으로 이동 + 스크롤 | 1행 |
| `Page Up` | 위로 페이지 이동 | 20행 |
| `Page Down` | 아래로 페이지 이동 | 20행 |

- 메인 윈도우 전역 바인딩 → Treeview에 포커스가 없어도 동작
- 인라인 편집 중(`_inplace_entry` 활성)에는 방향키 네비게이션 무시
- 이벤트 핸들러에서 `return "break"`로 기본 스크롤 동작과의 중복 방지
- 헬퍼 메서드: `_tree_select_by_index(row_index)` → `selection_set` + `focus` + `see` 통합

---

## 5. 데이터 및 설정 저장 구조 (Data Structures)

### 5.1 `settings.json`

```json
{
  "lang_code": "EN",
  "font_size": "보통",
  "ai_lang": "한국어",
  "ai_model": "자동",
  "log_viewer_visible": false,
  "main_win_width": 1200,
  "main_win_height": 800,
  "main_win_x": 100,
  "main_win_y": 100,
  "log_viewer_width": 400,
  "log_viewer_height": 600,
  "log_font_size": "작게",
  "glossary_font_size": "보통",
  "glossary_win_width": 500,
  "glossary_win_height": 400,
  "glossary_col_original_width": 200,
  "glossary_col_translated_width": 200
}
```

### 5.2 `glossary.json`

```json
{
  "English": { "원본단어": "translated_word" },
  "한국어": { "source_word": "번역단어" }
}
```

### 5.3 `model_performance.json`

```json
{
  "gemini-2.5-flash": {
    "total_seconds": 120.5,
    "total_items": 500
  }
}
```

### 5.4 `log_history.json`

```json
[
  {
    "ts": "2026-02-15 06:30:00",
    "msg": "[정보] 번역 시작..."
  }
]
```

### 5.5 런타임 데이터 구조

#### `self.rows` (메인 데이터)

```python
[
    {
        "index": 1,                          # SRT 순번
        "timecode": "00:00:01,000 --> 00:00:03,000",
        "original": "Hello world",           # 원본 (줄바꿈은 <br/>)
        "translated": "안녕하세요"             # 번역 (빈 문자열 가능)
    },
    ...
]
```

#### `self.srt_blocks` (SRT 파싱 결과)

```python
[{"index": 1, "timecode": "00:00:01,000 --> 00:00:03,000", "original": "Hello world"}, ...]
```

#### `self.txt_lines` (TXT 파싱 결과)

```python
["안녕하세요", "좋은 아침입니다", ...]
```

---

## 6. AI 어시스턴트를 위한 개발 가이드 (Dev Guidelines for AI)

> **이 프로젝트의 코드를 수정할 때는 다음 규칙을 엄격히 지켜라:**

### 6.1 스레딩 & UI 안전성

- **절대 금지**: 워커 스레드에서 Tkinter 위젯을 직접 조작하지 마라. 반드시 `self.root.after(0, callback)`을 통해 메인 스레드에서 실행해야 한다.
- 로그를 UI에 삽입한 직후에는 `self.text.update_idletasks()`를 호출하여 화면이 즉시 갱신되도록 보장하라. 이를 생략하면 번역 중 UI가 프리징된다.
- 번역 워커 스레드는 반드시 `daemon=True`로 생성하라.

### 6.2 경고 시스템 연결성

- 주황색 경고 태그(`warning_even`, `warning_odd`)와 카운트 업데이트 함수(`_update_warning_count`)의 연결성을 훼손하지 마라.
- **`_update_warning_count()` 호출이 필요한 시점**: 파일 로드, 번역 완료(성공/실패/중단), 사용자 셀 편집 완료. 새로운 데이터 변경 경로를 추가할 때 반드시 이 함수 호출을 포함하라.
- 경고 조건 판별은 `_is_warning_text()` 정적 메서드에 집중되어 있다. 조건을 변경할 때는 이 메서드 하나만 수정하라.

### 6.3 데이터 구조 보존

- `self.rows`의 딕셔너리 키(`index`, `timecode`, `original`, `translated`)를 임의로 변경하지 마라. Treeview, 병합, 추출, QA 등 모든 기능이 이 키에 의존한다.
- `glossary.json`의 구조(`Dict[str, Dict[str, str]]`)를 변경하지 마라. 기존 사용자 데이터와의 호환성이 깨진다.
- `settings.json`에 새 키를 추가할 때는 `_load_preferences()`에서 `.get(key, default)` 패턴으로 기본값을 반드시 제공하라.

### 6.4 번역 시스템

- 배치 크기(`BATCH_CHUNK_SIZE = 10`)를 변경하지 마라. Gemini API의 응답 품질과 토큰 제한에 최적화된 값이다.
- JSON 프롬프트의 `id` 필드는 SRT 순번(`row["index"]`)과 동기화되어야 한다. 이 매핑이 깨지면 번역 결과가 잘못된 행에 들어간다.
- 폴백 전략(배치 → 단일 행)의 순서를 변경하지 마라.
- 429/503 에러 시 즉시 중단하는 로직을 제거하지 마라 (API 비용 보호).

### 6.5 UI 레이아웃

- 메인 윈도우는 `grid` 레이아웃, 용어집 창은 `pack` 레이아웃을 사용한다. 혼용하지 마라.
- Treeview의 `iid`는 `f"r_{row_index}"` 형식이다 (`_tree_iid` 메서드). 이 규칙을 변경하면 선택/포커스 로직이 깨진다.
- LogViewer는 메인 창 우측에 자석 부착되는 독립 `Toplevel`이다. 위치 계산 로직(`_update_position`)을 변경할 때 주의하라.

### 6.6 코드 스타일

- 한국어 주석과 UI 텍스트를 유지하라. 사용자 대상 메시지는 모두 한국어이다.
- 메뉴얼 텍스트(`MANUAL_SIMPLE`, `MANUAL_DETAILED`)를 수정하면 `write_readme()`에 의해 `readme.txt`가 자동 갱신된다. 별도로 `readme.txt`를 수정할 필요 없다.
- 새 기능 추가 시 해당 기능의 설명을 `MANUAL_SIMPLE`(간단)과 `MANUAL_DETAILED`(상세)에 모두 반영하라.

### 6.7 설정 영속화

- 새로운 설정값을 추가할 때는 반드시 `_save_preferences()`와 `_load_preferences()` 양쪽에 추가하라.
- 창 크기/위치 저장은 `_on_close()` 이벤트에서 처리된다. 새 창을 추가할 때 닫기 시 크기 저장 로직을 포함하라.

---

## 7. 주요 클래스 & 메서드 레퍼런스

### `StatsManager` (Line 315)
| 메서드 | 설명 |
|--------|------|
| `accumulate(model, elapsed, count)` | 모델별 번역 시간/개수 누적 |
| `get_average(model)` | (평균초/개, 총개수) 반환 |

### `LogViewer` (Line 456)
| 메서드 | 설명 |
|--------|------|
| `show()` / `hide()` | 로그 창 표시/숨김 |
| `append(message)` | 로그 메시지 추가 (타임스탬프 자동) |
| `update_position_if_active()` | 메인 창 이동 시 위치 동기화 |

### `SrtVerifierMergerApp` (Line 915)
| 메서드 | 설명 |
|--------|------|
| `_build_ui()` | 전체 UI 구성 |
| `_refresh_tree()` | Treeview 전체 갱신 (경고 태그 포함) |
| `_commit_inplace_edit()` | 셀 편집 완료 처리 |
| `_is_warning_text(text)` | 경고 조건 판별 (정적 메서드) |
| `_update_warning_count()` | 경고 카운트 갱신 + 버튼 텍스트 업데이트 |
| `_on_warning_nav()` | 다음 경고 항목으로 이동 |
| `_do_translation_work()` | 배치 번역 핵심 로직 (워커 스레드) |
| `_on_translation_done()` | 번역 완료 콜백 (메인 스레드) |
| `_on_glossary_settings()` | 용어집 창 열기 |
| `_load_preferences()` / `_save_preferences()` | 설정 로드/저장 |
| `_merge_and_refresh()` | SRT+TXT 병합 후 Treeview 갱신 |

---

*이 문서는 코드 변경 시 함께 업데이트되어야 합니다. 마지막 업데이트: 2026-02-15*
