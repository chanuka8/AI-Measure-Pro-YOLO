"""
config.py - Central configuration for AI Measure Pro V5
"""

import os

# Measurement Settings
UNITS = "cm"  # "cm" or "inches"
CONVERSION_FACTOR = 2.54

# Voice Settings
VOICE_ENABLED = True
VOICE_RATE = 150
VOICE_VOLUME = 0.9

# Camera Settings
CAMERA_ID = 0
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720
MULTI_CAMERA_ENABLED = False
SECOND_CAMERA_ID = 1

# Tracking Settings
TRACKING_ENABLED = True
MAX_TRACKING_AGE = 30
MAX_MEASUREMENT_HISTORY = 20

# AR Guide Settings
AR_GUIDE_ENABLED = True
AR_GUIDE_OPACITY = 0.6
CALIBRATION_GUIDE_TEXT = "Show bank card here"

# Cloud Backup Settings
CLOUD_ENABLED = False
CLOUD_PROVIDER = "google_drive"
DROPBOX_TOKEN = ""
GOOGLE_CREDENTIALS_PATH = "credentials.json"

# Export Settings
AUTO_EXPORT_EXCEL = False
EXPORT_FOLDER = "exports"

# Barcode Settings
BARCODE_ENABLED = True
BARCODE_DATABASE = "product_dimensions.json"

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCREENSHOT_FOLDER = os.path.join(BASE_DIR, "screenshots")
REPORTS_FOLDER = os.path.join(BASE_DIR, "reports")
EXPORTS_FOLDER = os.path.join(BASE_DIR, "exports")
MODELS_FOLDER = os.path.join(BASE_DIR, "models")

# State Management
STATE_FILE = "app_state.json"