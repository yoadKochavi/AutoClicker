<div align="center">

# ⚡ AutoClicker Pro

**A professional-grade, multithreaded auto-clicker with a modern dark GUI**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![PyQt6](https://img.shields.io/badge/PyQt6-GUI-41CD52?style=for-the-badge&logo=qt&logoColor=white)](https://pypi.org/project/PyQt6/)
[![pynput](https://img.shields.io/badge/pynput-Input-00B4D8?style=for-the-badge)](https://pypi.org/project/pynput/)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)
[![Author](https://img.shields.io/badge/Author-Yoad%20Kochavi-blueviolet?style=for-the-badge)](https://github.com/YoadKochavi)

<br/>

*Multithreaded · Global Hotkey · Precision Timing · Single-file EXE*

</div>

---

## 📌 Overview

**AutoClicker Pro** is a high-quality desktop automation tool built entirely in Python. It combines a sleek dark-themed **PyQt6** interface with low-level input simulation via **pynput**, running the click engine on a dedicated thread so the GUI stays perfectly responsive at all times.

Whether you need rapid clicks for gaming, stress-testing a UI, or automating repetitive tasks — AutoClicker Pro handles it with precision.

---

## ✨ Features

| | Feature | Description |
|---|---|---|
| 🔀 | **Multithreaded Architecture** | Click logic runs on a `QThread`, keeping the GUI 100% responsive |
| ⚡ | **Configurable CPS** | Set 0.1–50 clicks per second with real-time ms interval preview |
| 🖱️ | **Mouse Button Selector** | Choose Left, Right, or Middle click from a dropdown |
| 👆 | **Single / Double Click** | Toggle between single and double click modes |
| ⌨️ | **Global Hotkey** | Works system-wide, even when the window is minimized |
| 📊 | **Live Click Counter** | Tracks total clicks in real time per session |
| 🛑 | **Safe Stop Mechanism** | Dedicated Stop button and hotkey toggle prevent runaway clicks |
| 🎨 | **Dark Modern UI** | Navy/teal dark theme built with PyQt6 stylesheets |

---

## 🖥️ Screenshot

```
┌─────────────────────────────────────┐
│         ⚡  AutoClicker Pro          │
├─────────────────────────────────────┤
│  Click Speed                        │
│  CPS: [  5.0 ▲▼]   Interval: 200ms │
├─────────────────────────────────────┤
│  Mouse Button & Click Type          │
│  Button: [Left      ▼]              │
│  Type:   ● Single   ○ Double        │
├─────────────────────────────────────┤
│  Activation Hotkey                  │
│  Hotkey: [F6  ]  [Apply]  Active:F6 │
├─────────────────────────────────────┤
│  Status: ● Stopped                  │
│  [▶ Start]          [■ Stop]        │
│         Total Clicks: 0             │
└─────────────────────────────────────┘
```

---

## 📋 Requirements

- **Python** 3.10 or higher
- **PyQt6** ≥ 6.5.0
- **pynput** ≥ 1.7.6

---

## 🚀 Installation

### 1 · Clone the repository

```bash
git clone https://github.com/YoadKochavi/autoclicker-pro.git
cd autoclicker-pro
```

### 2 · Install dependencies

```bash
pip install PyQt6 pynput
```

### 3 · Run

```bash
python auto_clicker.py
```

---

## 📦 Build a Standalone EXE

No Python required on the target machine.

```bash
pip install pyinstaller
```

**Windows:**
```bash
pyinstaller --onefile --windowed \
            --name "AutoClickerPro" \
            --hidden-import=pynput.keyboard._win32 \
            --hidden-import=pynput.mouse._win32 \
            auto_clicker.py
```

**macOS / Linux:**
```bash
pyinstaller --onefile --windowed \
            --name "AutoClickerPro" \
            auto_clicker.py
```

> The compiled binary will be in the `dist/` folder.

> ⚠️ **Antivirus note:** PyInstaller bundles may trigger false positives. This is normal behaviour — you can verify the source code yourself before building.

---

## 🏗️ Architecture

The application uses **three concurrent threads** so nothing ever blocks:

| Thread | Class | Role |
|---|---|---|
| **Main Thread** | `QApplication / MainWindow` | PyQt6 event loop — UI rendering & user input |
| **Worker Thread** | `ClickWorker(QThread)` | Precision click loop with `perf_counter` timing |
| **Listener Thread** | `HotkeyListener` (daemon) | pynput keyboard hook — works system-wide |

### How the global hotkey works

`pynput`'s `Listener` runs on a raw OS-level daemon thread that intercepts input before any app sees it. When the hotkey fires, it calls `toggle()` on the worker. The worker emits a **Qt Signal** (`status_changed`), which Qt automatically marshals onto the main GUI thread via its event queue — so no GUI widget is ever touched from a background thread.

```
OS key press
  └─► pynput daemon thread  →  _on_press()
          └─► _toggle()
                  └─► ClickWorker.start/stop_clicking()
                          └─► status_changed.emit()  [Qt Signal]
                                  └─► _on_status_changed()  [GUI thread ✓]
```

---

## 🎮 Usage

1. Launch: `python auto_clicker.py`
2. Set your desired **CPS** (0.1 – 50)
3. Pick a **Mouse Button** (Left / Right / Middle)
4. Choose **Single** or **Double** click
5. Optionally change the **Hotkey** and click **Apply**
6. Press **▶ Start** or your hotkey — status turns green
7. Press **■ Stop** or the hotkey again to halt

---

## 📁 Project Structure

```
autoclicker-pro/
├── auto_clicker.py     # Full application — single-file architecture
│   ├── ClickWorker     # QThread subclass — precision click loop
│   ├── HotkeyListener  # pynput daemon thread wrapper
│   └── MainWindow      # PyQt6 QMainWindow — all UI & wiring
└── README.md
```

---

## 🖥️ Platform Support

| Platform | Status | Notes |
|---|---|---|
| 🪟 Windows | ✅ Fully supported | Use `--hidden-import=pynput.keyboard._win32` for PyInstaller |
| 🍎 macOS | ✅ Fully supported | Grant **Accessibility** permissions when prompted |
| 🐧 Linux | ✅ Fully supported | Add user to `input` group: `sudo usermod -aG input $USER` |

---

## ❓ FAQ

<details>
<summary><b>Why is the EXE flagged by antivirus?</b></summary>
<br>
PyInstaller bundles pack the entire Python runtime into one binary — a pattern historically abused by malware. The application contains no malicious code. Read <code>auto_clicker.py</code> before building to verify.
</details>

<details>
<summary><b>The hotkey doesn't work when another app is focused</b></summary>
<br>
Make sure you pressed <b>Apply</b> after entering a new hotkey. On Linux, confirm your user is in the <code>input</code> group. On macOS, confirm Accessibility permissions are granted in System Settings → Privacy & Security.
</details>

<details>
<summary><b>Can I exceed 50 CPS?</b></summary>
<br>
50 CPS is the enforced maximum to prevent accidental system overload. To raise it, change the <code>MAX_CPS</code> constant at the top of <code>auto_clicker.py</code>.
</details>

<details>
<summary><b>How do I reset the click counter?</b></summary>
<br>
The counter resets automatically every time you press <b>▶ Start</b>.
</details>

---

## 📄 License

This project is licensed under the **MIT License** — free to use, modify, and distribute for any purpose, commercial or otherwise, provided the original copyright notice is retained.

---

<div align="center">

Built with ❤️ by **Yoad Kochavi**

*If this project helped you, consider giving it a ⭐*

</div>
