"""
app.py - Main Application
AI Measure Pro YOLO - Version 6.0 (FULLY FIXED)

Features:
  - Accurate mode with calibration
  - Estimated mode without calibration
  - Auto-orientation correction
  - AI Explanation Panel
  - SOC Security Event Logging
  - TapMap Visualization
  - Voice announcements with persistent ON/OFF
  - Barcode Scanner
  - Object Tracking
  - Persistent State Management
  - Touchless Drawing Mode (Hand Gestures)
  - Multi-hand drawing support
  - Gesture shortcuts (2 fingers = select, all fingers = clear, pinky = save)
  - AI suspicious annotation mode
  - Zoom & Pan support
  - PDF export with drawings and annotations
"""

import os
import csv
import cv2
import numpy as np
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

from detector import YOLODetector
from measure_utils import (
    calibrate_pixels_per_cm_from_card,
    measure_bbox_cm,
    estimate_bbox_cm_without_calibration,
    reset_calibration_buffer
)
from person_measure import PersonMeasurer
from pdf_report import generate_pdf_report

from ai_explainer import AIExplainer
from soc_logger import SOCLogger
from tapmap_view import TapMapWindow
from voice_announcer import VoiceAnnouncer
from barcode_scanner import BarcodeScanner
from object_tracker import ObjectTracker
from state_manager import StateManager
from drawing_mode import AirDrawing
import config


# Color scheme
C = {
    "bg": "#0a0e17",
    "panel": "#111827",
    "card": "#1e293b",
    "border": "#334155",
    "accent": "#06b6d4",
    "accent2": "#8b5cf6",
    "green": "#10b981",
    "yellow": "#f59e0b",
    "red": "#ef4444",
    "white": "#f8fafc",
    "muted": "#94a3b8",
    "btn": "#1e293b",
    "btn_hover": "#334155",
}


class GlassButton(tk.Button):
    def __init__(self, parent, accent=None, **kwargs):
        self._accent = accent or C["accent"]
        super().__init__(
            parent,
            relief="flat",
            bd=0,
            cursor="hand2",
            bg=C["btn"],
            fg=C["white"],
            activebackground=C["btn_hover"],
            activeforeground=C["white"],
            font=("Segoe UI", 10, "bold"),
            padx=14,
            pady=8,
            **kwargs
        )
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def _on_enter(self, _):
        self.config(bg=C["btn_hover"], fg=self._accent)

    def _on_leave(self, _):
        self.config(bg=C["btn"], fg=C["white"])


class AIMeasureV6App:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Measure Pro V6.0")
        self.root.configure(bg=C["bg"])
        self.root.minsize(1400, 800)
        self.root.geometry("1450x880")

        # Camera variables
        self.cap = None
        self.camera_running = False
        self.current_frame = None
        self.display_frame = None
        self.pixels_per_cm = None
        self.last_measurements = []
        self.detector = None
        self.model_path = "models/yolov8n.pt"

        # Zoom variables
        self.zoom_level = 1.0
        self.zoom_min = 1.0
        self.zoom_max = 4.0
        self.zoom_step = 0.1
        self.pan_x = 0
        self.pan_y = 0
        self.is_panning = False
        self.pan_start_x = 0
        self.pan_start_y = 0

        # State Manager
        self.state_manager = StateManager()
        saved_geometry = self.state_manager.get("window_geometry", "1450x880")
        self.root.geometry(saved_geometry)
        saved_position = self.state_manager.get("window_position")
        if saved_position:
            try:
                self.root.geometry(f"+{saved_position[0]}+{saved_position[1]}")
            except Exception:
                pass

        # Modules
        self.explainer = AIExplainer()
        self.soc_logger = SOCLogger()
        self.tapmap = TapMapWindow()

        saved_voice_state = self.state_manager.get("voice_enabled", True)
        self.voice = VoiceAnnouncer(
            enabled=saved_voice_state,
            rate=config.VOICE_RATE,
            volume=config.VOICE_VOLUME
        )

        saved_units = self.state_manager.get("last_units", "cm")
        if saved_units != config.UNITS:
            config.UNITS = saved_units

        self.barcode = BarcodeScanner(config.BARCODE_DATABASE)
        self.tracker = ObjectTracker(
            max_age=config.MAX_TRACKING_AGE,
            max_history=config.MAX_MEASUREMENT_HISTORY
        )

        # Drawing Mode
        self.drawing_mode = False
        self.annotation_mode = False
        self.drawer = AirDrawing()
        self.last_drawing_saved_path = None
        self.last_annotated_frame = None

        # Calibration
        saved_calibration = self.state_manager.get("last_calibration_ppc")
        if saved_calibration:
            self.pixels_per_cm = saved_calibration
            print(f"[Restored] Calibration: {saved_calibration:.2f} pixels/cm")

        # Person Measurer
        try:
            self.person_measurer = PersonMeasurer()
        except Exception as e:
            print(f"[App] PersonMeasurer error: {e}")
            self.person_measurer = None

        # File setup
        self.csv_file = "measurement_history.csv"
        self.screenshot_folder = "screenshots"
        self.report_folder = "reports"

        os.makedirs(self.screenshot_folder, exist_ok=True)
        os.makedirs(self.report_folder, exist_ok=True)
        self.ensure_csv_exists()

        # UI Setup
        self._apply_theme()
        self.load_model()
        self.build_ui()
        self.load_history_to_table()

        # Session setup
        if self.state_manager.get("first_run", True):
            self.state_manager.mark_first_run_complete()

        self.state_manager.increment_session_count()
        self.safe_log("log_system_start")

        if self.voice.enabled:
            try:
                self.voice.announce("AI Measure Pro version 6 started")
            except Exception:
                pass

        self.update_clock()
        print("[OK] Application ready")

    def safe_log(self, method_name, *args):
        try:
            if hasattr(self.soc_logger, method_name):
                getattr(self.soc_logger, method_name)(*args)
            elif hasattr(self.soc_logger, "log_event"):
                details = ", ".join(str(a) for a in args) if args else method_name
                self.soc_logger.log_event(method_name.upper(), "INFO", "", "", "SYSTEM", details)
        except Exception:
            pass

    def _apply_theme(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background=C["card"],
            fieldbackground=C["card"],
            foreground=C["white"],
            rowheight=26,
            borderwidth=0,
            font=("Segoe UI", 9)
        )
        style.configure(
            "Treeview.Heading",
            background=C["panel"],
            foreground=C["accent"],
            font=("Segoe UI", 9, "bold"),
            borderwidth=0
        )
        style.map(
            "Treeview",
            background=[("selected", C["accent2"])],
            foreground=[("selected", C["white"])]
        )

    def load_model(self):
        if not os.path.exists(self.model_path):
            print("[INFO] Downloading YOLO model...")
            try:
                from ultralytics import YOLO
                model = YOLO("yolov8n.pt")
                model.export(format="pt")
                if os.path.exists("yolov8n.pt"):
                    os.rename("yolov8n.pt", self.model_path)
                print("[OK] Model downloaded")
            except Exception as e:
                print(f"[ERROR] Model download failed: {e}")
                messagebox.showerror("Model Error", f"Cannot download model: {e}")
                return

        try:
            self.detector = YOLODetector(self.model_path, confidence_threshold=0.40)
            print("[OK] Model loaded")
        except Exception as e:
            print(f"[ERROR] Model load failed: {e}")
            messagebox.showerror("Model Error", str(e))

    def ensure_csv_exists(self):
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([
                    "Date", "Time", "Object ID", "Object Name", "Confidence",
                    "Width (cm)", "Height (cm)", "Extra", "Accuracy", "Screenshot"
                ])

    def save_window_state(self):
        try:
            geometry = self.root.geometry()
            parts = geometry.replace('+', 'x').split('x')
            if len(parts) >= 4:
                width = parts[0]
                height = parts[1]
                x_pos = parts[2]
                y_pos = parts[3].split('+')[0] if '+' in parts[3] else parts[3]
                self.state_manager.set("window_geometry", f"{width}x{height}")
                self.state_manager.set("window_position", [int(x_pos), int(y_pos)])
        except Exception:
            pass

    def update_clock(self):
        self.clock_label.config(text=datetime.now().strftime("%H:%M:%S"))
        self.root.after(1000, self.update_clock)

    # ========== ZOOM METHODS ==========
    def zoom_in(self):
        if self.zoom_level < self.zoom_max:
            self.zoom_level += self.zoom_step
            self.update_zoom_display()
            self.speak(f"Zoom {int(self.zoom_level * 100)} percent")

    def zoom_out(self):
        if self.zoom_level > self.zoom_min:
            self.zoom_level -= self.zoom_step
            self.update_zoom_display()
            self.speak(f"Zoom {int(self.zoom_level * 100)} percent")

    def zoom_reset(self):
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.update_zoom_display()
        self.speak("Zoom reset")

    def update_zoom_display(self):
        self.zoom_label.config(text=f"ZOOM: {int(self.zoom_level * 100)}%")

    def on_pan_start(self, event):
        self.is_panning = True
        self.pan_start_x = event.x
        self.pan_start_y = event.y

    def on_pan_move(self, event):
        if self.is_panning and self.zoom_level > 1.0:
            dx = event.x - self.pan_start_x
            dy = event.y - self.pan_start_y
            self.pan_x += dx
            self.pan_y += dy
            self.pan_start_x = event.x
            self.pan_start_y = event.y

    def on_pan_end(self, event):
        self.is_panning = False

    def apply_zoom(self, frame):
        if frame is None or self.zoom_level == 1.0:
            return frame
        h, w = frame.shape[:2]
        new_w = int(w * self.zoom_level)
        new_h = int(h * self.zoom_level)
        zoomed = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        if self.pan_x != 0 or self.pan_y != 0:
            start_x = max(0, min(self.pan_x, new_w - w))
            start_y = max(0, min(self.pan_y, new_h - h))
            zoomed = zoomed[start_y:start_y + h, start_x:start_x + w]
        else:
            start_x = (new_w - w) // 2
            start_y = (new_h - h) // 2
            if start_x > 0 and start_y > 0:
                zoomed = zoomed[start_y:start_y + h, start_x:start_x + w]
        return zoomed

    # ========== UI BUILD ==========
    def build_ui(self):
        # Top bar
        top = tk.Frame(self.root, bg=C["panel"], height=60)
        top.pack(fill="x", side="top")
        top.pack_propagate(False)

        title = tk.Label(
            top,
            text="AI MEASURE PRO V6.0",
            font=("Segoe UI", 18, "bold"),
            fg=C["accent"],
            bg=C["panel"]
        )
        title.pack(side="left", padx=25, pady=12)

        subtitle = tk.Label(
            top,
            text="AI · SOC · TapMap · Voice · Barcode · Drawing · Zoom",
            font=("Segoe UI", 10),
            fg=C["muted"],
            bg=C["panel"]
        )
        subtitle.pack(side="left", padx=5)

        # Voice button
        voice_status = "ON" if self.voice.enabled else "OFF"
        voice_icon = "🔊" if self.voice.enabled else "🔇"
        voice_color = C["green"] if self.voice.enabled else C["red"]

        self.voice_toggle_btn = tk.Button(
            top,
            text=f"{voice_icon} Voice: {voice_status}",
            font=("Segoe UI", 9, "bold"),
            bg=C["btn"],
            fg=voice_color,
            activebackground=C["btn_hover"],
            activeforeground=C["white"],
            bd=0,
            padx=15,
            pady=5,
            cursor="hand2",
            command=self.toggle_voice
        )
        self.voice_toggle_btn.pack(side="right", padx=10)

        self.clock_label = tk.Label(
            top,
            text="",
            font=("Segoe UI", 10),
            fg=C["muted"],
            bg=C["panel"]
        )
        self.clock_label.pack(side="right", padx=20)

        # Main content
        main = tk.Frame(self.root, bg=C["bg"])
        main.pack(fill="both", expand=True, padx=15, pady=10)

        # Left panel - Camera
        left = tk.Frame(main, bg=C["panel"], highlightthickness=1, highlightbackground=C["border"])
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))

        # Zoom control bar
        zoom_frame = tk.Frame(left, bg=C["panel"])
        zoom_frame.pack(fill="x", padx=5, pady=5)

        zoom_in_btn = tk.Button(
            zoom_frame, text="🔍 +", font=("Segoe UI", 10, "bold"),
            bg=C["btn"], fg=C["white"], bd=0, padx=10, pady=3,
            cursor="hand2", command=self.zoom_in
        )
        zoom_in_btn.pack(side="left", padx=2)

        zoom_out_btn = tk.Button(
            zoom_frame, text="🔍 -", font=("Segoe UI", 10, "bold"),
            bg=C["btn"], fg=C["white"], bd=0, padx=10, pady=3,
            cursor="hand2", command=self.zoom_out
        )
        zoom_out_btn.pack(side="left", padx=2)

        zoom_reset_btn = tk.Button(
            zoom_frame, text="⟲ RESET", font=("Segoe UI", 9, "bold"),
            bg=C["btn"], fg=C["yellow"], bd=0, padx=10, pady=3,
            cursor="hand2", command=self.zoom_reset
        )
        zoom_reset_btn.pack(side="left", padx=2)

        self.zoom_label = tk.Label(
            zoom_frame, text="ZOOM: 100%", font=("Segoe UI", 9),
            fg=C["accent"], bg=C["panel"]
        )
        self.zoom_label.pack(side="left", padx=15)

        # Video frame
        self.video_frame = tk.Frame(left, bg="black")
        self.video_frame.pack(fill="both", expand=True, padx=3, pady=3)

        self.video_label = tk.Label(self.video_frame, bg="black")
        self.video_label.place(relx=0.5, rely=0.5, anchor="center")

        # Overlay label (status messages)
        self.overlay_label = tk.Label(
            left,
            text="● CAMERA OFF - Click START to begin",
            font=("Segoe UI", 10),
            fg=C["muted"],
            bg=C["panel"]
        )
        self.overlay_label.pack(fill="x", pady=5)

        # Mouse bindings for pan
        self.video_label.bind("<ButtonPress-1>", self.on_pan_start)
        self.video_label.bind("<B1-Motion>", self.on_pan_move)
        self.video_label.bind("<ButtonRelease-1>", self.on_pan_end)

        # Status label
        self.status_label = tk.Label(
            left,
            text="● CAMERA OFF",
            font=("Segoe UI", 10),
            fg=C["muted"],
            bg=C["panel"]
        )
        self.status_label.pack(fill="x", pady=2)

        # Right panel
        right = tk.Frame(main, bg=C["bg"], width=480)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        # Stats cards
        stats_frame = tk.Frame(right, bg=C["bg"])
        stats_frame.pack(fill="x", pady=(0, 10))

        stat_names = [
            ("STATUS", "stat_status", C["green"]),
            ("MODE", "stat_mode", C["accent"]),
            ("OBJECTS", "stat_objects", C["yellow"]),
            ("ACCURACY", "stat_accuracy", C["accent2"])
        ]

        for label, var, color in stat_names:
            card = tk.Frame(stats_frame, bg=C["card"], highlightthickness=1, highlightbackground=C["border"])
            card.pack(side="left", fill="x", expand=True, padx=3)
            tk.Label(card, text=label, font=("Segoe UI", 8), fg=C["muted"], bg=C["card"]).pack(pady=(8, 0))
            lbl = tk.Label(card, text="---", font=("Segoe UI", 14, "bold"), fg=color, bg=C["card"])
            lbl.pack(pady=(0, 8))
            setattr(self, var, lbl)

        # AI Explanation panel
        explain_frame = tk.Frame(right, bg=C["card"], highlightthickness=1, highlightbackground=C["border"])
        explain_frame.pack(fill="x", pady=5)

        tk.Label(
            explain_frame,
            text="🤖 AI EXPLANATION PANEL",
            font=("Segoe UI", 9, "bold"),
            fg=C["accent"],
            bg=C["card"]
        ).pack(anchor="w", padx=12, pady=(8, 2))

        self.explain_text = tk.Text(
            explain_frame,
            height=9,
            font=("Consolas", 9),
            bg=C["card"],
            fg=C["white"],
            relief="flat",
            bd=0,
            state="disabled",
            wrap="word"
        )
        self.explain_text.pack(fill="x", padx=10, pady=(0, 10))

        # Accuracy bar
        acc_frame = tk.Frame(right, bg=C["card"], highlightthickness=1, highlightbackground=C["border"])
        acc_frame.pack(fill="x", pady=5)

        tk.Label(
            acc_frame,
            text="📊 MEASUREMENT ACCURACY",
            font=("Segoe UI", 9, "bold"),
            fg=C["accent"],
            bg=C["card"]
        ).pack(anchor="w", padx=12, pady=(8, 4))

        self.acc_canvas = tk.Canvas(acc_frame, height=28, bg=C["panel"], bd=0, highlightthickness=0)
        self.acc_canvas.pack(fill="x", padx=10, pady=(0, 10))
        self._draw_accuracy_bar(0, "N/A")

        # History table
        history_frame = tk.Frame(right, bg=C["card"], highlightthickness=1, highlightbackground=C["border"])
        history_frame.pack(fill="both", expand=True, pady=5)

        tk.Label(
            history_frame,
            text="📋 MEASUREMENT HISTORY",
            font=("Segoe UI", 9, "bold"),
            fg=C["white"],
            bg=C["card"]
        ).pack(anchor="w", padx=12, pady=(8, 4))

        cols = ("time", "object", "width", "height", "acc")
        self.history_tree = ttk.Treeview(history_frame, columns=cols, show="headings", height=10)
        self.history_tree.heading("time", text="Time")
        self.history_tree.heading("object", text="Object")
        self.history_tree.heading("width", text="W(cm)")
        self.history_tree.heading("height", text="H(cm)")
        self.history_tree.heading("acc", text="Accuracy")

        for col, width in [("time", 70), ("object", 95), ("width", 60), ("height", 60), ("acc", 75)]:
            self.history_tree.column(col, width=width, anchor="center")

        scroll = ttk.Scrollbar(history_frame, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.history_tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Bottom toolbar
        toolbar = tk.Frame(self.root, bg=C["panel"], height=55)
        toolbar.pack(fill="x", side="bottom")
        toolbar.pack_propagate(False)

        buttons = [
            ("▶ START", self.start_camera, C["green"]),
            ("■ STOP", self.stop_camera, C["red"]),
            ("↺ CALIBRATE", self.calibrate, C["yellow"]),
            ("✏ DRAW MODE", self.toggle_draw_mode, C["accent2"]),
            ("⭕ ANNOTATE", self.toggle_annotation_mode, C["red"]),
            ("💾 SAVE DRAW", self.save_drawing_only, C["accent"]),
            ("📷 SCREENSHOT", self.take_screenshot, C["accent"]),
            ("💾 SAVE DATA", self.save_measurement, C["accent"]),
            ("📄 EXPORT", self.export_pdf, C["accent2"]),
            ("🗺 TAPMAP", self.open_tapmap, C["accent2"]),
            ("🗑 CLEAR", self.clear_history, C["muted"]),
        ]

        for text, cmd, color in buttons:
            btn = tk.Button(
                toolbar, text=text, font=("Segoe UI", 9, "bold"),
                bg=C["btn"], fg=color, bd=0, padx=12, pady=8,
                cursor="hand2", command=cmd
            )
            btn.pack(side="left", padx=3, pady=10)
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=C["btn_hover"]))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg=C["btn"]))

        self.set_explanation_text(
            "✅ System ready. Click START CAMERA to begin.\n\n"
            "🎨 FEATURES:\n"
            "• DRAW MODE - Use hand gestures to draw (Index finger = draw)\n"
            "• ANNOTATE MODE - AI flags suspicious objects\n"
            "• MEASUREMENT MODE - Automatic object detection & measurement\n"
            "• ZOOM - Use +/- buttons or drag to pan\n"
            "• VOICE - Toggle ON/OFF for voice feedback\n\n"
            "✋ GESTURES:\n"
            "• Index Finger → Draw\n"
            "• Two Fingers → Select Color\n"
            "• All Fingers → Clear Canvas\n"
            "• Pinky → Save Drawing"
        )

    def _draw_accuracy_bar(self, pct: float, label: str = "N/A"):
        self.acc_canvas.update_idletasks()
        width = self.acc_canvas.winfo_width() or 350
        height = 28
        self.acc_canvas.delete("all")
        self.acc_canvas.create_rectangle(0, 0, width, height, fill=C["border"], outline="")
        if pct > 0:
            if pct >= 0.8:
                color = C["green"]
            elif pct >= 0.5:
                color = C["yellow"]
            else:
                color = C["red"]
            self.acc_canvas.create_rectangle(0, 0, int(width * pct), height, fill=color, outline="")
        self.acc_canvas.create_text(
            width // 2,
            height // 2,
            text=f"{label} ({int(pct * 100)}%)",
            fill=C["white"],
            font=("Segoe UI", 9, "bold")
        )

    def set_explanation_text(self, text):
        self.explain_text.config(state="normal")
        self.explain_text.delete("1.0", "end")
        self.explain_text.insert("end", text)
        self.explain_text.config(state="disabled")

    def _update_stat(self, var_name, text):
        getattr(self, var_name).config(text=text)

    # ========== VOICE METHODS ==========
    def toggle_voice(self):
        try:
            if self.voice.enabled:
                self.voice.set_enabled(False)
                self.voice_toggle_btn.config(text="🔇 Voice: OFF", fg=C["red"])
                self.state_manager.set("voice_enabled", False)
                self.overlay_label.config(text="▸ Voice announcements DISABLED", fg=C["yellow"])
            else:
                self.voice.set_enabled(True)
                self.voice_toggle_btn.config(text="🔊 Voice: ON", fg=C["green"])
                self.state_manager.set("voice_enabled", True)
                self.overlay_label.config(text="▸ Voice announcements ENABLED", fg=C["green"])
                self.voice.announce("Voice enabled")
        except Exception:
            pass

    def speak(self, message):
        if self.voice.enabled and self.voice.engine:
            try:
                self.voice.engine.say(message)
                self.voice.engine.runAndWait()
            except Exception:
                pass

    # ========== DRAWING MODE METHODS ==========
    def toggle_draw_mode(self):
        self.drawing_mode = not self.drawing_mode
        if self.drawing_mode:
            self.overlay_label.config(text="✏ DRAW MODE ENABLED - Use hand gestures", fg=C["accent2"])
            self.speak("Drawing mode enabled")
        else:
            self.overlay_label.config(text="📏 MEASUREMENT MODE ENABLED", fg=C["green"])
            self.speak("Measurement mode enabled")

    def toggle_annotation_mode(self):
        self.annotation_mode = not self.annotation_mode
        self.drawer.set_annotation_mode(self.annotation_mode)
        if self.annotation_mode:
            self.overlay_label.config(text="⚠️ AI ANNOTATION MODE ENABLED", fg=C["red"])
            self.speak("Annotation mode enabled")
        else:
            self.overlay_label.config(text="⭕ AI annotation mode disabled", fg=C["muted"])
            self.speak("Annotation mode disabled")

    def save_drawing_only(self):
        path = self.drawer.save_canvas_image()
        if path:
            self.last_drawing_saved_path = path
            self.safe_log("log_event", "DRAWING_SAVE", "INFO", "Drawing", "N/A", "DRAW", path)
            messagebox.showinfo("Saved", f"Drawing saved:\n{path}")
            self.speak("Drawing saved")
        else:
            messagebox.showwarning("Warning", "No drawing available to save.")

    # ========== CAMERA METHODS ==========
    def start_camera(self):
        if self.camera_running:
            return

        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            messagebox.showerror("Camera Error", "Could not open webcam.")
            return

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.camera_running = True
        self._update_stat("stat_status", "ON")

        if self.pixels_per_cm:
            self._update_stat("stat_mode", "ACC")
            self.overlay_label.config(text="✔ Calibration restored from last session", fg=C["green"])
            self.status_label.config(text="● CAMERA ON - Calibrated", fg=C["green"])
        else:
            self._update_stat("stat_mode", "EST")
            self.overlay_label.config(text="▸ Estimated mode active - Show bank card for accuracy", fg=C["yellow"])
            self.status_label.config(text="● CAMERA ON - Estimation mode", fg=C["yellow"])

        self.update_frame()
        self.speak("Camera started")

    def stop_camera(self):
        self.camera_running = False
        if self.cap:
            self.cap.release()
            self.cap = None
        self.video_label.config(image="")
        self._update_stat("stat_status", "OFF")
        self.overlay_label.config(text="● CAMERA OFF", fg=C["muted"])
        self.status_label.config(text="● CAMERA OFF", fg=C["muted"])
        self.speak("Camera stopped")

    def calibrate(self):
        self.pixels_per_cm = None
        reset_calibration_buffer()
        self.state_manager.set("last_calibration_ppc", None)
        if self.person_measurer:
            self.person_measurer.reset_buffers()
        self._update_stat("stat_mode", "EST")
        self.overlay_label.config(text="📷 Recalibrating... Show bank card clearly", fg=C["yellow"])
        self.safe_log("log_calibration", "RESET")
        try:
            if self.voice.enabled:
                self.voice.announce_calibration("reset")
        except Exception:
            pass
        messagebox.showinfo(
            "Recalibrate",
            "Calibration reset.\nShow your bank card clearly in the frame.\nKeep it steady for 2-3 seconds."
        )

    def take_screenshot(self):
        if self.display_frame is None:
            messagebox.showwarning("Warning", "No camera feed")
            return

        save_frame = self.display_frame.copy()
        if self.drawing_mode and self.drawer.canvas is not None:
            save_frame = self.drawer.merge_canvas_with_frame(save_frame)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(self.screenshot_folder, f"screenshot_{ts}.png")

        if cv2.imwrite(path, save_frame):
            self.safe_log("log_screenshot", path)
            messagebox.showinfo("Saved", f"Screenshot saved:\n{path}")
            self.speak("Screenshot saved")
        else:
            messagebox.showerror("Error", "Failed to save screenshot.")

    def save_measurement(self):
        if not self.last_measurements:
            messagebox.showwarning("Warning", "No measurement data to save.")
            return

        now = datetime.now()
        with open(self.csv_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for m in self.last_measurements:
                width_val = "N/A" if m["width_cm"] is None else m["width_cm"]
                height_val = "N/A" if m["height_cm"] is None else m["height_cm"]
                writer.writerow([
                    now.strftime("%Y-%m-%d"),
                    now.strftime("%H:%M:%S"),
                    m["object_id"],
                    m["object_name"],
                    m["confidence"],
                    width_val,
                    height_val,
                    m["extra"],
                    m.get("accuracy", "N/A"),
                    ""
                ])

        self.safe_log("log_save", len(self.last_measurements))
        self.load_history_to_table()
        messagebox.showinfo("Saved", f"Saved {len(self.last_measurements)} measurement(s) successfully.")
        self.speak(f"Saved {len(self.last_measurements)} measurements")

    def clear_history(self):
        if not messagebox.askyesno("Confirm", "Clear all saved history?"):
            return

        with open(self.csv_file, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([
                "Date", "Time", "Object ID", "Object Name", "Confidence",
                "Width (cm)", "Height (cm)", "Extra", "Accuracy", "Screenshot"
            ])

        self.load_history_to_table()
        self.safe_log("log_event", "CLEAR_HISTORY", "INFO", "History", "N/A", "SYSTEM", "All measurement history cleared")
        messagebox.showinfo("Cleared", "History cleared.")
        self.speak("History cleared")

    def open_tapmap(self):
        self.tapmap.open()
        self.tapmap.update_nodes(self.last_measurements)

    def export_pdf(self):
        if not self.last_measurements and self.current_frame is None:
            messagebox.showwarning("Warning", "No data to export.")
            return

        drawing_frame = None
        if self.current_frame is not None and self.drawer.canvas is not None:
            drawing_frame = self.drawer.canvas.copy()

        try:
            path = generate_pdf_report(
                self.last_measurements,
                screenshot_frame=self.current_frame,
                drawing_frame=drawing_frame,
                annotated_frame=self.last_annotated_frame
            )
            self.safe_log("log_export", "PDF", path)
            try:
                if self.voice.enabled:
                    self.voice.announce_export("PDF")
            except Exception:
                pass
            messagebox.showinfo("PDF Exported", f"Report saved:\n{path}")
            self.speak("PDF exported")
            try:
                os.startfile(path)
            except Exception:
                pass
        except Exception as e:
            messagebox.showerror("PDF Error", f"Failed to generate PDF:\n{e}")
            self.safe_log("log_error", "PDF_EXPORT", str(e))

    def load_history_to_table(self):
        for row in self.history_tree.get_children():
            self.history_tree.delete(row)

        if not os.path.exists(self.csv_file):
            return

        with open(self.csv_file, "r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if len(row) >= 9:
                    self.history_tree.insert("", "end", values=(row[1], row[3], row[5], row[6], row[8]))

        for item in self.history_tree.get_children():
            vals = self.history_tree.item(item, "values")
            acc = vals[4] if len(vals) > 4 else ""
            tag = {"High": "high", "Medium": "med", "Low": "low", "Estimated": "est"}.get(acc, "")
            if tag:
                self.history_tree.item(item, tags=(tag,))

        self.history_tree.tag_configure("high", foreground=C["green"])
        self.history_tree.tag_configure("med", foreground=C["yellow"])
        self.history_tree.tag_configure("low", foreground=C["red"])
        self.history_tree.tag_configure("est", foreground=C["accent"])

    # ========== DETECTION HELPERS ==========
    def apply_orientation_correction(self, label, width_cm, height_cm):
        if width_cm is None or height_cm is None:
            return width_cm, height_cm

        label_lower = label.lower()
        portrait_keywords = ["phone", "bottle", "person", "cup", "book", "remote", "mouse"]
        for kw in portrait_keywords:
            if kw in label_lower:
                if width_cm > height_cm:
                    return height_cm, width_cm
                break

        landscape_keywords = ["laptop", "keyboard", "tv", "monitor"]
        for kw in landscape_keywords:
            if kw in label_lower:
                if height_cm > width_cm:
                    return height_cm, width_cm
                break

        return width_cm, height_cm

    def get_display_name(self, label):
        label_lower = label.lower()
        if "phone" in label_lower:
            return "📱 Smartphone"
        elif "bottle" in label_lower:
            return "🧴 Bottle"
        elif "person" in label_lower:
            return "👤 Person"
        elif "cup" in label_lower:
            return "☕ Cup"
        elif "book" in label_lower:
            return "📖 Book"
        elif "laptop" in label_lower:
            return "💻 Laptop"
        elif "keyboard" in label_lower:
            return "⌨️ Keyboard"
        elif "mouse" in label_lower:
            return "🖱️ Mouse"
        else:
            return f"📦 {label.title()}"

    def update_ai_panel(self, measurement):
        mode = "ACC" if self.pixels_per_cm else "EST"
        explanation = self.explainer.build_explanation(measurement, mode)
        self._set_detection_text(explanation)

    def _set_detection_text(self, content: str):
        self.explain_text.config(state="normal")
        self.explain_text.delete("1.0", "end")
        self.explain_text.insert("end", content)
        self.explain_text.config(state="disabled")

    def handle_voice_and_soc(self, measurement, track_id=None):
        mode = "ACC" if self.pixels_per_cm else "EST"

        try:
            self.soc_logger.log_detection(measurement, mode=mode)
        except Exception:
            pass

        if self.voice.enabled and track_id is not None and track_id != self.last_spoken_track_id:
            self.last_spoken_track_id = track_id
            try:
                if measurement.get("width_cm") and measurement.get("height_cm"):
                    self.voice.announce_measurement(
                        measurement.get("object_name", "object"),
                        measurement.get("width_cm"),
                        measurement.get("height_cm"),
                        units=config.UNITS
                    )
                else:
                    self.voice.announce(f"{measurement.get('object_name', 'Object')} detected")
            except Exception:
                pass

    # ========== MAIN UPDATE FRAME ==========
    def update_frame(self):
        if not self.camera_running or self.cap is None or self.detector is None:
            self.root.after(30, self.update_frame)
            return

        ret, frame = self.cap.read()
        if not ret:
            self.root.after(30, self.update_frame)
            return

        frame = cv2.flip(frame, 1)
        display = frame.copy()
        self.last_measurements = []

        raw_detections = self.detector.detect(frame)

        # Barcode scanning
        if config.BARCODE_ENABLED:
            try:
                barcode_results = self.barcode.scan_frame(frame)
            except Exception:
                barcode_results = []

            if barcode_results:
                try:
                    display = self.barcode.draw_barcode_overlay(display, barcode_results)
                except Exception:
                    pass

                for b in barcode_results:
                    product_name = b["product"]["name"] if b.get("product") else ""
                    self.safe_log("log_barcode", b["data"], product_name)
                    try:
                        if self.voice.enabled:
                            if product_name:
                                self.voice.announce_barcode(b["data"], product_name)
                            else:
                                self.voice.announce_barcode(b["data"])
                    except Exception:
                        pass

        # Calibration
        if self.pixels_per_cm is None:
            ppc, ref_box = calibrate_pixels_per_cm_from_card(frame)
            if ppc is not None:
                self.pixels_per_cm = ppc
                self.state_manager.set("last_calibration_ppc", ppc)
                self._update_stat("stat_mode", "ACC")
                self.overlay_label.config(text="✔ Accurate mode active - Calibrated", fg=C["green"])
                self.safe_log("log_calibration", "SUCCESS", ppc)
                try:
                    if self.voice.enabled:
                        self.voice.announce_calibration("success")
                except Exception:
                    pass
                if ref_box is not None:
                    rb = ref_box.astype(int)
                    cv2.drawContours(display, [rb], -1, (0, 230, 255), 2)
            else:
                cv2.putText(
                    display,
                    "Show bank card for accurate mode",
                    (20, 38),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.70,
                    (0, 200, 255),
                    2
                )

        # AI Annotation Mode
        if self.annotation_mode:
            display = self.drawer.annotate_suspicious_objects(display, raw_detections)
            self.last_annotated_frame = display.copy()
        else:
            self.last_annotated_frame = None

        # Object Tracking
        tracked_detections = self.tracker.update(raw_detections)

        obj_count = 0
        best_accuracy = 0.0
        best_acc_label = "N/A"
        best_measurement = None

        for det in tracked_detections:
            label = det["label"]
            conf = det["confidence"]
            track_id = det.get("track_id", obj_count + 1)
            x1, y1, x2, y2 = det["bbox"]

            if (x2 - x1) < 30 or (y2 - y1) < 30:
                continue

            obj_count += 1
            width_cm = det.get("width_cm")
            height_cm = det.get("height_cm")
            extra = ""
            accuracy_str = "Low"
            acc_pct = 0.2

            if label == "person" and self.person_measurer:
                box_color = (0, 180, 255)
                pd = self.person_measurer.estimate_person_measurements(frame, self.pixels_per_cm)

                if pd.get("landmarks"):
                    self.person_measurer.draw_pose(display, pd["landmarks"])

                if pd.get("shoulder_width_cm") is not None:
                    width_cm = pd["shoulder_width_cm"]
                if pd.get("height_cm") is not None:
                    height_cm = pd["height_cm"]

                accuracy_str = pd.get("accuracy", "Estimated")
                extra = f"Pose {pd.get('confidence', 0):.0%}"
                acc_pct = 0.9 if accuracy_str == "High" else (0.55 if accuracy_str == "Medium" else 0.35)

            else:
                box_color = (50, 220, 80)

                if self.pixels_per_cm and width_cm is None:
                    width_cm, height_cm, accuracy_str = measure_bbox_cm(det["bbox"], self.pixels_per_cm, label)
                elif width_cm is None:
                    width_cm, height_cm, accuracy_str = estimate_bbox_cm_without_calibration(det["bbox"], label, frame.shape)
                    extra = "Show bank card for accurate mode"

                acc_pct = 0.9 if accuracy_str == "High" else (0.55 if accuracy_str == "Medium" else 0.35)

            if width_cm and height_cm:
                width_cm, height_cm = self.apply_orientation_correction(label, width_cm, height_cm)

            if acc_pct > best_accuracy:
                best_accuracy = acc_pct
                best_acc_label = accuracy_str

            display_name = self.get_display_name(label)

            cv2.rectangle(display, (x1, y1), (x2, y2), box_color, 2)
            lbl_txt = f"[{track_id}] {display_name} {conf:.0%}"
            (tw, th), _ = cv2.getTextSize(lbl_txt, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
            cv2.rectangle(display, (x1, max(0, y1 - th - 8)), (x1 + tw + 8, y1), box_color, -1)
            cv2.putText(display, lbl_txt, (x1 + 4, max(th, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2)

            if width_cm and height_cm:
                w_text = f"W: {width_cm} cm" if accuracy_str != "Estimated" else f"W: ~{width_cm} cm"
                h_text = f"H: {height_cm} cm" if accuracy_str != "Estimated" else f"H: ~{height_cm} cm"
                cv2.putText(display, w_text, (x1, y2 + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 255, 100), 2)
                cv2.putText(display, h_text, (x1, y2 + 42), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 200, 255), 2)

            item_data = {
                "object_id": track_id,
                "object_name": display_name,
                "confidence": conf,
                "width_cm": width_cm,
                "height_cm": height_cm,
                "extra": extra,
                "accuracy": accuracy_str,
            }
            self.last_measurements.append(item_data)

            if best_measurement is None or conf > best_measurement["confidence"]:
                best_measurement = item_data

        self._update_stat("stat_objects", str(obj_count))
        self._update_stat("stat_accuracy", best_acc_label)
        self._draw_accuracy_bar(best_accuracy, best_acc_label)

        if best_measurement:
            self.update_ai_panel(best_measurement)
            self.handle_voice_and_soc(best_measurement, track_id=best_measurement.get("object_id"))
        else:
            if self.drawing_mode:
                self._set_detection_text(
                    "✏ DRAWING MODE ACTIVE\n\n"
                    "Use hand gestures to draw:\n"
                    "• Index Finger → Draw\n"
                    "• Two Fingers → Select Color\n"
                    "• All Fingers → Clear Canvas\n"
                    "• Pinky → Save Drawing\n\n"
                    "Click START CAMERA to begin drawing"
                )
            else:
                self._set_detection_text(
                    "📡 No object detected.\n\n"
                    "Point camera at objects to measure.\n"
                    "Show a bank card to calibrate.\n\n"
                    "Enable DRAW MODE for hand gesture drawing"
                )

        if self.tapmap.window and self.tapmap.window.winfo_exists():
            self.tapmap.update_nodes(self.last_measurements)

        # ========== DRAWING MODE PROCESSING ==========
        if self.drawing_mode:
            try:
                processed_display, draw_status = self.drawer.process(display)
                display = processed_display

                if draw_status:
                    self.overlay_label.config(text=f"✏ {draw_status}", fg=C["accent2"])
                else:
                    gesture = getattr(self.drawer, 'last_gesture', 'idle')
                    if gesture == "draw":
                        self.overlay_label.config(text="✏ DRAWING - Move your index finger", fg=C["green"])
                    elif gesture == "select":
                        self.overlay_label.config(text="🎨 SELECT MODE - Point at color panel", fg=C["yellow"])
                    elif gesture == "clear":
                        self.overlay_label.config(text="🗑 CANVAS CLEARED", fg=C["red"])
                    elif gesture == "save":
                        self.overlay_label.config(text="💾 DRAWING SAVED", fg=C["accent"])
                    else:
                        self.overlay_label.config(text="✏ DRAW MODE - Raise index finger to draw", fg=C["accent2"])

            except Exception as e:
                print(f"[Drawing Error] {e}")

        # Apply zoom
        display = self.apply_zoom(display)
        self.display_frame = display

        # Convert for display
        rgb = cv2.cvtColor(display, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)

        container_w = max(100, self.video_frame.winfo_width() or 900)
        container_h = max(100, self.video_frame.winfo_height() or 540)

        img_w, img_h = img.size
        scale = min(container_w / img_w, container_h / img_h)
        new_w = max(1, int(img_w * scale))
        new_h = max(1, int(img_h * scale))
        resized_img = img.resize((new_w, new_h), Image.LANCZOS)

        imgtk = ImageTk.PhotoImage(image=resized_img)
        self.video_label.imgtk = imgtk
        self.video_label.config(image=imgtk, width=new_w, height=new_h)
        self.video_label.place(relx=0.5, rely=0.5, anchor="center", width=new_w, height=new_h)

        self.root.after(15, self.update_frame)

    def on_closing(self):
        try:
            self.state_manager.set("voice_enabled", self.voice.enabled)
            self.state_manager.set("last_units", config.UNITS)

            if self.pixels_per_cm:
                self.state_manager.set("last_calibration_ppc", self.pixels_per_cm)

            self.save_window_state()
            self.safe_log("log_system_stop")

            try:
                self.voice.shutdown()
            except Exception:
                pass

            self.state_manager.save_state()
        except Exception as e:
            print(f"Error saving state: {e}")

        self.stop_camera()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = AIMeasureV6App(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()