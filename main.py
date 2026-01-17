from __future__ import annotations

import json
import os
import re
import sys
import time
import winreg
from pathlib import Path
from typing import Optional

import psutil
import win32gui
import win32process
from PySide6 import QtCore, QtGui, QtWidgets

# -----------------------------
# Config / assets
# -----------------------------


def get_app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent


APP_DIR = get_app_dir()

SETTINGS_PATH = APP_DIR / "settings.json"
FONT_PATH = APP_DIR / "font.ttf"
ICON_PATH = APP_DIR / "icon.ico"

DEFAULT_SETTINGS = {
    "pos": [24, 24],
    "opacity": 0.5,
    "font_size": 22,
}

TF2_PROCESS_NAME = "tf_win64.exe"

# Queue start => reset and start timing
QUEUE_START_PATTERNS = [
    re.compile(r"^\[PartyClient\] Requesting queue for .*Casual Match\b"),
    re.compile(r"^\[PartyClient\] Entering queue for match group .*Casual Match\b"),
    re.compile(r"^\[ReliableMsg\] PartyQueueForMatch started\b"),
]

# Match found (lobby assigned) => stop timing here
# In your log, the earliest reliable signal is Leaving queue (you were assigned).
MATCH_FOUND_PATTERNS = [
    re.compile(r"^\[PartyClient\] Leaving queue for match group .*Casual Match\b"),
    re.compile(r"^\[ReliableMsg\] AcceptLobbyInvite\b", re.IGNORECASE),
    re.compile(r"^Lobby created\s*$", re.IGNORECASE),
    re.compile(r"^Differing lobby received\.", re.IGNORECASE),
]

# Map is only known after connecting (from your sample logs)
MAP_PATTERN = re.compile(r"^Map:\s*([A-Za-z0-9_]+)\s*$")


# -----------------------------
# Settings helpers
# -----------------------------


def load_settings() -> dict:
    if SETTINGS_PATH.exists():
        try:
            return {**DEFAULT_SETTINGS, **json.loads(SETTINGS_PATH.read_text())}
        except Exception:
            pass
    return DEFAULT_SETTINGS.copy()


def save_settings(settings: dict) -> None:
    try:
        SETTINGS_PATH.write_text(json.dumps(settings, indent=2))
    except Exception:
        pass


def ensure_settings_file() -> None:
    if not SETTINGS_PATH.exists():
        save_settings(DEFAULT_SETTINGS)


# -----------------------------
# TF2 focus check
# -----------------------------


def is_tf2_focused() -> bool:
    try:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return False
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        proc = psutil.Process(pid)
        return proc.name().lower() == TF2_PROCESS_NAME
    except Exception:
        return False


# -----------------------------
# Steam / TF2 path detection
# -----------------------------


def get_steam_path() -> Optional[Path]:
    reg_candidates = [
        (
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\WOW6432Node\Valve\Steam",
            "InstallPath",
        ),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", "InstallPath"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Valve\Steam", "SteamPath"),
    ]

    for root, subkey, value in reg_candidates:
        try:
            key = winreg.OpenKey(root, subkey)
            val, _ = winreg.QueryValueEx(key, value)
            winreg.CloseKey(key)
            p = Path(val)
            if p.exists() and (p / "steam.exe").exists():
                return p
        except OSError:
            continue

    common = [
        Path(r"C:\Program Files (x86)\Steam"),
        Path(r"C:\Program Files\Steam"),
        Path(r"D:\Steam"),
        Path(r"D:\SteamLibrary"),
        Path(r"E:\Steam"),
        Path(r"E:\SteamLibrary"),
    ]
    for p in common:
        if p.exists() and (p / "steam.exe").exists():
            return p

    return None


def parse_vdf_strings(text: str) -> list[str]:
    return re.findall(r'"([^"]*)"', text)


def get_library_folders(steam_path: Path) -> list[Path]:
    libs = [steam_path]
    vdf_path = steam_path / "steamapps" / "libraryfolders.vdf"
    if not vdf_path.exists():
        return libs

    try:
        text = vdf_path.read_text(encoding="utf-8", errors="ignore")
        strings = parse_vdf_strings(text)
        for i, s in enumerate(strings):
            if s.lower() == "path" and i + 1 < len(strings):
                p = Path(strings[i + 1])
                if p.exists() and p not in libs:
                    libs.append(p)
    except Exception:
        pass

    return libs


def find_tf2_tf_dir() -> Optional[Path]:
    steam_path = get_steam_path()
    if not steam_path:
        return None

    for lib in get_library_folders(steam_path):
        tf_dir = lib / "steamapps" / "common" / "Team Fortress 2" / "tf"
        if tf_dir.exists():
            return tf_dir

    return None


def get_console_log_path() -> Optional[Path]:
    tf_dir = find_tf2_tf_dir()
    if not tf_dir:
        return None
    return tf_dir / "console.log"


def clear_console_log(log_path: Path) -> None:
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "w", encoding="utf-8", errors="ignore"):
            pass
    except Exception:
        pass


# -----------------------------
# Log follower (non-blocking polling)
# -----------------------------


class ConsoleLogFollower:
    def __init__(self, path: Path):
        self.path = path
        self.f = None

    def open(self) -> None:
        self.f = open(self.path, "r", errors="ignore")
        self.f.seek(0, os.SEEK_END)

    def poll_lines(self, max_lines: int = 250) -> list[str]:
        if self.f is None:
            self.open()

        lines: list[str] = []
        for _ in range(max_lines):
            pos = self.f.tell()
            line = self.f.readline()
            if not line:
                self.f.seek(pos, os.SEEK_SET)
                break
            lines.append(line.rstrip("\n"))
        return lines


def format_mmss_mmm(seconds: float) -> str:
    seconds = max(0.0, seconds)
    total_ms = int(seconds * 1000.0)
    mins = total_ms // 60000
    secs = (total_ms % 60000) // 1000
    ms = total_ms % 1000
    return f"{mins:02d}:{secs:02d}.{ms:03d}"


# -----------------------------
# Icon helper
# -----------------------------


def get_app_icon() -> QtGui.QIcon:
    if ICON_PATH.exists():
        return QtGui.QIcon(str(ICON_PATH))

    pix = QtGui.QPixmap(64, 64)
    pix.fill(QtCore.Qt.GlobalColor.transparent)
    p = QtGui.QPainter(pix)
    p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
    p.setBrush(QtGui.QColor(26, 26, 30, 255))
    p.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 170), 2))
    p.drawRoundedRect(8, 8, 48, 48, 12, 12)
    p.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 220), 3))
    p.drawLine(22, 34, 32, 44)
    p.drawLine(32, 44, 46, 24)
    p.end()
    return QtGui.QIcon(pix)


# -----------------------------
# UI: polished overlay card
# -----------------------------


class OverlayWindow(QtWidgets.QWidget):
    def __init__(self, log_path: Path):
        super().__init__()
        self.settings = load_settings()

        self.status: str = "IDLE"  # IDLE, QUEUEING, MATCH FOUND
        self.queue_start_perf: Optional[float] = None
        self.last_match_found_seconds: float = 0.0
        self.map_name: Optional[str] = None

        self.follower = ConsoleLogFollower(log_path)

        self.setObjectName("Root")
        self.setWindowTitle("TF2 Queue Timer")
        self.setWindowIcon(get_app_icon())

        self.setWindowFlags(
            QtCore.Qt.WindowType.FramelessWindowHint
            | QtCore.Qt.WindowType.Tool
            | QtCore.Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        self.setWindowOpacity(float(self.settings["opacity"]))
        self.move(*self.settings["pos"])

        self._load_font()
        self._build_ui()

        # Poll log (events)
        self.poll_timer = QtCore.QTimer(self)
        self.poll_timer.timeout.connect(self.on_poll_tick)
        self.poll_timer.start(50)

        # Refresh UI frequently
        self.ui_timer = QtCore.QTimer(self)
        self.ui_timer.timeout.connect(self._update_ui)
        self.ui_timer.start(16)

        # Show/hide based on TF2 focus
        self.proc_timer = QtCore.QTimer(self)
        self.proc_timer.timeout.connect(self._sync_visibility_with_tf2)
        self.proc_timer.start(200)
        self._sync_visibility_with_tf2()

    def _load_font(self):
        self.font_family = None
        if FONT_PATH.exists():
            font_id = QtGui.QFontDatabase.addApplicationFont(str(FONT_PATH))
            families = QtGui.QFontDatabase.applicationFontFamilies(font_id)
            if families:
                self.font_family = families[0]

    def _font(self, size: int, bold: bool = False) -> QtGui.QFont:
        f = QtGui.QFont(self.font_family or "Segoe UI")
        f.setPointSize(size)
        f.setBold(bold)
        f.setStyleStrategy(QtGui.QFont.StyleStrategy.PreferAntialias)
        return f

    def _build_ui(self):
        self.card = QtWidgets.QFrame(self)
        self.card.setObjectName("Card")

        shadow = QtWidgets.QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 10)
        shadow.setColor(QtGui.QColor(0, 0, 0, 110))
        self.card.setGraphicsEffect(shadow)

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.card)

        layout = QtWidgets.QVBoxLayout(self.card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        header_row = QtWidgets.QHBoxLayout()
        header_row.setSpacing(10)

        self.title_label = QtWidgets.QLabel("Queue Timer")
        self.title_label.setFont(self._font(11, True))
        self.title_label.setObjectName("Title")

        self.status_pill = QtWidgets.QLabel("IDLE")
        self.status_pill.setFont(self._font(10, True))
        self.status_pill.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.status_pill.setObjectName("StatusPill")

        header_row.addWidget(self.title_label, 1)
        header_row.addWidget(self.status_pill, 0)
        layout.addLayout(header_row)

        self.timer_label = QtWidgets.QLabel("--:--.---")
        self.timer_label.setFont(
            self._font(int(self.settings["font_size"]) + 10, True)
        )
        self.timer_label.setObjectName("Timer")
        self.timer_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.timer_label)

        self.map_label = QtWidgets.QLabel("Map: —")
        self.map_label.setFont(self._font(11, False))
        self.map_label.setObjectName("Meta")
        layout.addWidget(self.map_label)

        self.setStyleSheet(
            """
            QFrame#Card {
              background-color: rgba(18, 18, 20, 165);
              border: 1px solid rgba(255, 255, 255, 40);
              border-radius: 14px;
            }
            QLabel#Title {
              color: rgba(255, 255, 255, 220);
              letter-spacing: 0.3px;
            }
            QLabel#Timer {
              color: rgba(255, 255, 255, 240);
            }
            QLabel#Meta {
              color: rgba(255, 255, 255, 175);
            }
            QLabel#StatusPill {
              padding: 4px 10px;
              border-radius: 999px;
              color: rgba(255, 255, 255, 230);
              background-color: rgba(120, 120, 120, 95);
              border: 1px solid rgba(255, 255, 255, 45);
              min-width: 110px;
            }
            """
        )

        self._update_ui()

    def _sync_visibility_with_tf2(self):
        if is_tf2_focused():
            if not self.isVisible():
                self.show()
            self.raise_()
        else:
            if self.isVisible():
                self.hide()

    def on_poll_tick(self):
        for line in self.follower.poll_lines():
            self._handle_line(line)

    def _handle_line(self, line: str):
        # Only update map after we connect; harmless at any time
        m = MAP_PATTERN.match(line)
        if m:
            self.map_name = m.group(1)
            return

        # Queue start => auto reset and start timing
        if any(p.search(line) for p in QUEUE_START_PATTERNS):
            self.status = "QUEUEING"
            self.queue_start_perf = time.perf_counter()
            self.last_match_found_seconds = 0.0
            self.map_name = None
            return

        # Stop timing at the first "match found" signal (lobby assigned).
        # IMPORTANT: only if we are currently queueing.
        if self.status == "QUEUEING" and self.queue_start_perf is not None:
            if any(p.search(line) for p in MATCH_FOUND_PATTERNS):
                self.status = "MATCH FOUND"
                self.last_match_found_seconds = (
                    time.perf_counter() - self.queue_start_perf
                )
                self.queue_start_perf = None
                return

    def _elapsed_seconds(self) -> float:
        if self.status == "QUEUEING" and self.queue_start_perf is not None:
            return time.perf_counter() - self.queue_start_perf
        if self.status == "MATCH FOUND":
            return self.last_match_found_seconds
        return 0.0

    def _status_style(self) -> tuple[str, str]:
        if self.status == "QUEUEING":
            return ("QUEUEING", "rgba(255, 193, 7, 100)")
        if self.status == "MATCH FOUND":
            return ("MATCH FOUND", "rgba(76, 175, 80, 100)")
        return ("IDLE", "rgba(120, 120, 120, 95)")

    def _update_ui(self):
        elapsed = self._elapsed_seconds()
        self.timer_label.setText(
            "--:--.---" if self.status == "IDLE" else format_mmss_mmm(elapsed)
        )

        pill_text, pill_bg = self._status_style()
        self.status_pill.setText(pill_text)
        self.status_pill.setStyleSheet(
            f"""
            QLabel#StatusPill {{
              padding: 4px 10px;
              border-radius: 999px;
              color: rgba(255, 255, 255, 230);
              background-color: {pill_bg};
              border: 1px solid rgba(255, 255, 255, 45);
              min-width: 110px;
            }}
            """
        )

        self.map_label.setText(f"Map: {self.map_name}" if self.map_name else "Map: —")
        self.adjustSize()


# -----------------------------
# Tray icon
# -----------------------------


def build_tray(
    app: QtWidgets.QApplication,
    window: QtWidgets.QWidget,
) -> QtWidgets.QSystemTrayIcon:
    tray = QtWidgets.QSystemTrayIcon(app)
    tray.setIcon(get_app_icon())
    tray.setToolTip("TF2 Queue Timer Overlay")

    menu = QtWidgets.QMenu()
    act_show = menu.addAction("Show Overlay")
    act_hide = menu.addAction("Hide Overlay")
    menu.addSeparator()
    act_quit = menu.addAction("Quit")

    act_show.triggered.connect(window.show)
    act_hide.triggered.connect(window.hide)
    act_quit.triggered.connect(app.quit)

    tray.setContextMenu(menu)
    tray.show()
    return tray


# -----------------------------
# Startup popup
# -----------------------------


def show_startup_message(tray: QtWidgets.QSystemTrayIcon) -> None:
    title = "TF2 Queue Timer started"
    body = (
        "Running in the system tray.\n"
        "Right-click the tray icon to quit or show/hide the overlay."
    )

    if tray.supportsMessages():
        tray.showMessage(
            title,
            body,
            QtWidgets.QSystemTrayIcon.MessageIcon.Information,
            6000,
        )
    else:
        QtWidgets.QMessageBox.information(None, title, body)


# -----------------------------
# Main
# -----------------------------


def main():
    ensure_settings_file()

    log_path = get_console_log_path()
    if not log_path:
        QtWidgets.QApplication([])
        QtWidgets.QMessageBox.critical(
            None,
            "TF2 Queue Timer",
            "Could not find TF2 installation.\n"
            "Make sure TF2 is installed via Steam.",
        )
        sys.exit(1)

    clear_console_log(log_path)

    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.touch(exist_ok=True)
    except Exception:
        pass

    app = QtWidgets.QApplication([])
    app.setWindowIcon(get_app_icon())
    app.setQuitOnLastWindowClosed(False)

    window = OverlayWindow(log_path)
    window.hide()

    tray = build_tray(app, window)

    QtCore.QTimer.singleShot(400, lambda: show_startup_message(tray))

    sys.exit(app.exec())


if __name__ == "__main__":
    main()