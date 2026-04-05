import csv
import os
from datetime import datetime

class SOCLogger:
    def __init__(self, log_file="soc_events.csv"):
        self.log_file = log_file
        self._ensure_file()
        self.event_count = 0

    def _ensure_file(self):
        if not os.path.exists(self.log_file):
            with open(self.log_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Timestamp", "Event ID", "Event Type", "Severity",
                    "Object", "Confidence", "Mode", "Details"
                ])

    def _get_next_id(self):
        self.event_count += 1
        return f"EVT{self.event_count:06d}"

    def log_event(self, event_type, severity, obj_name="", confidence="", mode="", details=""):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        event_id = self._get_next_id()
        with open(self.log_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([now, event_id, event_type, severity, obj_name, confidence, mode, details])
        print(f"[SOC] [{event_id}] {event_type} | {severity} | {obj_name}")
        return event_id

    def log_detection(self, measurement, mode="EST"):
        if not measurement:
            return
        conf = measurement.get("confidence", 0)
        obj_name = measurement.get("object_name", "Unknown")
        accuracy = measurement.get("accuracy", "N/A")
        if conf >= 0.85:
            severity = "INFO"
        elif conf >= 0.60:
            severity = "LOW"
        elif conf >= 0.40:
            severity = "MEDIUM"
        else:
            severity = "HIGH"
        details = (f"Width={measurement.get('width_cm')}, Height={measurement.get('height_cm')}, "
                  f"Accuracy={accuracy}, TrackID={measurement.get('object_id')}")
        return self.log_event("DETECTION", severity, obj_name, f"{conf:.0%}", mode, details)

    def log_barcode(self, barcode_data, product_name="", mode="BARCODE"):
        details = f"Barcode={barcode_data}"
        if product_name:
            details += f", Product={product_name}"
        return self.log_event("BARCODE_SCAN", "INFO", product_name or "Unknown Product", "N/A", mode, details)

    def log_calibration(self, status, pixels_per_cm=None):
        severity = "INFO" if status == "SUCCESS" else "LOW"
        details = status
        if pixels_per_cm:
            details += f" | Pixels/cm: {pixels_per_cm:.1f}"
        return self.log_event("CALIBRATION", severity, "Reference Card", "N/A", "ACC", details)

    def log_export(self, export_type, file_path=""):
        details = f"{export_type} export completed"
        if file_path:
            details += f" | Path: {file_path}"
        return self.log_event("EXPORT", "INFO", export_type, "N/A", "SYSTEM", details)

    def log_save(self, measurement_count):
        return self.log_event("SAVE_MEASUREMENT", "INFO", "Measurement", "N/A", "SYSTEM", f"Saved {measurement_count} measurement(s) to CSV")

    def log_screenshot(self, file_path):
        return self.log_event("SCREENSHOT", "INFO", "Camera Frame", "N/A", "SYSTEM", f"Screenshot saved: {file_path}")

    def log_error(self, error_type, error_message):
        return self.log_event("ERROR", "HIGH", error_type, "N/A", "SYSTEM", error_message)

    def log_system_start(self):
        return self.log_event("SYSTEM_START", "INFO", "AI Measure Pro V5", "N/A", "SYSTEM", "System initialized successfully")

    def log_system_stop(self):
        return self.log_event("SYSTEM_STOP", "INFO", "AI Measure Pro V5", "N/A", "SYSTEM", "System shutdown")

    def get_statistics(self):
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