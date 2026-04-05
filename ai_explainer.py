from datetime import datetime

class AIExplainer:
    def __init__(self):
        self.last_explanation = "System ready. Waiting for camera input."
        self.explanation_history = []

    def build_explanation(self, measurement: dict, mode: str = "EST"):
        if not measurement:
            self.last_explanation = "No object detected yet. Show an object to the camera."
            return self.last_explanation
        name = measurement.get("object_name", "Unknown object")
        conf = measurement.get("confidence", 0)
        width = measurement.get("width_cm")
        height = measurement.get("height_cm")
        accuracy = measurement.get("accuracy", "N/A")
        extra = measurement.get("extra", "")
        conf_pct = int(conf * 100) if isinstance(conf, (float, int)) else 0
        if width is None or height is None:
            size_text = "Size could not be calculated from the current frame."
        else:
            if accuracy == "Estimated" or mode == "EST":
                size_text = f"Estimated dimensions: width approx {width} cm, height approx {height} cm."
            else:
                size_text = f"Accurate measurements: width = {width} cm, height = {height} cm."
        if "person" in name.lower() or "" in name:
            role_text = "This detection used MediaPipe pose estimation for body measurements."
            if height and height > 100:
                role_text += f" Detected person height is {height} cm."
            else:
                role_text += " Full body visibility is recommended for accurate height."
        elif "phone" in name.lower() or "" in name:
            role_text = "Smartphone detected. Width and height measurements are auto-corrected for portrait orientation."
        elif "bottle" in name.lower() or "" in name:
            role_text = "Bottle detected. Height measurement is prioritized for vertical orientation."
        else:
            role_text = "This detection used bounding box measurement."
        if mode == "ACC":
            mode_text = " ACCURATE MODE: Calibration is active. Measurements are reliable within +-5-10%."
        else:
            mode_text = " ESTIMATED MODE: No calibration active. Show a bank card for accurate measurements."
        if accuracy == "High":
            acc_text = "High confidence measurement - multiple frames averaged."
        elif accuracy == "Medium":
            acc_text = "Medium confidence - hold object steady for better accuracy."
        elif accuracy == "Low":
            acc_text = "Low confidence - consider recalibrating or improving lighting."
        else:
            acc_text = f"Accuracy level: {accuracy}."
        extra_text = f" Note: {extra}" if extra else ""
        explanation = (
            f" {name} detected with {conf_pct}% confidence.\n"
            f" {size_text}\n"
            f" {role_text}\n"
            f" {mode_text}\n"
            f" {acc_text}{extra_text}"
        )
        self.last_explanation = explanation
        self.explanation_history.append({
            "timestamp": datetime.now(),
            "explanation": explanation,
            "object": name
        })
        while len(self.explanation_history) > 10:
            self.explanation_history.pop(0)
        return explanation

    def build_session_summary(self, measurements: list):
        if not measurements:
            return "No detections were saved in this session."
        total = len(measurements)
        persons = sum(1 for m in measurements if "person" in str(m.get("object_name", "")).lower() or "" in str(m.get("object_name", "")))
        phones = sum(1 for m in measurements if "phone" in str(m.get("object_name", "")).lower() or "" in str(m.get("object_name", "")))
        bottles = sum(1 for m in measurements if "bottle" in str(m.get("object_name", "")).lower() or "" in str(m.get("object_name", "")))
        objects = total - persons
        avg_conf = sum(m.get("confidence", 0) for m in measurements) / total if total > 0 else 0
        high_acc = sum(1 for m in measurements if m.get("accuracy") == "High")
        med_acc = sum(1 for m in measurements if m.get("accuracy") == "Medium")
        low_acc = sum(1 for m in measurements if m.get("accuracy") == "Low")
        est_acc = sum(1 for m in measurements if m.get("accuracy") == "Estimated")
        return (
            f" Session Summary ({datetime.now().strftime('%H:%M:%S')})\n"
            f"\n"
            f" Total Detections: {total}\n"
            f" Persons: {persons} | Phones: {phones} | Bottles: {bottles} | Other: {objects}\n"
            f" Average Confidence: {avg_conf:.0%}\n"
            f" Accuracy Distribution: High={high_acc}, Medium={med_acc}, Low={low_acc}, Estimated={est_acc}\n"
            f""
        )

    def get_last_explanation(self):
        return self.last_explanation