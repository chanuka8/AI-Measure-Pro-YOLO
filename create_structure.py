"""
Create project structure and necessary folders
Run this first to set up the project
"""

import os

def create_project_structure():
    """Create all necessary folders and files"""
    
    # Create folders
    folders = ["models", "screenshots"]
    for folder in folders:
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"✓ Created folder: {folder}")
        else:
            print(f"✓ Folder exists: {folder}")
    
    # Check if model exists
    model_path = "models/yolov8n.pt"
    if not os.path.exists(model_path):
        print("\n⚠️ YOLO model not found. It will be downloaded automatically when you run app.py")
        print("  (First download may take a few minutes)")
    else:
        print(f"✓ YOLO model found: {model_path}")
    
    print("\n✅ Project structure ready!")
    print("\nNext steps:")
    print("1. Install requirements: pip install -r requirements.txt")
    print("2. Run application: python app.py")

if __name__ == "__main__":
    create_project_structure()