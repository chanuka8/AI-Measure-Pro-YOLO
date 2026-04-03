"""
integrity_checker.py - File Integrity Monitoring
Cybersecurity feature for AI Measure Pro
"""

import hashlib
import os
import json
from datetime import datetime


class IntegrityChecker:
    def __init__(self, manifest_file="file_manifest.json"):
        self.manifest_file = manifest_file
        self.manifest = self.load_manifest()
    
    def load_manifest(self):
        """Load integrity manifest"""
        if os.path.exists(self.manifest_file):
            with open(self.manifest_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_manifest(self):
        """Save integrity manifest"""
        with open(self.manifest_file, 'w') as f:
            json.dump(self.manifest, f, indent=2)
    
    def calculate_hash(self, file_path):
        """Calculate SHA-256 hash of a file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def add_to_manifest(self, file_path):
        """Add file to integrity manifest"""
        if os.path.exists(file_path):
            self.manifest[file_path] = {
                "hash": self.calculate_hash(file_path),
                "last_checked": datetime.now().isoformat(),
                "size": os.path.getsize(file_path)
            }
            self.save_manifest()
    
    def verify_integrity(self, file_path):
        """Verify file integrity against manifest"""
        if file_path not in self.manifest:
            return False, "File not in manifest"
        
        current_hash = self.calculate_hash(file_path)
        stored_hash = self.manifest[file_path]["hash"]
        
        if current_hash == stored_hash:
            self.manifest[file_path]["last_checked"] = datetime.now().isoformat()
            self.save_manifest()
            return True, "Integrity verified"
        else:
            return False, "INTEGRITY VIOLATION - File has been modified!"
    
    def verify_all(self):
        """Verify all files in manifest"""
        results = {}
        for file_path in self.manifest:
            status, message = self.verify_integrity(file_path)
            results[file_path] = {"status": status, "message": message}
        return results
    
    def detect_tampering(self):
        """Detect any tampered files"""
        tampered = []
        for file_path in self.manifest:
            status, message = self.verify_integrity(file_path)
            if not status:
                tampered.append({"file": file_path, "message": message})
        return tampered