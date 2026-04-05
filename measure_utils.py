import cv2
import numpy as np
from collections import deque

REFERENCE_WIDTH_CM = 8.56
_calib_buffer = deque(maxlen=15)
_meas_buffer = {}

CLASS_SIZE_PRIORS = {
    "cell phone": (7.2, 15.0),
    "cellphone": (7.2, 15.0),
    "phone": (7.2, 15.0),
    "mobile phone": (7.2, 15.0),
    "bottle": (7.0, 24.0),
    "cup": (8.5, 10.0),
    "person": (45.0, 170.0),
    "book": (15.0, 22.0),
    "laptop": (32.0, 22.0),
    "keyboard": (45.0, 15.0),
    "mouse": (6.0, 11.0),
    "tv": (80.0, 45.0),
    "monitor": (55.0, 32.0),
}

PORTRAIT_OBJECTS = [
    "cell phone", "cellphone", "phone", "mobile phone",
    "bottle","Iphone", "cup", "person", "book", "remote", "mouse",
    "banana", "carrot", "toothbrush", "hair drier", "umbrella",
    "backpack", "vase", "wine glass", "mug", "water bottle"
]

LANDSCAPE_OBJECTS = [
    "laptop", "keyboard", "tv", "monitor", "pizza",
    "potted plant", "dining table", "refrigerator",
    "microwave", "oven", "toaster", "clock"
]

def order_points(pts):
    pts = np.array(pts, dtype="float32")
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect

def bbox_dimensions_from_points(points):
    rect = order_points(points)
    tl, tr, br, bl = rect
    width_pixels = np.linalg.norm(tr - tl)
    height_pixels = np.linalg.norm(bl - tl)
    return width_pixels, height_pixels

def find_reference_card(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (7, 7), 0)
    edged = cv2.Canny(blur, 40, 110)
    edged = cv2.dilate(edged, None, iterations=2)
    edged = cv2.erode(edged, None, iterations=1)
    cnts, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best_box = None
    best_area = 0
    for c in cnts:
        area = cv2.contourArea(c)
        if area < 3000:
            continue
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.025 * peri, True)
        if len(approx) == 4:
            box = approx.reshape(4, 2)
            wp, hp = bbox_dimensions_from_points(box)
            if wp == 0 or hp == 0:
                continue
            long_s = max(wp, hp)
            short_s = min(wp, hp)
            ratio = long_s / short_s if short_s > 0 else 0
            if 1.40 <= ratio <= 1.80:
                if area > best_area:
                    best_area = area
                    best_box = box
    return best_box

def calibrate_pixels_per_cm_from_card(frame):
    box = find_reference_card(frame)
    if box is None:
        return None, None
    wp, hp = bbox_dimensions_from_points(box)
    long_side = max(wp, hp)
    if long_side <= 0:
        return None, None
    raw_ppc = long_side / REFERENCE_WIDTH_CM
    _calib_buffer.append(raw_ppc)
    if len(_calib_buffer) < 5:
        return None, None
    smoothed_ppc = float(np.median(_calib_buffer))
    return smoothed_ppc, box

def reset_calibration_buffer():
    _calib_buffer.clear()
    _meas_buffer.clear()

def _smooth_values(label, width_val, height_val):
    if label not in _meas_buffer:
        _meas_buffer[label] = {"w": deque(maxlen=10), "h": deque(maxlen=10)}
    _meas_buffer[label]["w"].append(width_val)
    _meas_buffer[label]["h"].append(height_val)
    smooth_w = float(np.median(_meas_buffer[label]["w"]))
    smooth_h = float(np.median(_meas_buffer[label]["h"]))
    frames = len(_meas_buffer[label]["w"])
    return round(smooth_w, 2), round(smooth_h, 2), frames

def measure_bbox_cm(bbox, pixels_per_cm, label="object"):
    x1, y1, x2, y2 = bbox
    wp = max(1, x2 - x1)
    hp = max(1, y2 - y1)
    raw_w = wp / pixels_per_cm
    raw_h = hp / pixels_per_cm
    label_lower = label.lower()
    if "phone" in label_lower or label == "cell phone" or label == "cellphone":
        if raw_w > raw_h:
            raw_w, raw_h = raw_h, raw_w
        if raw_w > 10:
            raw_w = 7.2
        if raw_h < 12 or raw_h > 20:
            raw_h = 15.0
    elif "bottle" in label_lower:
        if raw_w > raw_h:
            raw_w, raw_h = raw_h, raw_w
    elif "person" in label_lower:
        if raw_w > raw_h:
            raw_w, raw_h = raw_h, raw_w
    smooth_w, smooth_h, frames = _smooth_values(label, raw_w, raw_h)
    if frames >= 8:
        note = "High"
    elif frames >= 4:
        note = "Medium"
    else:
        note = "Low"
    return round(smooth_w, 2), round(smooth_h, 2), note

def estimate_bbox_cm_without_calibration(bbox, label="object", frame_shape=None):
    x1, y1, x2, y2 = bbox
    wp = max(1, x2 - x1)
    hp = max(1, y2 - y1)
    aspect = wp / hp if hp > 0 else 1.0
    label_lower = label.lower()
    if "phone" in label_lower or label == "cell phone":
        prior_w, prior_h = 7.2, 15.0
        if aspect > 1.2:
            est_w = prior_w
            est_h = prior_w / aspect
        else:
            est_h = prior_h
            est_w = prior_h * aspect
        if est_w > est_h:
            est_w, est_h = est_h, est_w
        final_w, final_h = est_w, est_h
    elif "bottle" in label_lower:
        prior_w, prior_h = 7.0, 24.0
        if aspect > 1.0:
            est_w = prior_w
            est_h = prior_w / aspect
        else:
            est_h = prior_h
            est_w = prior_h * aspect
        if est_w > est_h:
            est_w, est_h = est_h, est_w
        final_w, final_h = est_w, est_h
    elif "person" in label_lower:
        prior_w, prior_h = 45.0, 170.0
        if aspect > 1.0:
            est_w = prior_w
            est_h = prior_w / aspect
        else:
            est_h = prior_h
            est_w = prior_h * aspect
        if est_w > est_h:
            est_w, est_h = est_h, est_w
        final_w, final_h = min(est_w, 60), max(est_h, 140)
    else:
        prior_w, prior_h = 15.0, 15.0
        if aspect >= 1.0:
            est_w = prior_w
            est_h = est_w / aspect
        else:
            est_h = prior_h
            est_w = est_h * aspect
        final_w, final_h = est_w, est_h
    smooth_w, smooth_h, _ = _smooth_values(f"est_{label}", final_w, final_h)
    return round(smooth_w, 2), round(smooth_h, 2), "Estimated"

def get_object_prior(label):
    label_lower = label.lower()
    for key, (pw, ph) in CLASS_SIZE_PRIORS.items():
        if key in label_lower:
            return pw, ph
    return 15.0, 15.0