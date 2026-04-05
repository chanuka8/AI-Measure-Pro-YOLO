"""
drawing_mode.py - Air Drawing Module for AI Measure Pro V6.0
"""

import os
import cv2
import numpy as np
import mediapipe as mp
from datetime import datetime


class AirDrawing:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )
        self.mp_draw = mp.solutions.drawing_utils

        self.canvas = None
        self.draw_color = (0, 255, 0)  # Green default (BGR)
        self.brush_thickness = 5
        self.eraser_thickness = 45

        self.prev_points = {}
        self.annotation_mode = False
        self.last_gesture = "idle"
        self.save_folder = "screenshots"

        os.makedirs(self.save_folder, exist_ok=True)

    def init_canvas(self, frame):
        if self.canvas is None or self.canvas.shape != frame.shape:
            self.canvas = np.zeros_like(frame)

    def clear_canvas(self):
        if self.canvas is not None:
            self.canvas[:] = 0

    def save_canvas_image(self):
        if self.canvas is None:
            return None
        if not np.any(self.canvas):
            return None
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(self.save_folder, f"drawing_{ts}.png")
        ok = cv2.imwrite(path, self.canvas)
        return path if ok else None

    def set_annotation_mode(self, enabled: bool):
        self.annotation_mode = enabled

    def draw_toolbar(self, frame):
        h, w = frame.shape[:2]
        toolbar_height = 90
        color_width = w // 9
        
        # Toolbar background
        cv2.rectangle(frame, (0, 0), (w, toolbar_height), (35, 35, 35), -1)
        
        # Color definitions
        colors = [
            (255, 0, 0),    # BLUE
            (0, 255, 0),    # GREEN
            (0, 0, 255),    # RED
            (0, 255, 255),  # YELLOW
            (255, 0, 255),  # PURPLE
            (255, 255, 0),  # CYAN
            (0, 165, 255),  # ORANGE
            (255, 255, 255),# WHITE
            (50, 50, 50)    # ERASE
        ]
        names = ["BLUE", "GREEN", "RED", "YELLOW", "PURPLE", "CYAN", "ORANGE", "WHITE", "ERASE"]
        
        for i, (color, name) in enumerate(zip(colors, names)):
            x1 = i * color_width
            x2 = (i + 1) * color_width
            
            # Draw color box
            cv2.rectangle(frame, (x1 + 5, 5), (x2 - 5, toolbar_height - 10), color, -1)
            
            # Highlight selected color
            if (self.draw_color[0] == color[0] and 
                self.draw_color[1] == color[1] and 
                self.draw_color[2] == color[2]):
                cv2.rectangle(frame, (x1 + 2, 2), (x2 - 2, toolbar_height - 7), (255, 255, 255), 3)
            else:
                cv2.rectangle(frame, (x1 + 2, 2), (x2 - 2, toolbar_height - 7), (100, 100, 100), 1)
            
            # Add text
            text_color = (0, 0, 0) if name in ["YELLOW", "WHITE"] else (255, 255, 255)
            text_size = cv2.getTextSize(name, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)[0]
            text_x = x1 + (color_width - text_size[0]) // 2
            text_y = toolbar_height - 12
            cv2.putText(frame, name, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, text_color, 1)
        
        # Mode indicator
        mode_text = "ANNOTATION" if self.annotation_mode else "DRAW"
        cv2.putText(frame, f"MODE: {mode_text}", (w - 150, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 255, 200), 2)
        
        # Instruction
        cv2.putText(frame, "USE TWO FINGERS TO SELECT COLOR", (w // 2 - 150, toolbar_height - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)

    def _finger_up(self, lm_list, tip_id, pip_id):
        if len(lm_list) <= max(tip_id, pip_id):
            return False
        return lm_list[tip_id][1] < lm_list[pip_id][1]

    def _detect_gesture(self, lm_list):
        if len(lm_list) < 21:
            return "unknown"
        
        index_up = self._finger_up(lm_list, 8, 6)
        middle_up = self._finger_up(lm_list, 12, 10)
        ring_up = self._finger_up(lm_list, 16, 14)
        pinky_up = self._finger_up(lm_list, 20, 18)
        
        fingers_up = sum([index_up, middle_up, ring_up, pinky_up])
        
        if index_up and not middle_up and not ring_up and not pinky_up:
            return "draw"
        elif index_up and middle_up and not ring_up and not pinky_up:
            return "select"
        elif index_up and middle_up and ring_up and pinky_up:
            return "clear"
        elif pinky_up and not index_up and not middle_up and not ring_up:
            return "save"
        elif fingers_up == 0:
            return "idle"
        else:
            return "other"

    def _handle_toolbar_selection(self, x, y, frame):
        """Handle toolbar button selection based on position"""
        h, w = frame.shape[:2]
        toolbar_height = 90
        
        if y > toolbar_height:
            return None
        
        color_width = w // 9
        button_index = x // color_width
        
        if button_index < 0:
            button_index = 0
        elif button_index > 8:
            button_index = 8
        
        colors = [
            (255, 0, 0), (0, 255, 0), (0, 0, 255), (0, 255, 255),
            (255, 0, 255), (255, 255, 0), (0, 165, 255), (255, 255, 255), (50, 50, 50)
        ]
        color_names = [
            "BLUE", "GREEN", "RED", "YELLOW", 
            "PURPLE", "CYAN", "ORANGE", "WHITE", "ERASE"
        ]
        
        self.draw_color = colors[button_index]
        return f"{color_names[button_index]} selected"

    def annotate_suspicious_objects(self, frame, detections):
        for det in detections:
            conf = float(det.get("confidence", 0))
            label = str(det.get("label", "")).lower()
            x1, y1, x2, y2 = det.get("bbox", (0, 0, 0, 0))
            
            suspicious = False
            reason = ""
            
            if conf < 0.50:
                suspicious = True
                reason = "Low confidence"
            elif any(k in label for k in ["cell phone", "knife", "scissors", "remote"]):
                suspicious = True
                reason = f"Suspicious: {label[:15]}"
            
            if suspicious:
                cx = (x1 + x2) // 2
                cy = (y1 + y2) // 2
                radius = max((x2 - x1) // 2, (y2 - y1) // 2) + 10
                
                cv2.circle(frame, (cx, cy), radius, (0, 0, 255), 3)
                cv2.putText(frame, f"⚠️ {reason}", (x1, max(20, y1 - 12)),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        return frame

    def merge_canvas_with_frame(self, frame):
        if self.canvas is None:
            return frame
        
        gray_canvas = cv2.cvtColor(self.canvas, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray_canvas, 20, 255, cv2.THRESH_BINARY)
        mask_inv = cv2.bitwise_not(mask)
        
        mask_inv_3ch = cv2.cvtColor(mask_inv, cv2.COLOR_GRAY2BGR)
        mask_3ch = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
        
        frame_bg = cv2.bitwise_and(frame, mask_inv_3ch)
        canvas_fg = cv2.bitwise_and(self.canvas, mask_3ch)
        
        result = cv2.add(frame_bg, canvas_fg)
        return result

    def process(self, frame):
        if frame is None:
            return frame, None
        
        self.init_canvas(frame)
        self.draw_toolbar(frame)
        
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb)
        
        status_message = None
        
        if results.multi_hand_landmarks:
            for hand_idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                self.mp_draw.draw_landmarks(
                    frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS,
                    self.mp_draw.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=3),
                    self.mp_draw.DrawingSpec(color=(0, 0, 255), thickness=2)
                )
                
                lm_list = []
                h, w, _ = frame.shape
                for lm in hand_landmarks.landmark:
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    lm_list.append((cx, cy))
                
                if len(lm_list) < 21:
                    continue
                
                x_index, y_index = lm_list[8]
                
                cv2.circle(frame, (x_index, y_index), 12, (0, 255, 255), -1)
                cv2.circle(frame, (x_index, y_index), 14, (255, 255, 255), 2)
                
                gesture = self._detect_gesture(lm_list)
                self.last_gesture = gesture
                
                if gesture == "select":
                    self.prev_points[hand_idx] = None
                    msg = self._handle_toolbar_selection(x_index, y_index, frame)
                    if msg:
                        status_message = msg
                    cv2.putText(frame, "🎨 SELECT", (x_index - 40, y_index - 20), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                    
                elif gesture == "draw":
                    if hand_idx not in self.prev_points or self.prev_points[hand_idx] is None:
                        self.prev_points[hand_idx] = (x_index, y_index)
                    
                    px, py = self.prev_points[hand_idx]
                    
                    if y_index > 90:
                        thickness = self.eraser_thickness if self.draw_color == (0, 0, 0) else self.brush_thickness
                        cv2.line(self.canvas, (px, py), (x_index, y_index), self.draw_color, thickness)
                        cv2.circle(self.canvas, (x_index, y_index), thickness // 2, self.draw_color, -1)
                    
                    self.prev_points[hand_idx] = (x_index, y_index)
                    cv2.putText(frame, "✏ DRAWING", (x_index - 40, y_index - 20), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    
                elif gesture == "clear":
                    self.clear_canvas()
                    self.prev_points[hand_idx] = None
                    status_message = "Canvas cleared"
                    cv2.putText(frame, "🗑 CLEARED", (x_index - 40, y_index - 20), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                    
                elif gesture == "save":
                    path = self.save_canvas_image()
                    self.prev_points[hand_idx] = None
                    status_message = f"Saved: {path}" if path else "Save failed"
                    cv2.putText(frame, "💾 SAVED", (x_index - 35, y_index - 20), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                    
                else:
                    self.prev_points[hand_idx] = None
        else:
            cv2.putText(frame, "🖐️ NO HAND - Show your hand to draw", (10, 120), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
        
        if self.last_gesture == "draw":
            cv2.putText(frame, "✏ DRAWING MODE - Move finger to draw", (10, 150), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        elif self.last_gesture == "select":
            cv2.putText(frame, "🎨 SELECT MODE - Point at color panel", (10, 150), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
        elif self.last_gesture == "idle":
            cv2.putText(frame, "✋ IDLE - Raise index finger to draw", (10, 150), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        frame = self.merge_canvas_with_frame(frame)
        
        return frame, status_message