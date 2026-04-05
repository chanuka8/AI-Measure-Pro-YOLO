"""
measurement_mode.py - Measurement Mode for AI Measure Pro
"""

import cv2
import numpy as np
from datetime import datetime


class MeasurementMode:
    def __init__(self):
        self.mode_active = True
        self.measuring = False
        self.start_point = None
        self.end_point = None
        self.measurements = []
        self.temp_line = None
        self.pixel_to_cm_ratio = 0.1
        self.calibrated = False
        self.measurement_color = (0, 255, 255)
        self.text_color = (255, 255, 255)
        
    def set_calibration(self, pixels_per_cm):
        """Update pixel to cm ratio from calibration"""
        if pixels_per_cm and pixels_per_cm > 0:
            self.pixel_to_cm_ratio = 1.0 / pixels_per_cm
            self.calibrated = True
            return True
        return False
    
    def start_measurement(self, pos):
        """Start measurement at position"""
        if not self.mode_active:
            return
        self.measuring = True
        self.start_point = pos
        self.end_point = pos
        
    def update_measurement(self, pos):
        """Update measurement end point"""
        if not self.measuring:
            return
        self.end_point = pos
        self.temp_line = (self.start_point, self.end_point)
        
    def stop_measurement(self, pos):
        """Stop measurement and save"""
        if not self.measuring:
            return None
        
        self.end_point = pos
        self.temp_line = None
        
        if self.start_point and self.end_point:
            # Calculate distance
            dx = self.end_point[0] - self.start_point[0]
            dy = self.end_point[1] - self.start_point[1]
            distance_px = np.sqrt(dx**2 + dy**2)
            distance_cm = distance_px * self.pixel_to_cm_ratio
            
            # Calculate angle
            angle = np.degrees(np.arctan2(dy, dx))
            
            measurement = {
                "id": len(self.measurements) + 1,
                "start": self.start_point,
                "end": self.end_point,
                "distance_px": distance_px,
                "distance_cm": round(distance_cm, 2),
                "angle": round(angle, 1),
                "dx": dx,
                "dy": dy,
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }
            self.measurements.append(measurement)
            
            self.measuring = False
            self.start_point = None
            self.end_point = None
            
            return measurement
        
        self.measuring = False
        return None
    
    def cancel_measurement(self):
        """Cancel current measurement"""
        self.measuring = False
        self.start_point = None
        self.end_point = None
        self.temp_line = None
    
    def delete_last_measurement(self):
        """Delete the last measurement"""
        if self.measurements:
            self.measurements.pop()
            return True
        return False
    
    def clear_all_measurements(self):
        """Clear all measurements"""
        self.measurements = []
    
    def draw_measurement_ui(self, frame):
        """Draw measurement UI on frame"""
        if not self.mode_active:
            return frame
        
        h, w = frame.shape[:2]
        
        # Draw semi-transparent overlay for measurement mode indicator
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, h - 45), (w, h), (0, 100, 200), -1)
        cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)
        
        # Draw mode text
        if self.calibrated:
            calib_text = "CALIBRATED"
            calib_color = (0, 255, 0)
        else:
            calib_text = "NOT CALIBRATED"
            calib_color = (0, 0, 255)
        
        cv2.putText(frame, f"MEASUREMENT MODE - Click and drag to measure | {calib_text}", 
                   (10, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 200, 100), 2)
        
        # Draw measurement count
        cv2.putText(frame, f"Measurements: {len(self.measurements)}", 
                   (w - 180, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (100, 255, 200), 2)
        
        # Draw temp measurement line
        if self.temp_line and self.start_point and self.end_point:
            cv2.line(frame, self.start_point, self.end_point, self.measurement_color, 3)
            
            # Draw circles at start and end
            cv2.circle(frame, self.start_point, 6, (0, 255, 0), -1)
            cv2.circle(frame, self.end_point, 6, (0, 0, 255), -1)
            
            # Calculate and display distance
            dx = self.end_point[0] - self.start_point[0]
            dy = self.end_point[1] - self.start_point[1]
            distance_px = np.sqrt(dx**2 + dy**2)
            distance_cm = distance_px * self.pixel_to_cm_ratio
            
            # Display distance at midpoint
            mid_x = (self.start_point[0] + self.end_point[0]) // 2
            mid_y = (self.start_point[1] + self.end_point[1]) // 2
            
            text = f"{distance_cm:.1f} cm"
            text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
            
            # Draw background for text
            cv2.rectangle(frame, (mid_x - text_size[0]//2 - 5, mid_y - 22),
                         (mid_x + text_size[0]//2 + 5, mid_y + 8), (0, 0, 0), -1)
            cv2.putText(frame, text, (mid_x - text_size[0]//2, mid_y - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.measurement_color, 2)
            
            # Draw angle
            angle = np.degrees(np.arctan2(dy, dx))
            angle_text = f"{angle:.0f} deg"
            angle_size = cv2.getTextSize(angle_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
            cv2.putText(frame, angle_text, (mid_x - angle_size//2, mid_y + 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        return frame
    
    def draw_saved_measurements(self, frame):
        """Draw all saved measurements on frame"""
        for i, m in enumerate(self.measurements[-15:]):  # Show last 15 measurements
            start = m["start"]
            end = m["end"]
            distance_cm = m["distance_cm"]
            
            # Color based on measurement age
            alpha = 0.5 + (i / max(1, len(self.measurements))) * 0.3
            color = (0, int(200 * alpha), int(255 * alpha))
            
            # Draw line
            cv2.line(frame, start, end, color, 2)
            
            # Draw circles
            cv2.circle(frame, start, 4, (0, 200, 0), -1)
            cv2.circle(frame, end, 4, (0, 0, 200), -1)
            
            # Draw distance text
            mid_x = (start[0] + end[0]) // 2
            mid_y = (start[1] + end[1]) // 2
            
            text = f"{distance_cm} cm"
            text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)[0]
            
            # Draw background for better visibility
            cv2.rectangle(frame, (mid_x - text_size[0]//2 - 3, mid_y - 15),
                         (mid_x + text_size[0]//2 + 3, mid_y + 5), (0, 0, 0, 0.5), -1)
            cv2.putText(frame, text, (mid_x - text_size[0]//2, mid_y - 3),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 200, 100), 1)
            
            # Draw measurement number for first few
            if i < 5:
                num_text = f"#{m['id']}"
                cv2.putText(frame, num_text, (start[0] - 20, start[1] - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
        
        return frame
    
    def draw_calibration_status(self, frame):
        """Draw calibration status indicator"""
        h, w = frame.shape[:2]
        
        if self.calibrated:
            status_text = "CALIBRATED"
            status_color = (0, 255, 0)
            bg_color = (0, 100, 0)
        else:
            status_text = "NEED CALIBRATION"
            status_color = (0, 0, 255)
            bg_color = (100, 0, 0)
        
        # Draw status indicator at top right
        text_size = cv2.getTextSize(status_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
        x = w - text_size[0] - 15
        y = 25
        
        cv2.rectangle(frame, (x - 5, y - 20), (x + text_size[0] + 5, y + 5), bg_color, -1)
        cv2.rectangle(frame, (x - 5, y - 20), (x + text_size[0] + 5, y + 5), status_color, 1)
        cv2.putText(frame, status_text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)
        
        return frame
    
    def get_measurement_stats(self):
        """Get statistics of all measurements"""
        if not self.measurements:
            return None
        
        distances = [m["distance_cm"] for m in self.measurements]
        
        return {
            "count": len(self.measurements),
            "min": min(distances),
            "max": max(distances),
            "avg": sum(distances) / len(distances),
            "total": sum(distances)
        }
    
    def set_mode(self, active):
        """Set measurement mode active/inactive"""
        self.mode_active = active
        if not active:
            self.cancel_measurement()
    
    def get_status_text(self):
        """Get current mode status text"""
        if self.mode_active:
            calib_status = "Calibrated" if self.calibrated else "Not Calibrated"
            return f"MEASUREMENT MODE | {calib_status} | Measurements: {len(self.measurements)}"
        return "MEASUREMENT MODE OFF"
    
    def get_last_measurement(self):
        """Get last measurement"""
        if self.measurements:
            return self.measurements[-1]
        return None
    
    def export_measurements(self):
        """Export measurements to list"""
        return self.measurements.copy()