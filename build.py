"""
Nuitka build script for TF2 Queue Timer.

Nuitka compiles Python to C for faster startup and smaller binaries.
Install with: pip install nuitka

Usage: python build_nuitka.py

This bundles font.ttf and icon.ico INTO the executable.
settings.json is created externally by the app on first run.
"""

import subprocess
import sys
from pathlib import Path


def main():
    print("Building TF2 Queue Timer with Nuitka...")
    print("=" * 50)
    
    # Check if Nuitka is installed
    try:
        import nuitka
    except ImportError:
        print("Nuitka not found. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "nuitka"], check=True)
    
    # Verify assets exist
    assets = ["icon.ico", "font.ttf"]
    for asset in assets:
        if not Path(asset).exists():
            print(f"ERROR: {asset} not found in current directory!")
            sys.exit(1)
    
    # Build command
    cmd = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--onefile",
        "--windows-console-mode=disable",  # No console window
        "--windows-icon-from-ico=icon.ico",
        "--output-filename=TF2QueueTimer.exe",
        "--output-dir=dist",
        # Include data files (bundled with the exe)
        "--include-data-files=icon.ico=icon.ico",
        "--include-data-files=font.ttf=font.ttf",
        # Enable Qt plugin detection
        "--enable-plugin=pyside6",
        # Exclude unused Qt modules to reduce size
        "--noinclude-qt-translations",
        # Optimization
        "--lto=yes",
        "--remove-output",  # Remove build folder after
        "main.py",
    ]
    
    print("Running:", " ".join(cmd))
    print()
    print("NOTE: First build will download MinGW64 compiler (~300MB)")
    print("      and may take 5-10 minutes. Subsequent builds are faster.")
    print()
    
    result = subprocess.run(cmd)
    
    if result.returncode != 0:
        print("\nBuild failed!")
        sys.exit(1)
    
    print()
    print("=" * 50)
    print("Build complete!")
    print()
    print("Files in dist/:")
    print("  - TF2QueueTimer.exe  (includes font.ttf and icon.ico)")
    print()
    print("Created on first run:")
    print("  - settings.json  (user-editable configuration)")
    print()
    print("The executable is self-contained! Just distribute TF2QueueTimer.exe")


if __name__ == "__main__":
    main()
