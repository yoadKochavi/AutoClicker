"""
Professional Auto-Clicker Application
======================================
A high-quality, multithreaded auto-clicker with a modern PyQt6 GUI.
Uses pynput for low-level mouse/keyboard interaction and threading
for non-blocking operation.

Author: Yoad Kochavi
"""

import sys
import threading
import time

from PyQt6.QtCore import Qt, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QFont, QIcon, QColor, QPalette
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QDoubleSpinBox, QFrame,
    QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QPushButton, QRadioButton,
    QSpinBox, QVBoxLayout, QWidget, QButtonGroup,
)
from pynput import keyboard as kb
from pynput import mouse as ms

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
APP_NAME = "AutoClicker Pro"
VERSION = "1.0.0"
DEFAULT_CPS = 5.0          # Clicks per second
MIN_CPS = 0.1
MAX_CPS = 50.0
HOTKEY_DEFAULT = "F6"

BUTTON_MAP = {
    "Left":   ms.Button.left,
    "Right":  ms.Button.right,
    "Middle": ms.Button.middle,
}

SPECIAL_KEYS = {
    "F1": kb.Key.f1, "F2": kb.Key.f2, "F3": kb.Key.f3,
    "F4": kb.Key.f4, "F5": kb.Key.f5, "F6": kb.Key.f6,
    "F7": kb.Key.f7, "F8": kb.Key.f8, "F9": kb.Key.f9,
    "F10": kb.Key.f10, "F11": kb.Key.f11, "F12": kb.Key.f12,
}


# ---------------------------------------------------------------------------
# ClickWorker – runs on a dedicated QThread
# ---------------------------------------------------------------------------
class ClickWorker(QThread):
    """
    Worker thread that performs the actual mouse clicking.

    Signals:
        status_changed (str): Emitted when the running state changes.
        click_count_changed (int): Emitted after each click with total count.
    """

    status_changed = pyqtSignal(str)
    click_count_changed = pyqtSignal(int)

    def __init__(self) -> None:
        super().__init__()
        self._running = False
        self._stop_event = threading.Event()
        self._mouse = ms.Controller()

        # Configuration (set before starting)
        self.cps: float = DEFAULT_CPS
        self.button: ms.Button = ms.Button.left
        self.double_click: bool = False
        self._click_count: int = 0

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def configure(
        self,
        cps: float,
        button: ms.Button,
        double_click: bool,
    ) -> None:
        """Update clicking parameters (safe to call while stopped)."""
        self.cps = max(MIN_CPS, min(MAX_CPS, cps))
        self.button = button
        self.double_click = double_click

    def start_clicking(self) -> None:
        """Begin the clicking loop on this QThread."""
        if self._running:
            return
        self._click_count = 0
        self._stop_event.clear()
        self._running = True
        self.start()                    # Calls run() in a new OS thread
        self.status_changed.emit("Running")

    def stop_clicking(self) -> None:
        """Signal the clicking loop to stop."""
        if not self._running:
            return
        self._stop_event.set()
        self._running = False
        self.status_changed.emit("Stopped")

    # ------------------------------------------------------------------
    # QThread entry point
    # ------------------------------------------------------------------

    def run(self) -> None:
        """
        Core click loop – executes in the worker thread.
        Sleeps between clicks using a high-resolution timer.
        """
        interval = 1.0 / self.cps

        while not self._stop_event.is_set():
            tick = time.perf_counter()

            if self.double_click:
                self._mouse.click(self.button, 2)
            else:
                self._mouse.click(self.button, 1)

            self._click_count += 1
            self.click_count_changed.emit(self._click_count)

            # Precision sleep: account for execution time
            elapsed = time.perf_counter() - tick
            remaining = interval - elapsed
            if remaining > 0:
                self._stop_event.wait(remaining)

        self._running = False


# ---------------------------------------------------------------------------
# HotkeyListener – runs on a plain daemon thread (pynput requirement)
# ---------------------------------------------------------------------------
class HotkeyListener:
    """
    Listens for a global hotkey using pynput's keyboard Listener.

    The listener runs on its own daemon thread so it works even when
    the application window is minimized or does not have focus.

    Parameters:
        hotkey_str: Key name, e.g. "F6" or "a".
        callback:   Called (no args) whenever the hotkey fires.
    """

    def __init__(self, hotkey_str: str, callback) -> None:
        self._hotkey_str = hotkey_str.strip()
        self._callback = callback
        self._listener: kb.Listener | None = None
        self._target_key = self._resolve_key(self._hotkey_str)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_key(name: str):
        """Return a pynput Key enum or a KeyCode for single characters."""
        upper = name.upper()
        if upper in SPECIAL_KEYS:
            return SPECIAL_KEYS[upper]
        # Single character
        if len(name) == 1:
            return kb.KeyCode.from_char(name.lower())
        return None

    # ------------------------------------------------------------------
    # Listener management
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the background listener thread."""
        self.stop()                     # Ensure no duplicate listeners
        if self._target_key is None:
            return

        self._listener = kb.Listener(on_press=self._on_press)
        self._listener.daemon = True    # Dies when main process exits
        self._listener.start()

    def stop(self) -> None:
        """Stop the background listener thread."""
        if self._listener and self._listener.is_alive():
            self._listener.stop()
        self._listener = None

    def update_hotkey(self, hotkey_str: str) -> None:
        """Replace the active hotkey at runtime."""
        self._hotkey_str = hotkey_str.strip()
        self._target_key = self._resolve_key(self._hotkey_str)
        self.start()

    # ------------------------------------------------------------------
    # Internal callback
    # ------------------------------------------------------------------

    def _on_press(self, key) -> None:
        """Fired on every key press; delegates only for the target key."""
        try:
            if key == self._target_key:
                self._callback()
        except Exception:
            pass                        # Silently ignore unexpected key types


# ---------------------------------------------------------------------------
# MainWindow – the PyQt6 GUI
# ---------------------------------------------------------------------------
class MainWindow(QMainWindow):
    """
    Primary application window.

    Wires the ClickWorker, HotkeyListener, and all UI controls together
    following a clean Model-View-Controller-ish structure.
    """

    def __init__(self) -> None:
        super().__init__()

        # Core components
        self._worker = ClickWorker()
        self._hotkey_listener = HotkeyListener(HOTKEY_DEFAULT, self._toggle)

        # Connect worker signals to GUI slots (thread-safe via Qt signals)
        self._worker.status_changed.connect(self._on_status_changed)
        self._worker.click_count_changed.connect(self._on_click_count_changed)

        self._build_ui()
        self._apply_styles()
        self._hotkey_listener.start()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Assemble all widgets and layouts."""
        self.setWindowTitle(f"{APP_NAME}  v{VERSION}")
        self.setMinimumWidth(400)
        self.setMaximumWidth(480)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(12)
        root.setContentsMargins(18, 18, 18, 18)

        # -- Header --
        root.addWidget(self._build_header())

        # -- Config groups --
        root.addWidget(self._build_speed_group())
        root.addWidget(self._build_button_group_widget())
        root.addWidget(self._build_hotkey_group())

        # -- Status bar --
        root.addWidget(self._build_status_bar())

        # -- Action buttons --
        root.addLayout(self._build_action_buttons())

        # -- Click counter --
        root.addWidget(self._build_counter())

    def _build_header(self) -> QLabel:
        lbl = QLabel(f"⚡  {APP_NAME}")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setObjectName("header")
        return lbl

    def _build_speed_group(self) -> QGroupBox:
        group = QGroupBox("Click Speed")
        layout = QGridLayout(group)

        # CPS spinner
        layout.addWidget(QLabel("Clicks per second (CPS):"), 0, 0)
        self._cps_spin = QDoubleSpinBox()
        self._cps_spin.setRange(MIN_CPS, MAX_CPS)
        self._cps_spin.setValue(DEFAULT_CPS)
        self._cps_spin.setSingleStep(0.5)
        self._cps_spin.setDecimals(1)
        layout.addWidget(self._cps_spin, 0, 1)

        # Derived ms display
        layout.addWidget(QLabel("Interval (ms):"), 1, 0)
        self._ms_label = QLabel(self._cps_to_ms_str(DEFAULT_CPS))
        self._ms_label.setObjectName("derived")
        layout.addWidget(self._ms_label, 1, 1)

        self._cps_spin.valueChanged.connect(
            lambda v: self._ms_label.setText(self._cps_to_ms_str(v))
        )
        return group

    def _build_button_group_widget(self) -> QGroupBox:
        group = QGroupBox("Mouse Button & Click Type")
        layout = QVBoxLayout(group)

        # Button selector
        h1 = QHBoxLayout()
        h1.addWidget(QLabel("Button:"))
        self._btn_combo = QComboBox()
        self._btn_combo.addItems(["Left", "Right", "Middle"])
        h1.addWidget(self._btn_combo)
        layout.addLayout(h1)

        # Click type radio buttons
        h2 = QHBoxLayout()
        h2.addWidget(QLabel("Type:"))
        self._single_radio = QRadioButton("Single")
        self._double_radio = QRadioButton("Double")
        self._single_radio.setChecked(True)
        self._click_type_group = QButtonGroup()
        self._click_type_group.addButton(self._single_radio)
        self._click_type_group.addButton(self._double_radio)
        h2.addWidget(self._single_radio)
        h2.addWidget(self._double_radio)
        layout.addLayout(h2)

        return group

    def _build_hotkey_group(self) -> QGroupBox:
        group = QGroupBox("Activation Hotkey")
        layout = QHBoxLayout(group)

        layout.addWidget(QLabel("Hotkey:"))
        self._hotkey_edit = QLineEdit(HOTKEY_DEFAULT)
        self._hotkey_edit.setMaximumWidth(80)
        self._hotkey_edit.setPlaceholderText("e.g. F6")
        layout.addWidget(self._hotkey_edit)

        apply_btn = QPushButton("Apply")
        apply_btn.setObjectName("secondary")
        apply_btn.clicked.connect(self._apply_hotkey)
        layout.addWidget(apply_btn)

        self._hotkey_status = QLabel(f"Active: {HOTKEY_DEFAULT}")
        self._hotkey_status.setObjectName("derived")
        layout.addWidget(self._hotkey_status)

        return group

    def _build_status_bar(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("statusFrame")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(12, 6, 12, 6)

        layout.addWidget(QLabel("Status:"))
        self._status_label = QLabel("Stopped")
        self._status_label.setObjectName("statusStopped")
        layout.addWidget(self._status_label)
        layout.addStretch()

        return frame

    def _build_action_buttons(self) -> QHBoxLayout:
        layout = QHBoxLayout()

        self._start_btn = QPushButton("▶  Start")
        self._start_btn.setObjectName("startBtn")
        self._start_btn.clicked.connect(self._start)
        layout.addWidget(self._start_btn)

        self._stop_btn = QPushButton("■  Stop")
        self._stop_btn.setObjectName("stopBtn")
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._stop)
        layout.addWidget(self._stop_btn)

        return layout

    def _build_counter(self) -> QLabel:
        self._counter_label = QLabel("Total Clicks: 0")
        self._counter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._counter_label.setObjectName("counter")
        return self._counter_label

    # ------------------------------------------------------------------
    # Styling
    # ------------------------------------------------------------------

    def _apply_styles(self) -> None:
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1a1d2e;
                color: #e0e4f0;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
            }
            QGroupBox {
                border: 1px solid #2e3250;
                border-radius: 8px;
                margin-top: 10px;
                padding: 10px 8px 8px 8px;
                font-weight: bold;
                color: #8892b0;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
            QLabel#header {
                font-size: 20px;
                font-weight: bold;
                color: #64ffda;
                padding: 6px 0;
            }
            QLabel#derived {
                color: #8892b0;
                font-size: 12px;
            }
            QLabel#counter {
                color: #8892b0;
                font-size: 12px;
                padding-bottom: 4px;
            }
            QFrame#statusFrame {
                background-color: #0d0f1a;
                border-radius: 6px;
            }
            QLabel#statusRunning {
                color: #64ffda;
                font-weight: bold;
                font-size: 14px;
            }
            QLabel#statusStopped {
                color: #ff6b6b;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton {
                border-radius: 6px;
                padding: 8px 18px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton#startBtn {
                background-color: #64ffda;
                color: #0d0f1a;
                border: none;
            }
            QPushButton#startBtn:hover { background-color: #4dcfb0; }
            QPushButton#startBtn:disabled { background-color: #2a3a35; color: #4a6a60; }
            QPushButton#stopBtn {
                background-color: #ff6b6b;
                color: #0d0f1a;
                border: none;
            }
            QPushButton#stopBtn:hover { background-color: #e05555; }
            QPushButton#stopBtn:disabled { background-color: #3a2a2a; color: #6a4a4a; }
            QPushButton#secondary {
                background-color: #2e3250;
                color: #8892b0;
                border: 1px solid #3e4470;
            }
            QPushButton#secondary:hover { background-color: #3e4470; }
            QDoubleSpinBox, QSpinBox, QComboBox, QLineEdit {
                background-color: #0d0f1a;
                border: 1px solid #2e3250;
                border-radius: 5px;
                padding: 4px 8px;
                color: #e0e4f0;
            }
            QComboBox::drop-down { border: none; }
            QRadioButton { spacing: 6px; }
            QRadioButton::indicator {
                width: 14px; height: 14px;
                border-radius: 7px;
                border: 2px solid #3e4470;
                background: #0d0f1a;
            }
            QRadioButton::indicator:checked {
                background: #64ffda;
                border-color: #64ffda;
            }
        """)

    # ------------------------------------------------------------------
    # Slots & actions
    # ------------------------------------------------------------------

    @pyqtSlot(str)
    def _on_status_changed(self, status: str) -> None:
        """Update status label and button states on the GUI thread."""
        is_running = status == "Running"
        self._status_label.setText(status)
        self._status_label.setObjectName(
            "statusRunning" if is_running else "statusStopped"
        )
        # Force style refresh after objectName change
        self._status_label.style().unpolish(self._status_label)
        self._status_label.style().polish(self._status_label)

        self._start_btn.setEnabled(not is_running)
        self._stop_btn.setEnabled(is_running)

    @pyqtSlot(int)
    def _on_click_count_changed(self, count: int) -> None:
        self._counter_label.setText(f"Total Clicks: {count:,}")

    def _toggle(self) -> None:
        """Toggle start/stop – safe to call from any thread."""
        if self._worker.isRunning():
            self._stop()
        else:
            self._start()

    def _start(self) -> None:
        """Read config and start the worker thread."""
        self._worker.configure(
            cps=self._cps_spin.value(),
            button=BUTTON_MAP[self._btn_combo.currentText()],
            double_click=self._double_radio.isChecked(),
        )
        self._worker.start_clicking()

    def _stop(self) -> None:
        self._worker.stop_clicking()

    def _apply_hotkey(self) -> None:
        raw = self._hotkey_edit.text().strip()
        if not raw:
            return
        self._hotkey_listener.update_hotkey(raw)
        self._hotkey_status.setText(f"Active: {raw.upper()}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _cps_to_ms_str(cps: float) -> str:
        return f"{1000.0 / cps:.1f} ms"

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:
        """Ensure all threads are stopped on exit."""
        self._worker.stop_clicking()
        self._hotkey_listener.stop()
        self._worker.wait(2000)     # Give worker thread up to 2 s to finish
        event.accept()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()