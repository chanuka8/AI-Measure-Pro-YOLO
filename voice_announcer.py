"""
voice_announcer.py - Text-to-speech voice announcements
Supports Windows, macOS, Linux
"""

import threading
import queue
import time


class VoiceAnnouncer:
    def __init__(self, enabled=True, rate=150, volume=0.9):
        """
        Initialize voice announcer
        
        Args:
            enabled: Whether voice is enabled
            rate: Speaking rate (words per minute, 100-200)
            volume: Volume level (0.0 to 1.0)
        """
        self.enabled = enabled
        self.rate = rate
        self.volume = volume
        self.engine = None
        self.message_queue = queue.Queue()
        self.is_speaking = False
        self.worker_thread = None
        self.running = True
        
        if enabled:
            self._init_engine()
            self._start_worker()
    
    def _init_engine(self):
        """Initialize TTS engine"""
        try:
            import pyttsx3
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', self.rate)
            self.engine.setProperty('volume', self.volume)
            
            # Get available voices
            voices = self.engine.getProperty('voices')
            if voices:
                # Try to use female voice if available
                for voice in voices:
                    voice_name = voice.name.lower()
                    if 'female' in voice_name or 'zira' in voice_name:
                        self.engine.setProperty('voice', voice.id)
                        break
                    elif 'david' in voice_name:
                        self.engine.setProperty('voice', voice.id)
            
            print(f"✓ Voice announcer initialized (Rate: {self.rate}, Volume: {self.volume})")
            print(f"  Available voices: {len(voices) if voices else 0}")
            
        except ImportError:
            print("⚠️ pyttsx3 not installed. Install with: pip install pyttsx3")
            print("   Voice announcements will be disabled")
            self.enabled = False
            self.engine = None
        except Exception as e:
            print(f"⚠️ Voice engine initialization failed: {e}")
            self.enabled = False
            self.engine = None
    
    def _start_worker(self):
        """Start background worker for announcements"""
        def worker():
            while self.running:
                try:
                    # Wait for message with timeout
                    message = self.message_queue.get(timeout=0.5)
                    
                    if message and self.enabled and self.engine:
                        self.is_speaking = True
                        try:
                            self.engine.say(message)
                            self.engine.runAndWait()
                        except Exception as e:
                            print(f"Voice playback error: {e}")
                        finally:
                            self.is_speaking = False
                    
                except queue.Empty:
                    pass
                except Exception as e:
                    print(f"Voice worker error: {e}")
        
        self.worker_thread = threading.Thread(target=worker, daemon=True)
        self.worker_thread.start()
    
    def announce(self, message):
        """Add message to announcement queue"""
        if self.enabled and message and message.strip():
            # Limit message length
            if len(message) > 200:
                message = message[:197] + "..."
            self.message_queue.put(message)
    
    def announce_measurement(self, label, width, height, units="cm"):
        """Announce measurement results"""
        if not self.enabled:
            return
        
        # Format numbers
        width_val = round(width, 1) if width and width > 0 else 0
        height_val = round(height, 1) if height and height > 0 else 0
        
        # Create natural language message
        if width_val > 0 and height_val > 0:
            message = f"{label}. Width {width_val} {units}, Height {height_val} {units}"
        elif width_val > 0:
            message = f"{label}. Width {width_val} {units}"
        elif height_val > 0:
            message = f"{label}. Height {height_val} {units}"
        else:
            message = f"Detected {label}"
        
        self.announce(message)
    
    def announce_calibration(self, status):
        """Announce calibration status"""
        messages = {
            "success": "Calibration successful. Accurate mode active.",
            "reset": "Calibration reset. Please show bank card clearly.",
            "failed": "Calibration failed. Please hold card steady.",
            "in_progress": "Calibrating. Please hold bank card steady.",
            "card_detected": "Bank card detected. Calibrating..."
        }
        
        if status in messages:
            self.announce(messages[status])
    
    def announce_object_count(self, count):
        """Announce number of objects detected"""
        if count == 0:
            pass  # Silent when no objects
        elif count == 1:
            self.announce("Detected 1 object")
        else:
            self.announce(f"Detected {count} objects")
    
    def announce_tracking(self, track_id, label, confidence):
        """Announce when new object is tracked"""
        if confidence > 0.7:  # Only announce high confidence detections
            self.announce(f"Tracking {label} as object {track_id}")
    
    def announce_barcode(self, barcode_data, product_name=None):
        """Announce barcode detection"""
        if product_name:
            self.announce(f"Barcode detected. Product: {product_name}")
        else:
            self.announce(f"Barcode detected. Code: {barcode_data}")
    
    def announce_export(self, file_type):
        """Announce export completion"""
        self.announce(f"{file_type} export complete")
    
    def announce_error(self, error_message):
        """Announce error"""
        self.announce(f"Error: {error_message}")
    
    def set_enabled(self, enabled):
        """Enable or disable voice"""
        if enabled != self.enabled:
            self.enabled = enabled
            if enabled and not self.engine:
                self._init_engine()
                if self.engine:
                    self._start_worker()
            
            status = "enabled" if enabled else "disabled"
            self.announce(f"Voice announcements {status}")
    
    def set_rate(self, rate):
        """Set speaking rate (100-200)"""
        self.rate = max(100, min(200, rate))
        if self.engine:
            self.engine.setProperty('rate', self.rate)
    
    def set_volume(self, volume):
        """Set volume level (0.0-1.0)"""
        self.volume = max(0.0, min(1.0, volume))
        if self.engine:
            self.engine.setProperty('volume', self.volume)
    
    def get_voices(self):
        """Get list of available voices"""
        if self.engine:
            return self.engine.getProperty('voices')
        return []
    
    def set_voice(self, voice_id):
        """Set voice by ID"""
        if self.engine:
            try:
                self.engine.setProperty('voice', voice_id)
                return True
            except:
                return False
        return False
    
    def speak_now(self, message):
        """Speak message immediately (bypasses queue)"""
        if self.enabled and self.engine:
            try:
                self.engine.say(message)
                self.engine.runAndWait()
            except:
                pass
    
    def is_busy(self):
        """Check if currently speaking"""
        return self.is_speaking
    
    def shutdown(self):
        """Shutdown voice announcer"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=1)
        if self.engine:
            try:
                self.engine.stop()
            except:
                pass
    
    def get_status(self):
        """Get voice announcer status"""
        return {
            "enabled": self.enabled,
            "rate": self.rate,
            "volume": self.volume,
            "is_speaking": self.is_speaking,
            "queue_size": self.message_queue.qsize(),
            "engine_ready": self.engine is not None
        }