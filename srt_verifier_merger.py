# -*- coding: utf-8 -*-
"""
SRT 자막 검수 및 병합 도구 (Subtitle Verifier & Merger)
Python 3 + tkinter / ttk 단일 파일 실행
"""

import json
import sys
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set, Callable

try:
    from PIL import Image
    from PIL import ImageTk
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False

try:
    from google import genai
    from google.genai import types as genai_types
    _HAS_GEMINI = True
except ImportError:
    genai = None
    genai_types = None
    _HAS_GEMINI = False

# 설정 파일 경로 (언어 선택 저장) — exe 실행 시 exe와 같은 폴더에 저장
_base_dir = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
PREFS_PATH = _base_dir / "settings.json"
README_PATH = _base_dir / "readme.txt"
# Gemini API 키를 읽을 .env 후보 (배포 exe에서는 exe 폴더만 사용, 개발 시에만 GEMINI_ENV_PATH 추가)
GEMINI_ENV_PATH = Path(r"C:\cursor2\ai-chatbot-app\ai-chatbot\.env.local")

# 프로그램 아이콘 PNG (스크립트 기준 경로)
_ICON_CANDIDATES = ("icon.png", "Gemini_Generated_Image_28x0ow28x0ow28x0.png")


# 메뉴얼: 간단(툴팁용) / 자세한(상세 창용)
MANUAL_SIMPLE = """SRT 자막 검수 및 병합 도구 (SubBridge)
• 원본 SRT 열기: 자막 파일 로드
• 추출하기: 원본 텍스트만 TXT로 저장 (언어 코드 선택)
• 번역 TXT 열기: 번역문 로드 후 3번째 컬럼에 매칭
• AI 번역하기: Gemini API로 선택 구간 또는 전체 자동 번역 (범위 입력 또는 [모두 번역] 체크)
• 용어집 설정: 원본:번역 형식 용어집으로 번역 결과 고정
• 병합하기: 타임코드+번역문으로 새 SRT 저장
• 글자 크기: 상단 우측 5단계 (저장됨)
• 번역 셀 더블클릭: 번역 열만 수정 가능, 병합 시 반영
• 검색: Ctrl+F → 검색창, 원본/번역 모두 검색
? 클릭 시 자세한 메뉴얼 표시"""

MANUAL_DETAILED = """■ SRT 자막 검수 및 병합 도구 (SubBridge) — 자세한 메뉴얼

【1. 기본 흐름】
  ① 원본 SRT 열기 → 자막 파일을 불러옵니다.
  ② (선택 A) 추출하기 → 원본 대사만 TXT로 뽑아 외부 번역에 쓸 수 있습니다.
  ② (선택 B) AI 번역하기 → Gemini API로 지정 구간 또는 전체를 자동 번역합니다.
  ③ 번역 TXT 열기 → (선택 A인 경우) 번역된 텍스트를 불러오면 줄 순서대로 3번째 컬럼에 채워집니다.
  ④ 병합하기 → 타임코드와 번역문을 합쳐 새 SRT 파일로 저장합니다.

【2. 상단 버튼 및 설정】
  • 원본 SRT 열기: .srt 자막 파일을 엽니다. (컬럼 1: 순번/타임코드, 컬럼 2: 원본 텍스트, 컬럼 3: 번역 텍스트)
  • 번역 TXT 열기: 번역된 한 줄씩 텍스트를 불러와 컬럼 3에 순서대로 채웁니다.
  • AI 번역하기: Gemini API로 원본 텍스트를 번역합니다. API 키는 exe/프로그램 폴더의 .env 파일에 GEMINI_API_KEY=... 로 넣어 주세요.
  • 모두 번역: 체크 시 [번역 범위]에 입력한 시작 번호부터 끝까지 전체를 번역합니다. 체크 해제 시 범위 입력(예: 1-10, 1,3,5)으로 구간만 번역(최대 50개).
  • 번역 범위: 일반 모드에서는 "1-10" 또는 "1,3,5" 형식. 모두 번역 모드에서는 시작 순번만 입력(예: 1).
  • AI 모델: 자동 또는 고정 모델(gemini-2.5-flash 등) 선택. 저장됩니다.
  • AI 번역 대상 언어: 번역 결과 언어(English, 한국어 등). 병합 파일명에도 반영됩니다.
  • 용어집 설정: "원본단어:번역단어" 한 줄씩 입력하면 AI 번역 시 해당 단어가 지정대로 번역됩니다. 설정 파일에 저장됩니다.
  • 추출하기: 원본 텍스트만 TXT로 저장. 오른쪽 언어 선택에 따라 파일명에 _EN, _KR 등이 붙습니다.
  • 언어 선택: 추출 시 파일명에 붙을 언어 코드(EN, RU, KR 등). 저장됩니다.
  • 병합하기(Merge): 컬럼 1(타임코드)과 컬럼 3(번역)을 합쳐 새 .srt 파일로 저장합니다.
  • 글자 크기: 뷰어 표 글자 크기 5단계(매우 작게·작게·보통·크게·매우 크게). 저장됩니다.

【3. 중단 표(검수 뷰어)】
  • 3개 컬럼: 순번/타임코드 | 원본 텍스트 | 번역 텍스트 (AI 번역 후에는 "번역 텍스트 (AI)"로 표시)
  • 순번/타임코드 열은 고정 너비, 원본·번역 열은 창 크기에 따라 넓어집니다. 글자 크기 변경 시 첫 열 너비 자동 조절.
  • 스크롤 가능, 홀/짝 행 색 구분.
  • SRT 블록 수와 TXT 줄 수가 다르면 경고 후에도 로드되며, 화면에서 어긋난 부분을 확인할 수 있습니다.
  • 번역 텍스트 직접 수정: [번역 텍스트] 열 셀 더블클릭 → 입력창에서 수정. Enter 또는 다른 곳 클릭으로 저장, Esc로 취소. 병합 시 반영됩니다.

【4. 하단 검색】
  • 검색창에 단어 입력 후 [찾기(Find)] 또는 Enter: 원본·번역 양쪽에서 검색, 다음 결과로 이동.
  • Ctrl+F: 검색 입력창으로 포커스 이동.

【5. 기본 파일명】
  • 추출: (원본 SRT 파일이름)_(언어코드).txt  예: video_KR.txt
  • 병합(번역 TXT를 연 경우): (번역 TXT 파일이름)_(AI언어코드)(_flash 등).srt
  • 병합(번역 TXT를 안 연 경우): (원본 SRT 파일이름)_(AI언어코드)(_flash 등).srt
  • AI 번역 사용 시 병합 파일명에 모델 접미사(_flash, _flash_lite, _pro)가 붙을 수 있습니다.

【6. API 키 및 설정 저장】
  • Gemini API: exe(또는 프로그램) 폴더에 .env 파일을 만들고 한 줄 입력: GEMINI_API_KEY=여기에_키_입력
  • 언어 선택, 글자 크기, AI 모델, AI 대상 언어, 용어집 등은 설정 파일(settings.json)에 저장되어 재실행 시 유지됩니다."""


def write_readme() -> None:
    """readme.txt에 프로그램 내부의 간단·세부 메뉴얼만 기록. 실행 시마다 갱신되어 코드와 싱크 유지."""
    try:
        content = (
            "[ 간단 메뉴얼 ]\n\n"
            + MANUAL_SIMPLE
            + "\n\n\n"
            "[ 자세한 메뉴얼 ]\n\n"
            + MANUAL_DETAILED
            + "\n"
        )
        README_PATH.write_text(content, encoding="utf-8")
    except Exception:
        pass


# exe 단일 파일 배포 시 PyInstaller가 묶는 API 키 파일명 (build.py와 동일하게 유지)
GEMINI_KEY_BUNDLE_FILENAME = "gemini_api_key_bundle.txt"


def load_gemini_api_key() -> Optional[str]:
    """GEMINI_API_KEY 로드. exe 실행 시 내장 키 파일 → 실행 파일 폴더 .env 순으로 검사."""
    if getattr(sys, "frozen", False) and getattr(sys, "_MEIPASS", None):
        bundle_path = Path(sys._MEIPASS) / GEMINI_KEY_BUNDLE_FILENAME
        if bundle_path.exists():
            try:
                key = bundle_path.read_text(encoding="utf-8").strip()
                if key:
                    return key
            except Exception:
                pass
    key_name = "GEMINI_API_KEY"
    paths = [
        _base_dir / ".env.local",
        _base_dir / ".env",
    ]
    if not getattr(sys, "frozen", False):
        paths.insert(0, GEMINI_ENV_PATH)
    for path in paths:
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
            for line in text.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith(key_name + "="):
                    value = line.split("=", 1)[1].strip().strip('"\'')
                    if value:
                        return value
        except Exception:
            continue
    return None


def save_gemini_api_key_to_env(key: str) -> bool:
    """GEMINI_API_KEY를 실행 파일(또는 스크립트) 폴더의 .env에 저장. 배포 exe에서 별도 설정 없이 키 입력만 가능하게 함."""
    if not key or not key.strip():
        return False
    key = key.strip()
    path = _base_dir / ".env"
    try:
        content = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
        lines = [ln for ln in content.splitlines() if ln.strip() and not ln.strip().startswith("GEMINI_API_KEY=")]
        lines.append(f"GEMINI_API_KEY={key}")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return True
    except Exception:
        return False


# 로그 영구 저장: 최대 개수 초과 시 오래된 항목 자동 삭제
MAX_LOG_LIMIT = 500
PRUNE_COUNT = 100
LOG_HISTORY_PATH = _base_dir / "log_history.json"

# AI 번역 배치 크기 (한 번에 API에 보낼 줄 수). 크게 하면 요청 횟수 감소 → 무료 한도(일 20회) 절약
AI_TRANSLATE_BATCH_SIZE = 50
# 번역 구간 지정 시 한 번에 최대 개수
AI_TRANSLATE_RANGE_MAX = 50
# 번역 범위 입력 placeholder
TRANSLATE_RANGE_PLACEHOLDER = "예: 1-10 또는 1,3,5 (최대 50개)"
# AI 번역 결과가 빈 줄/내용 없을 때 표시 (라인 밀림 방지)
AI_TRANSLATE_EMPTY_PLACEHOLDER = "<빈줄>"


# 언어 옵션: (코드, 표시명) — 1.영어 2.러시아어 3.한국어, 이하 사용량 순
LANG_OPTIONS: List[Tuple[str, str]] = [
    ("EN", "English"),
    ("RU", "Русский"),
    ("KR", "한국어"),
    ("ZH", "中文"),
    ("ES", "Español"),
    ("JA", "日本語"),
    ("FR", "Français"),
    ("DE", "Deutsch"),
    ("PT", "Português"),
    ("AR", "العربية"),
]

# 뷰어 글자 크기 옵션: (표시명, pt)
FONT_SIZE_OPTIONS: List[Tuple[str, int]] = [
    ("매우 작게", 9),
    ("작게", 10),
    ("보통", 11),
    ("크게", 13),
    ("매우 크게", 16),
]
# 폰트 크기별 행 높이 (한 줄 기준, 글자 잘리지 않게)
FONT_ROWHEIGHT: Dict[int, int] = {9: 24, 10: 26, 11: 28, 13: 32, 16: 38}
# 폰트 크기별 첫 번째 열(순번/타임코드) 고정 너비 (텍스트 잘리지 않게)
FONT_COLUMN_WIDTH: Dict[int, int] = {9: 180, 10: 210, 11: 250, 13: 320, 16: 400}

# AI 번역 모델 옵션 (Google AI Studio 텍스트 출력 모델 기준) — "자동"은 API 목록에서 첫 사용 가능 모델 사용
AI_MODEL_AUTO = "자동"
AI_MODEL_FALLBACKS = ("gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite")
AI_MODEL_OPTIONS: List[str] = [
    AI_MODEL_AUTO,
    *AI_MODEL_FALLBACKS,
]
# UI용 라벨 목록 (한 번만 생성)
LANG_DISPLAYS: List[str] = [display for _, display in LANG_OPTIONS]
FONT_LABELS: List[str] = [label for label, _ in FONT_SIZE_OPTIONS]
DEFAULT_FONT_LABEL = "보통"
DEFAULT_FONT_PT = 11

# 모델별 성능 데이터 영구 저장 경로
MODEL_PERF_PATH = _base_dir / "model_performance.json"


class StatsManager:
    """모델별 번역 성능 데이터를 영구 저장하고 평균 속도를 계산한다."""

    def __init__(self, path: Path = MODEL_PERF_PATH):
        self._path = path
        self._data: Dict[str, Dict[str, float]] = {}
        self._load()

    # ── 내부 I/O ──

    def _load(self) -> None:
        if self._path.exists():
            try:
                self._data = json.loads(self._path.read_text(encoding="utf-8"))
            except Exception:
                self._data = {}

    def _save(self) -> None:
        try:
            self._path.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    # ── 공개 API ──

    def accumulate(self, model: str, elapsed_seconds: float, items: int) -> None:
        """번역 완료 시 소요 시간과 처리 개수를 누적 합산한다."""
        if not model or items <= 0 or elapsed_seconds <= 0:
            return
        if model not in self._data:
            self._data[model] = {"total_time": 0.0, "total_items": 0}
        self._data[model]["total_time"] += round(elapsed_seconds, 3)
        self._data[model]["total_items"] += items
        self._save()

    def get_average(self, model: str) -> Optional[Tuple[float, int]]:
        """(평균 초/개, 누적 총 개수) 반환. 데이터 없으면 None."""
        entry = self._data.get(model)
        if not entry or entry.get("total_items", 0) <= 0:
            return None
        avg = entry["total_time"] / entry["total_items"]
        return (round(avg, 2), int(entry["total_items"]))


# --- 데이터 계층 (UI와 로직 분리) --------------------------------------------

def parse_srt(content: str) -> List[Dict[str, Any]]:
    """
    SRT 내용을 파싱하여 블록 리스트 반환.
    각 블록: {"index": int, "timecode": str, "original": str}
    """
    # UTF-8 BOM 제거 (BOM이 있으면 첫 블록의 index가 '\ufeff1'이 되어 파싱 실패)
    content = content.lstrip("\ufeff")
    blocks = []
    # 빈 줄 기준으로 블록 분리 (연속 빈 줄도 처리)
    raw_blocks = re.split(r'\n\s*\n', content.strip())
    for raw in raw_blocks:
        # 줄 단위로 분리 시 \r 제거 (Windows 줄바꿈)
        lines = [ln.strip().replace("\r", "") for ln in raw.strip().split("\n") if ln.strip()]
        if len(lines) < 2:
            continue
        try:
            index = int(lines[0])
        except ValueError:
            continue
        # 두 번째 줄: 타임코드 (00:00:00,000 --> 00:00:00,000)
        timecode = lines[1]
        text = '\n'.join(lines[2:]) if len(lines) > 2 else ''
        # 자막 내용의 줄바꿈을 <br/>로 치환 (추출/뷰어에서 한 줄로 통일)
        text = text.replace("\n", "<br/>")
        blocks.append({
            "index": index,
            "timecode": timecode,
            "original": text,
        })
    return blocks


def parse_txt_lines(content: str) -> List[str]:
    """TXT 파일 내용을 줄 단위 리스트로 반환 (strip 적용)."""
    return [ln.strip() for ln in content.strip().split('\n')]


def merge_data(srt_blocks: List[Dict[str, Any]], txt_lines: List[str]) -> List[Dict[str, Any]]:
    """
    SRT 블록 리스트에 TXT 라인을 순서대로 매칭.
    반환 리스트의 각 항목에 "translated" 키 추가 (없으면 "").
    """
    result = []
    for i, block in enumerate(srt_blocks):
        row = dict(block)
        row["translated"] = txt_lines[i] if i < len(txt_lines) else ""
        result.append(row)
    return result


def build_srt_from_merged(rows: List[Dict[str, Any]]) -> str:
    """병합된 데이터로 SRT 문자열 생성. 번역 텍스트의 <br/>는 줄바꿈(\\n)으로 복원."""
    out = []
    for r in rows:
        out.append(str(r["index"]))
        out.append(r["timecode"])
        trans = (r.get("translated", "") or "").replace("<br/>", "\n")
        out.append(trans)
        out.append("")
    return "\n".join(out).rstrip()


def extract_text_lines(rows: List[Dict[str, Any]]) -> str:
    """순번·타임코드 제외, 순수 텍스트만 블록당 한 줄로 추출. (원본은 이미 <br/>로 저장됨, SRT 블록 수 = TXT 라인 수)"""
    return "\n".join(r.get("original", "") for r in rows)


def _lang_code_for_display(display: str) -> str:
    """표시명(예: English)에 해당하는 언어 코드 반환."""
    for code, label in LANG_OPTIONS:
        if label == display:
            return code
    return LANG_OPTIONS[0][0]


def _read_file_utf(path: str, encoding: str, error_title: str) -> Optional[str]:
    """파일을 UTF로 읽기. 실패 시 메시지 박스 후 None 반환."""
    try:
        with open(path, "r", encoding=encoding) as f:
            return f.read()
    except Exception as e:
        messagebox.showerror(error_title, f"파일 읽기 실패:\n{e}")
        return None


# --- 로그 뷰어 (메인 윈도우 우측 자석 배치, 이동 시 따라감) ---

# 설정 파일 경로 (로그 창 크기 저장 — PREFS_PATH와 동일한 settings.json 사용)
def _log_viewer_prefs_path() -> Path:
    return PREFS_PATH


class LogViewer:
    """AI 번역 등 작업 로그를 표시하는 별도 창. 메인 윈도우 우측에 붙어 따라 이동. 영구 저장·자동 정리."""

    LOG_DEFAULT_WIDTH = 480
    LOG_DEFAULT_HEIGHT = 400

    def __init__(self, parent: tk.Tk, on_user_close_callback: Optional[Callable[[], None]] = None):
        self.parent = parent
        self.on_user_close = on_user_close_callback
        self.win: Optional[tk.Toplevel] = None
        self.text: Optional[ScrolledText] = None
        self._active = True  # False 시 Configure 콜백 무시
        self._entries: List[Dict[str, str]] = []  # {"ts": "...", "msg": "..."}
        self._header_frame: Optional[ttk.Frame] = None
        self._load_history()

    # ---- 영구 저장 / 로드 ----

    def _load_history(self) -> None:
        """log_history.json에서 이전 로그 불러오기."""
        try:
            if LOG_HISTORY_PATH.exists():
                with open(LOG_HISTORY_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    self._entries = data
        except Exception:
            self._entries = []

    def _save_history(self) -> None:
        """현재 로그 리스트를 log_history.json에 저장."""
        try:
            with open(LOG_HISTORY_PATH, "w", encoding="utf-8") as f:
                json.dump(self._entries, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _prune_if_needed(self) -> None:
        """로그 개수가 MAX_LOG_LIMIT 초과 시, 가장 오래된 PRUNE_COUNT개 삭제 후 저장."""
        if len(self._entries) > MAX_LOG_LIMIT:
            self._entries = self._entries[PRUNE_COUNT:]
            self._save_history()
            self._rebuild_text_widget()

    def _rebuild_text_widget(self) -> None:
        """텍스트 위젯을 현재 _entries 기준으로 다시 그림."""
        if self.text is None or not self.text.winfo_exists():
            return
        self.text.config(state="normal")
        self.text.delete("1.0", "end")
        for entry in self._entries:
            line = f"[{entry.get('ts', '')}] {entry.get('msg', '')}\n"
            self.text.insert("end", line)
        self.text.see("end")
        self.text.config(state="disabled")

    # ---- 크기 저장 / 로드 ----

    def load_size(self) -> Tuple[int, int]:
        """settings.json에서 저장된 로그 창 크기 로드. 없으면 기본값 반환."""
        try:
            path = _log_viewer_prefs_path()
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    prefs = json.load(f)
                w = prefs.get("log_viewer_width")
                h = prefs.get("log_viewer_height")
                if isinstance(w, (int, float)) and isinstance(h, (int, float)):
                    w, h = int(w), int(h)
                    if 200 <= w <= 2000 and 150 <= h <= 1500:
                        return (w, h)
        except Exception:
            pass
        return (self.LOG_DEFAULT_WIDTH, self.LOG_DEFAULT_HEIGHT)

    def save_size(self) -> None:
        """현재 로그 창 크기를 settings.json에 저장 (위치는 저장하지 않음)."""
        if self.win is None or not self.win.winfo_exists():
            return
        try:
            w = self.win.winfo_width()
            h = self.win.winfo_height()
            if w < 200 or h < 150:
                return
            path = _log_viewer_prefs_path()
            prefs: Dict[str, Any] = {}
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    prefs = json.load(f)
            prefs["log_viewer_width"] = w
            prefs["log_viewer_height"] = h
            with open(path, "w", encoding="utf-8") as f:
                json.dump(prefs, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ---- UI ----

    def _create_window(self) -> None:
        """로그 창 생성 (메인 윈도우 우측에 배치)."""
        if self.win is not None and self.win.winfo_exists():
            return
        self.win = tk.Toplevel(self.parent)
        self.win.title("SubBridge — 로그")
        self.win.resizable(True, True)
        self.win.minsize(200, 150)
        lw, lh = self.load_size()
        self.win.geometry(f"{lw}x{lh}")
        self.win.protocol("WM_DELETE_WINDOW", self._on_user_close)
        # 상단 헤더: 크기 초기화 버튼
        self._header_frame = ttk.Frame(self.win)
        self._header_frame.pack(fill="x", padx=4, pady=(4, 2))
        ttk.Button(self._header_frame, text="크기 초기화", command=self._on_reset_size).pack(side="right")
        frame = ttk.Frame(self.win, padding=4)
        frame.pack(fill="both", expand=True)
        self.text = ScrolledText(frame, wrap="word", font=("Consolas", 9), height=20, width=40)
        self.text.pack(fill="both", expand=True)
        self.text.config(state="disabled")  # 편집 불가, append만
        # 저장된 이전 로그를 텍스트 위젯에 복원
        self._rebuild_text_widget()
        self._update_position()
        self._bind_configure()

    def _on_user_close(self) -> None:
        """사용자가 로그 창 X 버튼 클릭 시: 크기 저장 → 숨김 → 체크박스 동기화."""
        self.save_size()
        if self.win and self.win.winfo_exists():
            self.win.withdraw()
        if self.on_user_close:
            self.on_user_close()

    def _on_reset_size(self) -> None:
        """크기 초기화 버튼: 기본 크기로 복원."""
        if self.win is None or not self.win.winfo_exists():
            return
        self.win.geometry(f"{self.LOG_DEFAULT_WIDTH}x{self.LOG_DEFAULT_HEIGHT}")
        self._update_position()

    def _update_position(self) -> None:
        """메인 윈도우 우측에 로그 창 위치 설정 (자석 효과). 크기는 유지."""
        if self.win is None or not self.win.winfo_exists():
            return
        try:
            self.parent.update_idletasks()
            self.win.update_idletasks()
            mx = self.parent.winfo_x()
            my = self.parent.winfo_y()
            mw = self.parent.winfo_width()
            w = self.win.winfo_width()
            h = self.win.winfo_height()
            x = mx + mw
            y = my
            self.win.geometry(f"{w}x{h}+{x}+{y}")
        except (tk.TclError, Exception):
            pass

    def update_position_if_active(self) -> None:
        """외부에서 Configure 이벤트 시 호출. 로그 창이 활성 상태면 위치 갱신."""
        if self._active:
            self._update_position()

    def _bind_configure(self) -> None:
        """LogViewer 자체 바인딩은 사용하지 않음 — 앱에서 통합 관리."""
        pass

    def show(self) -> None:
        """로그 창 표시 (없으면 생성, 숨김 상태면 복원)."""
        self._create_window()
        if self.win:
            try:
                self.win.deiconify()
            except tk.TclError:
                pass
            self.win.lift()
            self.win.focus_set()

    def hide(self) -> None:
        """로그 창 숨김 (withdraw). 크기 저장 후 숨김."""
        if self.win and self.win.winfo_exists():
            self.save_size()
            try:
                self.win.withdraw()
            except tk.TclError:
                pass

    def append(self, message: str) -> None:
        """로그 메시지 추가 (타임스탬프 자동, 영구 저장, 자동 정리)."""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = {"ts": ts, "msg": message}
        # 리스트에 추가
        self._entries.append(entry)
        # UI에 추가 (텍스트 위젯이 있으면)
        if self.text is not None and self.text.winfo_exists():
            line = f"[{ts}] {message}\n"
            self.text.config(state="normal")
            self.text.insert("end", line)
            self.text.see("end")
            self.text.config(state="disabled")
        # 개수 초과 체크 → 자동 정리
        self._prune_if_needed()
        # 파일 저장
        self._save_history()

    def clear(self) -> None:
        """로그 내용 초기화 (리스트·파일·UI)."""
        self._entries.clear()
        self._save_history()
        if self.text is not None and self.text.winfo_exists():
            self.text.config(state="normal")
            self.text.delete("1.0", "end")
            self.text.config(state="disabled")

    def destroy(self) -> None:
        """로그 창 종료. 종료 전 크기 저장."""
        self._active = False
        if self.win and self.win.winfo_exists():
            self.save_size()
            self.win.destroy()
        self.win = None
        self.text = None


def _map_translation_response_lines(
    response_lines: List[str],
    batch_rows: List[Dict[str, Any]],
    requested_len: int,
    log_callback: Optional[Any] = None,
) -> List[str]:
    """
    API 응답 줄을 배치 행 수에 맞게 매핑.
    <br/>로 인한 줄 분리 시 행별로 병합하여 반환.
    log_callback(msg)가 있으면 로그 메시지 전달, 없으면 print.
    """
    response_len = len(response_lines)
    expected_per_row = [
        1 + ((r.get("original") or "").count("<br/>"))
        for r in batch_rows
    ]
    total_expected = sum(expected_per_row)

    def _log(msg: str) -> None:
        if log_callback:
            log_callback(msg)
        else:
            print(msg, file=sys.stderr)

    if response_len == requested_len:
        return response_lines
    if response_len == total_expected and response_len > requested_len:
        lines_final = []
        idx = 0
        for take in expected_per_row:
            chunk = response_lines[idx : idx + take]
            lines_final.append("<br/>".join(chunk) if chunk else "")
            idx += take
        _log(f"<br/> 줄 분리 보정: 요청={requested_len}행, 응답={response_len}줄 -> 행별 병합 후 {len(lines_final)}행")
        return lines_final
    if response_len > requested_len:
        merged = "<br/>".join(response_lines[requested_len - 1 :])
        lines_final = response_lines[: requested_len - 1] + [merged]
    else:
        lines_final = response_lines + [""] * (requested_len - response_len)
    _log(f"번역 줄 수 불일치 보정: 요청={requested_len}, 응답={response_len} -> {len(lines_final)}줄로 매핑")
    return lines_final


# --- UI 애플리케이션 ---------------------------------------------------------

class SrtVerifierMergerApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("SRT 자막 검수 및 병합 도구 (Subtitle Verifier & Merger)")
        self.root.minsize(1404, 936)   # 기본 대비 가로·세로 150% (936*1.5, 624*1.5)
        self.root.geometry("1602x1131")  # 기본 대비 가로·세로 150% (1068*1.5, 754*1.5)

        # 데이터 저장소 (UI와 분리)
        self.srt_blocks: List[Dict[str, Any]] = []
        self.txt_lines: List[str] = []
        self.rows: List[Dict[str, Any]] = []  # merge_data 결과 (Treeview에 표시)

        # 검색 상태
        self.search_query = ""
        self.search_current_index = -1
        self.search_matches: List[int] = []  # row indices

        # 로드한 파일 경로 (추출/병합 기본 파일명용)
        self.srt_file_path: Optional[str] = None
        self.txt_file_path: Optional[str] = None

        # 마지막 AI 번역에 사용한 모델 (병합 시 파일명 네이밍에 사용)
        self._last_ai_model: Optional[str] = None
        # 사용자 정의 용어집 (원본:번역 한 줄씩, settings.json에 저장)
        self._glossary_text: str = ""

        # 모두 번역(Translate All) 모드 상태
        self.translate_all_var = tk.BooleanVar(value=False)
        self._translate_all_dialog: Optional[tk.Toplevel] = None
        self._translate_all_progress_var: Optional[tk.DoubleVar] = None
        self._translate_all_status_var: Optional[tk.StringVar] = None
        self._translate_all_cancel_requested: bool = False
        self._translate_all_total_batches: int = 0
        self._translate_all_current_batch: int = 0
        self._translate_all_mode_active: bool = False

        self._log_viewer: Optional[LogViewer] = None  # AI 번역 등 로그 창
        self._log_viewer_visible_var = tk.BooleanVar(value=False)  # 작업 내용 체크박스
        self._stats_manager = StatsManager()  # 모델별 누적 성능 데이터
        self._translation_start_time: float = 0.0  # 번역 시작 시각 (time.time())
        self._icon_photo: Optional[Any] = None  # 창 아이콘 참조 유지
        write_readme()  # 실행 시 readme.txt 생성(간단·세부 메뉴얼 기록, 실행 없이 읽기용)
        self._build_ui()
        self._setup_styles()
        self._set_window_icon()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        # 통합 Configure 이벤트 바인딩 (로그 창 우측 + 프로그레스바 좌측 동시 갱신)
        self.root.bind("<Configure>", self._on_main_configure)

    def _on_main_configure(self, event: tk.Event) -> None:
        """메인 윈도우 이동/리사이즈 시 로그 창(우측)·프로그레스바(좌측) 위치 업데이트."""
        if event.widget != self.root:
            return
        if self._log_viewer:
            self._log_viewer.update_position_if_active()
        self._update_translate_all_dialog_position()

    def _update_translate_all_dialog_position(self) -> None:
        """프로그레스바 창을 메인 윈도우 상단 좌측에 배치 (좌측 정렬, 위에 붙음)."""
        if self._translate_all_dialog is None or not self._translate_all_dialog.winfo_exists():
            return
        try:
            self.root.update_idletasks()
            mx = self.root.winfo_x()
            my = self.root.winfo_y()
            self._translate_all_dialog.update_idletasks()
            dh = self._translate_all_dialog.winfo_height()
            x = mx
            y = max(0, my - dh - 30)
            self._translate_all_dialog.geometry(f"+{x}+{y}")
        except (tk.TclError, Exception):
            pass

    def _ensure_log_viewer(self) -> LogViewer:
        """로그 뷰어 생성·표시. 없으면 생성 후 메인 윈도우 우측에 배치. 체크박스 동기화."""
        if self._log_viewer is None:
            self._log_viewer = LogViewer(
                self.root,
                on_user_close_callback=lambda: self._log_viewer_visible_var.set(False),
            )
        self._log_viewer_visible_var.set(True)
        self._log_viewer.show()
        return self._log_viewer

    def _on_log_viewer_visible_toggled(self) -> None:
        """작업 내용 체크박스 토글: 로그 창 표시/숨김."""
        if self._log_viewer_visible_var.get():
            self._ensure_log_viewer()
        else:
            if self._log_viewer:
                self._log_viewer.hide()
        self._save_preferences()

    def _append_log(self, message: str) -> None:
        """로그 메시지 추가 (메인 스레드에서만 호출). 로그 창이 없으면 생성."""
        lv = self._ensure_log_viewer()
        lv.append(message)

    def _set_window_icon(self):
        """PNG 파일을 창 아이콘으로 설정 (Pillow 사용, 없으면 tk.PhotoImage 시도)."""
        def try_load(path: Path) -> bool:
            if not path.exists():
                return False
            if _HAS_PIL:
                try:
                    img = Image.open(path)
                    self._icon_photo = ImageTk.PhotoImage(img)
                    self.root.iconphoto(True, self._icon_photo)
                    return True
                except Exception:
                    pass
            try:
                self._icon_photo = tk.PhotoImage(file=str(path))
                self.root.iconphoto(True, self._icon_photo)
                return True
            except Exception:
                pass
            return False

        base = Path(getattr(sys, "_MEIPASS", _base_dir)) if getattr(sys, "frozen", False) else _base_dir
        for name in _ICON_CANDIDATES:
            if try_load(base / name):
                return
        for name in _ICON_CANDIDATES:
            if try_load(_base_dir / name):
                return

    def _setup_styles(self):
        style = ttk.Style()
        # Treeview 본문/헤더 폰트·행높이는 _apply_viewer_font()에서 적용
        self._apply_viewer_font()
        # Zebra stripe
        style.map("Treeview", background=[("selected", "#0078d4")])
        self.tree.tag_configure("odd", background="#f5f5f5")
        self.tree.tag_configure("even", background="#ffffff")

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=8)
        main.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # ---- 제목 행: 프로그램 이름 + ? (마우스 오버 시 간단 메뉴얼) ----
        header = ttk.Frame(main)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        main.columnconfigure(0, weight=1)
        title_label = ttk.Label(header, text="SRT 자막 검수 및 병합 도구", font=("", 10, "bold"))
        title_label.grid(row=0, column=0, sticky="w")
        # ? 도움말: 프레임 안에 ? 라벨 + 알림 배지(붉은 점) 나란히 배치 (배지가 잘리지 않도록)
        help_frame = tk.Frame(header)
        help_frame.grid(row=0, column=1, padx=(4, 0), sticky="w")
        self._help_label = tk.Label(help_frame, text="  ?  ", cursor="hand2", fg="#0066cc", font=("", 10))
        self._help_label.grid(row=0, column=0, sticky="w", padx=(3, 0))  # ? 우측 3px 이동 → 배지가 왼쪽으로 3px 보이게
        self._help_badge_visible = True
        self._help_badge = tk.Canvas(help_frame, width=10, height=10, highlightthickness=0, bg="SystemButtonFace")
        self._help_badge.create_oval(2, 2, 8, 8, fill="#e53935", outline="#e53935")
        self._help_badge.grid(row=0, column=1, sticky="n", padx=(0, 0))
        self._help_tooltip_id = None
        self._help_leave_after_id = None
        self._tooltip_window: Optional[tk.Toplevel] = None
        self._tooltip_label: Optional[tk.Label] = None
        self._help_label.bind("<Enter>", self._on_help_enter)
        self._help_label.bind("<Leave>", self._on_help_leave)
        self._help_label.bind("<Button-1>", lambda e: self._show_detailed_manual())
        help_frame.bind("<Button-3>", self._on_help_right_click)
        self._help_label.bind("<Button-3>", self._on_help_right_click)
        self._help_badge.bind("<Button-3>", self._on_help_right_click)

        # ---- A. 상단: 파일 컨트롤 패널 ----
        top = ttk.Frame(main)
        top.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        main.columnconfigure(0, weight=1)

        # 1행: 원본 SRT | 번역 TXT | [AI번역 그룹] | 모두 번역 | 번역 범위 | (weight) | 병합하기 | 글자 크기
        ttk.Button(top, text="원본 SRT 열기", command=self._on_open_srt).grid(row=0, column=0, padx=4)
        ttk.Button(top, text="번역 TXT 열기", command=self._on_open_txt).grid(row=0, column=1, padx=4)
        self.ai_translate_btn = ttk.Button(top, text="AI 번역하기", command=self._on_ai_translate)
        self.ai_translate_btn.grid(row=0, column=2, padx=4)
        # 모두 번역 체크박스 (AI 번역 / 범위 입력 사이)
        self.translate_all_chk = ttk.Checkbutton(
            top,
            text="모두 번역",
            variable=self.translate_all_var,
            command=self._on_translate_all_toggled,
        )
        self.translate_all_chk.grid(row=0, column=3, padx=(4, 2))

        ttk.Label(top, text="번역 범위:").grid(row=0, column=4, padx=(8, 2))
        self.translate_range_var = tk.StringVar(value=TRANSLATE_RANGE_PLACEHOLDER)
        self.translate_range_entry = ttk.Entry(top, textvariable=self.translate_range_var, width=28)
        self.translate_range_entry.grid(row=0, column=5, padx=2)
        self._translate_range_placeholder_active = True
        self.translate_range_entry.bind("<FocusIn>", self._on_translate_range_focus_in)
        self.translate_range_entry.bind("<FocusOut>", self._on_translate_range_focus_out)
        self.translate_range_entry.bind("<Return>", lambda e: self._on_ai_translate())
        self._range_tooltip_after_id: Optional[str] = None
        self._range_tooltip_win: Optional[tk.Toplevel] = None
        self.translate_range_entry.bind("<Enter>", lambda e: self._schedule_range_tooltip())
        self.translate_range_entry.bind("<Leave>", lambda e: self._cancel_range_tooltip())
        self.translate_range_entry.bind("<KeyPress>", self._on_translate_range_keypress)

        ttk.Label(top, text="AI 모델:").grid(row=0, column=6, padx=(8, 2))
        self.ai_model_combo = ttk.Combobox(top, values=AI_MODEL_OPTIONS, state="readonly", width=18)
        self.ai_model_combo.grid(row=0, column=7, padx=2)
        self.ai_model_combo.bind("<<ComboboxSelected>>", self._on_ai_model_changed)
        self.ai_lang_combo = ttk.Combobox(top, values=LANG_DISPLAYS, state="readonly", width=10)
        self.ai_lang_combo.grid(row=0, column=8, padx=4)
        self.ai_lang_combo.bind("<<ComboboxSelected>>", lambda e: self._save_preferences())
        self.glossary_btn = ttk.Button(top, text="용어집 설정", command=self._on_glossary_settings)
        self.glossary_btn.grid(row=0, column=9, padx=4)
        top.columnconfigure(10, weight=1)
        self.merge_btn = ttk.Button(top, text="병합하기(Merge)", command=self._on_merge)
        self.merge_btn.grid(row=0, column=11, padx=4)
        self.log_viewer_chk = ttk.Checkbutton(
            top,
            text="작업 내용",
            variable=self._log_viewer_visible_var,
            command=self._on_log_viewer_visible_toggled,
        )
        self.log_viewer_chk.grid(row=0, column=12, padx=(8, 4))
        ttk.Label(top, text="글자 크기:").grid(row=0, column=13, padx=(12, 4))
        self.font_size_combo = ttk.Combobox(top, values=FONT_LABELS, state="readonly", width=10)
        self.font_size_combo.grid(row=0, column=14, padx=(0, 4))
        self.font_size_combo.bind("<<ComboboxSelected>>", lambda e: self._on_font_size_changed())

        # 모델 평균 속도 라벨 (AI 모델 콤보박스 아래)
        self._model_speed_var = tk.StringVar(value="")
        self._model_speed_label = ttk.Label(top, textvariable=self._model_speed_var, foreground="#555555", font=("", 8))
        self._model_speed_label.grid(row=1, column=6, columnspan=2, sticky="w", padx=(8, 2))

        # 2행: 추출하기 그룹 (AI 번역하기와 같은 시작 컬럼)
        self.export_btn = ttk.Button(top, text="추출하기", command=self._on_export)
        self.export_btn.grid(row=1, column=2, padx=4)
        self.lang_combo = ttk.Combobox(top, values=LANG_DISPLAYS, state="readonly", width=12)
        self.lang_combo.grid(row=1, column=3, padx=4)
        self.lang_combo.bind("<<ComboboxSelected>>", lambda e: self._save_preferences())

        # ---- B. 중단: Treeview + 스크롤 ----
        mid = ttk.Frame(main)
        mid.grid(row=2, column=0, sticky="nsew", pady=4)
        main.rowconfigure(2, weight=1)

        scroll = ttk.Scrollbar(mid)
        self.tree = ttk.Treeview(
            mid,
            columns=("timecode", "original", "translated"),
            show="headings",
            height=39,   # 창 크기 150%에 맞춘 표시 행 수 (26 * 1.5)
            yscrollcommand=scroll.set,
            selectmode="browse",
        )
        scroll.config(command=self.tree.yview)

        self.tree.heading("timecode", text="순번/타임코드")
        self.tree.heading("original", text="원본 텍스트 (Original)")
        self.tree.heading("translated", text="번역 텍스트 (Translated)")
        # 첫 번째 열: 고정 너비(글자 크기별로 _apply_viewer_font에서 설정), stretch=False, 가운데 정렬
        self.tree.column("timecode", width=250, minwidth=180, stretch=False, anchor="center")
        # 나머지 열: stretch=True — 창이 커지면 남은 공간을 나눠서 채움
        self.tree.column("original", width=255, minwidth=90, stretch=True)   # 30% 감소 (364→255)
        self.tree.column("translated", width=473, minwidth=170, stretch=True)  # 동일량 증가 (364→473)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        mid.columnconfigure(0, weight=1)
        mid.rowconfigure(0, weight=1)
        # 번역 텍스트 열 더블클릭 시 인라인 편집
        self.tree.bind("<Double-1>", self._on_tree_double_click)
        self._inplace_entry: Optional[tk.Entry] = None
        self._inplace_iid: Optional[str] = None
        self._inplace_row_index: Optional[int] = None

        # ---- C. 하단: 검색 + 상태바 ----
        bottom = ttk.Frame(main)
        bottom.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        main.columnconfigure(0, weight=1)

        ttk.Label(bottom, text="검색:").grid(row=0, column=0, padx=(0, 4))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(bottom, textvariable=self.search_var, width=30)
        self.search_entry.grid(row=0, column=1, padx=4)
        self.search_entry.bind("<Return>", lambda e: self._on_find())
        ttk.Button(bottom, text="찾기(Find) Ctrl+F", command=self._on_find).grid(row=0, column=2, padx=4)
        self.root.bind("<Control-f>", lambda e: (self._focus_search_entry(), "break")[-1])

        self.status_var = tk.StringVar(value="준비됨. 원본 SRT 또는 번역 TXT를 열어주세요.")
        status = ttk.Label(bottom, textvariable=self.status_var, relief="sunken", anchor="w")
        status.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(6, 0))
        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_bar = ttk.Progressbar(bottom, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(4, 0))
        self.progress_bar.grid_remove()  # 번역 중에만 표시
        self._progress_after_id: Optional[str] = None  # Fake Progress 타이머 (root.after id)
        self._translation_done_flag = False
        bottom.columnconfigure(1, weight=1)

        # Treeview 생성 후 저장된 설정(언어·글자 크기) 불러오기 (_apply_viewer_font에서 self.tree 사용)
        self._load_preferences()
        self._update_merge_button_state()  # 초기: 병합하기 비활성화
        self._update_export_and_ai_translate_state()  # 초기: 원본 없음 → 추출/AI번역 비활성화

    def _on_help_enter(self, event: tk.Event) -> None:
        """? 위젯에 마우스 진입 시 잠시 후 간단 메뉴얼 툴팁 표시."""
        if self._help_leave_after_id:
            self.root.after_cancel(self._help_leave_after_id)
            self._help_leave_after_id = None
        if self._help_tooltip_id:
            self.root.after_cancel(self._help_tooltip_id)
            self._help_tooltip_id = None
        self._help_tooltip_id = self.root.after(400, self._show_simple_tooltip)

    def _on_help_leave(self, event: Optional[tk.Event] = None) -> None:
        """? 위젯에서 마우스 이탈 시: 툴팁으로 이동할 수 있도록 짧은 지연 후 숨김."""
        if self._help_tooltip_id:
            self.root.after_cancel(self._help_tooltip_id)
            self._help_tooltip_id = None
        if self._tooltip_window and self._tooltip_window.winfo_exists():
            # 툴팁이 이미 떠 있으면, 툴팁 위로 마우스가 갈 수 있으므로 200ms 지연 후 닫기
            self._help_leave_after_id = self.root.after(200, self._destroy_tooltip)
        else:
            self._destroy_tooltip()

    def _destroy_tooltip(self) -> None:
        """툴팁 창 닫기."""
        self._help_leave_after_id = None
        if self._tooltip_window and self._tooltip_window.winfo_exists():
            self._tooltip_window.destroy()
            self._tooltip_window = None
        self._tooltip_label = None

    def _get_simple_manual_text(self) -> str:
        """알림 배지 표시 여부에 따라 간단 매뉴얼 텍스트 반환."""
        if self._help_badge_visible:
            return MANUAL_SIMPLE + "\n(알림: 우클릭 시 붉은 점 사라짐)"
        return MANUAL_SIMPLE

    def _on_help_right_click(self, event: tk.Event) -> None:
        """? 영역 우클릭: 알림 배지 숨기고, 떠 있는 툴팁 문구에서 알림 문구 제거."""
        self._help_badge_visible = False
        self._help_badge.grid_forget()
        if self._tooltip_label and self._tooltip_label.winfo_exists():
            self._tooltip_label.config(text=MANUAL_SIMPLE)

    def _show_simple_tooltip(self) -> None:
        """간단 메뉴얼 툴팁 창 표시 (배지 상태에 따라 알림 문구 포함/제외)."""
        self._help_tooltip_id = None
        if self._tooltip_window and self._tooltip_window.winfo_exists():
            return
        tw = tk.Toplevel(self.root)
        tw.wm_overrideredirect(True)
        tw.attributes("-topmost", True)
        tw.wm_geometry("+0+0")
        f = tk.Frame(tw, padx=10, pady=8, bg="SystemButtonFace", relief="solid", borderwidth=1)
        f.pack(fill="both", expand=True)
        lbl = tk.Label(f, text=self._get_simple_manual_text(), justify="left", wraplength=320, bg="SystemButtonFace", font=("맑은 고딕", 9))
        lbl.pack(anchor="w")
        self._tooltip_label = lbl
        tw.update_idletasks()
        self.root.update_idletasks()
        self._help_label.update_idletasks()
        try:
            x = self._help_label.winfo_rootx() + self._help_label.winfo_width() + 4
            y = self._help_label.winfo_rooty()
            tw.wm_geometry(f"+{x}+{y}")
        except Exception:
            pass
        self._tooltip_window = tw
        tw.lift()
        # 툴팁 위로 마우스가 들어오면 지연 닫기 취소
        for w in (f, lbl):
            w.bind("<Enter>", lambda e: self._cancel_tooltip_close())
        tw.bind("<Leave>", lambda e: self._on_help_leave(None))

    def _cancel_tooltip_close(self) -> None:
        """툴팁 지연 닫기 취소 (마우스가 툴팁 위에 있음)."""
        if self._help_leave_after_id:
            self.root.after_cancel(self._help_leave_after_id)
            self._help_leave_after_id = None

    def _show_detailed_manual(self) -> None:
        """자세한 메뉴얼 창 표시 (? 클릭 시)."""
        if self._help_leave_after_id:
            self.root.after_cancel(self._help_leave_after_id)
            self._help_leave_after_id = None
        if self._help_tooltip_id:
            self.root.after_cancel(self._help_tooltip_id)
            self._help_tooltip_id = None
        self._destroy_tooltip()
        win = tk.Toplevel(self.root)
        win.title("자세한 메뉴얼")
        win.minsize(420, 360)
        win.geometry("500x480")
        # '순번/타임코드' 열(테이블 상단) 아래쪽에 창 위치
        try:
            self.root.update_idletasks()
            self.tree.update_idletasks()
            tx = self.tree.winfo_rootx()
            ty = self.tree.winfo_rooty() + 28
            win.geometry(f"500x480+{tx}+{ty}")
        except Exception:
            pass
        f = ttk.Frame(win, padding=8)
        f.pack(fill="both", expand=True)
        scroll = ttk.Scrollbar(f)
        txt = tk.Text(f, wrap="word", yscrollcommand=scroll.set, font=("맑은 고딕", 9), padx=8, pady=8)
        scroll.config(command=txt.yview)
        txt.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        txt.insert("1.0", MANUAL_DETAILED)
        txt.config(state="disabled")

    def _tree_iid(self, row_index: int) -> str:
        """Treeview iid (0번 행이 '0'이면 일부 환경에서 누락되므로 접두사 사용)."""
        return f"r_{row_index}"

    def _on_tree_double_click(self, event: tk.Event) -> None:
        """Treeview 더블클릭: 번역 텍스트 열(#3)일 때만 인라인 편집 시작."""
        if self._inplace_entry:
            return
        item = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if not item or col != "#3":
            return
        try:
            row_index = int(item[2:] if item.startswith("r_") else item)
        except ValueError:
            return
        bbox = self.tree.bbox(item, col)
        if not bbox:
            return
        x, y, w, h = bbox
        mid = self.tree.master
        # 셀 위치를 부모(mid) 기준 좌표로 변환
        cx = self.tree.winfo_x() + x
        cy = self.tree.winfo_y() + y
        current = self.tree.set(item, "translated")
        entry = tk.Entry(mid, font=("Segoe UI", self._get_viewer_font_pt()))
        entry.place(x=cx, y=cy, width=max(w, 100), height=h)
        entry.insert(0, current)
        entry.select_range(0, tk.END)
        entry.focus_set()
        entry.bind("<Return>", lambda e: self._commit_inplace_edit())
        entry.bind("<Escape>", lambda e: self._cancel_inplace_edit())
        entry.bind("<FocusOut>", lambda e: self.root.after(50, self._commit_inplace_edit))
        self._inplace_entry = entry
        self._inplace_iid = item
        self._inplace_row_index = row_index

    def _commit_inplace_edit(self) -> None:
        """인라인 편집 내용을 Treeview와 self.rows에 반영 후 입력창 제거."""
        if not self._inplace_entry or not self._inplace_entry.winfo_exists():
            self._inplace_entry = None
            self._inplace_iid = None
            self._inplace_row_index = None
            return
        value = self._inplace_entry.get()
        iid = self._inplace_iid
        row_index = self._inplace_row_index
        self._inplace_entry.destroy()
        self._inplace_entry = None
        self._inplace_iid = None
        self._inplace_row_index = None
        if iid and row_index is not None and 0 <= row_index < len(self.rows):
            self.tree.set(iid, "translated", value)
            self.rows[row_index]["translated"] = value
            self._update_merge_button_state()

    def _cancel_inplace_edit(self) -> None:
        """인라인 편집 취소(입력창만 제거)."""
        if self._inplace_entry and self._inplace_entry.winfo_exists():
            self._inplace_entry.destroy()
        self._inplace_entry = None
        self._inplace_iid = None
        self._inplace_row_index = None

    def _refresh_tree(self):
        """self.rows 기준으로 Treeview 갱신 (Zebra stripe 적용). 행 간격 한 줄 기준 고정."""
        if self._inplace_entry and self._inplace_entry.winfo_exists():
            self._commit_inplace_edit()
        for item in self.tree.get_children():
            self.tree.delete(item)
        # 행 간격 한 줄 기준, 현재 글자 크기에 맞는 행 높이 유지
        ttk.Style().configure("Treeview", rowheight=self._get_viewer_rowheight())
        for i, row in enumerate(self.rows):
            tag = "even" if i % 2 == 0 else "odd"
            self.tree.insert(
                "",
                "end",
                iid=self._tree_iid(i),
                values=(
                    f'{row["index"]} ({row["timecode"]})',
                    row.get("original", ""),
                    row.get("translated", ""),
                ),
                tags=(tag,),
            )

    def _on_open_srt(self):
        path = filedialog.askopenfilename(
            title="원본 SRT 선택",
            filetypes=[("SRT 파일", "*.srt"), ("모든 파일", "*.*")],
        )
        if not path:
            return
        content = _read_file_utf(path, "utf-8-sig", "오류")
        if content is None:
            return
        self.srt_file_path = path
        self.srt_blocks = parse_srt(content)
        self._merge_and_refresh()
        if self.rows:
            first_index = self.rows[0].get("index", 1)
            self.translate_range_var.set(str(first_index))
            self._translate_range_placeholder_active = False
        self.status_var.set(f"원본 SRT 로드됨: {path} — 총 {len(self.srt_blocks)}개 블록.")

    def _on_open_txt(self):
        path = filedialog.askopenfilename(
            title="번역 TXT 선택",
            filetypes=[("텍스트 파일", "*.txt"), ("모든 파일", "*.*")],
        )
        if not path:
            return
        content = _read_file_utf(path, "utf-8", "오류")
        if content is None:
            return
        self.txt_file_path = path
        self.txt_lines = parse_txt_lines(content)
        self._merge_and_refresh()
        self.status_var.set(f"번역 TXT 로드됨: {path} — 총 {len(self.txt_lines)}줄.")
        if self.srt_blocks and len(self.srt_blocks) != len(self.txt_lines):
            messagebox.showwarning(
                "라인 수 불일치",
                f"SRT 블록 수({len(self.srt_blocks)})와 TXT 라인 수({len(self.txt_lines)})가 다릅니다.\n"
                "로딩은 완료되었습니다. 화면에서 어디가 밀렸는지 확인해 주세요.",
            )

    def _rows_have_translated(self) -> bool:
        """번역 텍스트에 내용이 하나라도 있으면 True."""
        return any((r.get("translated") or "").strip() for r in self.rows)

    def _rows_have_original(self) -> bool:
        """원본 텍스트에 내용이 하나라도 있으면 True."""
        return bool(self.rows) and any((r.get("original") or "").strip() for r in self.rows)

    def _update_merge_button_state(self) -> None:
        """번역 텍스트에 내용이 하나라도 있으면 병합하기 활성화, 없으면 비활성화(암전)."""
        if not self.rows:
            self.merge_btn.config(state="disabled")
            return
        self.merge_btn.config(state="normal" if self._rows_have_translated() else "disabled")

    def _update_export_and_ai_translate_state(self) -> None:
        """원본 텍스트에 내용이 하나라도 있으면 추출하기·AI번역 관련 메뉴 활성화, 없으면 비활성화(암전)."""
        has_original = self._rows_have_original()
        self.export_btn.config(state="normal" if has_original else "disabled")
        self.ai_translate_btn.config(state="normal" if has_original else "disabled")
        self.translate_range_entry.config(state="normal" if has_original else "disabled")
        self.ai_model_combo.config(state="readonly" if has_original else "disabled")
        self.ai_lang_combo.config(state="readonly" if has_original else "disabled")
        self.glossary_btn.config(state="normal" if has_original else "disabled")

    def _merge_and_refresh(self):
        """SRT 블록과 TXT 라인을 병합한 뒤 Treeview 갱신."""
        if not self.srt_blocks:
            self.rows = []
        else:
            self.rows = merge_data(self.srt_blocks, self.txt_lines)
        self.search_current_index = -1
        self.search_matches = []
        self._refresh_tree()
        self.tree.heading("translated", text="번역 텍스트 (Translated)")
        self._update_merge_button_state()
        self._update_export_and_ai_translate_state()

    def _get_selected_lang_code(self) -> str:
        """추출하기용 언어 드롭다운에서 선택된 언어 코드 반환 (예: EN, KR)."""
        return _lang_code_for_display(self.lang_combo.get() or LANG_DISPLAYS[0])

    def _get_ai_lang_code(self) -> str:
        """AI 번역 대상 언어 드롭다운에서 선택된 언어 코드 반환 (병합 네이밍용)."""
        return _lang_code_for_display(self.ai_lang_combo.get() or LANG_DISPLAYS[0])

    def _get_viewer_font_pt(self) -> int:
        """뷰어 글자 크기 콤보에서 현재 선택된 pt 반환."""
        label = self.font_size_combo.get()
        for name, pt in FONT_SIZE_OPTIONS:
            if name == label:
                return pt
        return DEFAULT_FONT_PT

    def _get_viewer_rowheight(self) -> int:
        """현재 폰트 크기에 맞는 Treeview 행 높이 반환."""
        return FONT_ROWHEIGHT.get(self._get_viewer_font_pt(), 28)

    def _apply_viewer_font(self) -> None:
        """Treeview 본문·헤더 폰트 크기, 행 높이, 첫 번째 열 너비를 현재 선택값으로 적용."""
        pt = self._get_viewer_font_pt()
        rowheight = self._get_viewer_rowheight()
        style = ttk.Style()
        style.configure("Treeview", font=("Segoe UI", pt), rowheight=rowheight)
        style.configure("Treeview.Heading", font=("Segoe UI", pt, "bold"))
        # 첫 번째 열(순번/타임코드) 너비를 글자 크기에 비례해 설정, stretch=False 유지
        col_width = FONT_COLUMN_WIDTH.get(pt, 250)
        self.tree.column("#1", width=col_width, stretch=False, anchor="center")

    def _on_font_size_changed(self) -> None:
        """글자 크기 콤보 선택 시 즉시 스타일 반영 및 설정 저장."""
        self._apply_viewer_font()
        self._save_preferences()
        # 이미 로드된 트리 있으면 행 높이만 다시 적용 (화면 갱신)
        if self.rows:
            ttk.Style().configure("Treeview", rowheight=self._get_viewer_rowheight())

    def _load_preferences(self):
        """저장된 언어·글자 크기 불러오기 (프로그램 시작 시)."""
        prefs: Dict[str, Any] = {}
        try:
            if PREFS_PATH.exists():
                with open(PREFS_PATH, "r", encoding="utf-8") as f:
                    prefs = json.load(f)
        except Exception:
            pass
        # 언어
        code = prefs.get("lang_code")
        if code:
            for _code, label in LANG_OPTIONS:
                if _code == code:
                    self.lang_combo.set(label)
                    break
        else:
            self.lang_combo.set(LANG_DISPLAYS[0])
        # 글자 크기 (기본: 보통)
        font_label = prefs.get("font_size", DEFAULT_FONT_LABEL)
        self.font_size_combo.set(font_label if font_label in FONT_LABELS else DEFAULT_FONT_LABEL)
        # AI 번역 대상 언어 (기본: 영어)
        ai_lang = prefs.get("ai_lang", LANG_DISPLAYS[0])
        self.ai_lang_combo.set(ai_lang if ai_lang in LANG_DISPLAYS else LANG_DISPLAYS[0])
        # AI 모델 (기본: 자동)
        ai_model = prefs.get("ai_model", AI_MODEL_AUTO)
        if ai_model == "자동 (API에서 선택)":
            ai_model = AI_MODEL_AUTO
        self.ai_model_combo.set(ai_model if ai_model in AI_MODEL_OPTIONS else AI_MODEL_AUTO)
        # 사용자 정의 용어집
        self._glossary_text = prefs.get("glossary", "") or ""
        # 작업 내용(로그 창) 표시 여부
        log_visible = prefs.get("log_viewer_visible", False)
        self._log_viewer_visible_var.set(log_visible)
        self._apply_viewer_font()
        # 모델별 평균 속도 라벨 초기 표시
        self._update_model_speed_label()
        # 로그 창 표시가 저장되어 있으면 지연 표시 (UI 준비 후)
        if log_visible:
            self.root.after(100, self._show_log_viewer_if_checked)

    def _show_log_viewer_if_checked(self) -> None:
        """체크박스가 체크되어 있으면 로그 창 표시 (초기 로드용)."""
        if self._log_viewer_visible_var.get():
            self._ensure_log_viewer()

    def _save_preferences(self):
        """언어·글자 크기 설정 저장 (변경 시·종료 시)."""
        try:
            prefs: Dict[str, Any] = {}
            if PREFS_PATH.exists():
                with open(PREFS_PATH, "r", encoding="utf-8") as f:
                    prefs = json.load(f)
            prefs["lang_code"] = self._get_selected_lang_code()
            prefs["font_size"] = self.font_size_combo.get()
            prefs["ai_lang"] = self.ai_lang_combo.get()
            prefs["ai_model"] = self.ai_model_combo.get()
            prefs["glossary"] = self._glossary_text
            prefs["log_viewer_visible"] = self._log_viewer_visible_var.get()
            with open(PREFS_PATH, "w", encoding="utf-8") as f:
                json.dump(prefs, f, ensure_ascii=False)
        except Exception:
            pass

    def _on_close(self):
        """창 닫기: 설정 저장 후 종료."""
        self._save_preferences()
        if self._log_viewer:
            self._log_viewer.destroy()
            self._log_viewer = None
        self.root.destroy()

    def _get_gemini_api_key(self) -> Optional[str]:
        """사용 중인 Gemini API 키 반환 (.env 등에서 로드)."""
        return load_gemini_api_key()

    def _on_glossary_settings(self) -> None:
        """용어집 설정 팝업: 원본:번역 형식 입력, 저장 시 settings.json에 유지."""
        win = tk.Toplevel(self.root)
        win.title("사용자 정의 용어집 (Custom Glossary)")
        win.transient(self.root)
        win.grab_set()
        win.geometry("520x320")
        ttk.Label(
            win,
            text="원본단어:번역단어 형식으로 한 줄에 하나씩 입력 (예: Stark:스타크, Winterfell:윈터펠)",
            font=("", 9),
        ).pack(anchor="w", padx=10, pady=(10, 4))
        frame = ttk.Frame(win)
        frame.pack(fill="both", expand=True, padx=10, pady=4)
        text_scroll = ttk.Scrollbar(frame)
        text_scroll.pack(side="right", fill="y")
        text_widget = tk.Text(frame, wrap="word", height=12, width=60, yscrollcommand=text_scroll.set, font=("Consolas", 10))
        text_widget.pack(side="left", fill="both", expand=True)
        text_scroll.config(command=text_widget.yview)
        text_widget.insert("1.0", self._glossary_text)
        text_widget.focus_set()

        def save_and_close() -> None:
            self._glossary_text = text_widget.get("1.0", tk.END).strip()
            self._save_preferences()
            win.destroy()

        btn_frame = ttk.Frame(win)
        btn_frame.pack(pady=(8, 10))
        ttk.Button(btn_frame, text="저장", command=save_and_close).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="닫기", command=save_and_close).pack(side="left", padx=4)
        win.protocol("WM_DELETE_WINDOW", save_and_close)

    def _on_translate_range_focus_in(self, event: tk.Event) -> None:
        if self._translate_range_placeholder_active:
            self.translate_range_var.set("")
            self._translate_range_placeholder_active = False

    def _on_translate_range_focus_out(self, event: tk.Event) -> None:
        if not self.translate_range_var.get().strip():
            self.translate_range_var.set(TRANSLATE_RANGE_PLACEHOLDER)
            self._translate_range_placeholder_active = True
            return

    def _on_ai_model_changed(self, event=None) -> None:
        """AI 모델 콤보박스 변경 시: 환경설정 저장 + 평균 속도 라벨 갱신."""
        self._save_preferences()
        self._update_model_speed_label()

    def _update_model_speed_label(self) -> None:
        """현재 선택된 AI 모델의 누적 평균 속도를 라벨에 표시."""
        selected = (self.ai_model_combo.get() or "").strip()
        if not selected or selected == AI_MODEL_AUTO:
            # "자동" 모드: 모든 모델의 합산 평균 표시
            all_data = self._stats_manager._data
            total_time = sum(v.get("total_time", 0) for v in all_data.values())
            total_items = sum(v.get("total_items", 0) for v in all_data.values())
            if total_items > 0:
                avg = total_time / total_items
                self._model_speed_var.set(
                    f"평균 {avg:.2f}s/개 ({total_items:,}개)"
                )
            else:
                self._model_speed_var.set("")
            return
        result = self._stats_manager.get_average(selected)
        if result is not None:
            avg, count = result
            self._model_speed_var.set(
                f"평균 {avg:.2f}s/개 ({count:,}개)"
            )
        else:
            self._model_speed_var.set("")

    def _on_translate_all_toggled(self) -> None:
        """모두 번역 체크박스 토글 시 입력 힌트 초기화."""
        if self.translate_all_var.get():
            # 모두 번역 모드: 시작 번호만 사용하므로 플레이스홀더 제거
            if self._translate_range_placeholder_active:
                self.translate_range_var.set("")
                self._translate_range_placeholder_active = False
        else:
            # 일반 모드로 복귀 시, 입력이 비어 있으면 다시 플레이스홀더 표시
            if not (self.translate_range_var.get() or "").strip():
                self.translate_range_var.set(TRANSLATE_RANGE_PLACEHOLDER)
                self._translate_range_placeholder_active = True

    def _schedule_range_tooltip(self) -> None:
        self._cancel_range_tooltip()
        self._range_tooltip_after_id = self.root.after(500, self._show_range_tooltip)

    def _cancel_range_tooltip(self) -> None:
        if self._range_tooltip_after_id is not None:
            self.root.after_cancel(self._range_tooltip_after_id)
            self._range_tooltip_after_id = None
        if self._range_tooltip_win is not None and self._range_tooltip_win.winfo_exists():
            self._range_tooltip_win.destroy()
        self._range_tooltip_win = None

    def _show_range_tooltip(self) -> None:
        self._range_tooltip_after_id = None
        self._cancel_range_tooltip()
        tw = tk.Toplevel(self.root)
        tw.wm_overrideredirect(True)
        # 모두 번역 모드 여부에 따라 안내 문구 변경
        if self.translate_all_var.get():
            text = "번역을 시작할 순번을 입력하세요. (여기부터 끝까지 번역)"
        else:
            text = "번역할 자막 번호를 입력하세요. (범위: -, 개별: ,)"
        lbl = ttk.Label(tw, text=text, relief="solid", padding=4)
        lbl.pack()
        tw.update_idletasks()
        ex = self.translate_range_entry.winfo_rootx()
        ey = self.translate_range_entry.winfo_rooty() + self.translate_range_entry.winfo_height() + 2
        tw.wm_geometry(f"+{ex}+{ey}")
        tw.lift()
        self._range_tooltip_win = tw
        tw.bind("<Leave>", lambda e: self._cancel_range_tooltip())

    def _on_translate_range_keypress(self, event: tk.Event) -> Optional[str]:
        """
        모두 번역 모드에서는 시작 번호만 허용.
        숫자/제어키 외 문자는 막고, 특히 '-'나 ',' 입력 시 경고 후 취소.
        """
        if not self.translate_all_var.get():
            return None
        ch = event.char
        if not ch:
            return None
        # 허용: 숫자, 백스페이스, Delete, Enter
        if ch.isdigit() or ord(ch) in (8, 127, 13):
            return None
        messagebox.showwarning("입력 제한", "모두 번역 모드에서는 시작 번호만 입력하세요.")
        return "break"

    def _get_translate_range_input(self) -> str:
        """번역 범위 입력창 실제 값 (placeholder면 빈 문자열)."""
        s = (self.translate_range_var.get() or "").strip()
        if s == TRANSLATE_RANGE_PLACEHOLDER or not s:
            return ""
        return s

    def _get_translate_all_start_index(self, max_index: int) -> Optional[int]:
        """
        모두 번역 모드에서 시작 순번(1-based) 반환.
        빈 입력이면 1, 잘못된 형식/범위면 경고 후 None.
        """
        s = (self.translate_range_var.get() or "").strip()
        if s == TRANSLATE_RANGE_PLACEHOLDER or not s:
            return 1
        try:
            n = int(s)
        except ValueError:
            messagebox.showwarning(
                "입력 오류",
                "모두 번역 모드에서는 시작 번호만 입력하세요.\n예: 1 또는 10",
            )
            return None
        if n < 1 or n > max_index:
            messagebox.showwarning(
                "범위 오류",
                f"시작 번호는 1부터 {max_index} 사이여야 합니다.",
            )
            return None
        return n

    def _parse_translate_range(self, s: str) -> Tuple[Optional[List[int]], bool]:
        """입력 문자열 파싱 → (1-based 정렬된 순번 리스트, 입력에 '-' 포함 여부). 실패 시 (None, False)."""
        s = (s or "").strip().replace("，", ",").replace("－", "-")
        if not s:
            return ([], False)
        had_hyphen = "-" in s
        seen: Set[int] = set()
        for part in s.split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                a_b = part.split("-", 1)
                try:
                    lo = int(a_b[0].strip())
                    hi = int(a_b[1].strip())
                    if lo > hi:
                        lo, hi = hi, lo
                    for n in range(lo, hi + 1):
                        if n >= 1:
                            seen.add(n)
                except ValueError:
                    return (None, had_hyphen)
            else:
                try:
                    n = int(part.strip())
                    if n >= 1:
                        seen.add(n)
                except ValueError:
                    return (None, had_hyphen)
        if not seen:
            return ([], had_hyphen)
        return (sorted(seen), had_hyphen)

    def _validate_translate_range_and_maybe_correct(
        self, max_index: int
    ) -> Tuple[bool, Optional[List[int]]]:
        """
        번역 범위 검증. 실패 시 입력창 수정·메시지 후 (False, None).
        성공 시 (True, 0-based 인덱스 리스트). 빈 입력 = 전체 → (True, None)으로 전체 사용.
        """
        min_index = 1
        raw = self._get_translate_range_input()
        if not raw:
            return (True, None)
        parsed, had_hyphen = self._parse_translate_range(raw)
        if parsed is None:
            messagebox.showwarning(
                "입력 오류",
                "번역 범위 형식을 확인해 주세요.\n예: 1-10 또는 1,3,5",
            )
            return (False, None)
        if not parsed:
            return (True, None)
        out_of_range = [n for n in parsed if n < min_index or n > max_index]
        if out_of_range:
            if had_hyphen:
                valid = [n for n in parsed if min_index <= n <= max_index]
                if not valid:
                    self.translate_range_var.set("")
                    self._translate_range_placeholder_active = True
                    messagebox.showwarning(
                        "범위 조정",
                        "유효하지 않은 순번이 포함되어 있어 입력을 비웠습니다. 다시 입력해 주세요.",
                    )
                    return (False, None)
                lo, hi = min(valid), max(valid)
                new_text = f"{lo}-{hi}" if lo != hi else str(lo)
                self.translate_range_var.set(new_text)
                self._translate_range_placeholder_active = False
                messagebox.showwarning(
                    "범위 조정",
                    f"유효하지 않은 순번이 포함되어 있어 {new_text}(으)로 조정했습니다. 다시 시도해 주세요.",
                )
                return (False, None)
            else:
                bad = ", ".join(str(n) for n in sorted(set(out_of_range)))
                messagebox.showwarning(
                    "순번 오류",
                    f"순번 {bad}번은 존재하지 않습니다. 확인 후 다시 입력해 주세요.",
                )
                return (False, None)
        if len(parsed) > AI_TRANSLATE_RANGE_MAX:
            trimmed = sorted(parsed)[: AI_TRANSLATE_RANGE_MAX]
            if len(trimmed) == 1:
                new_text = str(trimmed[0])
            elif trimmed == list(range(trimmed[0], trimmed[-1] + 1)):
                new_text = f"{trimmed[0]}-{trimmed[-1]}"
            else:
                new_text = ",".join(str(n) for n in trimmed)
            self.translate_range_var.set(new_text)
            self._translate_range_placeholder_active = False
            messagebox.showwarning(
                "개수 제한",
                f"한 번에 최대 {AI_TRANSLATE_RANGE_MAX}개까지만 번역 가능합니다. 범위를 조정했습니다.",
            )
            return (False, None)
        indices_0based = [n - 1 for n in parsed]
        return (True, indices_0based)

    # ---- Fake Progress (0% → 99% in 5s, 50ms/1%; 완료 시 100% 후 0.5초 뒤 숨김) ----
    FAKE_PROGRESS_INTERVAL_MS = 50  # 5000ms / 100단계 ≈ 50ms
    FAKE_PROGRESS_CAP = 99
    HIDE_PROGRESS_AFTER_MS = 500

    def _start_fake_progress(self) -> None:
        """프로그레스 바 표시, 0%로 초기화, 1%씩 증가하는 타이머 시작 (5초에 99% 도달)."""
        self._translation_done_flag = False
        self.progress_bar.grid()
        self.progress_var.set(0)
        self._progress_after_id = self.root.after(self.FAKE_PROGRESS_INTERVAL_MS, self._tick_fake_progress)

    def _tick_fake_progress(self) -> None:
        """타이머 콜백: 1% 증가, 99% 미만이고 번역 미완료일 때만 다음 타이머 예약."""
        self._progress_after_id = None
        if self._translation_done_flag:
            return
        current = self.progress_var.get()
        if current >= self.FAKE_PROGRESS_CAP:
            return  # 99%에서 대기, 타이머 중지
        self.progress_var.set(current + 1)
        self._progress_after_id = self.root.after(self.FAKE_PROGRESS_INTERVAL_MS, self._tick_fake_progress)

    def _hide_progress_bar(self) -> None:
        """프로그레스 바 숨기기 (메인 스레드에서만 호출)."""
        self.progress_bar.grid_remove()

    # ---- 모두 번역(Translate All) 전용 진행 다이얼로그 ----

    def _start_translate_all_progress(self, total_batches: int) -> None:
        """모두 번역 모드용 모달 진행 다이얼로그 생성."""
        self._translate_all_total_batches = max(1, total_batches)
        self._translate_all_current_batch = 0
        self._translate_all_cancel_requested = False

        if self._translate_all_dialog is not None and self._translate_all_dialog.winfo_exists():
            try:
                self._translate_all_dialog.destroy()
            except Exception:
                pass

        win = tk.Toplevel(self.root)
        win.title("모두 번역 진행 중")
        win.resizable(False, False)
        win.transient(self.root)
        # grab_set 미사용 — 메인 윈도우 드래그 가능하도록

        status_var = tk.StringVar(value=f"진행 중... (0/{self._translate_all_total_batches} 단계)")
        pb_var = tk.DoubleVar(value=0.0)
        ttk.Label(win, textvariable=status_var).pack(padx=12, pady=(10, 4))
        pb = ttk.Progressbar(win, variable=pb_var, maximum=100, length=280)
        pb.pack(padx=12, pady=(0, 8))
        ttk.Button(win, text="취소", command=self._on_translate_all_cancel).pack(pady=(0, 10))

        win.protocol("WM_DELETE_WINDOW", self._on_translate_all_cancel)

        self._translate_all_dialog = win
        self._translate_all_progress_var = pb_var
        self._translate_all_status_var = status_var

        # 좌측 자석 배치 (메인 윈도우 왼쪽에 붙임)
        win.update_idletasks()
        self._update_translate_all_dialog_position()

    def _update_translate_all_progress_ui(self, current_batch: int, total_batches: int) -> None:
        """모두 번역 배치 완료 시 진행률/상태 라벨 갱신 (메인 스레드)."""
        if self._translate_all_progress_var is None or self._translate_all_status_var is None:
            return
        total_batches = max(1, total_batches)
        current_batch = max(0, min(current_batch, total_batches))
        percent = (current_batch / total_batches) * 100.0
        self._translate_all_progress_var.set(percent)
        self._translate_all_status_var.set(f"진행 중... ({current_batch}/{total_batches} 단계)")

    def _on_translate_all_cancel(self) -> None:
        """모두 번역 진행 중 취소 요청."""
        if not self._translate_all_mode_active:
            return
        self._translate_all_cancel_requested = True
        if self._translate_all_status_var is not None:
            self._translate_all_status_var.set("취소 요청 중... 현재 배치 완료 후 중단됩니다.")

    def _on_translation_done(self, success: bool, arg1: Any, arg2: Any, elapsed: float = 0.0) -> None:
        """번역 스레드 완료 시 메인 스레드에서 호출: 100% 강제, 타이머 중지, UI 갱신 후 0.5초 뒤 바 숨김."""
         # 모두 번역 진행 다이얼로그 정리
        if self._translate_all_dialog is not None and self._translate_all_dialog.winfo_exists():
            try:
                self._translate_all_dialog.destroy()
            except Exception:
                pass
        self._translate_all_dialog = None
        self._translate_all_mode_active = False
        self._translate_all_cancel_requested = False

        self._translation_done_flag = True
        if self._progress_after_id is not None and self._progress_after_id != "":
            try:
                self.root.after_cancel(self._progress_after_id)
            except (tk.TclError, OSError, ValueError):
                pass
            self._progress_after_id = None
        self.progress_var.set(100)
        if success:
            chosen_name, total = arg1, arg2
            self._last_ai_model = chosen_name
            self._refresh_tree()
            self.tree.heading("translated", text="번역 텍스트 (AI)")
            self._update_merge_button_state()
            model_label = chosen_name or "알 수 없음"
            per_line = (elapsed / total) if (elapsed > 0 and total > 0) else 0
            speed_info = f", {elapsed:.1f}s, {per_line:.2f}s/ea" if elapsed > 0 else ""
            self.status_var.set(f"AI 번역 완료. (모델: {model_label}, 총 {total}줄{speed_info})")
            # 누적 성능 데이터 저장 후 로그 출력 (역대 평균 계산용)
            if chosen_name and elapsed > 0 and total > 0:
                self._stats_manager.accumulate(chosen_name, elapsed, total)
                self._update_model_speed_label()
            # 로그: 작업 평균 vs 누적 평균 (가독성 강화)
            cum = self._stats_manager.get_average(chosen_name) if chosen_name else None
            cum_str = f"{cum[0]:.2f}s/개 (총 {cum[1]:,}개 기준)" if cum else "(데이터 수집 중...)"
            self._append_log(
                "[OK] [작업 완료] 모든 번역이 끝났습니다.\n"
                f"[Stats] 작업 내역 (Model: {model_label})\n"
                f"   |- 작업 평균: {per_line:.2f}s/개\n"
                f"   |- 누적 평균: {cum_str}"
            )
            messagebox.showinfo("AI 번역 완료", f"모델: {model_label}\n총 {total}줄 번역 완료.\n소요 시간: {elapsed:.1f}초 ({per_line:.2f}s/줄)")
        else:
            err_msg = arg1 or "알 수 없는 오류"
            self._refresh_tree()
            is_cancel = "사용자 중단" in str(err_msg)
            self.status_var.set("AI 번역 중단." if is_cancel else "AI 번역 실패.")
            if is_cancel:
                # 상세 중단 로그: "사용자 중단|모델|완료행|전체행|완료배치|전체배치|시작줄|마지막줄"
                parts = str(err_msg).split("|")
                if len(parts) >= 8:
                    model_name = parts[1]
                    done_rows, all_rows = parts[2], parts[3]
                    done_batches, all_batches = parts[4], parts[5]
                    first_line, last_line = parts[6], parts[7]
                    done_rows_int = int(done_rows)
                    per_line_cancel = (elapsed / done_rows_int) if (elapsed > 0 and done_rows_int > 0) else 0
                    self._append_log(
                        f"AI 번역 사용자 중단 (모델: {model_name}, {elapsed:.1f}초, {per_line_cancel:.2f}s/ea)"
                    )
                    if done_rows_int > 0:
                        self._append_log(
                            f"  - 완료: {done_rows}/{all_rows}줄 "
                            f"(Line {first_line}~{last_line}, "
                            f"배치 {done_batches}/{all_batches})"
                        )
                        # 중단 시에도 완료된 부분만큼 누적 성능 데이터 저장
                        if model_name and elapsed > 0:
                            self._stats_manager.accumulate(model_name, elapsed, done_rows_int)
                            self._update_model_speed_label()
                    else:
                        self._append_log("  - 완료된 번역 없음 (첫 배치 시작 전 중단)")
                else:
                    self._append_log("AI 번역 사용자 중단")
            elif "503_UNAVAILABLE" in str(err_msg):
                failed_model = str(err_msg).split("|", 1)[1] if "|" in str(err_msg) else "알 수 없음"
                self._append_log(f"AI 번역 실패: 모델({failed_model}) 일시 사용 불가 (503)")
            else:
                self._append_log(f"AI 번역 실패: {err_msg}")
            if is_cancel:
                # 사용자 취소는 조용히 상태만 갱신
                pass
            elif "429" in str(err_msg) or "quota" in (str(err_msg)).lower() or "exceeded" in (str(err_msg)).lower():
                messagebox.showerror(
                    "API 한도 초과 (429)",
                    "API 사용량이 초과되었습니다. 잠시 후 다시 시도하거나 API 키를 확인해주세요.",
                )
            elif "503_UNAVAILABLE" in str(err_msg):
                # 사용 중이던 모델명 추출
                failed_model = str(err_msg).split("|", 1)[1] if "|" in str(err_msg) else ""
                # 현재 모델과 다른 대안 모델 추천
                alt_models = [m for m in AI_MODEL_FALLBACKS if m != failed_model]
                if alt_models:
                    alt_hint = f"• AI 모델을 다른 모델(예: {alt_models[0]})로 변경해 보세요."
                else:
                    alt_hint = "• AI 모델 선택에서 다른 모델로 변경해 보세요."
                messagebox.showerror(
                    "모델 일시 사용 불가 (503)",
                    f"현재 사용 중인 모델({failed_model or '알 수 없음'})의 서버에 요청이 집중되어\n"
                    "일시적으로 사용할 수 없습니다.\n\n"
                    "해결 방법:\n"
                    "• 잠시(1~5분) 후 다시 시도해 보세요.\n"
                    f"{alt_hint}\n"
                    "• '자동'을 사용하면 가용 모델을 자동으로 찾습니다.",
                )
            else:
                err_text = str(err_msg).strip() or "알 수 없는 오류"
                if "Errno 22" in err_text or "Invalid argument" in err_text:
                    err_text = "잘못된 인자로 API 호출이 실패했습니다. API 키·경로·입력 내용을 확인해 주세요.\n\n(원인: " + err_text + ")"
                messagebox.showerror("API 오류", err_text)
        self._update_export_and_ai_translate_state()
        self.root.after(self.HIDE_PROGRESS_AFTER_MS, self._hide_progress_bar)

    def _do_translation_work(
        self,
        api_key: str,
        target_lang: str,
        selected_model: str,
        use_auto: bool,
        total: int,
        batch_size: int,
        num_batches: int,
        glossary_text: str = "",
        row_indices_0based: Optional[List[int]] = None,
    ) -> Tuple[bool, Any, Any]:
        """번역 실행 (워커 스레드에서만 호출). self.rows를 직접 수정. row_indices_0based가 있으면 해당 행만 번역. (success, chosen_name_or_err, total_or_none) 반환."""
        try:
            client = genai.Client(api_key=api_key)
            system_instruction = (
                f"너는 뛰어난 **{target_lang}** 번역 전문가야. 문맥을 고려해 자연스럽게 번역해 줘.\n\n"
                "【필수 규칙 — <br/> 처리 (최우선)】\n"
                "- 원본 텍스트에 있는 `<br/>`는 **HTML 태그가 아니라 그대로 복사해야 할 문자 열(문자 그대로)**이다.\n"
                "- `<br/>`는 번역하지 말고, 삭제하지 말고, 공백·줄바꿈으로 바꾸지 말고, **원문과 동일한 문자 `<br/>` 그대로** 번역 결과에 넣어야 한다.\n"
                "- 원본에 `Hello<br/>World`가 있으면 번역문에도 반드시 `(번역된앞부분)<br/>(번역된뒷부분)` 형태로 `<br/>`를 그대로 포함할 것.\n"
                "- `<br/>` 앞뒤 문장만 번역하고, `<br/>` 자체는 한 글자도 바꾸지 말 것."
            )
            if (glossary_text or "").strip():
                system_instruction += (
                    "\n\n【필수 번역 용어집】\n"
                    "다음은 사용자가 지정한 '필수 번역 용어집'이다. 본문에 해당 단어가 나오면 반드시 아래 지정된 대로 번역해야 한다.\n"
                    "---\n"
                    f"{glossary_text.strip()}\n"
                    "---"
                )
            config = genai_types.GenerateContentConfig(system_instruction=system_instruction)
            chosen_name = None
            if use_auto:
                try:
                    for m in client.models.list():
                        name = getattr(m, "name", None) or ""
                        if not name:
                            continue
                        short_name = name.replace("models/", "", 1) if name.startswith("models/") else name
                        try:
                            client.models.generate_content(model=short_name, contents="Hi", config=config)
                            chosen_name = short_name
                            break
                        except Exception:
                            continue
                except Exception:
                    pass
                if chosen_name is None:
                    for name in AI_MODEL_FALLBACKS:
                        try:
                            client.models.generate_content(model=name, contents="Hi", config=config)
                            chosen_name = name
                            break
                        except Exception:
                            continue
            else:
                try:
                    client.models.generate_content(model=selected_model, contents="Hi", config=config)
                    chosen_name = selected_model
                except Exception:
                    pass
            if chosen_name is None:
                if use_auto:
                    return (False, "사용 가능한 Gemini 모델을 찾지 못했습니다. API 키와 Google AI Studio 권한을 확인해 주세요.", None)
                return (False, f"선택한 모델 '{selected_model}'을(를) 사용할 수 없습니다.", None)

            indices = row_indices_0based if row_indices_0based is not None else list(range(len(self.rows)))
            for batch_idx, batch_start in enumerate(range(0, total, batch_size)):
                # 모두 번역 모드에서 취소 요청이 들어오면 다음 배치부터 중단
                if self._translate_all_mode_active and self._translate_all_cancel_requested:
                    completed_rows = batch_start
                    first_idx = self.rows[indices[0]].get("index", 1) if indices else 1
                    last_idx = self.rows[indices[completed_rows - 1]].get("index", completed_rows) if completed_rows > 0 else 0
                    cancel_info = f"사용자 중단|{chosen_name}|{completed_rows}|{total}|{batch_idx}|{num_batches}|{first_idx}|{last_idx}"
                    return (False, cancel_info, None)
                batch_end = min(batch_start + batch_size, total)
                batch_indices = indices[batch_start:batch_end]
                batch_rows = [self.rows[i] for i in batch_indices]
                # 한 행당 한 줄로 맞춤: original 내 줄바꿈을 <br/>로 치환해 전송 줄 수 = 행 수가 되도록 함
                originals = [
                    (r.get("original", "") or "").replace("\r\n", "<br/>").replace("\n", "<br/>").strip()
                    for r in batch_rows
                ]
                block = "\n".join(originals)
                n_lines = len(batch_rows)
                user_prompt = (
                    "【중요】 원본 텍스트의 `<br/>`는 **문자 그대로 인식**하고, 번역 내용에 **동일하게 반영**해야 한다. "
                    "`<br/>`를 줄바꿈(\\n)으로 바꾸거나 삭제하거나 번역하지 말 것.\n\n"
                    "【Few-shot 예시】 원본에 `<br/>`가 있으면 번역문에도 같은 위치에 `<br/>`를 그대로 포함.\n\n"
                    "User: \"Hello<br/>World\"\n"
                    "Model: \"안녕하세요<br/>세상\"\n\n"
                    "User: \"This is a test.<br/>Do not break this.\"\n"
                    "Model: \"이것은 테스트입니다.<br/>이것을 깨뜨리지 마세요.\"\n\n"
                    "【출력 형식】 입력 1줄 = 출력 1줄. 원본 줄에 `<br/>`가 있으면 그 줄의 번역 결과에도 **반드시 `<br/>`를 문자 그대로** 한 줄 안에 포함. "
                    "`<br/>`를 \\n으로 나누지 말 것.\n\n"
                    "---\n\n"
                    f"아래 텍스트는 정확히 {n_lines}줄이다. {target_lang}로 번역한 뒤, 정확히 {n_lines}줄만 출력. "
                    "각 줄에서 `<br/>`는 번역문에 그대로 복사할 것. 한 줄에 한 문장씩, 빈 줄 없이 번역 결과만 출력.\n\n"
                    f"{block}"
                )
                try:
                    response = client.models.generate_content(
                        model=chosen_name, contents=user_prompt, config=config
                    )
                    text = (response.text or "").strip()
                    response_lines = [ln.strip() for ln in text.split("\n")]
                except Exception as e:
                    err_msg = str(e)
                    if "429" in err_msg or "Resource Exhausted" in err_msg or "quota" in err_msg.lower() or "exceeded" in err_msg.lower():
                        return (False, "API 사용량이 초과되었습니다. 잠시 후 다시 시도하거나 API 키를 확인해주세요. (429)", None)
                    if "503" in err_msg or "UNAVAILABLE" in err_msg:
                        return (False, f"503_UNAVAILABLE|{chosen_name}", None)
                    for row in batch_rows:
                        row["translated"] = "[통신 오류]"
                    return (False, f"통신 오류: {err_msg}", None)
                requested_len = len(batch_rows)
                log_cb = lambda m: self.root.after(0, lambda msg=m: self._append_log(msg))
                lines_final = _map_translation_response_lines(
                    response_lines, batch_rows, requested_len, log_callback=log_cb
                )
                for i, row in enumerate(batch_rows):
                    raw = lines_final[i] if i < len(lines_final) else ""
                    row["translated"] = raw if (raw and raw.strip()) else AI_TRANSLATE_EMPTY_PLACEHOLDER

                # 빈줄 감지 시 로그 (모든 모드)
                empty_count = sum(1 for r in batch_rows if (r.get("translated") or "").strip() == "" or r.get("translated") == AI_TRANSLATE_EMPTY_PLACEHOLDER)
                if empty_count > 0:
                    start_1 = batch_rows[0].get("index", batch_indices[0] + 1)
                    end_1 = batch_rows[-1].get("index", batch_indices[-1] + 1)
                    msg = f"Line {start_1}-{end_1}: 빈 줄 {empty_count}건 감지되어 <빈줄> 처리"
                    self.root.after(0, lambda m=msg: self._append_log(m))
                # 모두 번역 모드: 진행률 갱신 + 그리드 즉시 갱신
                if self._translate_all_mode_active:
                    if num_batches > 0:
                        current_batch = batch_idx + 1
                        self.root.after(0, lambda c=current_batch, t=num_batches: self._update_translate_all_progress_ui(c, t))
                    self.root.after(0, self._refresh_tree)
            return (True, chosen_name, total)
        except Exception as e:
            return (False, str(e), None)

    def _run_translation_worker(
        self,
        api_key: str,
        target_lang: str,
        selected_model: str,
        use_auto: bool,
        total: int,
        batch_size: int,
        num_batches: int,
        glossary_text: str = "",
        row_indices_0based: Optional[List[int]] = None,
    ) -> None:
        """워커 스레드 엔트리: 번역 실행 후 메인 스레드에 완료 콜백 예약."""
        self._translation_start_time = time.time()
        result = self._do_translation_work(
            api_key, target_lang, selected_model, use_auto, total, batch_size, num_batches, glossary_text, row_indices_0based
        )
        elapsed = time.time() - self._translation_start_time
        self.root.after(0, lambda: self._on_translation_done(result[0], result[1], result[2], elapsed))

    def _on_ai_translate(self):
        """AI 번역하기: Fake Progress 표시 후 백그라운드 스레드에서 Gemini API 번역 실행."""
        if not _HAS_GEMINI or genai is None:
            messagebox.showerror("오류", "Gemini API를 사용하려면\npip install google-genai\n를 실행해 주세요.")
            return
        api_key = self._get_gemini_api_key()
        if not api_key:
            folder_hint = "실행 파일(SubBridgeAI.exe)이 있는 폴더" if getattr(sys, "frozen", False) else "프로그램 폴더"
            messagebox.showwarning(
                "API 키 없음",
                "Gemini API 키가 없습니다.\n\n"
                f"{folder_hint}에 .env 파일을 만들고 다음 한 줄을 넣어 주세요:\n\n"
                "GEMINI_API_KEY=여기에_API_키_입력"
            )
            return
        if not self.rows:
            messagebox.showwarning("알림", "먼저 원본 SRT를 열어주세요.")
            return
        max_index = len(self.rows)

        is_translate_all = bool(self.translate_all_var.get())
        # AI 번역 대상 언어 (기본: 영어)
        target_lang = self.ai_lang_combo.get() or "English"

        if is_translate_all:
            # 모두 번역: 시작 번호만 사용, 나머지는 끝까지 자동
            start_index = self._get_translate_all_start_index(max_index)
            if start_index is None:
                return
            # 사전 경고
            proceed = messagebox.askyesno(
                "모두 번역 확인",
                "전체 번역은 시간이 오래 걸릴 수 있습니다.\n진행하시겠습니까?",
            )
            if not proceed:
                return
            row_indices_0based = list(range(start_index - 1, max_index))
            total = len(row_indices_0based)
            batch_size = 10  # 모두 번역 전용: 10개씩 끊어서 호출
        else:
            ok, row_indices_0based = self._validate_translate_range_and_maybe_correct(max_index)
            if not ok:
                return
            if row_indices_0based is not None:
                total = len(row_indices_0based)
            else:
                total = len(self.rows)
                row_indices_0based = list(range(len(self.rows)))
            batch_size = AI_TRANSLATE_BATCH_SIZE

        num_batches = (total + batch_size - 1) // batch_size
        selected_model = (self.ai_model_combo.get() or "").strip()
        use_auto = not selected_model or selected_model == AI_MODEL_AUTO
        glossary_text = self._glossary_text or ""

        self.status_var.set("AI 번역 중...")
        self.ai_translate_btn.config(state="disabled")
        # 로그 뷰어 표시 및 작업 시작 로그
        self._append_log(f"AI 번역 작업 시작 (대상: {total}줄, {target_lang})")
        if is_translate_all:
            self._translate_all_mode_active = True
            self._start_translate_all_progress(num_batches)
        else:
            self._translate_all_mode_active = False
            self._start_fake_progress()

        thread = threading.Thread(
            target=self._run_translation_worker,
            args=(api_key, target_lang, selected_model, use_auto, total, batch_size, num_batches, glossary_text, row_indices_0based),
            daemon=True,
        )
        thread.start()

    def _on_export(self):
        """현재 [컬럼 2] 원본 텍스트만 추출하여 저장."""
        if not self.rows:
            messagebox.showwarning("알림", "먼저 원본 SRT를 열어주세요.")
            return
        lang_code = self._get_selected_lang_code()
        default_name = (Path(self.srt_file_path).stem if self.srt_file_path else "export") + "_" + lang_code + ".txt"
        initial_dir = str(Path(self.srt_file_path).parent) if self.srt_file_path else None
        path = filedialog.asksaveasfilename(
            title="추출 텍스트 저장",
            defaultextension=".txt",
            initialfile=default_name,
            initialdir=initial_dir,
            filetypes=[("텍스트 파일", "*.txt"), ("모든 파일", "*.*")],
        )
        if not path:
            return
        try:
            text = extract_text_lines(self.rows)
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
        except Exception as e:
            messagebox.showerror("오류", f"저장 실패:\n{e}")
            return
        self.status_var.set(f"추출 완료: {path}")

    def _model_suffix_for_merge(self) -> str:
        """마지막 AI 번역 모델명에서 병합 파일명 접미사 반환: _flash_lite, _flash, _pro 또는 빈 문자열."""
        name = (self._last_ai_model or "").lower()
        if "flash-lite" in name or "flash_lite" in name:
            return "_flash_lite"
        if "flash" in name:
            return "_flash"
        if "pro" in name:
            return "_pro"
        return ""

    def _on_merge(self):
        """[컬럼 1] 타임코드 + [컬럼 3] 번역으로 SRT 저장."""
        if not self.rows:
            messagebox.showwarning("알림", "먼저 원본 SRT를 열어주세요.")
            return
        # 번역 텍스트가 비어 있는 행이 있으면 병합 불가
        empty_indices = [i + 1 for i, r in enumerate(self.rows) if not (r.get("translated") or "").strip()]
        if empty_indices:
            messagebox.showwarning(
                "병합하기 사용 불가",
                "번역 텍스트에 내용이 비어 있는 행이 있습니다.\n병합하기를 사용할 수 없습니다.\n\n"
                f"비어 있는 행 예: {empty_indices[:10]}{'…' if len(empty_indices) > 10 else ''}",
            )
            return
        if self.srt_blocks and self.txt_lines and len(self.srt_blocks) != len(self.txt_lines):
            messagebox.showwarning(
                "라인 수 불일치",
                f"SRT 블록 수({len(self.srt_blocks)})와 번역 TXT 라인 수({len(self.txt_lines)})가 다릅니다.\n"
                "병합 결과가 어긋날 수 있으니 확인 후 진행하세요.",
            )
        model_suffix = self._model_suffix_for_merge()
        ai_lang_code = self._get_ai_lang_code()
        if self.txt_file_path:
            default_name = Path(self.txt_file_path).stem + "_" + ai_lang_code + model_suffix + ".srt"
            initial_dir = str(Path(self.txt_file_path).parent)
        else:
            base = Path(self.srt_file_path).stem if self.srt_file_path else "merged"
            default_name = base + "_" + ai_lang_code + model_suffix + ".srt"
            initial_dir = str(Path(self.srt_file_path).parent) if self.srt_file_path else None
        path = filedialog.asksaveasfilename(
            title="병합 SRT 저장",
            defaultextension=".srt",
            initialfile=default_name,
            initialdir=initial_dir,
            filetypes=[("SRT 파일", "*.srt"), ("모든 파일", "*.*")],
        )
        if not path:
            return
        try:
            content = build_srt_from_merged(self.rows)
            with open(path, "w", encoding="utf-8-sig") as f:
                f.write(content)
        except Exception as e:
            messagebox.showerror("오류", f"저장 실패:\n{e}")
            return
        self.status_var.set(f"병합 SRT 저장 완료: {path}")

    def _collect_search_matches(self):
        """원본·번역 양쪽에서 검색어가 포함된 row index 수집."""
        q = self.search_var.get().strip()
        if not q:
            return []
        q_lower = q.lower()
        indices = []
        for i, row in enumerate(self.rows):
            orig = (row.get("original") or "").lower()
            trans = (row.get("translated") or "").lower()
            if q_lower in orig or q_lower in trans:
                indices.append(i)
        return indices

    def _focus_search_entry(self):
        """검색 입력창으로 포커스 이동 (Ctrl+F)."""
        self.search_entry.focus_set()
        self.search_entry.select_range(0, tk.END)

    def _on_find(self):
        """찾기: 다음 검색 결과로 이동 및 포커스."""
        query = self.search_var.get().strip()
        if not query:
            self.status_var.set("검색어를 입력한 뒤 찾기를 실행하세요.")
            return
        # 검색어가 바뀌었으면 매칭 목록 재계산
        if query != self.search_query:
            self.search_query = query
            self.search_matches = self._collect_search_matches()
            self.search_current_index = -1
        if not self.search_matches:
            self.status_var.set(f'"{query}"에 해당하는 행이 없습니다.')
            return
        self.search_current_index = (self.search_current_index + 1) % len(self.search_matches)
        row_index = self.search_matches[self.search_current_index]
        self._focus_row(row_index)
        total = len(self.search_matches)
        nth = self.search_current_index + 1
        self.status_var.set(f'총 {len(self.rows)} 라인 중 검색 결과 {nth}/{total}번째 라인 (행 인덱스 {row_index + 1}).')

    def _focus_row(self, row_index: int):
        """해당 행을 선택하고 스크롤하여 보이게 함."""
        iid = self._tree_iid(row_index)
        self.tree.selection_set(iid)
        self.tree.see(iid)
        self.tree.focus(iid)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = SrtVerifierMergerApp()
    app.run()
