"""
tapmap_view.py - TapMap Style Network Map Visualization
Creates a visual network map of detected objects and relationships.
"""

import math
import tkinter as tk
from tkinter import ttk


class TapMapWindow:
    def __init__(self, master=None):
        self.window = None
        self.canvas = None
        self.nodes = []
        self.last_update_time = None
        self.animation_angle = 0

    def open(self):
        """Open the TapMap visualization window"""
        if self.window and self.window.winfo_exists():
            self.window.lift()
            self.update_nodes()
            return

        self.window = tk.Toplevel()
        self.window.title("🗺 TapMap View - Object Network Map")
        self.window.geometry("950x580")
        self.window.configure(bg="#0b1220")
        self.window.minsize(800, 500)

        # Title bar
        title_frame = tk.Frame(self.window, bg="#0b1220")
        title_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(title_frame, text="🗺 Object Network Map", 
                font=("Segoe UI", 14, "bold"), fg="#00e5ff", bg="#0b1220").pack(side="left")
        
        tk.Label(title_frame, text="TapMap Style Visualization", 
                font=("Segoe UI", 10), fg="#7f8ea3", bg="#0b1220").pack(side="left", padx=10)
        
        # Refresh button
        refresh_btn = tk.Button(title_frame, text="🔄 Refresh", command=self.refresh,
                               bg="#21262d", fg="white", font=("Segoe UI", 9))
        refresh_btn.pack(side="right", padx=5)
        
        # Info label
        self.info_label = tk.Label(self.window, text="", font=("Segoe UI", 9),
                                   fg="#7f8ea3", bg="#0b1220")
        self.info_label.pack(fill="x", padx=10, pady=(0, 5))

        # Canvas for map
        self.canvas = tk.Canvas(
            self.window,
            bg="#071018",
            highlightthickness=1,
            highlightbackground="#1a2a3a"
        )
        self.canvas.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Bind resize event
        self.canvas.bind("<Configure>", self._on_resize)
        
        # Start animation
        self._animate()
        
        self._draw_background()

    def _on_resize(self, event):
        """Handle window resize"""
        self._draw_background()
        if hasattr(self, 'last_measurements'):
            self.update_nodes(self.last_measurements)

    def _animate(self):
        """Animate the map (pulse effect)"""
        if self.window and self.window.winfo_exists():
            self.animation_angle = (self.animation_angle + 2) % 360
            if hasattr(self, 'last_measurements'):
                self.update_nodes(self.last_measurements)
            self.window.after(2000, self._animate)

    def _draw_background(self):
        """Draw the map background with grid and central hub"""
        if not self.canvas:
            return

        self.canvas.delete("all")
        w = self.canvas.winfo_width() or 900
        h = self.canvas.winfo_height() or 520
        
        if w < 100:
            return

        # Draw grid
        for x in range(0, w, 50):
            self.canvas.create_line(x, 0, x, h, fill="#0f1a2a", width=1)
        for y in range(0, h, 50):
            self.canvas.create_line(0, y, w, y, fill="#0f1a2a", width=1)

        # Draw concentric circles
        center_x = w // 2
        center_y = h // 2
        for r in [80, 160, 240]:
            self.canvas.create_oval(center_x - r, center_y - r, center_x + r, center_y + r,
                                    outline="#0f2a3a", width=1, dash=(5, 5))

        # Central AI Core node
        glow = 8 + int(abs(math.sin(self.animation_angle * math.pi / 180)) * 4)
        self.canvas.create_oval(center_x - 35, center_y - 35, center_x + 35, center_y + 35,
                                fill="#00e5ff", outline="#8ef8ff", width=3)
        self.canvas.create_text(center_x, center_y - 8, text="AI", fill="#000000", 
                                font=("Segoe UI", 16, "bold"))
        self.canvas.create_text(center_x, center_y + 12, text="CORE", fill="#000000", 
                                font=("Segoe UI", 10, "bold"))
        
        # Store center coordinates
        self.center_x = center_x
        self.center_y = center_y

    def update_nodes(self, measurements=None):
        """Update the map with current detections"""
        if not self.window or not self.window.winfo_exists():
            return
        
        if measurements is not None:
            self.last_measurements = measurements
        
        if not hasattr(self, 'last_measurements') or not self.last_measurements:
            self._draw_background()
            if self.canvas:
                self.canvas.create_text(
                    self.center_x, self.center_y + 120,
                    text="📡 No active objects detected\nPoint camera at objects to see them here",
                    fill="#7f8ea3",
                    font=("Segoe UI", 10),
                    justify="center"
                )
            return

        self._draw_background()
        
        if not hasattr(self, 'center_x'):
            return

        center_x = self.center_x
        center_y = self.center_y
        max_radius = 180
        min_radius = 80
        
        measurements_list = self.last_measurements[:10]  # Max 10 nodes
        
        for i, m in enumerate(measurements_list):
            # Calculate angle with some spread
            angle = (2 * math.pi / max(1, len(measurements_list))) * i
            angle += self.animation_angle * math.pi / 180 * 0.5
            
            radius = min_radius + (max_radius - min_radius) * (i / max(1, len(measurements_list) - 1))
            
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            
            label = str(m.get("object_name", "Unknown"))
            conf = m.get("confidence", 0)
            acc = str(m.get("accuracy", "N/A"))
            width = m.get("width_cm", "?")
            height = m.get("height_cm", "?")
            
            # Color based on accuracy
            if acc == "High":
                node_color = "#22c55e"
                node_bg = "#0a2a1a"
            elif acc == "Medium":
                node_color = "#f59e0b"
                node_bg = "#2a1a0a"
            elif acc == "Estimated":
                node_color = "#00e5ff"
                node_bg = "#0a1a2a"
            else:
                node_color = "#ef4444"
                node_bg = "#2a0a0a"
            
            # Draw connection line
            self.canvas.create_line(center_x, center_y, x, y, fill=node_color, width=2, dash=(4, 2))
            
            # Draw node
            self.canvas.create_oval(x - 28, y - 28, x + 28, y + 28, fill=node_bg, outline=node_color, width=2)
            
            # Node label
            short_label = label[:10] + ".." if len(label) > 12 else label
            self.canvas.create_text(x, y - 12, text=short_label, fill="#e6faff", 
                                    font=("Segoe UI", 9, "bold"))
            
            # Confidence and size
            self.canvas.create_text(x, y + 2, text=f"{int(conf * 100)}%", 
                                    fill=node_color, font=("Segoe UI", 8, "bold"))
            
            # Dimensions if available
            if width != "?" and height != "?":
                dim_text = f"{width}×{height}"
                self.canvas.create_text(x, y + 16, text=dim_text, 
                                        fill="#7f8ea3", font=("Segoe UI", 7))
            
            # Pulse effect for high confidence
            if conf > 0.8:
                pulse = 3 + int(abs(math.sin(self.animation_angle * math.pi / 180)) * 2)
                self.canvas.create_oval(x - 32 - pulse, y - 32 - pulse, 
                                        x + 32 + pulse, y + 32 + pulse,
                                        outline=node_color, width=1, dash=(2, 2))

        # Update info label
        self.info_label.config(
            text=f"📊 Active Objects: {len(measurements_list)} | "
                 f"🟢 High Acc: {sum(1 for m in measurements_list if m.get('accuracy') == 'High')} | "
                 f"🟡 Medium: {sum(1 for m in measurements_list if m.get('accuracy') == 'Medium')} | "
                 f"🔴 Low: {sum(1 for m in measurements_list if m.get('accuracy') == 'Low')}"
        )

    def refresh(self):
        """Manually refresh the map"""
        if hasattr(self, 'last_measurements'):
            self.update_nodes(self.last_measurements)

    def close(self):
        """Close the map window"""
        if self.window and self.window.winfo_exists():
            self.window.destroy()