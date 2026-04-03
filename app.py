"""
app.py - Main Application
AI Measure Pro YOLO - Version 5.1 (FINAL COMPLETE)

Features:
  - Accurate mode with calibration
  - Estimated mode without calibration
  - AUTO-ORIENTATION CORRECTION for phones/bottles/persons
  - AI Explanation Panel
  - SOC Security Event Logging
  - TapMap Style Network Visualization
  - Voice Announcements with ON/OFF Toggle (Persistent)
  - Barcode Scanner
  - Object Tracking
  - Persistent State Management (remembers settings)
  - Visual measurement lines with arrows
"""

import os
import csv
import cv2
import json
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

# V5 Imports
from ai_explainer import AIExplainer
from soc_logger import SOCLogger
from tapmap_view import TapMapWindow
from voice_announcer import VoiceAnnouncer
from barcode_scanner import BarcodeScanner
from object_tracker import ObjectTracker
from state_manager import StateManager
import config


C = {
    "bg": "#0d1117",
    "panel": "#161b22",
    "card": "#1c2128",
    "border": "#30363d",
    "accent": "#00e5ff",
    "accent2": "#7c3aed",
    "green": "#22c55e",
    "yellow": "#f59e0b",
    "red": "#ef4444",
    "white": "#f0f6fc",
    "muted": "#8b949e",
    "btn": "#21262d",
    "btn_hover": "#30363d",
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


class AIMeasureV5App:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Measure Pro  ·  V5.1")
        self.root.configure(bg=C["bg"])
        self.root.minsize(1200, 700)

        self.cap = None
        self.camera_running = False
        self.current_frame = None
        self.pixels_per_cm = None
        self.last_measurements = []
        self.detector = None
        self.last_spoken_track_id = None

        # Initialize State Manager FIRST
        self.state_manager = StateManager()
        
        # Load saved window geometry
        saved_geometry = self.state_manager.get("window_geometry", "1440x860")
        self.root.geometry(saved_geometry)
        saved_position = self.state_manager.get("window_position")
        if saved_position:
            try:
                self.root.geometry(f"+{saved_position[0]}+{saved_position[1]}")
            except:
                pass

        # Initialize V5 Modules
        self.explainer = AIExplainer()
        self.soc_logger = SOCLogger()
        self.tapmap = TapMapWindow()
        
        # Load saved voice state
        saved_voice_state = self.state_manager.get("voice_enabled", True)
        self.voice = VoiceAnnouncer(
            enabled=saved_voice_state,
            rate=config.VOICE_RATE,
            volume=config.VOICE_VOLUME
        )
        
        # Load saved units
        saved_units = self.state_manager.get("last_units", "cm")
        if saved_units != config.UNITS:
            config.UNITS = saved_units
        
        self.barcode = BarcodeScanner(config.BARCODE_DATABASE)
        self.tracker = ObjectTracker(
            max_age=config.MAX_TRACKING_AGE,
            max_history=config.MAX_MEASUREMENT_HISTORY
        )

        # Load saved calibration
        saved_calibration = self.state_manager.get("last_calibration_ppc")
        if saved_calibration:
            self.pixels_per_cm = saved_calibration
            print(f"[Restored] Calibration: {saved_calibration:.2f} pixels/cm")

        try:
            self.person_measurer = PersonMeasurer()
        except Exception as e:
            print(f"[App] PersonMeasurer error: {e}")
            self.person_measurer = None

        self.csv_file = "measurement_history.csv"
        self.screenshot_folder = "screenshots"
        self.model_path = "models/yolov8n.pt"

        os.makedirs(self.screenshot_folder, exist_ok=True)
        os.makedirs("reports", exist_ok=True)
        self.ensure_csv_exists()

        self._apply_theme()
        self.load_model()
        self.build_ui()
        self.load_history_to_table()
        
        # Mark first run complete
        if self.state_manager.get("first_run", True):
            self.state_manager.mark_first_run_complete()
            print("First run - default settings created")
        
        # Log system start
        session_count = self.state_manager.increment_session_count()
        self.soc_logger.log_system_start()
        print(f"Session #{session_count} started")
        
        if self.voice.enabled:
            self.voice.announce("AI Measure Pro V5 started")

    def _apply_theme(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background=C["card"], fieldbackground=C["card"],
                       foreground=C["white"], rowheight=26, borderwidth=0, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", background=C["panel"], foreground=C["accent"],
                       font=("Segoe UI", 9, "bold"), borderwidth=0)
        style.map("Treeview", background=[("selected", C["accent2"])],
                 foreground=[("selected", C["white"])])

    def load_model(self):
        if not os.path.exists(self.model_path):
            messagebox.showerror("Model Missing", "yolov8n.pt not found in models/ folder.")
            self.root.after(300, self.root.destroy)
            return
        try:
            self.detector = YOLODetector(self.model_path, confidence_threshold=0.40)
        except Exception as e:
            messagebox.showerror("Model Error", str(e))
            self.root.after(300, self.root.destroy)

    def ensure_csv_exists(self):
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([
                    "Date", "Time", "Object ID", "Object Name", "Confidence",
                    "Width (cm)", "Height (cm)", "Extra", "Accuracy", "Screenshot"
                ])

    def save_window_state(self):
        """Save window position and size"""
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
        except:
            pass

    def toggle_voice(self):
        """Toggle voice announcements ON/OFF"""
        if self.voice.enabled:
            self.voice.set_enabled(False)
            self.voice_toggle_btn.config(text="🔇 Voice: OFF", fg=C["red"])
            self.state_manager.set("voice_enabled", False)
            self.overlay_label.config(text="▸ Voice announcements DISABLED", fg=C["yellow"])
            def reset_status():
                if self.camera_running:
                    self.overlay_label.config(text="▸ Camera running - Voice OFF", fg=C["muted"])
                else:
                    self.overlay_label.config(text="▸ Camera OFF - Voice OFF", fg=C["muted"])
            self.root.after(2500, reset_status)
        else:
            self.voice.set_enabled(True)
            self.voice_toggle_btn.config(text="🔊 Voice: ON", fg=C["green"])
            self.state_manager.set("voice_enabled", True)
            self.overlay_label.config(text="▸ Voice announcements ENABLED", fg=C["green"])
            def reset_status():
                if self.camera_running:
                    self.overlay_label.config(text="▸ Camera running - Voice ON", fg=C["muted"])
                else:
                    self.overlay_label.config(text="▸ Camera OFF - Voice ON", fg=C["muted"])
            self.root.after(2500, reset_status)
            self.voice.announce("Voice enabled")

    def build_ui(self):
        topbar = tk.Frame(self.root, bg=C["panel"], height=56)
        topbar.pack(fill="x", side="top")
        topbar.pack_propagate(False)

        tk.Label(topbar, text="⬡  AI Measure Pro V5.1", font=("Segoe UI", 17, "bold"),
                fg=C["accent"], bg=C["panel"]).pack(side="left", padx=20, pady=10)
        tk.Label(topbar, text="AI · SOC · TapMap · Voice · Barcode", font=("Segoe UI", 10),
                fg=C["muted"], bg=C["panel"]).pack(side="left", padx=4)

        # Voice Toggle Button
        voice_status = "ON" if self.voice.enabled else "OFF"
        voice_icon = "🔊" if self.voice.enabled else "🔇"
        voice_color = C["green"] if self.voice.enabled else C["red"]
        
        self.voice_toggle_btn = tk.Button(
            topbar, text=f"{voice_icon} Voice: {voice_status}",
            font=("Segoe UI", 9, "bold"), bg=C["btn"], fg=voice_color,
            activebackground=C["btn_hover"], activeforeground=C["white"],
            bd=0, padx=12, pady=5, cursor="hand2", command=self.toggle_voice
        )
        self.voice_toggle_btn.pack(side="left", padx=10)

        self.clock_label = tk.Label(topbar, text="", font=("Segoe UI", 10),
                                   fg=C["muted"], bg=C["panel"])
        self.clock_label.pack(side="right", padx=20)
        self._tick_clock()

        main = tk.Frame(self.root, bg=C["bg"])
        main.pack(fill="both", expand=True, padx=12, pady=(8, 0))

        left = tk.Frame(main, bg=C["panel"], highlightthickness=1, highlightbackground=C["border"])
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))
        left.pack_propagate(False)

        self.video_container = tk.Frame(left, bg="black")
        self.video_container.pack(fill="both", expand=True, padx=2, pady=2)
        self.video_container.pack_propagate(False)

        self.video_label = tk.Label(self.video_container, bg="black", cursor="crosshair",
                                   bd=0, highlightthickness=0)
        self.video_label.place(relx=0.5, rely=0.5, anchor="center")

        self.overlay_label = tk.Label(left, text="▸  Camera OFF  —  Click Start Camera to begin",
                                     font=("Segoe UI", 10), fg=C["muted"], bg=C["panel"])
        self.overlay_label.pack(fill="x", pady=(0, 2))

        right = tk.Frame(main, bg=C["bg"], width=420)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        self._build_info_panel(right)

        toolbar = tk.Frame(self.root, bg=C["panel"], height=58)
        toolbar.pack(fill="x", side="bottom")
        toolbar.pack_propagate(False)

        btns = [
            ("▶  Start Camera", self.start_camera, C["green"]),
            ("■  Stop Camera", self.stop_camera, C["red"]),
            ("↺  Recalibrate", self.recalibrate, C["yellow"]),
            ("📷  Screenshot", self.save_screenshot, C["accent"]),
            ("💾  Save Data", self.save_measurement, C["accent"]),
            ("📄  Export PDF", self.export_pdf, C["accent2"]),
            ("🗺  TapMap", self.open_tapmap, C["accent2"]),
            ("🗑  Clear History", self.clear_history, C["muted"]),
        ]
        for text, cmd, acc in btns:
            GlassButton(toolbar, text=text, command=cmd, accent=acc).pack(side="left", padx=6, pady=10)

    def _build_info_panel(self, parent):
        cards = tk.Frame(parent, bg=C["bg"])
        cards.pack(fill="x", pady=(0, 6))

        def stat_card(master, label, var_name, color):
            f = tk.Frame(master, bg=C["card"], highlightthickness=1, highlightbackground=C["border"])
            f.pack(side="left", fill="x", expand=True, padx=3, pady=4)
            tk.Label(f, text=label, font=("Segoe UI", 8), fg=C["muted"], bg=C["card"]).pack(pady=(6, 0))
            lbl = tk.Label(f, text="—", font=("Segoe UI", 13, "bold"), fg=color, bg=C["card"])
            lbl.pack(pady=(0, 6))
            setattr(self, var_name, lbl)

        stat_card(cards, "STATUS", "stat_status", C["green"])
        stat_card(cards, "MODE", "stat_mode", C["accent"])
        stat_card(cards, "OBJECTS", "stat_objects", C["yellow"])
        stat_card(cards, "ACCURACY", "stat_accuracy", C["accent2"])

        info_box = tk.Frame(parent, bg=C["card"], highlightthickness=1, highlightbackground=C["border"])
        info_box.pack(fill="x", padx=3, pady=3)
        tk.Label(info_box, text="🤖 AI Explanation Panel", font=("Segoe UI", 9, "bold"),
                fg=C["accent"], bg=C["card"]).pack(anchor="w", padx=10, pady=(8, 2))

        self.detection_text = tk.Text(info_box, height=10, width=38, font=("Consolas", 9),
                                     bg=C["card"], fg=C["white"], relief="flat", bd=0,
                                     state="disabled", wrap="word", insertbackground=C["accent"])
        self.detection_text.pack(fill="x", padx=10, pady=(0, 8))

        acc_frame = tk.Frame(parent, bg=C["card"], highlightthickness=1, highlightbackground=C["border"])
        acc_frame.pack(fill="x", padx=3, pady=3)
        tk.Label(acc_frame, text="Measurement Accuracy", font=("Segoe UI", 9, "bold"),
                fg=C["accent"], bg=C["card"]).pack(anchor="w", padx=10, pady=(8, 4))

        self.acc_canvas = tk.Canvas(acc_frame, height=24, bg=C["panel"], bd=0, highlightthickness=0)
        self.acc_canvas.pack(fill="x", padx=10, pady=(0, 10))
        self._draw_accuracy_bar(0)

        hist_frame = tk.Frame(parent, bg=C["card"], highlightthickness=1, highlightbackground=C["border"])
        hist_frame.pack(fill="both", expand=True, padx=3, pady=3)
        tk.Label(hist_frame, text="Measurement History", font=("Segoe UI", 10, "bold"),
                fg=C["white"], bg=C["card"]).pack(anchor="w", padx=10, pady=(8, 4))

        cols = ("time", "name", "width", "height", "accuracy")
        self.tree = ttk.Treeview(hist_frame, columns=cols, show="headings", height=12)
        col_cfg = {"time": ("Time", 70), "name": ("Object", 90), "width": ("W (cm)", 65),
                  "height": ("H (cm)", 65), "accuracy": ("Accuracy", 80)}
        for c, (hdr, w) in col_cfg.items():
            self.tree.heading(c, text=hdr)
            self.tree.column(c, width=w, anchor="center")
        sb = ttk.Scrollbar(hist_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y", padx=(0, 6))
        self.tree.pack(fill="both", expand=True, padx=6, pady=(0, 8))

    def _tick_clock(self):
        self.clock_label.config(text=datetime.now().strftime("%A  %d %b %Y  |  %H:%M:%S"))
        self.root.after(1000, self._tick_clock)

    def _draw_accuracy_bar(self, pct: float, label: str = "N/A"):
        self.acc_canvas.update_idletasks()
        width = self.acc_canvas.winfo_width() or 360
        height = 24
        self.acc_canvas.delete("all")
        self.acc_canvas.create_rectangle(0, 0, width, height, fill=C["border"], outline="")
        if pct > 0:
            col = C["green"] if pct >= 0.8 else (C["yellow"] if pct >= 0.5 else C["red"])
            self.acc_canvas.create_rectangle(0, 0, int(width * pct), height, fill=col, outline="")
        self.acc_canvas.create_text(width // 2, height // 2,
                                   text=f"{label}  ({int(pct * 100)}%)",
                                   fill=C["white"], font=("Segoe UI", 8, "bold"))

    def _set_detection_text(self, content: str):
        self.detection_text.config(state="normal")
        self.detection_text.delete("1.0", "end")
        self.detection_text.insert("end", content)
        self.detection_text.config(state="disabled")

    def _update_stat(self, var_name, text):
        getattr(self, var_name).config(text=text)

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
        
        # Restore calibration if available
        if self.pixels_per_cm:
            self._update_stat("stat_mode", "ACC")
            self.overlay_label.config(text="✔ Calibration restored from last session", fg=C["green"])
        else:
            self._update_stat("stat_mode", "EST")
            self.overlay_label.config(text="▸ Estimated mode active - Show bank card for accuracy", fg=C["yellow"])
        
        self.update_frame()

    def stop_camera(self):
        self.camera_running = False
        if self.cap:
            self.cap.release()
            self.cap = None
        self.video_label.config(image="")
        self._update_stat("stat_status", "OFF")
        self.overlay_label.config(text="▸  Camera OFF", fg=C["muted"])

    def recalibrate(self):
        self.pixels_per_cm = None
        reset_calibration_buffer()
        self.state_manager.set("last_calibration_ppc", None)
        if self.person_measurer:
            self.person_measurer.reset_buffers()
        self._update_stat("stat_mode", "EST")
        self.overlay_label.config(text="▸  Recalibrating... Show bank card clearly", fg=C["yellow"])
        self.soc_logger.log_calibration("RESET")
        if self.voice.enabled:
            self.voice.announce_calibration("reset")
        messagebox.showinfo("Recalibrate", 
            "Calibration reset.\nShow your bank card clearly in the frame.\nKeep it steady for 2-3 seconds.")

    def open_tapmap(self):
        self.tapmap.open()
        self.tapmap.update_nodes(self.last_measurements)

    def update_ai_panel(self, measurement):
        mode = "ACC" if self.pixels_per_cm else "EST"
        explanation = self.explainer.build_explanation(measurement, mode)
        self._set_detection_text(explanation)

    def handle_voice_and_soc(self, measurement, track_id=None):
        mode = "ACC" if self.pixels_per_cm else "EST"
        self.soc_logger.log_detection(measurement, mode=mode)
        if self.voice.enabled and track_id is not None and track_id != self.last_spoken_track_id:
            self.last_spoken_track_id = track_id
            if measurement.get("width_cm") and measurement.get("height_cm"):
                self.voice.announce_measurement(
                    measurement.get("object_name", "object"),
                    measurement.get("width_cm"),
                    measurement.get("height_cm"),
                    units=config.UNITS
                )
            else:
                self.voice.announce(f"{measurement.get('object_name', 'Object')} detected")

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

    def update_frame(self):
        if not self.camera_running or self.cap is None or self.detector is None:
            return

        ret, frame = self.cap.read()
        if not ret:
            self.root.after(30, self.update_frame)
            return

        frame = cv2.flip(frame, 1)
        display = frame.copy()
        self.last_measurements = []

        # Barcode scanning
        if config.BARCODE_ENABLED:
            barcode_results = self.barcode.scan_frame(frame)
            if barcode_results:
                display = self.barcode.draw_barcode_overlay(display, barcode_results)
                for b in barcode_results:
                    product_name = b["product"]["name"] if b.get("product") else ""
                    self.soc_logger.log_barcode(b["data"], product_name=product_name)
                    if self.voice.enabled:
                        if product_name:
                            self.voice.announce_barcode(b["data"], product_name)
                        else:
                            self.voice.announce_barcode(b["data"])

        # Calibration
        if self.pixels_per_cm is None:
            ppc, ref_box = calibrate_pixels_per_cm_from_card(frame)
            if ppc is not None:
                self.pixels_per_cm = ppc
                self.state_manager.set("last_calibration_ppc", ppc)
                self._update_stat("stat_mode", "ACC")
                self.overlay_label.config(text="✔ Accurate mode active - Calibrated", fg=C["green"])
                self.soc_logger.log_calibration("SUCCESS", ppc)
                if self.voice.enabled:
                    self.voice.announce_calibration("success")
                if ref_box is not None:
                    rb = ref_box.astype(int)
                    cv2.drawContours(display, [rb], -1, (0, 230, 255), 2)
            else:
                cv2.putText(display, "Show bank card for accurate mode", (20, 38),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.70, (0, 200, 255), 2)

        detections = self.detector.detect(frame)
        tracked_detections = self.tracker.update(detections)
        
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

            # Draw bounding box
            cv2.rectangle(display, (x1, y1), (x2, y2), box_color, 2)
            lbl_txt = f"[{track_id}] {display_name}  {conf:.0%}"
            (tw, th), _ = cv2.getTextSize(lbl_txt, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(display, (x1, max(0, y1 - th - 12)), (x1 + tw + 10, y1), box_color, -1)
            cv2.putText(display, lbl_txt, (x1 + 4, max(th, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

            if width_cm and height_cm:
                cv2.putText(display, f"W: {width_cm} cm", (x1, y2 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (100, 255, 100), 2)
                cv2.putText(display, f"H: {height_cm} cm", (x1, y2 + 42), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (100, 200, 255), 2)

            item_data = {
                "object_id": track_id, "object_name": display_name, "confidence": conf,
                "width_cm": width_cm, "height_cm": height_cm, "extra": extra, "accuracy": accuracy_str,
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
            self._set_detection_text("📡 No object detected.\n\nPoint camera at objects to measure.\n\nShow a bank card to calibrate.")

        if self.tapmap.window and self.tapmap.window.winfo_exists():
            self.tapmap.update_nodes(self.last_measurements)

        self.current_frame = display
        rgb = cv2.cvtColor(display, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)

        container_w = max(100, self.video_container.winfo_width() or 900)
        container_h = max(100, self.video_container.winfo_height() or 540)
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

    def save_screenshot(self):
        if self.current_frame is None:
            messagebox.showwarning("Warning", "No frame to save.")
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(self.screenshot_folder, f"screenshot_{ts}.png")
        if cv2.imwrite(path, self.current_frame):
            self.soc_logger.log_screenshot(path)
            messagebox.showinfo("Saved", f"Screenshot saved:\n{path}")
        else:
            messagebox.showerror("Error", "Failed to save screenshot.")

    def get_latest_screenshot(self):
        files = [f for f in os.listdir(self.screenshot_folder) if f.lower().endswith(".png")]
        if not files:
            return "N/A"
        files.sort(reverse=True)
        return files[0]

    def save_measurement(self):
        if not self.last_measurements:
            messagebox.showwarning("Warning", "No measurement data to save.")
            return
        now = datetime.now()
        shot = self.get_latest_screenshot()
        with open(self.csv_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for m in self.last_measurements:
                width_val = "N/A" if m["width_cm"] is None else m["width_cm"]
                height_val = "N/A" if m["height_cm"] is None else m["height_cm"]
                writer.writerow([
                    now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"),
                    m["object_id"], m["object_name"], m["confidence"],
                    width_val, height_val, m["extra"],
                    m.get("accuracy", "N/A"), shot
                ])
        self.soc_logger.log_save(len(self.last_measurements))
        self.load_history_to_table()
        messagebox.showinfo("Saved", f"Saved {len(self.last_measurements)} measurement(s) successfully.")

    def export_pdf(self):
        if not self.last_measurements:
            messagebox.showwarning("Warning", "No measurements to export.")
            return
        try:
            path = generate_pdf_report(self.last_measurements, screenshot_frame=self.current_frame)
            self.soc_logger.log_export("PDF", path)
            if self.voice.enabled:
                self.voice.announce_export("PDF")
            messagebox.showinfo("PDF Exported", f"Report saved:\n{path}")
            try:
                os.startfile(path)
            except:
                pass
        except Exception as e:
            messagebox.showerror("PDF Error", f"Failed to generate PDF:\n{e}")
            self.soc_logger.log_error("PDF_EXPORT", str(e))

    def load_history_to_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        if not os.path.exists(self.csv_file):
            return
        with open(self.csv_file, "r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if len(row) >= 9:
                    self.tree.insert("", "end", values=(row[1], row[3], row[5], row[6], row[8]))
        for item in self.tree.get_children():
            vals = self.tree.item(item, "values")
            acc = vals[4] if len(vals) > 4 else ""
            tag = {"High": "high", "Medium": "med", "Low": "low", "Estimated": "est"}.get(acc, "")
            if tag:
                self.tree.item(item, tags=(tag,))
        self.tree.tag_configure("high", foreground=C["green"])
        self.tree.tag_configure("med", foreground=C["yellow"])
        self.tree.tag_configure("low", foreground=C["red"])
        self.tree.tag_configure("est", foreground=C["accent"])

    def clear_history(self):
        if not messagebox.askyesno("Confirm", "Clear all saved history?"):
            return
        with open(self.csv_file, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([
                "Date", "Time", "Object ID", "Object Name", "Confidence",
                "Width (cm)", "Height (cm)", "Extra", "Accuracy", "Screenshot"
            ])
        self.load_history_to_table()
        self.soc_logger.log_event("CLEAR_HISTORY", "INFO", "History", "N/A", "SYSTEM", "All measurement history cleared")
        messagebox.showinfo("Cleared", "History cleared.")

    def on_closing(self):
        try:
            self.state_manager.set("voice_enabled", self.voice.enabled)
            self.state_manager.set("last_units", config.UNITS)
            if self.pixels_per_cm:
                self.state_manager.set("last_calibration_ppc", self.pixels_per_cm)
            self.save_window_state()
            self.soc_logger.log_system_stop()
            self.voice.shutdown()
            self.state_manager.save_state()
        except Exception as e:
            print(f"Error saving state: {e}")
        self.stop_camera()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = AIMeasureV5App(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()