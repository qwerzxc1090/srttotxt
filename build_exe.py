# -*- coding: utf-8 -*-
"""
배포용 exe 빌드 스크립트.
실행: python build_exe.py
필요: pip install pyinstaller pillow
"""
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PNG_SOURCE = SCRIPT_DIR / "Gemini_Generated_Image_28x0ow28x0ow28x0.png"
ICON_PNG = SCRIPT_DIR / "icon.png"
ICON_ICO = SCRIPT_DIR / "app.ico"
MAIN_SCRIPT = SCRIPT_DIR / "srt_verifier_merger.py"
EXE_NAME = "SRT_Verifier_Merger"


def main():
    if not MAIN_SCRIPT.exists():
        print(f"오류: {MAIN_SCRIPT} 를 찾을 수 없습니다.")
        sys.exit(1)

    # 1. 아이콘 PNG 준비 (icon.png)
    if PNG_SOURCE.exists():
        shutil.copy2(PNG_SOURCE, ICON_PNG)
        print(f"아이콘 복사: {PNG_SOURCE.name} -> icon.png")
    elif not ICON_PNG.exists():
        print("오류: icon.png 또는 Gemini_Generated_Image_28x0ow28x0ow28x0.png 가 없습니다.")
        sys.exit(1)

    # 2. PNG -> ICO 변환 (exe 아이콘용)
    try:
        from PIL import Image
        img = Image.open(ICON_PNG)
        # Windows ICO는 여러 크기 포함 권장
        sizes = [(256, 256), (48, 48), (32, 32), (16, 16)]
        img.save(ICON_ICO, format="ICO", sizes=sizes)
        print(f"ICO 생성: {ICON_ICO}")
    except ImportError:
        print("Pillow 필요: pip install pillow")
        sys.exit(1)
    except Exception as e:
        print(f"ICO 변환 실패: {e}")
        sys.exit(1)

    # 3. PyInstaller 실행
    add_data = f"icon.png;." if sys.platform == "win32" else "icon.png:."
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        f"--icon={ICON_ICO}",
        f"--add-data={add_data}",
        f"--name={EXE_NAME}",
        "--clean",
        str(MAIN_SCRIPT),
    ]
    print("실행:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=SCRIPT_DIR)
    if result.returncode != 0:
        sys.exit(result.returncode)
    print(f"\n완료. 실행 파일: {SCRIPT_DIR / 'dist' / EXE_NAME}{'.exe' if sys.platform == 'win32' else ''}")


if __name__ == "__main__":
    main()
