"""
soc_logger.py - Cyber-style SOC Event Logger
Logs all system events for security and audit purposes.
"""

import csv
import os
from datetime import datetime


class SOCLogger:
    def __init__(self, log_file="soc_events.csv"):
        self.log_file = log_file
        self._ensure_file()
        self.event_count = 0

    def _ensure_file(self):
        """Create log file with headers if not exists"""
        if not os.path.exists(self.log_file):
            with open(self.log_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Timestamp",
                    "Event ID",
                    "Event Type",
                    "Severity",
                    "Object",
                    "Confidence",
                    "Mode",
                    "Details"
                ])

    def _get_next_id(self):
        """Generate sequential event ID"""
        self.event_count += 1
        return f"EVT{self.event_count:06d}"

    def log_event(self, event_type, severity, obj_name="", confidence="", mode="", details=""):
        """Log a system event"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        event_id = self._get_next_id()
        
        with open(self.log_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                now,
                event_id,
                event_type,
                severity,
                obj_name,
                confidence,
                mode,
                details
            ])
        
        # Also print to console for real-time monitoring
        print(f"[SOC] [{event_id}] {event_type} | {severity} | {obj_name}")
        return event_id

    def log_detection(self, measurement, mode="EST"):
        """Log object detection event"""
        if not measurement:
            return

        conf = measurement.get("confidence", 0)
        obj_name = measurement.get("object_name", "Unknown")
        accuracy = measurement.get("accuracy", "N/A")

        # Determine severity based on confidence
        if conf >= 0.85:
            severity = "INFO"
        elif conf >= 0.60:
            severity = "LOW"
        elif conf >= 0.40:
            severity = "MEDIUM"
        else:
            severity = "HIGH"

        details = (
            f"Width={measurement.get('width_cm')}, "
            f"Height={measurement.get('height_cm')}, "
            f"Accuracy={accuracy}, "
            f"TrackID={measurement.get('object_id')}"
        )

        return self.log_event(
            event_type="DETECTION",
            severity=severity,
            obj_name=obj_name,
            confidence=f"{conf:.0%}",
            mode=mode,
            details=details
        )

    def log_barcode(self, barcode_data, product_name="", mode="BARCODE"):
        """Log barcode scan event"""
        details = f"Barcode={barcode_data}"
        if product_name:
            details += f", Product={product_name}"

        return self.log_event(
            event_type="BARCODE_SCAN",
            severity="INFO",
            obj_name=product_name or "Unknown Product",
            confidence="N/A",
            mode=mode,
            details=details
        )

    def log_calibration(self, status, pixels_per_cm=None):
        """Log calibration event"""
        severity = "INFO" if status == "SUCCESS" else "LOW"
        details = status
        if pixels_per_cm:
            details += f" | Pixels/cm: {pixels_per_cm:.1f}"
        
        return self.log_event(
            event_type="CALIBRATION",
            severity=severity,
            obj_name="Reference Card",
            confidence="N/A",
            mode="ACC",
            details=details
        )

    def log_export(self, export_type, file_path=""):
        """Log export event"""
        details = f"{export_type} export completed"
        if file_path:
            details += f" | Path: {file_path}"
        
        return self.log_event(
            event_type="EXPORT",
            severity="INFO",
            obj_name=export_type,
            confidence="N/A",
            mode="SYSTEM",
            details=details
        )

    def log_save(self, measurement_count):
        """Log save measurement event"""
        return self.log_event(
            event_type="SAVE_MEASUREMENT",
            severity="INFO",
            obj_name="Measurement",
            confidence="N/A",
            mode="SYSTEM",
            details=f"Saved {measurement_count} measurement(s) to CSV"
        )

    def log_screenshot(self, file_path):
        """Log screenshot capture"""
        return self.log_event(
            event_type="SCREENSHOT",
            severity="INFO",
            obj_name="Camera Frame",
            confidence="N/A",
            mode="SYSTEM",
            details=f"Screenshot saved: {file_path}"
        )

    def log_error(self, error_type, error_message):
        """Log error event"""
        return self.log_event(
            event_type="ERROR",
            severity="HIGH",
            obj_name=error_type,
            confidence="N/A",
            mode="SYSTEM",
            details=error_message
        )

    def log_system_start(self):
        """Log system startup"""
        return self.log_event(
            event_type="SYSTEM_START",
            severity="INFO",
            obj_name="AI Measure Pro V5",
            confidence="N/A",
            mode="SYSTEM",
            details="System initialized successfully"
        )

    def log_system_stop(self):
        """Log system shutdown"""
        return self.log_event(
            event_type="SYSTEM_STOP",
            severity="INFO",
            obj_name="AI Measure Pro V5",
            confidence="N/A",
            mode="SYSTEM",
            details="System shutdown"
        )

    def get_statistics(self):
        """Get SOC log statistics"""
        if not os.path.exists(self.log_file):
            return {"total_events": 0, "by_type": {}, "by_severity": {}}
        
        try:
            import pandas as pd
            df = pd.read_csv(self.log_file)
            return {
                "total_events": len(df),
                "by_type": df['Event Type'].value_counts().to_dict(),
                "by_severity": df['Severity'].value_counts().to_dict(),
                "last_event": df.iloc[-1]['Timestamp'] if len(df) > 0 else None
            }
        except:
            return {"total_events": 0, "by_type": {}, "by_severity": {}}