"""
multi_camera.py - Multi-camera support for stereo vision
"""

import cv2
import numpy as np


class MultiCameraSystem:
    def __init__(self, camera_ids=[0, 1]):
        """
        Initialize multi-camera system
        
        Args:
            camera_ids: List of camera IDs to use
        """
        self.cameras = {}
        self.camera_ids = camera_ids
        self.stereo_enabled = len(camera_ids) >= 2
        
        for cam_id in camera_ids:
            self.cameras[cam_id] = None
    
    def open_cameras(self):
        """Open all cameras"""
        for cam_id in self.camera_ids:
            cap = cv2.VideoCapture(cam_id)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.cameras[cam_id] = cap
                print(f"✓ Camera {cam_id} opened")
            else:
                print(f"✗ Camera {cam_id} failed to open")
    
    def read_frames(self):
        """Read frames from all cameras"""
        frames = {}
        for cam_id, cap in self.cameras.items():
            if cap and cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    frames[cam_id] = frame
        
        return frames
    
    def get_stereo_depth(self, frame_left, frame_right):
        """
        Calculate depth map from stereo images
        
        Args:
            frame_left: Left camera image
            frame_right: Right camera image
            
        Returns:
            Depth map and distance to object
        """
        if not self.stereo_enabled:
            return None, None
        
        # Convert to grayscale
        gray_left = cv2.cvtColor(frame_left, cv2.COLOR_BGR2GRAY)
        gray_right = cv2.cvtColor(frame_right, cv2.COLOR_BGR2GRAY)
        
        # StereoBM matcher
        stereo = cv2.StereoBM_create(numDisparities=16, blockSize=15)
        disparity = stereo.compute(gray_left, gray_right)
        
        # Normalize for display
        disparity_norm = cv2.normalize(disparity, None, 0, 255, cv2.NORM_MINMAX)
        disparity_norm = np.uint8(disparity_norm)
        
        # Estimate distance (simplified)
        # In real implementation, you'd use camera calibration parameters
        focal_length = 700  # Approximate focal length in pixels
        baseline = 5.0  # Baseline distance between cameras in cm
        
        # Calculate depth at center
        h, w = disparity.shape
        center_disp = disparity[h//2, w//2]
        
        if center_disp > 0:
            distance = (focal_length * baseline) / center_disp
        else:
            distance = None
        
        return disparity_norm, distance
    
    def release_all(self):
        """Release all cameras"""
        for cap in self.cameras.values():
            if cap:
                cap.release()
    
    def get_active_cameras(self):
        """Get list of active camera IDs"""
        return [cam_id for cam_id, cap in self.cameras.items() if cap and cap.isOpened()]