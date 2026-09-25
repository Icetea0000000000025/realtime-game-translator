#!/usr/bin/env python3
"""
live_translate_windows.py

Real-time audio transcription and translation for Windows.
- Audio capture via WASAPI Loopback (YouTube, PC Games, Videos) or Microphone / Sounddevice
- Speech-to-Text via faster-whisper (CTranslate2, local offline AI)
- Translation via Google Gemini AI, Ollama LLM, or TranslatePy
- UI: Floating translucent dark overlay (Tkinter) with side-by-side original + translation
"""

import argparse
import contextlib
import json
import os
import queue
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk
from typing import Optional, Tuple, List, cast

try:
    import ctypes
    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
    HAS_WIN32 = True
    GWL_EXSTYLE = -20
    WS_EX_TRANSPARENT = 0x00000020
    WS_EX_LAYERED = 0x00080000
except Exception:
    HAS_WIN32 = False

import numpy as np

def setup_cuda_dlls():
    """Register CUDA & cuDNN pip package dll directories so CTranslate2 can use CUDA on Windows."""
    if sys.platform != "win32":
        return
    import site
    dirs_to_check = []
    base_dir = os.path.dirname(os.path.abspath(__file__))
    venv_site = os.path.join(base_dir, ".venv", "Lib", "site-packages")
    if os.path.isdir(venv_site):
        dirs_to_check.append(venv_site)
    with contextlib.suppress(Exception):
        dirs_to_check.extend(site.getsitepackages())
    with contextlib.suppress(Exception):
        user_site = site.getusersitepackages()
        if user_site:
            dirs_to_check.append(user_site)

    for sp in dirs_to_check:
        nvidia_root = os.path.join(sp, "nvidia")
        if os.path.isdir(nvidia_root):
            for root, dirs, files in os.walk(nvidia_root):
                for f in files:
                    if f.endswith(".dll"):
                        with contextlib.suppress(Exception):
                            os.add_dll_directory(root)
                        if root not in os.environ.get("PATH", ""):
                            os.environ["PATH"] = root + os.pathsep + os.environ.get("PATH", "")
                        break

setup_cuda_dlls()

# sounddevice for microphone input
try:
    import sounddevice as sd
    HAS_SD = True
except ImportError:
    HAS_SD = False

# pyaudiowpatch for WASAPI Loopback (system audio)
try:
    import pyaudiowpatch as pyaudio
    HAS_PYAUDIO = True
except ImportError:
    HAS_PYAUDIO = False

from live_translation.text_pipeline import (
    LANG_MENU,
    WAITING_ORIGINAL,
    WAITING_TRANSLATION,
    dedup_words_by_time,
    language_label,
    merge_overlap_text,
    punctuated_context,
    sentence_case_text,
    strip_hallucinations,
    take_blocks_for_translation,
    take_endpoint_blocks,
)
from live_translation.translators import (
    LanguageSettings,
    OllamaTranslator,
    GeminiTranslator,
    FallbackTranslator,
)

WHISPER_MODELS = ["tiny", "base", "small", "medium", "turbo", "large-v3"]


def load_config():
    """Loads config.json and .env if present in the current or parent directory."""
    with contextlib.suppress(Exception):
        from dotenv import load_dotenv
        load_dotenv()

    for p in ["config.json", os.path.join(os.path.dirname(__file__), "config.json")]:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    return {}


def is_device_openable(device_idx: int) -> Tuple[bool, int]:
    """Test if a device can actually be opened by PortAudio, and return (openable, native_samplerate)."""
    if not HAS_SD:
        return False, 0
    try:
        dev = cast(dict, sd.query_devices(device_idx))
        if dev.get("max_input_channels", 0) <= 0:
            return False, 0
        hostapi = dev.get("hostapi", -1)
        api_name = sd.query_hostapis(hostapi).get("name", "") if hostapi >= 0 else ""
        if "wdm-ks" in api_name.lower():
            return False, 0
        
        native_sr = int(dev.get("default_samplerate", 16000)) or 16000
        with sd.InputStream(device=device_idx, channels=1, samplerate=native_sr):
            pass
        return True, native_sr
    except Exception:
        try:
            with sd.InputStream(device=device_idx, channels=1, samplerate=16000):
                pass
            return True, 16000
        except Exception:
            return False, 0


def list_devices():
    """Print all available audio devices on Windows and indicate working ones."""
    print("\n--- Available Audio Devices on Windows ---")
    if HAS_PYAUDIO:
        try:
            p = pyaudio.PyAudio()
            print("  [Loopback Available]: WASAPI Loopback (Captures internal PC Audio / YouTube / Games)")
            for d in p.get_loopback_device_info_generator():
                print(f"    * {d['name']}")
            p.terminate()
        except Exception:
            pass

    if HAS_SD:
        devices = sd.query_devices()
        for idx, dev in enumerate(devices):
            dev = cast(dict, dev)
            channels_in = dev.get("max_input_channels", 0)
            name = dev.get("name", "Unknown")
            hostapi = dev.get("hostapi", 0)
            api_name = sd.query_hostapis(hostapi).get("name", "") if hostapi is not None else ""
            if channels_in > 0:
                openable, sr = is_device_openable(idx)
                status = f"[Ready - {sr}Hz]" if openable else "[Unavailable / Error]"
                hint = ""
                if "stereo mix" in name.lower():
                    hint = " (Stereo Mix)"
                elif "cable output" in name.lower() or "virtual" in name.lower():
                    hint = " (Virtual Cable)"
                print(f"  [{idx:2d}] IN:  {name} ({api_name}){hint} -> {status}")
    print("\nUse '--mode loopback' for internal audio (YouTube/Games), or '--mode mic' for Microphone.")
    print("Example: python live_translate_windows.py --mode loopback\n")


def auto_detect_input_device() -> Tuple[Optional[int], str, int]:
    """Auto-detect suitable, openable microphone input device."""
    if not HAS_SD:
        return None, "None", 16000
    devices = sd.query_devices()

    # 1. System default input
    try:
        default_in = sd.default.device[0]
        if default_in is not None and default_in >= 0:
            openable, sr = is_device_openable(default_in)
            if openable:
                dev_info = cast(dict, sd.query_devices(default_in))
                return default_in, dev_info.get("name", "Default Input"), sr
    except Exception:
        pass

    # 2. Any openable input
    for idx, dev in enumerate(devices):
        dev = cast(dict, dev)
        if dev.get("max_input_channels", 0) > 0:
            openable, sr = is_device_openable(idx)
            if openable:
                return idx, dev.get("name", f"Device {idx}"), sr

    return None, "None", 16000


class ConsoleOverlay:
    """Terminal output overlay (--no-window)."""
    def __init__(self, stop_event, show_partial=False):
        self.stop_event = stop_event
        self.show_partial = show_partial

    def post_pair(self, source, translated, **kwargs):
        if source:
            print("\n[Original]   ", source)
        if translated:
            print("[Translation]", translated, flush=True)

    def post_source(self, source, **kwargs):
        if source:
            print("\n[Speech]     ", source, flush=True)

    def post_status_text(self, text, **kwargs):
        if text:
            print(f"[*] {text}", flush=True)

    def post_partial(self, source):
        if self.show_partial and source:
            print(f"~ {source}", flush=True)

    def set_engine_status(self, engine_name: str):
        pass

    def run(self):
        while not self.stop_event.is_set():
            time.sleep(0.2)

    def stop(self):
        self.stop_event.set()


class TkinterOverlay:
    """
    Dual-mode Overlay for Windows:
    1. Compact Mode (โหมดย่อ): Transparent, borderless floating subtitle HUD showing only translated text.
    2. Full Mode (โหมดหน้าใหญ่): Complete 2-column dashboard with original speech, translated text history, and status.
    """
    def __init__(
        self,
        stop_event,
        title="Live Translation (Windows)",
        width=960,
        height=130,
        opacity=1.0,
        show_partial=False,
        on_switch_source=None,
        current_engine="google",
        on_switch_engine=None,
        has_gemini=False,
        source_lang="en",
        target_lang="th",
        on_switch_lang=None,
    ):
        self.stop_event = stop_event
        self.title = title
        self.canvas_w = width
        self.canvas_h = height
        self.show_partial = show_partial
        self.on_switch_source = on_switch_source
        self.current_engine = current_engine
        self.on_switch_engine = on_switch_engine
        self.has_gemini = has_gemini
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.on_switch_lang = on_switch_lang
        self.msg_queue = queue.Queue()

        # State
        self.is_compact = True
        self.font_size = 24
        self.font_color = "#00FFCC"
        self.auto_hide_seconds = 6.0
        self._last_post_time = time.monotonic()
        self._current_text = ""

        # Mini Bar State (ซ่อนอัตโนมัติ / โปร่งใส ไร้กล่องทึบ)
        self.bar_visible = True
        self.bar_display_mode = "auto"  # "auto" | "always_hide" | "always_show"
        self._bar_hide_timer = time.monotonic() + 3.0
        self._is_dragging = False

        # Lock state (ป้องกันการเลื่อน / ล็อกตำแหน่ง)
        self.is_locked = False

        # Tk root window
        self.root = tk.Tk()
        self.root.title(title)
        self.root.attributes("-topmost", True)

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        init_cx = max(20, (sw - self.canvas_w) // 2)
        init_cy = max(40, int(sh * 0.78))
        self.compact_geo = f"{self.canvas_w}x{self.canvas_h + 32}+{init_cx}+{init_cy}"

        init_fx = max(20, (sw - 850) // 2)
        init_fy = max(40, (sh - 440) // 2)
        self.full_geo = f"850x440+{init_fx}+{init_fy}"

        # Drag state
        self._drag_data = {"x": 0, "y": 0}

        self._build_ui()
        self.switch_to_compact()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Hotkeys
        self.root.bind("<F2>", lambda e: self.toggle_mode())
        self.root.bind("<F3>", lambda e: self.toggle_bar())
        self.root.bind("<F4>", lambda e: self.toggle_lock())
        self.root.bind("<F8>", lambda e: self.toggle_engine())
        self.root.bind("<F10>", lambda e: self.toggle_lock())

    def _build_ui(self):
        # -----------------------------
        # 1. COMPACT FRAME (โหมดย่อ: ซับโปร่งใส)
        # -----------------------------
        self.compact_frame = tk.Frame(self.root, bg="#010101")

        # Compact Mini Bar (โปร่งใส 100% ไร้กล่องทึบบดบังสายตา)
        self.bar = tk.Frame(self.compact_frame, bg="#010101")
        self.bar.pack(anchor="center", pady=(0, 2))

        self.drag_lbl = tk.Label(
            self.bar,
            text="⠿ ลากเพื่อย้าย",
            font=("Segoe UI", 8, "bold"),
            fg="#94A3B8",
            bg="#010101",
            padx=8,
            pady=2,
            cursor="fleur"
        )
        self.drag_lbl.pack(side=tk.LEFT, padx=(0, 4))
        self.drag_lbl.bind("<ButtonPress-1>", self._start_drag)
        self.drag_lbl.bind("<B1-Motion>", self._on_drag)
        self.drag_lbl.bind("<ButtonRelease-1>", self._stop_drag)
        self.drag_lbl.bind("<Enter>", lambda e: self.drag_lbl.config(fg="#FFFFFF"))
        self.drag_lbl.bind("<Leave>", lambda e: self.drag_lbl.config(fg="#94A3B8"))

        # Lock Button (ปุ่มล็อกตำแหน่ง / ปลดล็อก)
        self.btn_lock = tk.Label(
            self.bar,
            text="🔓 ล็อก (F4)",
            font=("Segoe UI", 8, "bold"),
            fg="#38BDF8",
            bg="#010101",
            padx=6,
            pady=2,
            cursor="hand2"
        )
        self.btn_lock.pack(side=tk.LEFT, padx=(0, 4))
        self.btn_lock.bind("<Button-1>", lambda e: self.toggle_lock())
        self.btn_lock.bind("<Enter>", lambda e: self.btn_lock.config(fg="#FFFFFF"))
        self.btn_lock.bind("<Leave>", lambda e: self.btn_lock.config(fg="#F59E0B" if self.is_locked else "#38BDF8"))

        # Engine Switch Button (Google Fast ⚡ / Gemini AI 🤖)
        self.btn_engine = tk.Label(
            self.bar,
            text="⚡ เร็ว (F8)" if self.current_engine == "google" else "🤖 AI (F8)",
            font=("Segoe UI", 8, "bold"),
            fg="#38BDF8" if self.current_engine == "google" else "#A78BFA",
            bg="#010101",
            padx=6,
            pady=2,
            cursor="hand2"
        )
        self.btn_engine.pack(side=tk.LEFT, padx=(0, 4))
        self.btn_engine.bind("<Button-1>", lambda e: self.toggle_engine())
        self.btn_engine.bind("<Enter>", lambda e: self.btn_engine.config(fg="#FFFFFF"))
        self.btn_engine.bind("<Leave>", lambda e: self.btn_engine.config(fg="#38BDF8" if self.current_engine == "google" else "#A78BFA"))

        # Button to switch to Full Window
        self.btn_to_full = tk.Label(
            self.bar,
            text="🗖 หน้าใหญ่ (F2)",
            font=("Segoe UI", 8, "bold"),
            fg="#00FFCC",
            bg="#010101",
            padx=6,
            pady=2,
            cursor="hand2"
        )
        self.btn_to_full.pack(side=tk.LEFT, padx=(0, 4))
        self.btn_to_full.bind("<Button-1>", lambda e: self.switch_to_full())
        self.btn_to_full.bind("<Enter>", lambda e: self.btn_to_full.config(fg="#FFFFFF"))
        self.btn_to_full.bind("<Leave>", lambda e: self.btn_to_full.config(fg="#00FFCC"))

        self.btn_close_compact = tk.Label(
            self.bar,
            text="✖ ปิด",
            font=("Segoe UI", 8, "bold"),
            fg="#EF4444",
            bg="#010101",
            padx=6,
            pady=2,
            cursor="hand2"
        )
        self.btn_close_compact.pack(side=tk.LEFT)
        self.btn_close_compact.bind("<Button-1>", lambda e: self.on_close())
        self.btn_close_compact.bind("<Enter>", lambda e: self.btn_close_compact.config(fg="#FFAAAA"))
        self.btn_close_compact.bind("<Leave>", lambda e: self.btn_close_compact.config(fg="#EF4444"))

        # Bind bar drag
        self.bar.bind("<ButtonPress-1>", self._start_drag)
        self.bar.bind("<B1-Motion>", self._on_drag)
        self.bar.bind("<ButtonRelease-1>", self._stop_drag)

        # Subtitle Canvas (100% transparent background with 8-direction shadow text)
        self.canvas = tk.Canvas(
            self.compact_frame,
            bg="#010101",
            highlightthickness=0,
            width=self.canvas_w,
            height=self.canvas_h,
            cursor="fleur"
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<ButtonPress-1>", self._start_drag)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._stop_drag)

        # -----------------------------
        # 2. FULL FRAME (โหมดหน้าใหญ่: แผงควบคุม 2 คอลัมน์)
        # -----------------------------
        self.full_frame = tk.Frame(self.root, bg="#0f1117")

        # Full Header
        header = tk.Frame(self.full_frame, bg="#161922", height=38)
        header.pack(fill=tk.X, side=tk.TOP)

        title_lbl = tk.Label(
            header,
            text="  🌐 Live Translation (โหมดหน้าใหญ่)",
            font=("Segoe UI", 10, "bold"),
            fg="#00FFCC",
            bg="#161922"
        )
        title_lbl.pack(side=tk.LEFT, pady=6)

        self.status_label = tk.Label(header, text="● Ready", font=("Segoe UI", 9), fg="#94A3B8", bg="#161922")
        self.status_label.pack(side=tk.LEFT, padx=10, pady=6)

        btn_close_full = tk.Button(
            header,
            text="✖ ปิด",
            font=("Segoe UI", 8, "bold"),
            fg="#EF4444",
            bg="#232936",
            relief="flat",
            padx=8,
            command=self.on_close
        )
        btn_close_full.pack(side=tk.RIGHT, padx=8, pady=4)

        btn_clear = tk.Button(
            header,
            text="ล้างประวัติ (Clear)",
            font=("Segoe UI", 8),
            fg="#E2E8F0",
            bg="#232936",
            relief="flat",
            padx=8,
            command=self.clear_text
        )
        btn_clear.pack(side=tk.RIGHT, padx=4, pady=4)

        # Lock button in Full Mode
        self.btn_lock_full = tk.Button(
            header,
            text="🔓 ล็อกซับ (F4)",
            font=("Segoe UI", 8),
            fg="#94A3B8",
            bg="#232936",
            relief="flat",
            padx=8,
            command=self.toggle_lock
        )
        self.btn_lock_full.pack(side=tk.RIGHT, padx=4, pady=4)

        # Engine switch button in Full Mode
        self.btn_engine_full = tk.Button(
            header,
            text="⚡ แปลเร็ว: Google (F8)" if self.current_engine == "google" else "🤖 แปลฉลาด: Gemini (F8)",
            font=("Segoe UI", 8, "bold"),
            fg="#38BDF8" if self.current_engine == "google" else "#A78BFA",
            bg="#232936",
            relief="flat",
            padx=8,
            command=self.toggle_engine
        )
        self.btn_engine_full.pack(side=tk.RIGHT, padx=4, pady=4)

        # Button to switch to Compact HUD
        btn_to_compact = tk.Button(
            header,
            text="🗗 ย่อซับโปร่งใส (F2)",
            font=("Segoe UI", 8, "bold"),
            fg="#00FFCC",
            bg="#232936",
            relief="flat",
            padx=10,
            command=self.switch_to_compact
        )
        btn_to_compact.pack(side=tk.RIGHT, padx=4, pady=4)

        header.bind("<ButtonPress-1>", self._start_drag)
        header.bind("<B1-Motion>", self._on_drag)
        title_lbl.bind("<ButtonPress-1>", self._start_drag)
        title_lbl.bind("<B1-Motion>", self._on_drag)

        # Full Content split (Left: Original Speech, Right: Translation)
        content = tk.Frame(self.full_frame, bg="#0f1117")
        content.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        left_box = tk.Frame(content, bg="#141721", bd=1, relief="solid")
        left_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))
        lbl_left = tk.Label(left_box, text="ORIGINAL SPEECH (เสียงต้นฉบับ)", font=("Segoe UI", 9, "bold"), fg="#94A3B8", bg="#141721")
        lbl_left.pack(anchor="w", padx=10, pady=(6, 2))
        self.txt_orig = tk.Text(left_box, bg="#141721", fg="#F8FAFC", font=("Segoe UI", 11), wrap=tk.WORD, bd=0, padx=10, pady=4)
        self.txt_orig.pack(fill=tk.BOTH, expand=True)

        right_box = tk.Frame(content, bg="#141721", bd=1, relief="solid")
        right_box.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(4, 0))
        lbl_right = tk.Label(right_box, text="TRANSLATION (คำแปลภาษาไทย)", font=("Segoe UI", 9, "bold"), fg="#00FFCC", bg="#141721")
        lbl_right.pack(anchor="w", padx=10, pady=(6, 2))
        self.txt_trans = tk.Text(right_box, bg="#141721", fg="#00FFCC", font=("Segoe UI", 11), wrap=tk.WORD, bd=0, padx=10, pady=4)
        self.txt_trans.pack(fill=tk.BOTH, expand=True)

        # Context menu on right click
        self.lock_var = tk.BooleanVar(value=False)
        self.bar_mode_var = tk.StringVar(value="auto")
        self.engine_var = tk.StringVar(value=self.current_engine)
        self.source_lang_var = tk.StringVar(value=self.source_lang)
        self.target_lang_var = tk.StringVar(value=self.target_lang)
        self.menu = tk.Menu(self.root, tearoff=0)
        self.menu.add_command(label="🗖 ขยายเป็นหน้าใหญ่ (F2)", command=self.switch_to_full)
        self.menu.add_checkbutton(label="🔒 ล็อกตำแหน่งซับ (F4 / F10)", variable=self.lock_var, command=self.toggle_lock)
        self.menu.add_command(label="👁 ซ่อน/แสดง แถบด้านบนทันที (F3)", command=self.toggle_bar)

        engine_sub = tk.Menu(self.menu, tearoff=0)
        engine_sub.add_radiobutton(label="⚡ Google Fast (เร็วสุดยอด ~0.2s - แนะนำเล่นเกม)", value="google", variable=self.engine_var, command=lambda: self.set_engine("google"))
        engine_sub.add_radiobutton(label="🤖 Gemini AI (ฉลาด ละเอียด แต่ช้ากว่า ~1-2s)", value="gemini", variable=self.engine_var, command=lambda: self.set_engine("gemini"))
        self.menu.add_cascade(label="🌐 โหมดแปลภาษา (F8 Engine)", menu=engine_sub)

        # Source language submenu
        src_sub = tk.Menu(self.menu, tearoff=0)
        src_sub.add_radiobutton(label="🇬🇧 ภาษาอังกฤษ (English: en)", value="en", variable=self.source_lang_var, command=lambda: self.change_language("en", None))
        src_sub.add_radiobutton(label="🇯🇵 ภาษาญี่ปุ่น (Japanese: ja)", value="ja", variable=self.source_lang_var, command=lambda: self.change_language("ja", None))
        src_sub.add_radiobutton(label="🇰🇷 ภาษาเกาหลี (Korean: ko)", value="ko", variable=self.source_lang_var, command=lambda: self.change_language("ko", None))
        src_sub.add_radiobutton(label="🇨🇳 ภาษาจีน (Chinese: zh)", value="zh", variable=self.source_lang_var, command=lambda: self.change_language("zh", None))
        src_sub.add_radiobutton(label="🌐 ตรวจจับภาษาอัตโนมัติ (Auto Detect)", value="auto", variable=self.source_lang_var, command=lambda: self.change_language("auto", None))
        self.menu.add_cascade(label="🗣 ภาษาเสียงต้นทาง (Source)", menu=src_sub)

        # Target language submenu
        tgt_sub = tk.Menu(self.menu, tearoff=0)
        tgt_sub.add_radiobutton(label="🇹🇭 ภาษาไทย (Thai)", value="th", variable=self.target_lang_var, command=lambda: self.change_language(None, "th"))
        tgt_sub.add_radiobutton(label="🇬🇧 ภาษาอังกฤษ (English)", value="en", variable=self.target_lang_var, command=lambda: self.change_language(None, "en"))
        tgt_sub.add_radiobutton(label="🇯🇵 ภาษาญี่ปุ่น (Japanese)", value="ja", variable=self.target_lang_var, command=lambda: self.change_language(None, "ja"))
        self.menu.add_cascade(label="🎯 ภาษาคำแปลซับ (Target)", menu=tgt_sub)

        bar_sub = tk.Menu(self.menu, tearoff=0)
        bar_sub.add_radiobutton(label="ซ่อนอัตโนมัติเมื่อไม่ได้ใช้ (Auto-Hide)", value="auto", variable=self.bar_mode_var, command=lambda: self._set_bar_mode("auto"))
        bar_sub.add_radiobutton(label="ซ่อนแถบตลอดเวลา (Always Hide)", value="always_hide", variable=self.bar_mode_var, command=lambda: self._set_bar_mode("always_hide"))
        bar_sub.add_radiobutton(label="แสดงแถบตลอดเวลา (Always Show)", value="always_show", variable=self.bar_mode_var, command=lambda: self._set_bar_mode("always_show"))
        self.menu.add_cascade(label="⚙ การแสดงผลแถบควบคุม (Bar)", menu=bar_sub)

        self.menu.add_separator()
        self.menu.add_command(label="ล้างข้อความ (Clear)", command=self.clear_text)
        self.menu.add_separator()
        self.menu.add_command(label="สีซับ: ฟ้าสว่าง (Cyan)", command=lambda: self._set_color("#00FFCC"))
        self.menu.add_command(label="สีซับ: ขาวสว่าง (White)", command=lambda: self._set_color("#FFFFFF"))
        self.menu.add_command(label="สีซับ: เหลืองทอง (Yellow)", command=lambda: self._set_color("#FFDD00"))
        self.menu.add_separator()
        self.menu.add_command(label="ฟอนต์: เล็ก (20px)", command=lambda: self._set_font_size(20))
        self.menu.add_command(label="ฟอนต์: ปกติ (24px)", command=lambda: self._set_font_size(24))
        self.menu.add_command(label="ฟอนต์: ใหญ่ (28px)", command=lambda: self._set_font_size(28))
        self.menu.add_separator()
        self.menu.add_command(label="ปิดโปรแกรม (Exit)", command=self.on_close)

        self.canvas.bind("<Button-3>", self._show_context_menu)
        self.bar.bind("<Button-3>", self._show_context_menu)
        self.drag_lbl.bind("<Button-3>", self._show_context_menu)
        self.btn_lock.bind("<Button-3>", self._show_context_menu)
        self.btn_engine.bind("<Button-3>", self._show_context_menu)
        self.btn_to_full.bind("<Button-3>", self._show_context_menu)
        self.btn_close_compact.bind("<Button-3>", self._show_context_menu)

    def _is_pointer_near_bar(self) -> bool:
        """Check if mouse cursor is currently hovering near the top control bar region."""
        if not HAS_WIN32:
            return False
        try:
            pt = POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
            wx = self.root.winfo_rootx()
            wy = self.root.winfo_rooty()
            ww = self.root.winfo_width()
            return (wx - 10 <= pt.x <= wx + ww + 10) and (wy - 15 <= pt.y <= wy + 45)
        except Exception:
            return False

    def _set_bar_mode(self, mode: str):
        """Set the bar display behavior."""
        self.bar_display_mode = mode
        if mode == "always_hide":
            self.hide_bar()
        elif mode == "always_show":
            self.show_bar()
        else:  # "auto"
            self.show_bar()
            self._bar_hide_timer = time.monotonic() + 3.0

    def toggle_bar(self):
        """Toggle top bar visibility immediately."""
        if self.bar_visible:
            self.hide_bar()
        else:
            self.show_bar()
            self._bar_hide_timer = time.monotonic() + 4.0

    def show_bar(self):
        """Shows the compact control bar."""
        if not self.bar_visible:
            try:
                self.bar.pack(anchor="center", pady=(0, 2), before=self.canvas)
            except Exception:
                self.bar.pack(anchor="center", pady=(0, 2))
            self.bar_visible = True

    def hide_bar(self):
        """Hides the compact control bar completely."""
        if self.bar_visible:
            self.bar.pack_forget()
            self.bar_visible = False

    def toggle_lock(self):
        """Toggle lock state (prevent moving/dragging and enable click-through)."""
        self.set_lock(not self.is_locked)

    def set_lock(self, locked: bool):
        """Set lock state and update UI buttons, cursors, and click-through."""
        self.is_locked = locked
        if hasattr(self, "lock_var"):
            self.lock_var.set(locked)
        if hasattr(self, "btn_lock"):
            if self.is_locked:
                self.btn_lock.config(text="🔒 ล็อกแล้ว (F4)", fg="#F59E0B")
            else:
                self.btn_lock.config(text="🔓 ล็อก (F4)", fg="#38BDF8")
        if hasattr(self, "btn_lock_full"):
            if self.is_locked:
                self.btn_lock_full.config(text="🔒 ล็อกแล้ว (F4)", fg="#F59E0B")
            else:
                self.btn_lock_full.config(text="🔓 ล็อกซับ (F4)", fg="#94A3B8")
        if hasattr(self, "drag_lbl"):
            self.drag_lbl.config(cursor="arrow" if self.is_locked else "fleur")
        if hasattr(self, "canvas"):
            self.canvas.config(cursor="arrow" if self.is_locked else "fleur")

    def toggle_engine(self):
        """Toggle translation engine between Google Fast and Gemini AI."""
        next_engine = "gemini" if self.current_engine == "google" else "google"
        self.set_engine(next_engine)

    def set_engine(self, engine_name: str):
        """Set translation engine and update UI buttons."""
        if not self.has_gemini and engine_name == "gemini":
            self.post_status_text("ไม่มี Gemini API Key - ใช้งาน Google Fast")
            if hasattr(self, "engine_var"):
                self.engine_var.set("google")
            return
        self.current_engine = engine_name
        if hasattr(self, "engine_var"):
            self.engine_var.set(engine_name)
        is_fast = (engine_name == "google")
        if hasattr(self, "btn_engine"):
            self.btn_engine.config(
                text="⚡ เร็ว (F8)" if is_fast else "🤖 AI (F8)",
                fg="#38BDF8" if is_fast else "#A78BFA"
            )
        if hasattr(self, "btn_engine_full"):
            self.btn_engine_full.config(
                text="⚡ แปลเร็ว: Google (F8)" if is_fast else "🤖 แปลฉลาด: Gemini (F8)",
                fg="#38BDF8" if is_fast else "#A78BFA"
            )
        if self.on_switch_engine:
            self.on_switch_engine(engine_name)

    def set_engine_status(self, engine_name: str):
        """Externally sync UI when engine changes."""
        self.current_engine = engine_name
        if hasattr(self, "engine_var"):
            self.engine_var.set(engine_name)
        is_fast = (engine_name == "google")
        if hasattr(self, "btn_engine"):
            self.btn_engine.config(
                text="⚡ เร็ว (F8)" if is_fast else "🤖 AI (F8)",
                fg="#38BDF8" if is_fast else "#A78BFA"
            )
        if hasattr(self, "btn_engine_full"):
            self.btn_engine_full.config(
                text="⚡ แปลเร็ว: Google (F8)" if is_fast else "🤖 แปลฉลาด: Gemini (F8)",
                fg="#38BDF8" if is_fast else "#A78BFA"
            )

    def change_language(self, src: Optional[str] = None, tgt: Optional[str] = None):
        """Change source spoken language or target translation language."""
        if src:
            self.source_lang = src
            if hasattr(self, "source_lang_var"):
                self.source_lang_var.set(src)
        if tgt:
            self.target_lang = tgt
            if hasattr(self, "target_lang_var"):
                self.target_lang_var.set(tgt)
        if self.on_switch_lang:
            self.on_switch_lang(self.source_lang, self.target_lang)

    def switch_to_compact(self):
        """Switches to Transparent Compact Subtitle HUD mode."""
        if not self.is_compact:
            self.full_geo = self.root.winfo_geometry()
        self.is_compact = True
        self.full_frame.pack_forget()
        self.root.overrideredirect(True)
        self.root.attributes("-transparentcolor", "#010101")
        self.root.config(bg="#010101")
        self.root.geometry(self.compact_geo)
        self.compact_frame.pack(fill=tk.BOTH, expand=True)

        if self.bar_display_mode == "always_hide":
            self.hide_bar()
        else:
            self.show_bar()
            self._bar_hide_timer = time.monotonic() + 3.0

    def switch_to_full(self):
        """Switches to Full Window mode with 2-column view."""
        if self.is_compact:
            self.compact_geo = self.root.winfo_geometry()
        self.is_compact = False
        self.compact_frame.pack_forget()
        self.root.attributes("-transparentcolor", "")
        self.root.overrideredirect(False)
        self.root.config(bg="#0f1117")
        self.root.geometry(self.full_geo)
        self.full_frame.pack(fill=tk.BOTH, expand=True)

    def toggle_mode(self):
        """Toggles between Full Window Mode and Compact HUD Mode."""
        if self.is_compact:
            self.switch_to_full()
        else:
            self.switch_to_compact()

    def _show_context_menu(self, event):
        self.menu.tk_popup(event.x_root, event.y_root)

    def _set_color(self, color):
        self.font_color = color
        self.render(self._current_text)

    def _set_font_size(self, size):
        self.font_size = size
        self.render(self._current_text)

    def _start_drag(self, event):
        if self.is_locked:
            return
        self._is_dragging = True
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def _stop_drag(self, event):
        self._is_dragging = False
        self._bar_hide_timer = time.monotonic() + 2.0

    def _on_drag(self, event):
        if self.is_locked:
            return
        deltax = event.x - self._drag_data["x"]
        deltay = event.y - self._drag_data["y"]
        x = self.root.winfo_x() + deltax
        y = self.root.winfo_y() + deltay
        self.root.geometry(f"+{x}+{y}")

    def render(self, text: str):
        """Renders subtitle with an 8-direction crisp black outline for perfect readability."""
        self._current_text = text or ""
        self.canvas.delete("all")
        if not text:
            return

        font = ("Segoe UI", self.font_size, "bold")
        cx = self.canvas_w // 2
        cy = self.canvas_h // 2
        wrap_w = self.canvas_w - 60

        # Draw 8-direction drop shadow (black outline)
        for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2), (-2, -2), (2, 2), (-2, 2), (2, -2)]:
            self.canvas.create_text(
                cx + dx, cy + dy,
                text=text,
                font=font,
                fill="#000000",
                width=wrap_w,
                justify="center"
            )

        # Draw primary foreground text
        self.canvas.create_text(
            cx, cy,
            text=text,
            font=font,
            fill=self.font_color,
            width=wrap_w,
            justify="center"
        )

    def clear_text(self):
        self.render("")
        if hasattr(self, "txt_orig"):
            self.txt_orig.delete("1.0", tk.END)
        if hasattr(self, "txt_trans"):
            self.txt_trans.delete("1.0", tk.END)

    def on_close(self):
        self.stop_event.set()
        try:
            self.root.destroy()
        except Exception:
            pass

    def post_pair(self, source, translated, **kwargs):
        self.msg_queue.put(("pair", source, translated))

    def post_source(self, source, **kwargs):
        if source:
            self.msg_queue.put(("source", source, None))

    def post_status_text(self, text, **kwargs):
        if text:
            self.msg_queue.put(("status", text, None))

    def post_partial(self, source):
        if self.show_partial and source:
            self.msg_queue.put(("partial", source, None))

    def _process_queue(self):
        try:
            while not self.msg_queue.empty():
                msg_type, val1, val2 = self.msg_queue.get_nowait()
                if msg_type == "pair":
                    self._last_post_time = time.monotonic()
                    # 1. Update Full Mode Text Widgets (History)
                    if hasattr(self, "txt_orig") and val1:
                        self.txt_orig.insert(tk.END, f"{val1}\n\n")
                        self.txt_orig.see(tk.END)
                    if hasattr(self, "txt_trans") and val2:
                        self.txt_trans.insert(tk.END, f"{val2}\n\n")
                        self.txt_trans.see(tk.END)
                    # 2. Update Compact Mode Subtitle HUD (Translation only)
                    self.render(val2 or val1)
                    # When speech/subtitles arrive, auto-hide the top bar immediately if user isn't hovering
                    if self.is_compact and self.bar_display_mode == "auto" and not self._is_dragging and not self._is_pointer_near_bar():
                        self.hide_bar()

                elif msg_type == "source":
                    self._last_post_time = time.monotonic()
                    if hasattr(self, "txt_orig") and val1:
                        self.txt_orig.insert(tk.END, f"{val1}\n\n")
                        self.txt_orig.see(tk.END)
                    self.render(val1)
                    if self.is_compact and self.bar_display_mode == "auto" and not self._is_dragging and not self._is_pointer_near_bar():
                        self.hide_bar()

                elif msg_type == "partial":
                    if val1:
                        self.render(val1)

                elif msg_type == "status":
                    if hasattr(self, "status_label") and self.status_label:
                        self.status_label.config(text=f"● {val1}")
                    if hasattr(self, "drag_lbl") and self.drag_lbl:
                        self.drag_lbl.config(text=f"⠿ {val1}")
        except Exception:
            pass

        now = time.monotonic()
        if self.is_compact:
            cursor_near = self._is_pointer_near_bar()

            # Auto-hide: clear subtitle after inactivity in compact mode
            if self.auto_hide_seconds > 0 and (now - self._last_post_time) > self.auto_hide_seconds:
                if self._current_text:
                    self.render("")

            # Top bar auto-hide / hover logic
            if self.bar_display_mode == "always_hide":
                if self.bar_visible:
                    self.hide_bar()
            elif self.bar_display_mode == "always_show":
                if not self.bar_visible:
                    self.show_bar()
            else:  # "auto"
                if self._is_dragging or cursor_near:
                    if not self.bar_visible:
                        self.show_bar()
                    self._bar_hide_timer = now + 2.0
                else:
                    if self.bar_visible and now > self._bar_hide_timer:
                        self.hide_bar()

        if not self.stop_event.is_set():
            self.root.after(80, self._process_queue)
        else:
            try:
                self.root.destroy()
            except Exception:
                pass

    def run(self):
        self.root.after(80, self._process_queue)
        self.root.mainloop()

    def stop(self):
        self.stop_event.set()



def resample_to_16k(audio: np.ndarray, orig_sr: int) -> np.ndarray:
    """Resample 1D float32 audio to 16,000 Hz using linear interpolation."""
    if orig_sr == 16000 or len(audio) == 0:
        return audio.astype(np.float32)
    target_len = int(len(audio) * 16000 / orig_sr)
    if target_len <= 0:
        return np.empty(0, dtype=np.float32)
    return np.interp(
        np.linspace(0, len(audio), target_len, endpoint=False),
        np.arange(len(audio)),
        audio,
    ).astype(np.float32)


def loopback_audio_capture_thread(audio_q, stop_event, block_seconds=0.2):
    """Continuously captures internal PC sound (YouTube/Games) via WASAPI Loopback."""
    if not HAS_PYAUDIO:
        print("[Audio Error] pyaudiowpatch is not installed!", file=sys.stderr)
        stop_event.set()
        return

    p = pyaudio.PyAudio()
    stream = None
    try:
        wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
        default_speakers = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
        
        loopback_dev = None
        for dev in p.get_loopback_device_info_generator():
            if default_speakers["name"] in dev["name"]:
                loopback_dev = dev
                break
        if loopback_dev is None:
            for dev in p.get_loopback_device_info_generator():
                loopback_dev = dev
                break

        if loopback_dev is None:
            raise RuntimeError("No WASAPI Loopback device found on this system.")

        dev_index = int(loopback_dev["index"])
        samplerate = int(loopback_dev.get("defaultSampleRate", 48000))
        channels = int(loopback_dev.get("maxInputChannels", 2))
        frames_per_buffer = max(512, int(samplerate * block_seconds))

        stream = p.open(
            format=pyaudio.paInt16,
            channels=channels,
            rate=samplerate,
            input=True,
            input_device_index=dev_index,
            frames_per_buffer=frames_per_buffer,
        )

        while not stop_event.is_set():
            try:
                data = stream.read(frames_per_buffer, exception_on_overflow=False)
            except Exception:
                continue
            if not data or stop_event.is_set():
                break

            arr = np.frombuffer(data, dtype=np.int16)
            if channels == 2:
                arr = arr.reshape(-1, 2).mean(axis=1)
            float_mono = (arr.astype(np.float32)) / 32768.0

            if samplerate != 16000:
                float_mono = resample_to_16k(float_mono, samplerate)

            audio_q.put(float_mono.copy())

    except Exception as exc:
        print(f"[Loopback Error] {exc}", file=sys.stderr)
        stop_event.set()
    finally:
        if stream:
            with contextlib.suppress(Exception):
                stream.stop_stream()
                stream.close()
        p.terminate()


def mic_audio_capture_thread(audio_q, stop_event, device, samplerate, block_seconds=0.2):
    """Continuously captures audio blocks from the chosen microphone and resamples to 16 kHz."""
    if not HAS_SD:
        print("[Audio Error] sounddevice is not installed!", file=sys.stderr)
        stop_event.set()
        return

    blocksize = max(256, int(samplerate * block_seconds))
    
    def callback(indata, frames, time_info, status):
        if not stop_event.is_set():
            mono = indata[:, 0] if indata.ndim > 1 else indata.flatten()
            if samplerate != 16000:
                mono = resample_to_16k(mono, samplerate)
            audio_q.put(mono.copy())

    try:
        with sd.InputStream(device=device, samplerate=samplerate, channels=1,
                            blocksize=blocksize, dtype="float32", callback=callback):
            while not stop_event.is_set():
                time.sleep(0.1)
    except Exception as exc:
        print(f"[Microphone Error] {exc}", file=sys.stderr)
        stop_event.set()


def processing_worker(
    audio_q,
    overlay,
    stop_event,
    whisper_model,
    translator_holder,
    samplerate=16000,
    chunk_seconds=1.2,
    silence_rms=0.003,
    task="transcribe",
    source_lang="auto",
    target_lang="th",
    lang_holder=None,
):
    """Aggregates audio blocks, performs dynamic silence cutting, transcribes with faster-whisper and translates."""
    buffer = []
    buffer_duration = 0.0
    speech_detected = False
    consecutive_silence = 0.0
    overlay.post_status_text("Listening...")

    # Conversation history for translation context
    translation_history = []

    def get_translator():
        if isinstance(translator_holder, dict):
            return translator_holder.get("translator")
        elif callable(translator_holder):
            return translator_holder()
        return translator_holder

    def get_source_lang():
        if isinstance(lang_holder, dict):
            return lang_holder.get("source", source_lang)
        return source_lang

    while not stop_event.is_set():
        try:
            block = audio_q.get(timeout=0.15)
            buffer.append(block)
            block_dur = len(block) / samplerate
            buffer_duration += block_dur

            block_rms = float(np.sqrt(np.mean(block**2)))
            if block_rms >= silence_rms:
                speech_detected = True
                consecutive_silence = 0.0
            else:
                if speech_detected:
                    consecutive_silence += block_dur
        except queue.Empty:
            continue

        # Dynamic Silence Cut Conditions:
        # 1. Speech was active, accumulated >= 0.45s, and pause detected (0.22s silence)
        # 2. Or buffer duration exceeded chunk_seconds (max speech window: 1.2s)
        should_cut = False
        if speech_detected and buffer_duration >= 0.45 and consecutive_silence >= 0.22:
            should_cut = True
        elif buffer_duration >= chunk_seconds:
            should_cut = True

        if should_cut:
            audio_clip = np.concatenate(buffer, axis=0)
            buffer.clear()
            buffer_duration = 0.0
            had_speech = speech_detected
            speech_detected = False
            consecutive_silence = 0.0

            # Energy / RMS check for speech
            rms = float(np.sqrt(np.mean(audio_clip**2)))
            if rms < silence_rms and not had_speech:
                continue

            cur_src = get_source_lang()
            overlay.post_status_text("Transcribing...")
            try:
                segments, info = whisper_model.transcribe(
                    audio_clip,
                    language=None if cur_src == "auto" else cur_src,
                    task=task,
                    beam_size=1,
                    best_of=1,
                    temperature=0.0,
                    condition_on_previous_text=False,
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=200),
                )
                text = " ".join([seg.text.strip() for seg in segments]).strip()
                
                if not text:
                    overlay.post_status_text("Listening...")
                    continue

                text = strip_hallucinations(text)
                if not text:
                    continue

                translator = get_translator()
                
                # Translation step
                if translator is not None:
                    overlay.post_status_text("Translating...")
                    try:
                        translated = translator.translate(
                            text,
                            history=translation_history[-3:],
                        )
                        if translated:
                            translation_history.append((text, translated))
                            if len(translation_history) > 10:
                                translation_history.pop(0)
                    except Exception as exc:
                        translated = f"[Translate Error: {exc}]"
                    overlay.post_pair(text, translated)
                else:
                    # Direct transcript
                    overlay.post_source(text)

                overlay.post_status_text("Listening...")

            except Exception as exc:
                print(f"[Whisper Error] {exc}", file=sys.stderr)
                overlay.post_status_text(f"Error: {exc}")


def parse_args():
    p = argparse.ArgumentParser(description="Live Translation for Windows")
    p.add_argument("--list", action="store_true", help="List audio input devices and exit")
    p.add_argument("--mode", default="loopback", choices=["loopback", "mic"], 
                   help="Audio source: 'loopback' for YouTube/Games, 'mic' for Microphone (default: loopback)")
    p.add_argument("--device", type=int, default=None, help="Microphone audio device index (see --list)")
    p.add_argument("--whisper", default="base", choices=WHISPER_MODELS, help="Whisper model size (default: base, use 'tiny' for maximum speed)")
    p.add_argument("--device-type", default="auto", choices=["auto", "cpu", "cuda"], help="Inference device for faster-whisper (default: auto - uses CUDA if available)")
    p.add_argument("--compute-type", default="auto", choices=["auto", "int8", "float16", "float32"], help="Compute quantization type (default: auto - float16 for CUDA, int8 for CPU)")
    p.add_argument("--source", default=None, help="Source spoken language (default: 'en' or from config.json)")
    p.add_argument("--target", default=None, help="Target translation language (default: 'th' or from config.json)")
    p.add_argument("--engine", default=None, choices=["google", "gemini", "ollama", "whisper", "auto"],
                   help="Translation engine: 'google' (Fast ~0.2s), 'gemini' (AI Cloud), 'auto' (read config.json)")
    p.add_argument("--chunk-seconds", type=float, default=1.2, help="Audio buffer chunk size in seconds (default: 1.2)")
    p.add_argument("--silence-rms", type=float, default=0.003, help="RMS energy threshold for silence (default: 0.003)")
    p.add_argument("--ollama-model", default="", help="Ollama model name (e.g. gemma2:2b, qwen2.5:3b)")
    p.add_argument("--gemini-key", default="", help="Google Gemini API key (or read from config.json)")
    p.add_argument("--whisper-translate", action="store_true", help="Use Whisper built-in translation to English (task=translate)")
    p.add_argument("--no-window", action="store_true", help="Console output only (no Tkinter overlay)")
    p.add_argument("--opacity", type=float, default=0.92, help="Window opacity 0.1-1.0 (default: 0.92)")
    p.add_argument("--width", type=int, default=960, help="Overlay window width (default: 960)")
    p.add_argument("--height", type=int, default=120, help="Overlay window height (default: 120)")
    return p.parse_args()


def main():
    args = parse_args()

    if args.list:
        list_devices()
        return

    config = load_config()
    cfg_trans = config.get("translation", {})

    # Determine languages
    source_lang = args.source or cfg_trans.get("source_lang", "en")
    target_lang = args.target or cfg_trans.get("target_lang", "th")

    # Determine translation engine
    engine_choice = (args.engine or cfg_trans.get("engine", "google")).lower()
    if engine_choice == "auto":
        engine_choice = cfg_trans.get("engine", "google").lower()

    gemini_key = args.gemini_key or os.environ.get("GEMINI_API_KEY", "") or cfg_trans.get("gemini_api_key", "")
    gemini_model = cfg_trans.get("gemini_model", "gemini-3.5-flash-lite")

    # Prepare available translators
    fast_translator = FallbackTranslator(target=target_lang, source=source_lang)
    gemini_translator = None
    if gemini_key:
        try:
            gemini_translator = GeminiTranslator(
                api_key=gemini_key,
                model=gemini_model,
                target=target_lang,
                source=source_lang,
            )
        except Exception as e:
            print(f"[Warning] Failed to init GeminiTranslator: {e}")

    ollama_translator = None
    if args.ollama_model:
        ollama_translator = OllamaTranslator(
            model=args.ollama_model,
            target=target_lang,
            url="http://127.0.0.1:11434",
            max_tokens=256,
            temperature=0.0,
            reasoning=False,
            source=source_lang,
        )

    # Active engine holder for dynamic switching
    active_engine = {
        "name": engine_choice,
        "translator": fast_translator,
    }

    if args.whisper_translate or (target_lang == "en" and engine_choice == "whisper"):
        print("[*] Whisper built-in translation to English enabled (task='translate').")
        active_engine["translator"] = None
        active_engine["name"] = "whisper"
        trans_name = "Whisper Translate (EN)"
    elif engine_choice == "ollama" and ollama_translator:
        print(f"[*] Initializing Ollama translator with model '{args.ollama_model}'...")
        active_engine["translator"] = ollama_translator
        active_engine["name"] = "ollama"
        trans_name = f"Ollama ({args.ollama_model})"
    elif engine_choice == "gemini" and gemini_translator:
        print(f"[*] Initializing Gemini AI translator ({gemini_model})...")
        active_engine["translator"] = gemini_translator
        active_engine["name"] = "gemini"
        trans_name = f"Gemini ({gemini_model})"
    else:
        print("[*] Initializing Fast Google Translator (~0.2s ultra-low latency)...")
        active_engine["translator"] = fast_translator
        active_engine["name"] = "google"
        trans_name = "Google Fast (Instant)"

    # Determine Whisper device and compute type
    cfg_audio = config.get("audio", {})
    whisper_size = args.whisper if args.whisper != "base" else cfg_audio.get("whisper_model", "base")
    device_type = args.device_type
    compute_type = args.compute_type

    if device_type == "auto":
        try:
            import ctranslate2
            has_cuda = (ctranslate2.get_cuda_device_count() > 0)
            device_type = "cuda" if has_cuda else "cpu"
        except Exception:
            device_type = "cpu"

    if compute_type == "auto":
        compute_type = "float16" if device_type == "cuda" else "int8"

    # Initialize Whisper model with optimal CPU threads or GPU
    print(f"[*] Loading faster-whisper model '{whisper_size}' on {device_type.upper()} ({compute_type})...")
    from faster_whisper import WhisperModel
    num_cpus = os.cpu_count() or 4
    threads = min(8, max(4, num_cpus - 2))
    try:
        whisper_model = WhisperModel(
            whisper_size,
            device=device_type,
            compute_type=compute_type,
            cpu_threads=threads if device_type == "cpu" else 0,
        )
    except Exception as exc:
        if device_type == "cuda":
            print(f"[Warning] CUDA init failed: {exc}, falling back to CPU (int8)...")
            device_type = "cpu"
            compute_type = "int8"
            whisper_model = WhisperModel(
                whisper_size,
                device="cpu",
                compute_type="int8",
                cpu_threads=threads,
            )
        else:
            raise

    print(f"[*] Whisper model loaded on {device_type.upper()} ({compute_type}) (source_lang='{source_lang}', target_lang='{target_lang}').")

    stop_event = threading.Event()
    audio_q = queue.Queue(maxsize=100)

    # Audio source setup
    use_loopback = (args.mode == "loopback")
    device_name = "System Audio (Loopback)"
    device_idx = args.device
    device_sr = 16000

    if not use_loopback:
        if device_idx is None:
            device_idx, device_name, device_sr = auto_detect_input_device()
            if device_idx is None:
                print("[Warning] No microphone found, switching to System Audio Loopback.")
                use_loopback = True
        else:
            info = cast(dict, sd.query_devices(device_idx)) if HAS_SD else {}
            device_name = info.get("name", f"Mic Device {device_idx}")
            device_sr = int(info.get("default_samplerate", 16000)) if info else 16000

    print(f"[*] Audio source: {device_name}")

    overlay = None

    # Language holder for dynamic language switching
    lang_holder = {
        "source": source_lang,
        "target": target_lang,
    }

    def on_switch_lang(new_src: str, new_tgt: str):
        lang_holder["source"] = new_src
        lang_holder["target"] = new_tgt
        fast_translator.set_source(new_src)
        fast_translator.set_target(new_tgt)
        if gemini_translator:
            gemini_translator.set_source(new_src)
            gemini_translator.set_target(new_tgt)
        print(f"[*] Language switched: [{new_src}] ➔ [{new_tgt}]")
        if overlay:
            overlay.post_status_text(f"Language: [{new_src}] ➔ [{new_tgt}]")

    # Engine switcher callback
    def on_switch_engine(new_engine: str):
        if new_engine == "gemini":
            if not gemini_translator:
                if overlay:
                    overlay.post_status_text("Gemini API key is not configured!")
                return
            active_engine["translator"] = gemini_translator
            active_engine["name"] = "gemini"
            print("[*] Translation engine switched to: Gemini AI")
            if overlay:
                overlay.post_status_text("Engine: 🤖 Gemini AI")
        elif new_engine == "google":
            active_engine["translator"] = fast_translator
            active_engine["name"] = "google"
            print("[*] Translation engine switched to: Google Fast (~0.2s)")
            if overlay:
                overlay.post_status_text("Engine: ⚡ Google Fast (~0.2s)")

    # UI Overlay
    gpu_badge = f" [GPU: {device_type.upper()}]" if device_type == "cuda" else " [CPU]"
    title_str = f"Live Translation — [{device_name}{gpu_badge}] ➔ [{trans_name}]"
    if args.no_window:
        overlay = ConsoleOverlay(stop_event)
    else:
        overlay = TkinterOverlay(
            stop_event,
            title=title_str,
            width=args.width,
            height=args.height,
            opacity=args.opacity,
            current_engine=active_engine["name"],
            on_switch_engine=on_switch_engine,
            has_gemini=(gemini_translator is not None),
            source_lang=source_lang,
            target_lang=target_lang,
            on_switch_lang=on_switch_lang,
        )

    # Worker thread
    task_mode = "translate" if (args.whisper_translate or (target_lang == "en" and not active_engine["translator"])) else "transcribe"
    worker_th = threading.Thread(
        target=processing_worker,
        args=(audio_q, overlay, stop_event, whisper_model, active_engine),
        kwargs={
            "samplerate": 16000,
            "chunk_seconds": args.chunk_seconds,
            "silence_rms": args.silence_rms,
            "task": task_mode,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "lang_holder": lang_holder,
        },
        daemon=True,
    )
    worker_th.start()

    # Audio Capture Thread (0.2s block size for low latency)
    if use_loopback:
        audio_th = threading.Thread(
            target=loopback_audio_capture_thread,
            args=(audio_q, stop_event, 0.2),
            daemon=True,
        )
    else:
        audio_th = threading.Thread(
            target=mic_audio_capture_thread,
            args=(audio_q, stop_event, device_idx, device_sr, 0.2),
            daemon=True,
        )
    audio_th.start()

    print("[*] Live translation is running! Play YouTube / game audio or speak into mic...")
    try:
        overlay.run()
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        print("\n[*] Stopped.")


if __name__ == "__main__":
    main()
