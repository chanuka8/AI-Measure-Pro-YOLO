import numpy as np
from collections import deque
from datetime import datetime

class ObjectTracker:
    def __init__(self, max_age=30, max_history=20, iou_threshold=0.3):
        self.tracks = {}
        self.next_id = 1
        self.max_age = max_age
        self.max_history = max_history
        self.iou_threshold = iou_threshold

    def calculate_iou(self, box1, box2):
        x1_1, y1_1, x2_1, y2_1 = box1
        x1_2, y1_2, x2_2, y2_2 = box2
        xi1 = max(x1_1, x1_2)
        yi1 = max(y1_1, y1_2)
        xi2 = min(x2_1, x2_2)
        yi2 = min(y2_1, y2_2)
        inter_area = max(0, xi2 - xi1) * max(0, yi2 - yi1)
        box1_area = (x2_1 - x1_1) * (y2_1 - y1_1)
        box2_area = (x2_2 - x1_2) * (y2_2 - y1_2)
        union_area = box1_area + box2_area - inter_area
        iou = inter_area / union_area if union_area > 0 else 0
        return iou

    def update(self, detections):
        for track_id in list(self.tracks.keys()):
            self.tracks[track_id]["age"] += 1
        matched_pairs = []
        for track_id, track in self.tracks.items():
            best_iou = 0
            best_det_idx = -1
            for i, det in enumerate(detections):
                iou = self.calculate_iou(track["bbox"], det["bbox"])
                if track["label"] == det["label"]:
                    iou *= 1.2
                if iou > best_iou and iou > self.iou_threshold:
                    best_iou = iou
                    best_det_idx = i
            if best_det_idx >= 0:
                matched_pairs.append((track_id, best_det_idx))
        used_detections = set()
        for track_id, det_idx in matched_pairs:
            det = detections[det_idx]
            track = self.tracks[track_id]
            track["bbox"] = det["bbox"]
            track["label"] = det["label"]
            track["confidence"] = det["confidence"]
            track["age"] = 0
            track["frames_seen"] += 1
            if "width_cm" in det and det["width_cm"]:
                track["measurements"].append({
                    "width": det["width_cm"], "height": det["height_cm"],
                    "confidence": det["confidence"], "timestamp": datetime.now()
                })
                while len(track["measurements"]) > self.max_history:
                    track["measurements"].pop(0)
            used_detections.add(det_idx)
        for i, det in enumerate(detections):
            if i not in used_detections:
                track_id = self.next_id
                self.next_id += 1
                self.tracks[track_id] = {
                    "id": track_id, "bbox": det["bbox"], "label": det["label"],
                    "confidence": det["confidence"], "age": 0, "frames_seen": 1,
                    "measurements": []
                }
                if "width_cm" in det and det["width_cm"]:
                    self.tracks[track_id]["measurements"].append({
                        "width": det["width_cm"], "height": det["height_cm"],
                        "confidence": det["confidence"], "timestamp": datetime.now()
                    })
        to_remove = []
        for track_id, track in self.tracks.items():
            if track["age"] > self.max_age:
                to_remove.append(track_id)
        for track_id in to_remove:
            del self.tracks[track_id]
        output = []
        for track_id, track in self.tracks.items():
            avg_width = None
            avg_height = None
            if track["measurements"]:
                widths = [m["width"] for m in track["measurements"] if m["width"]]
                heights = [m["height"] for m in track["measurements"] if m["height"]]
                if widths:
                    avg_width = round(np.median(widths), 2)
                if heights:
                    avg_height = round(np.median(heights), 2)
            output.append({
                "track_id": track_id, "label": track["label"], "confidence": track["confidence"],
                "bbox": track["bbox"], "width_cm": avg_width, "height_cm": avg_height,
                "frames_seen": track["frames_seen"], "measurement_count": len(track["measurements"])
            })
        return output

    def get_track_history(self, track_id):
        if track_id in self.tracks:
            return self.tracks[track_id]["measurements"]
        return []

    def get_all_tracks(self):
        return self.tracks

    def reset(self):
        self.tracks = {}
        self.next_id = 1