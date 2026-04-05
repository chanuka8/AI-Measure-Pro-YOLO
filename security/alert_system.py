"""
alert_system.py - Security Alert System for AI Measure Pro
Monitors system events and generates alerts for security incidents
"""

import time
import threading
from datetime import datetime
from collections import deque
import json
import os


class AlertLevel:
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    EMERGENCY = "EMERGENCY"


class AlertType:
    UNAUTHORIZED_ACCESS = "UNAUTHORIZED_ACCESS"
    DATA_BREACH = "DATA_BREACH"
    SYSTEM_ANOMALY = "SYSTEM_ANOMALY"
    CALIBRATION_FAILURE = "CALIBRATION_FAILURE"
    DETECTION_ANOMALY = "DETECTION_ANOMALY"
    CAMERA_TAMPER = "CAMERA_TAMPER"
    VOICE_ANOMALY = "VOICE_ANOMALY"
    NETWORK_ISSUE = "NETWORK_ISSUE"


class Alert:
    def __init__(self, alert_type, level, message, source=None):
        self.id = int(time.time() * 1000)
        self.timestamp = datetime.now()
        self.type = alert_type
        self.level = level
        self.message = message
        self.source = source
        self.acknowledged = False
        self.resolved = False


class AlertSystem:
    def __init__(self, log_file="security/alerts.json"):
        self.alerts = []
        self.active_alerts = []
        self.log_file = log_file
        self.alert_callbacks = []
        self.running = True
        self.alert_history = deque(maxlen=1000)
        
        # Create security directory if not exists
        os.makedirs("security", exist_ok=True)
        
        # Load existing alerts
        self.load_alerts()
        
        # Start alert monitor thread
        self.monitor_thread = threading.Thread(target=self._monitor_alerts, daemon=True)
        self.monitor_thread.start()
        
        print("[AlertSystem] Initialized")

    def add_alert(self, alert_type, level, message, source=None):
        """Add a new security alert"""
        alert = Alert(alert_type, level, message, source)
        self.alerts.append(alert)
        self.active_alerts.append(alert)
        self.alert_history.append(alert)
        
        # Log to file
        self._log_alert(alert)
        
        # Notify callbacks
        self._notify_callbacks(alert)
        
        # Console output
        print(f"[ALERT][{level}] {alert_type}: {message}")
        
        # Speak critical alerts
        if level in [AlertLevel.CRITICAL, AlertLevel.EMERGENCY]:
            self._speak_alert(message)
        
        return alert

    def _log_alert(self, alert):
        """Log alert to JSON file"""
        try:
            alert_data = {
                "id": alert.id,
                "timestamp": alert.timestamp.isoformat(),
                "type": alert.type,
                "level": alert.level,
                "message": alert.message,
                "source": alert.source,
                "acknowledged": alert.acknowledged,
                "resolved": alert.resolved
            }
            
            # Load existing alerts
            existing = []
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r') as f:
                    existing = json.load(f)
            
            existing.append(alert_data)
            
            # Keep only last 1000 alerts
            if len(existing) > 1000:
                existing = existing[-1000:]
            
            with open(self.log_file, 'w') as f:
                json.dump(existing, f, indent=2)
                
        except Exception as e:
            print(f"[AlertSystem] Error logging alert: {e}")

    def load_alerts(self):
        """Load alerts from file"""
        try:
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r') as f:
                    alerts_data = json.load(f)
                    for data in alerts_data:
                        alert = Alert(
                            data['type'], data['level'], 
                            data['message'], data.get('source')
                        )
                        alert.id = data['id']
                        alert.timestamp = datetime.fromisoformat(data['timestamp'])
                        alert.acknowledged = data.get('acknowledged', False)
                        alert.resolved = data.get('resolved', False)
                        self.alerts.append(alert)
                        if not alert.resolved:
                            self.active_alerts.append(alert)
        except Exception as e:
            print(f"[AlertSystem] Error loading alerts: {e}")

    def acknowledge_alert(self, alert_id):
        """Mark alert as acknowledged"""
        for alert in self.active_alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                print(f"[AlertSystem] Alert {alert_id} acknowledged")
                return True
        return False

    def resolve_alert(self, alert_id):
        """Mark alert as resolved"""
        for alert in self.active_alerts:
            if alert.id == alert_id:
                alert.resolved = True
                self.active_alerts.remove(alert)
                print(f"[AlertSystem] Alert {alert_id} resolved")
                return True
        return False

    def register_callback(self, callback):
        """Register callback for new alerts"""
        self.alert_callbacks.append(callback)

    def _notify_callbacks(self, alert):
        """Notify all registered callbacks"""
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                print(f"[AlertSystem] Callback error: {e}")

    def _speak_alert(self, message):
        """Speak alert message"""
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.say(f"Security alert: {message}")
            engine.runAndWait()
        except:
            pass

    def _monitor_alerts(self):
        """Monitor for alert conditions"""
        anomaly_count = 0
        last_check = time.time()
        
        while self.running:
            try:
                # Check for unresolved critical alerts
                critical_count = sum(1 for a in self.active_alerts 
                                   if a.level == AlertLevel.CRITICAL)
                
                if critical_count > 3:
                    self.add_alert(
                        AlertType.SYSTEM_ANOMALY,
                        AlertLevel.EMERGENCY,
                        f"Multiple critical alerts: {critical_count}",
                        "AlertSystem"
                    )
                
                time.sleep(5)
                
            except Exception as e:
                print(f"[AlertSystem] Monitor error: {e}")

    def get_active_alerts(self):
        """Get all active alerts"""
        return self.active_alerts

    def get_all_alerts(self):
        """Get all alerts"""
        return self.alerts

    def clear_resolved(self):
        """Clear resolved alerts"""
        self.active_alerts = [a for a in self.active_alerts if not a.resolved]

    def shutdown(self):
        """Shutdown alert system"""
        self.running = False
        print("[AlertSystem] Shutdown")

    def get_statistics(self):
        """Get alert statistics"""
        stats = {
            "total": len(self.alerts),
            "active": len(self.active_alerts),
            "by_level": {},
            "by_type": {}
        }
        
        for alert in self.alerts:
            stats["by_level"][alert.level] = stats["by_level"].get(alert.level, 0) + 1
            stats["by_type"][alert.type] = stats["by_type"].get(alert.type, 0) + 1
        
        return stats


# Example usage
if __name__ == "__main__":
    alert_system = AlertSystem()
    
    # Test alerts
    alert_system.add_alert(AlertType.UNAUTHORIZED_ACCESS, AlertLevel.CRITICAL, 
                          "Unauthorized access detected", "AuthManager")
    alert_system.add_alert(AlertType.CALIBRATION_FAILURE, AlertLevel.WARNING,
                          "Calibration failed 3 times", "Calibration")
    
    print(f"Active alerts: {len(alert_system.get_active_alerts())}")
    print(f"Statistics: {alert_system.get_statistics()}")
    
    alert_system.shutdown()