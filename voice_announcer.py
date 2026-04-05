import threading
import queue
import time

class VoiceAnnouncer:
    def __init__(self, enabled=True, rate=150, volume=0.9):
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
        try:
            import pyttsx3
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', self.rate)
            self.engine.setProperty('volume', self.volume)
            voices = self.engine.getProperty('voices')
            if voices:
                for voice in voices:
                    voice_name = voice.name.lower()
                    if 'female' in voice_name or 'zira' in voice_name:
                        self.engine.setProperty('voice', voice.id)
                        break
            print(f" Voice announcer initialized (Rate: {self.rate}, Volume: {self.volume})")
        except ImportError:
            print(" pyttsx3 not installed. Install with: pip install pyttsx3")
            self.enabled = False
            self.engine = None
        except Exception as e:
            print(f" Voice engine initialization failed: {e}")
            self.enabled = False
            self.engine = None

    def _start_worker(self):
        def worker():
            while self.running:
                try:
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
        if self.enabled and message and message.strip():
            if len(message) > 200:
                message = message[:197] + "..."
            self.message_queue.put(message)

    def announce_measurement(self, label, width, height, units="cm"):
        if not self.enabled:
            return
        width_val = round(width, 1) if width and width > 0 else 0
        height_val = round(height, 1) if height and height > 0 else 0
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
        if count == 0:
            pass
        elif count == 1:
            self.announce("Detected 1 object")
        else:
            self.announce(f"Detected {count} objects")

    def announce_tracking(self, track_id, label, confidence):
        if confidence > 0.7:
            self.announce(f"Tracking {label} as object {track_id}")

    def announce_barcode(self, barcode_data, product_name=None):
        if product_name:
            self.announce(f"Barcode detected. Product: {product_name}")
        else:
            self.announce(f"Barcode detected. Code: {barcode_data}")

    def announce_export(self, file_type):
        self.announce(f"{file_type} export complete")

    def announce_error(self, error_message):
        self.announce(f"Error: {error_message}")

    def set_enabled(self, enabled):
        if enabled != self.enabled:
            self.enabled = enabled
            if enabled and not self.engine:
                self._init_engine()
                if self.engine:
                    self._start_worker()
            status = "enabled" if enabled else "disabled"
            self.announce(f"Voice announcements {status}")

    def set_rate(self, rate):
        self.rate = max(100, min(200, rate))
        if self.engine:
            self.engine.setProperty('rate', self.rate)

    def set_volume(self, volume):
        self.volume = max(0.0, min(1.0, volume))
        if self.engine:
            self.engine.setProperty('volume', self.volume)

    def get_voices(self):
        if self.engine:
            return self.engine.getProperty('voices')
        return []

    def set_voice(self, voice_id):
        if self.engine:
            try:
                self.engine.setProperty('voice', voice_id)
                return True
            except:
                return False
        return False

    def speak_now(self, message):
        if self.enabled and self.engine:
            try:
                self.engine.say(message)
                self.engine.runAndWait()
            except:
                pass

    def is_busy(self):
        return self.is_speaking

    def shutdown(self):
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=1)
        if self.engine:
            try:
                self.engine.stop()
            except:
                pass

    def get_status(self):
        return {
            "enabled": self.enabled,
            "rate": self.rate,
            "volume": self.volume,
            "is_speaking": self.is_speaking,
            "queue_size": self.message_queue.qsize(),
            "engine_ready": self.engine is not None
        }