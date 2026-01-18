from __future__ import annotations

import atexit
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


def get_app_dir() -> Path:
    """Directory for external files (settings.json). Next to the executable."""
    if hasattr(sys, "frozen"):  # PyInstaller
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent  # Development


def get_data_dir() -> Path:
    """Directory for bundled assets (font.ttf, icon.ico)."""
    if hasattr(sys, "_MEIPASS"):  # PyInstaller bundles to _MEIPASS
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent  # Development


APP_DIR = get_app_dir()
DATA_DIR = get_data_dir()
SETTINGS_PATH = APP_DIR / "settings.json"
FONT_PATH = DATA_DIR / "font.ttf"
ICON_PATH = DATA_DIR / "icon.ico"
LOCK_PATH = APP_DIR / ".lock"

DEFAULT_SETTINGS = {"pos": [24, 24], "opacity": 0.5, "font_size": 22}
TF2_PROCESS_NAME = "tf_win64.exe"

QUEUE_START_PATTERN = re.compile(
    r"^\[PartyClient\] (?:Requesting queue for|Entering queue for match group) .*Casual Match\b"
    r"|^\[ReliableMsg\] PartyQueueForMatch started\b"
)
MATCH_FOUND_PATTERN = re.compile(
    r"^\[PartyClient\] Leaving queue for match group .*Casual Match\b"
    r"|^\[ReliableMsg\] AcceptLobbyInvite\b"
    r"|^Lobby created\s*$"
    r"|^Differing lobby received\.",
    re.IGNORECASE,
)
MAP_PATTERN = re.compile(r"^Map:\s*([A-Za-z0-9_]+)")


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


def is_tf2_focused() -> bool:
    try:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return False
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        return psutil.Process(pid).name().lower() == TF2_PROCESS_NAME
    except Exception:
        return False


def get_steam_path() -> Optional[Path]:
    for root, subkey, value in [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", "InstallPath"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Valve\Steam", "SteamPath"),
    ]:
        try:
            key = winreg.OpenKey(root, subkey)
            val, _ = winreg.QueryValueEx(key, value)
            winreg.CloseKey(key)
            p = Path(val)
            if p.exists() and (p / "steam.exe").exists():
                return p
        except OSError:
            continue
    for p in [Path(r"C:\Program Files (x86)\Steam"), Path(r"C:\Program Files\Steam"),
              Path(r"D:\Steam"), Path(r"D:\SteamLibrary"), Path(r"E:\Steam"), Path(r"E:\SteamLibrary")]:
        if p.exists() and (p / "steam.exe").exists():
            return p
    return None


def get_library_folders(steam_path: Path) -> list[Path]:
    libs = [steam_path]
    vdf_path = steam_path / "steamapps" / "libraryfolders.vdf"
    if not vdf_path.exists():
        return libs
    try:
        text = vdf_path.read_text(encoding="utf-8", errors="ignore")
        strings = re.findall(r'"([^"]*)"', text)
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


def clear_console_log(log_path: Path) -> None:
    try:
        with open(log_path, "w", encoding="utf-8", errors="ignore"):
            pass
    except Exception:
        pass


class ConsoleLogFollower:
    def __init__(self, path: Path):
        self.path = path
        self.f = None
        self._last_size = 0

    def open(self) -> None:
        self.f = open(self.path, "r", encoding="utf-8", errors="ignore")
        self.f.seek(0, os.SEEK_END)
        try:
            self._last_size = self.path.stat().st_size
        except OSError:
            self._last_size = 0

    def close(self) -> None:
        if self.f:
            try:
                self.f.close()
            except Exception:
                pass
            self.f = None

    def poll_lines(self, max_lines: int = 250) -> list[str]:
        try:
            if self.f is None:
                self.open()
            try:
                current_size = self.path.stat().st_size
                if current_size < self._last_size:
                    self.close()
                    self.open()
                self._last_size = current_size
            except OSError:
                pass
            lines = []
            for _ in range(max_lines):
                pos = self.f.tell()
                line = self.f.readline()
                if not line:
                    self.f.seek(pos, os.SEEK_SET)
                    break
                lines.append(line.rstrip("\n"))
            return lines
        except (OSError, IOError):
            self.close()
            return []


def format_mmss_mmm(seconds: float) -> str:
    seconds = max(0.0, min(seconds, 99 * 3600 + 99 * 60 + 99.9))
    total_ms = int(seconds * 1000.0)
    total_secs = total_ms // 1000
    hours, mins, secs = total_secs // 3600, (total_secs % 3600) // 60, total_secs % 60
    ms = total_ms % 1000
    if hours > 0:
        return f"{hours:02d}:{mins:02d}:{secs:02d}.{ms // 100}"
    return f"{mins:02d}:{secs:02d}.{ms:03d}"


_cached_app_icon: Optional[QtGui.QIcon] = None


def get_app_icon() -> QtGui.QIcon:
    global _cached_app_icon
    if _cached_app_icon is not None:
        return _cached_app_icon
    if ICON_PATH.exists():
        _cached_app_icon = QtGui.QIcon(str(ICON_PATH))
    else:
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
        _cached_app_icon = QtGui.QIcon(pix)
    return _cached_app_icon


class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, overlay: "OverlayWindow", parent=None):
        super().__init__(parent)
        self.overlay = overlay
        self.settings = overlay.settings.copy()
        
        self.setWindowTitle("Settings")
        self.setWindowIcon(get_app_icon())
        self.setFixedWidth(300)
        
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(12)
        
        # Opacity
        opacity_group = QtWidgets.QGroupBox("Opacity")
        opacity_layout = QtWidgets.QHBoxLayout(opacity_group)
        self.opacity_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(10, 100)
        self.opacity_slider.setValue(int(self.settings["opacity"] * 100))
        self.opacity_label = QtWidgets.QLabel(f"{int(self.settings['opacity'] * 100)}%")
        self.opacity_label.setFixedWidth(40)
        self.opacity_slider.valueChanged.connect(self._on_opacity_change)
        opacity_layout.addWidget(self.opacity_slider)
        opacity_layout.addWidget(self.opacity_label)
        layout.addWidget(opacity_group)
        
        # Font Size
        font_group = QtWidgets.QGroupBox("Font Size")
        font_layout = QtWidgets.QHBoxLayout(font_group)
        self.font_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.font_slider.setRange(14, 40)
        self.font_slider.setValue(int(self.settings["font_size"]))
        self.font_label = QtWidgets.QLabel(f"{int(self.settings['font_size'])}pt")
        self.font_label.setFixedWidth(40)
        self.font_slider.valueChanged.connect(self._on_font_change)
        font_layout.addWidget(self.font_slider)
        font_layout.addWidget(self.font_label)
        layout.addWidget(font_group)
        
        # Position
        pos_group = QtWidgets.QGroupBox("Position (X, Y)")
        pos_layout = QtWidgets.QHBoxLayout(pos_group)
        self.pos_x = QtWidgets.QSpinBox()
        self.pos_x.setRange(0, 3840)
        self.pos_x.setValue(self.settings["pos"][0])
        self.pos_y = QtWidgets.QSpinBox()
        self.pos_y.setRange(0, 2160)
        self.pos_y.setValue(self.settings["pos"][1])
        pos_layout.addWidget(QtWidgets.QLabel("X:"))
        pos_layout.addWidget(self.pos_x)
        pos_layout.addWidget(QtWidgets.QLabel("Y:"))
        pos_layout.addWidget(self.pos_y)
        layout.addWidget(pos_group)
        
        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()
        self.save_btn = QtWidgets.QPushButton("Save")
        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        self.save_btn.clicked.connect(self._save)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
    
    def _on_opacity_change(self, value: int):
        self.opacity_label.setText(f"{value}%")
        self.overlay.setWindowOpacity(value / 100.0)
    
    def _on_font_change(self, value: int):
        self.font_label.setText(f"{value}pt")
    
    def _save(self):
        self.settings["opacity"] = self.opacity_slider.value() / 100.0
        self.settings["font_size"] = self.font_slider.value()
        self.settings["pos"] = [self.pos_x.value(), self.pos_y.value()]
        
        self.overlay.settings = self.settings
        self.overlay.setWindowOpacity(self.settings["opacity"])
        self.overlay.move(*self.settings["pos"])
        self.overlay.timer_label.setFont(self.overlay._font(self.settings["font_size"] + 10, True))
        self.overlay.adjustSize()
        
        save_settings(self.settings)
        self.accept()
    
    def reject(self):
        # Restore original opacity on cancel
        self.overlay.setWindowOpacity(self.overlay.settings["opacity"])
        super().reject()


class OverlayWindow(QtWidgets.QWidget):
    _STATUS_STYLES = {
        "IDLE": "QLabel#StatusPill { padding: 4px 10px; border-radius: 999px; color: rgba(255,255,255,230); background-color: rgba(120,120,120,95); border: 1px solid rgba(255,255,255,45); min-width: 110px; }",
        "QUEUEING": "QLabel#StatusPill { padding: 4px 10px; border-radius: 999px; color: rgba(255,255,255,230); background-color: rgba(255,193,7,100); border: 1px solid rgba(255,255,255,45); min-width: 110px; }",
        "MATCH FOUND": "QLabel#StatusPill { padding: 4px 10px; border-radius: 999px; color: rgba(255,255,255,230); background-color: rgba(76,175,80,100); border: 1px solid rgba(255,255,255,45); min-width: 110px; }",
    }

    def __init__(self, log_path: Path):
        super().__init__()
        self.settings = load_settings()
        self.status = "IDLE"
        self._last_status = ""
        self.queue_start_perf: Optional[float] = None
        self.last_match_found_seconds = 0.0
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

        self.poll_timer = QtCore.QTimer(self)
        self.poll_timer.timeout.connect(self._on_poll_tick)
        self.poll_timer.start(100)

        self.ui_timer = QtCore.QTimer(self)
        self.ui_timer.timeout.connect(self._update_ui)

        self.proc_timer = QtCore.QTimer(self)
        self.proc_timer.timeout.connect(self._sync_visibility)
        self.proc_timer.start(500)
        self._sync_visibility()

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

        header = QtWidgets.QHBoxLayout()
        header.setSpacing(10)
        self.title_label = QtWidgets.QLabel("Queue Timer")
        self.title_label.setFont(self._font(11, True))
        self.title_label.setObjectName("Title")
        self.status_pill = QtWidgets.QLabel("IDLE")
        self.status_pill.setFont(self._font(10, True))
        self.status_pill.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.status_pill.setObjectName("StatusPill")
        header.addWidget(self.title_label, 1)
        header.addWidget(self.status_pill, 0)
        layout.addLayout(header)

        self.timer_label = QtWidgets.QLabel("--:--.---")
        self.timer_label.setFont(self._font(int(self.settings["font_size"]) + 10, True))
        self.timer_label.setObjectName("Timer")
        self.timer_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.timer_label)

        self.map_label = QtWidgets.QLabel("Map: —")
        self.map_label.setFont(self._font(11, False))
        self.map_label.setObjectName("Meta")
        layout.addWidget(self.map_label)

        self.setStyleSheet("""
            QFrame#Card { background-color: rgba(18,18,20,165); border: 1px solid rgba(255,255,255,40); border-radius: 14px; }
            QLabel#Title { color: rgba(255,255,255,220); }
            QLabel#Timer { color: rgba(255,255,255,240); }
            QLabel#Meta { color: rgba(255,255,255,175); }
            QLabel#StatusPill { padding: 4px 10px; border-radius: 999px; color: rgba(255,255,255,230); background-color: rgba(120,120,120,95); border: 1px solid rgba(255,255,255,45); min-width: 110px; }
        """)
        self._update_ui()

    def _sync_visibility(self):
        if is_tf2_focused():
            if not self.isVisible():
                self.show()
            self.raise_()
        elif self.isVisible():
            self.hide()

    def _on_poll_tick(self):
        for line in self.follower.poll_lines():
            self._handle_line(line)

    def _handle_line(self, line: str):
        m = MAP_PATTERN.search(line)
        if m:
            self.map_name = m.group(1)
            self._update_ui()
            return
        if QUEUE_START_PATTERN.search(line):
            self.status = "QUEUEING"
            self.queue_start_perf = time.perf_counter()
            self.last_match_found_seconds = 0.0
            self.map_name = None
            self._update_timers()
            return
        if self.status == "QUEUEING" and self.queue_start_perf and MATCH_FOUND_PATTERN.search(line):
            self.status = "MATCH FOUND"
            self.last_match_found_seconds = time.perf_counter() - self.queue_start_perf
            self.queue_start_perf = None
            self._update_timers()

    def _update_timers(self):
        if self.status == "QUEUEING":
            self.poll_timer.setInterval(50)
            if not self.ui_timer.isActive():
                self.ui_timer.start(16)
        else:
            self.poll_timer.setInterval(100)
            if self.ui_timer.isActive():
                self.ui_timer.stop()
                self._update_ui()

    def _elapsed_seconds(self) -> float:
        if self.status == "QUEUEING" and self.queue_start_perf:
            return time.perf_counter() - self.queue_start_perf
        if self.status == "MATCH FOUND":
            return self.last_match_found_seconds
        return 0.0

    def _update_ui(self):
        self.timer_label.setText("--:--.---" if self.status == "IDLE" else format_mmss_mmm(self._elapsed_seconds()))
        if self.status != self._last_status:
            self.status_pill.setText(self.status)
            self.status_pill.setStyleSheet(self._STATUS_STYLES[self.status])
            self._last_status = self.status
        self.map_label.setText(f"Map: {self.map_name}" if self.map_name else "Map: —")
        self.adjustSize()

    def reset_timer(self):
        self.status = "IDLE"
        self.queue_start_perf = None
        self.last_match_found_seconds = 0.0
        self.map_name = None
        self._update_timers()
        self._update_ui()
    
    def show_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec()


def build_tray(app: QtWidgets.QApplication, window: OverlayWindow) -> QtWidgets.QSystemTrayIcon:
    tray = QtWidgets.QSystemTrayIcon(app)
    tray.setIcon(get_app_icon())
    tray.setToolTip("TF2 Queue Timer Overlay")
    menu = QtWidgets.QMenu()
    menu.addAction("Settings...").triggered.connect(window.show_settings)
    menu.addAction("Reset Timer").triggered.connect(window.reset_timer)
    menu.addSeparator()
    menu.addAction("Quit").triggered.connect(app.quit)
    tray.setContextMenu(menu)
    tray.show()
    return tray


def acquire_lock() -> bool:
    try:
        if LOCK_PATH.exists():
            try:
                old_pid = int(LOCK_PATH.read_text().strip())
                if psutil.pid_exists(old_pid):
                    try:
                        proc = psutil.Process(old_pid)
                        if "python" in proc.name().lower() or "tf2queuetimer" in proc.name().lower():
                            return False
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
            except (ValueError, OSError):
                pass
        LOCK_PATH.write_text(str(os.getpid()))
        return True
    except Exception:
        return True


def release_lock() -> None:
    try:
        if LOCK_PATH.exists() and int(LOCK_PATH.read_text().strip()) == os.getpid():
            LOCK_PATH.unlink()
    except Exception:
        pass


def main():
    if not acquire_lock():
        app = QtWidgets.QApplication([])
        app.setWindowIcon(get_app_icon())
        QtWidgets.QMessageBox.warning(None, "TF2 Queue Timer", "Another instance is already running.\nCheck your system tray.")
        sys.exit(0)

    atexit.register(release_lock)
    ensure_settings_file()

    tf_dir = find_tf2_tf_dir()
    if not tf_dir:
        app = QtWidgets.QApplication([])
        app.setWindowIcon(get_app_icon())
        QtWidgets.QMessageBox.critical(None, "TF2 Queue Timer", "Could not find TF2 installation.\nMake sure TF2 is installed via Steam.")
        sys.exit(1)

    log_path = tf_dir / "console.log"
    if not log_path.exists():
        app = QtWidgets.QApplication([])
        app.setWindowIcon(get_app_icon())
        QtWidgets.QMessageBox.warning(None, "TF2 Queue Timer",
            f"TF2 console.log was not found.\n\nAdd -condebug to TF2 launch options:\nSteam → Library → TF2 → Properties → Launch Options\n\nExpected: {tf_dir}\\console.log")
        sys.exit(1)

    clear_console_log(log_path)

    app = QtWidgets.QApplication([])
    app.setWindowIcon(get_app_icon())
    app.setQuitOnLastWindowClosed(False)

    window = OverlayWindow(log_path)
    window.hide()

    tray = build_tray(app, window)
    QtCore.QTimer.singleShot(400, lambda: tray.showMessage("TF2 Queue Timer started", "Running in the system tray.\nRight-click the tray icon for options.", QtWidgets.QSystemTrayIcon.MessageIcon.Information, 6000) if tray.supportsMessages() else None)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()