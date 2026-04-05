"""
hand_tracking.py - Hand Tracking using MediaPipe
"""

import cv2
import mediapipe as mp
import numpy as np


class HandTracker:
    def __init__(self, min_detection_confidence=0.7, min_tracking_confidence=0.5):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
        self.mp_draw = mp.solutions.drawing_utils
        self.landmarks = None
        self.finger_tips = [4, 8, 12, 16, 20]
        self.index_finger_tip = None
        self.middle_finger_tip = None
        self.index_finger_mcp = None
        self.thumb_tip = None
        self.all_landmarks = []
        
    def process_frame(self, frame):
        """Process frame and get hand landmarks"""
        if frame is None:
            return None
            
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb)
        
        self.landmarks = None
        self.index_finger_tip = None
        self.middle_finger_tip = None
        self.index_finger_mcp = None
        self.thumb_tip = None
        self.all_landmarks = []
        
        if results.multi_hand_landmarks:
            hand_landmarks = results.multi_hand_landmarks[0]
            self.landmarks = hand_landmarks
            h, w = frame.shape[:2]
            
            # Get all landmarks
            for idx, lm in enumerate(hand_landmarks.landmark):
                x, y = int(lm.x * w), int(lm.y * h)
                self.all_landmarks.append((x, y, lm.z))
            
            # Get index finger tip (landmark 8)
            idx_tip = hand_landmarks.landmark[8]
            self.index_finger_tip = (int(idx_tip.x * w), int(idx_tip.y * h))
            
            # Get index finger MCP (landmark 5)
            idx_mcp = hand_landmarks.landmark[5]
            self.index_finger_mcp = (int(idx_mcp.x * w), int(idx_mcp.y * h))
            
            # Get middle finger tip (landmark 12)
            mid_tip = hand_landmarks.landmark[12]
            self.middle_finger_tip = (int(mid_tip.x * w), int(mid_tip.y * h))
            
            # Get thumb tip (landmark 4)
            thumb = hand_landmarks.landmark[4]
            self.thumb_tip = (int(thumb.x * w), int(thumb.y * h))
            
            return hand_landmarks
        
        return None
    
    def draw_hand(self, frame, draw_landmarks=True):
        """Draw hand landmarks on frame"""
        if self.landmarks:
            if draw_landmarks:
                self.mp_draw.draw_landmarks(
                    frame, 
                    self.landmarks, 
                    self.mp_hands.HAND_CONNECTIONS,
                    self.mp_draw.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=3),
                    self.mp_draw.DrawingSpec(color=(0, 0, 255), thickness=2)
                )
            
            # Draw index finger tip with circle
            if self.index_finger_tip:
                cv2.circle(frame, self.index_finger_tip, 10, (0, 255, 255), -1)
                cv2.circle(frame, self.index_finger_tip, 12, (255, 255, 255), 2)
                
        return frame
    
    def is_index_up(self):
        """Check if index finger is raised (drawing mode)"""
        if not self.landmarks:
            return False
        
        # Get Y coordinates
        idx_tip_y = self.landmarks.landmark[8].y
        idx_mcp_y = self.landmarks.landmark[5].y
        mid_tip_y = self.landmarks.landmark[12].y
        mid_mcp_y = self.landmarks.landmark[9].y
        ring_tip_y = self.landmarks.landmark[16].y
        ring_mcp_y = self.landmarks.landmark[13].y
        pinky_tip_y = self.landmarks.landmark[20].y
        pinky_mcp_y = self.landmarks.landmark[17].y
        
        # Index finger up, other fingers down
        index_up = idx_tip_y < idx_mcp_y
        middle_down = mid_tip_y > mid_mcp_y
        ring_down = ring_tip_y > ring_mcp_y
        pinky_down = pinky_tip_y > pinky_mcp_y
        
        return index_up and middle_down and ring_down and pinky_down
    
    def is_two_fingers_up(self):
        """Check if index and middle fingers are raised (color selection)"""
        if not self.landmarks:
            return False
        
        idx_tip_y = self.landmarks.landmark[8].y
        idx_mcp_y = self.landmarks.landmark[5].y
        mid_tip_y = self.landmarks.landmark[12].y
        mid_mcp_y = self.landmarks.landmark[9].y
        ring_tip_y = self.landmarks.landmark[16].y
        ring_mcp_y = self.landmarks.landmark[13].y
        
        index_up = idx_tip_y < idx_mcp_y
        middle_up = mid_tip_y < mid_mcp_y
        ring_down = ring_tip_y > ring_mcp_y
        
        return index_up and middle_up and ring_down
    
    def is_pinching(self):
        """Check if index finger and thumb are pinching"""
        if not self.landmarks:
            return False
        
        thumb_tip = self.landmarks.landmark[4]
        index_tip = self.landmarks.landmark[8]
        
        distance = ((thumb_tip.x - index_tip.x)**2 + (thumb_tip.y - index_tip.y)**2)**0.5
        
        return distance < 0.05
    
    def is_fist(self):
        """Check if hand is making a fist (stop drawing)"""
        if not self.landmarks:
            return False
        
        idx_tip_y = self.landmarks.landmark[8].y
        idx_mcp_y = self.landmarks.landmark[5].y
        mid_tip_y = self.landmarks.landmark[12].y
        mid_mcp_y = self.landmarks.landmark[9].y
        
        index_down = idx_tip_y > idx_mcp_y
        middle_down = mid_tip_y > mid_mcp_y
        
        return index_down and middle_down
    
    def get_pinch_position(self, frame_shape):
        """Get pinch position for color selection"""
        if not self.landmarks:
            return None
        
        thumb_tip = self.landmarks.landmark[4]
        index_tip = self.landmarks.landmark[8]
        
        x = (thumb_tip.x + index_tip.x) / 2
        y = (thumb_tip.y + index_tip.y) / 2
        
        h, w = frame_shape[:2]
        return (int(x * w), int(y * h))
    
    def get_drawing_position(self):
        """Get index finger tip position for drawing"""
        return self.index_finger_tip
    
    def get_finger_positions(self):
        """Get all finger tip positions"""
        if not self.landmarks:
            return {}
        
        tips = {
            "thumb": 4,
            "index": 8,
            "middle": 12,
            "ring": 16,
            "pinky": 20
        }
        
        positions = {}
        for name, idx in tips.items():
            lm = self.landmarks.landmark[idx]
            positions[name] = (lm.x, lm.y, lm.z)
        
        return positions
    
    def get_gesture(self):
        """Detect current hand gesture"""
        if not self.landmarks:
            return "NO_HAND"
        
        if self.is_index_up():
            return "DRAWING"
        elif self.is_two_fingers_up():
            return "TWO_FINGERS"
        elif self.is_pinching():
            return "PINCHING"
        elif self.is_fist():
            return "FIST"
        else:
            return "IDLE"
    
    def release(self):
        """Release resources"""
        self.hands.close()