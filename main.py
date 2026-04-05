"""
main.py - Main entry point for AI Measure Pro V5.1
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_dependencies():
    missing = []
    packages = {
        'cv2': 'opencv-python',
        'ultralytics': 'ultralytics',
        'PIL': 'pillow',
        'numpy': 'numpy',
        'mediapipe': 'mediapipe',
        'reportlab': 'reportlab',
        'pyttsx3': 'pyttsx3'
    }
    for module, package in packages.items():
        try:
            if module == 'cv2':
                import cv2
            elif module == 'PIL':
                import PIL
            else:
                __import__(module)
            print(f"[OK] {package}")
        except ImportError:
            missing.append(package)
            print(f"[MISSING] {package}")
    if missing:
        print("\n Install: pip install " + " ".join(missing))
        return False
    print("\n All dependencies OK!")
    return True

def create_folders():
    for folder in ["models", "screenshots", "reports", "exports"]:
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"[CREATED] {folder}")

def download_model():
    model_path = "models/yolov8n.pt"
    if not os.path.exists(model_path):
        print("\n Downloading YOLOv8 model...")
        try:
            from ultralytics import YOLO
            model = YOLO("yolov8n.pt")
            model.export(format="pt")
            import shutil
            if os.path.exists("yolov8n.pt"):
                shutil.move("yolov8n.pt", model_path)
            print("[OK] Model downloaded")
        except Exception as e:
            print(f"[ERROR] {e}")
            return False
    else:
        print("[OK] YOLO model found")
    return True

def main():
    print("=" * 50)
    print(" AI Measure Pro V5.1")
    print("=" * 50)
    if not check_dependencies():
        return
    create_folders()
    if not download_model():
        return
    try:
        import tkinter as tk
        from app import AIMeasureV5App
        root = tk.Tk()
        app = AIMeasureV5App(root)
        root.protocol("WM_DELETE_WINDOW", app.on_closing)
        root.mainloop()
    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    main()