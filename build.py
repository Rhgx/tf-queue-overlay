"""
PyInstaller build script for TF2 Queue Timer.

Usage: python build.py

Creates: dist/TF2QueueTimer/
  - TF2QueueTimer.exe
  - font.ttf, icon.ico
  - _internal/          <- Dependencies hidden here
"""

import subprocess
import sys
from pathlib import Path


def main():
    print("Building TF2 Queue Timer with PyInstaller...")
    print("=" * 55)
    
    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller not found. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
    
    assets = ["icon.ico", "font.ttf"]
    for asset in assets:
        if not Path(asset).exists():
            print(f"ERROR: {asset} not found!")
            sys.exit(1)
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "TF2QueueTimer",
        "--windowed",
        "--icon", "icon.ico",
        "--add-data", "icon.ico;.",
        "--add-data", "font.ttf;.",
        "--noconfirm",
        "--clean",
        "main.py",
    ]
    
    print("Running PyInstaller...")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("\nBuild failed!")
        sys.exit(1)
    
    print()
    print("=" * 55)
    print("Build complete!")
    print()
    print("Output: dist/TF2QueueTimer/")
    print("  ├── TF2QueueTimer.exe")
    print("  ├── font.ttf, icon.ico")
    print("  ├── settings.json       (created on first run)")
    print("  └── _internal/          (dependencies)")
    print()
    print("Zip and distribute the TF2QueueTimer folder.")


if __name__ == "__main__":
    main()
