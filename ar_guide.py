"""
ar_guide.py - Augmented Reality measurement guide overlay
"""

import cv2
import numpy as np


class ARGuide:
    def __init__(self, enabled=True):
        """
        Initialize AR guide
        
        Args:
            enabled: Whether AR guide is enabled
        """
        self.enabled = enabled
        self.calibration_complete = False
        self.guide_opacity = 0.6
        
    def draw_calibration_guide(self, frame, card_detected=False):
        """
        Draw calibration guide overlay
        
        Args:
            frame: Image frame
            card_detected: Whether bank card is detected
            
        Returns:
            Frame with overlay
        """
        if not self.enabled:
            return frame
        
        h, w = frame.shape[:2]
        overlay = frame.copy()
        
        if not card_detected:
            # Draw semi-transparent overlay
            alpha = self.guide_opacity
            cv2.rectangle(overlay, (50, 50), (w - 50, h - 50), (0, 0, 0), -1)
            cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
            
            # Draw card outline guide
            card_w = int(w * 0.3)
            card_h = int(card_w / 1.586)  # Credit card aspect ratio
            
            center_x = w // 2
            center_y = h // 2
            
            x1 = center_x - card_w // 2
            y1 = center_y - card_h // 2
            x2 = center_x + card_w // 2
            y2 = center_y + card_h // 2
            
            # Animated dashed rectangle
            for i in range(0, 4):
                offset = int(cv2.getTickCount() / 500) % 20
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)
            
            # Guide text
            text = "PLACE BANK CARD HERE"
            text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
            text_x = center_x - text_size[0] // 2
            text_y = y2 + 40
            
            cv2.putText(frame, text, (text_x, text_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            
            # Draw measuring tape animation
            self._draw_measuring_tape(frame, center_x, center_y, card_w, card_h)
        
        else:
            # Calibration success overlay
            cv2.putText(frame, "✓ CALIBRATION SUCCESS", (w // 2 - 150, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        
        return frame
    
    def _draw_measuring_tape(self, frame, cx, cy, width, height):
        """Draw animated measuring tape effect"""
        t = cv2.getTickCount() / 1000
        
        # Horizontal tape
        x1 = cx - width // 2
        x2 = cx + width // 2
        y = cy - height // 2 - 20
        
        for i in range(0, width, 10):
            offset = int((t * 100 + i) % 20)
            if offset < 10:
                cv2.line(frame, (x1 + i, y), (x1 + i, y + 10), (0, 255, 255), 1)
        
        # Vertical tape
        y1 = cy - height // 2
        y2 = cy + height // 2
        x = cx + width // 2 + 20
        
        for i in range(0, height, 10):
            offset = int((t * 100 + i) % 20)
            if offset < 10:
                cv2.line(frame, (x, y1 + i), (x + 10, y1 + i), (0, 255, 255), 1)
    
    def draw_measurement_guide(self, frame, bbox, dimensions):
        """
        Draw measurement guide for detected object
        
        Args:
            frame: Image frame
            bbox: Bounding box (x1, y1, x2, y2)
            dimensions: (width_cm, height_cm) tuple
        """
        if not self.enabled:
            return frame
        
        x1, y1, x2, y2 = bbox
        width_cm, height_cm = dimensions
        
        # Draw measurement lines with animations
        t = cv2.getTickCount() / 1000
        
        # Horizontal measurement line
        mid_y = y1 + (y2 - y1) // 2
        
        # Animated line
        progress = (t % 1.0)
        line_end = int(x1 + (x2 - x1) * progress)
        cv2.line(frame, (x1, mid_y), (line_end, mid_y), (100, 255, 100), 2)
        
        # Vertical measurement line
        mid_x = x1 + (x2 - x1) // 2
        line_end_y = int(y1 + (y2 - y1) * progress)
        cv2.line(frame, (mid_x, y1), (mid_x, line_end_y), (100, 200, 255), 2)
        
        # Dimension labels with background
        w_text = f"{width_cm} cm"
        h_text = f"{height_cm} cm"
        
        # Width label at bottom
        w_x = x1 + (x2 - x1) // 2 - 30
        w_y = y2 + 25
        
        cv2.rectangle(frame, (w_x - 5, w_y - 20), (w_x + 70, w_y + 5), (0, 0, 0), -1)
        cv2.putText(frame, w_text, (w_x, w_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 255, 100), 2)
        
        # Height label at side
        h_x = x2 + 15
        h_y = y1 + (y2 - y1) // 2 + 10
        
        cv2.rectangle(frame, (h_x - 5, h_y - 15), (h_x + 70, h_y + 10), (0, 0, 0), -1)
        cv2.putText(frame, h_text, (h_x, h_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 200, 255), 2)
        
        return frame
    
    def draw_distance_indicator(self, frame, distance_cm):
        """Draw distance from camera indicator"""
        if not self.enabled or not distance_cm:
            return frame
        
        h, w = frame.shape[:2]
        
        # Create distance bar
        bar_width = 200
        bar_height = 10
        bar_x = w - bar_width - 20
        bar_y = 20
        
        # Optimal distance is 50-100cm
        distance_pct = min(1.0, max(0, (100 - abs(distance_cm - 75)) / 75))
        
        # Draw bar background
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), (50, 50, 50), -1)
        
        # Draw fill
        fill_width = int(bar_width * distance_pct)
        color = (0, 255, 0) if 40 < distance_cm < 120 else (0, 165, 255)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill_width, bar_y + bar_height), color, -1)
        
        # Draw text
        cv2.putText(frame, f"Distance: {int(distance_cm)}cm", (bar_x, bar_y - 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        return frame