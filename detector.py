from ultralytics import YOLO

class YOLODetector:
    def __init__(self, model_path="models/yolov8n.pt", confidence_threshold=0.40):
        self.model = YOLO(model_path)
        self.confidence_threshold = confidence_threshold

    def detect(self, frame):
        detections = []
        results = self.model(frame, verbose=False)
        for result in results:
            boxes = result.boxes
            names = result.names
            for box in boxes:
                conf = float(box.conf[0])
                if conf < self.confidence_threshold:
                    continue
                cls_id = int(box.cls[0])
                label = names[cls_id]
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                detections.append({
                    "label": label,
                    "confidence": round(conf, 2),
                    "bbox": (x1, y1, x2, y2)
                })
        return detections