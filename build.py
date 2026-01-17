import shutil
import subprocess
import sys
from pathlib import Path


def main():
    # Build the exe
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--windowed",
        "--name",
        "TF2QueueTimer",
        "--icon",
        "icon.ico",
        "main.py",
    ]

    subprocess.run(cmd, check=True)

    # Copy assets next to the exe
    dist = Path("dist")
    for asset in ["icon.ico", "font.ttf"]:
        src = Path(asset)
        if src.exists():
            shutil.copy(src, dist / asset)
            print(f"Copied {asset} to dist/")

    print("\nBuild complete!")
    print("Files in dist/:")
    print("  - TF2QueueTimer.exe")
    print("  - icon.ico")
    print("  - font.ttf")
    print("  - settings.json (created on first run)")


if __name__ == "__main__":
    main()