# -*- coding: utf-8 -*-
"""
자동 버전 관리 빌드 스크립트
PyInstaller로 단일 실행 파일을 만들고, dist 내 순차 버전 번호(v0001, v0002, ...)로 저장.
"""
import glob
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

# 프로젝트 루트 = 이 스크립트가 있는 폴더
SCRIPT_DIR = Path(__file__).resolve().parent
DIST_DIR = SCRIPT_DIR / "dist"
# PyInstaller로 묶을 진입점 스크립트 (필요 시 변경)
MAIN_SCRIPT = SCRIPT_DIR / "srt_verifier_merger.py"
OUTPUT_BASENAME = "SubBridgeAI"
# 빌드 시 API 키를 읽을 .env 후보 (exe 내장용)
GEMINI_ENV_PATH = Path(r"C:\cursor2\ai-chatbot-app\ai-chatbot\.env.local")
# exe에 묶을 API 키 파일명 (srt_verifier_merger.GEMINI_KEY_BUNDLE_FILENAME 과 동일)
GEMINI_KEY_BUNDLE_FILENAME = "gemini_api_key_bundle.txt"


def get_next_version() -> int:
    """dist 폴더에서 SubBridgeAI_v*.exe 를 스캔해 다음 버전 번호 반환."""
    pattern = str(DIST_DIR / f"{OUTPUT_BASENAME}_v*.exe")
    files = glob.glob(pattern)
    if not files:
        return 1
    versions = []
    for f in files:
        name = os.path.basename(f)
        # SubBridgeAI_v0003.exe -> 3
        m = re.search(r"_v(\d+)\.exe$", name)
        if m:
            versions.append(int(m.group(1)))
    return max(versions) + 1 if versions else 1


def load_api_key_for_build() -> Optional[str]:
    """현재 환경에서 GEMINI_API_KEY를 읽음. 빌드 시 dist에 .env로 복사하기 위함."""
    key_name = "GEMINI_API_KEY"
    paths = [
        GEMINI_ENV_PATH,
        SCRIPT_DIR / ".env.local",
        SCRIPT_DIR / ".env",
    ]
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


def find_icon() -> Optional[str]:
    """스크립트와 같은 경로의 *.ico 파일 경로 반환. 없으면 None."""
    for p in SCRIPT_DIR.glob("*.ico"):
        return str(p)
    return None


def main() -> None:
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    version = get_next_version()
    version_str = f"v{version:04d}"  # v0001, v0002, ...
    final_name = f"{OUTPUT_BASENAME}_{version_str}.exe"
    final_path = DIST_DIR / final_name

    api_key = load_api_key_for_build()
    bundle_file = SCRIPT_DIR / GEMINI_KEY_BUNDLE_FILENAME
    if api_key:
        try:
            bundle_file.write_text(api_key.strip(), encoding="utf-8")
        except Exception as e:
            print("경고: API 키 번들 파일 생성 실패:", e)
            api_key = None

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--noconsole",
        "--name", OUTPUT_BASENAME,
        "--distpath", str(DIST_DIR),
        "--specpath", str(SCRIPT_DIR),
        "--workpath", str(SCRIPT_DIR / "build"),
        "--clean",
        str(MAIN_SCRIPT),
    ]
    if api_key and bundle_file.exists():
        # Windows: "source;dest" → exe 실행 시 sys._MEIPASS 에 풀림
        cmd.extend(["--add-data", str(bundle_file) + ";."])
    icon = find_icon()
    if icon:
        cmd.extend(["--icon", icon])
        print(f"아이콘 사용: {icon}")
    else:
        print("아이콘 없음, 기본 아이콘 사용")

    if api_key:
        print("API 키 포함: exe 단일 파일로 배포됩니다.")
    else:
        print("참고: GEMINI_API_KEY를 찾지 못했습니다. 배포 exe는 실행 파일 폴더의 .env가 필요합니다.")

    print("PyInstaller 실행 중...")
    ret = subprocess.run(cmd, cwd=SCRIPT_DIR)
    if bundle_file.exists():
        try:
            bundle_file.unlink()
        except Exception:
            pass
    if ret.returncode != 0:
        print("빌드 실패. PyInstaller 반환 코드:", ret.returncode)
        sys.exit(1)

    built_exe = DIST_DIR / f"{OUTPUT_BASENAME}.exe"
    if not built_exe.exists():
        print("빌드 결과물을 찾을 수 없습니다:", built_exe)
        sys.exit(1)

    shutil.move(str(built_exe), str(final_path))
    print("빌드 완료:", final_path)

    # ── GitHub Releases 자동 업로드 ──
    upload_to_github_release(version_str, exe_path=final_path)


def upload_to_github_release(version_str: str, exe_path: Path) -> None:
    """빌드된 exe를 GitHub Releases에 업로드한다."""
    # gh CLI 존재 확인
    try:
        subprocess.run(
            ["gh", "--version"],
            capture_output=True, check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("[SKIP] GitHub CLI(gh)가 설치되어 있지 않아 릴리스 업로드를 건너뜁니다.")
        return

    # 인증 확인
    auth_check = subprocess.run(
        ["gh", "auth", "status"],
        capture_output=True, text=True,
    )
    if auth_check.returncode != 0:
        print("[SKIP] GitHub 인증이 되어 있지 않아 릴리스 업로드를 건너뜁니다.")
        print("  → 'gh auth login' 으로 인증 후 다시 시도하세요.")
        return

    tag = version_str  # v0001, v0002, ...
    release_title = f"{OUTPUT_BASENAME} {version_str}"
    release_notes = f"Auto build release - {release_title}"

    print(f"\n[UPLOAD] GitHub Release upload start... (tag: {tag})")

    # git add + commit + push (변경사항이 있는 경우)
    subprocess.run(["git", "add", "-A"], cwd=SCRIPT_DIR, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", f"Release {tag}"],
        cwd=SCRIPT_DIR, capture_output=True,
    )
    subprocess.run(["git", "push"], cwd=SCRIPT_DIR, capture_output=True)

    # 릴리스 생성 + exe 첨부
    gh_cmd = [
        "gh", "release", "create", tag,
        str(exe_path),
        "--title", release_title,
        "--notes", release_notes,
    ]
    result = subprocess.run(gh_cmd, cwd=SCRIPT_DIR, capture_output=True, text=True)

    if result.returncode == 0:
        release_url = result.stdout.strip()
        download_url = (
            f"https://github.com/qwerzxc1090/srttotxt/releases/download/"
            f"{tag}/{exe_path.name}"
        )
        print(f"[OK] GitHub Release 업로드 성공!")
        print(f"   릴리스 페이지: {release_url}")
        print(f"   다운로드 URL : {download_url}")
    else:
        print(f"[FAIL] GitHub Release 업로드 실패:")
        print(f"   {result.stderr.strip()}")


if __name__ == "__main__":
    main()
