"""
encryption.py - AES-256 Encryption for Sensitive Data
Cybersecurity feature for AI Measure Pro
"""

import os
import json
import hashlib

# Try to import cryptography
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    print("⚠️ cryptography not installed. Install with: pip install cryptography")
    print("   Using fallback encryption (less secure)")


class DataEncryption:
    def __init__(self, key_file="encryption.key"):
        self.key_file = key_file
        self.crypto_available = CRYPTO_AVAILABLE
        
        if self.crypto_available:
            self.key = self.load_or_create_key()
            self.cipher = Fernet(self.key)
        else:
            self.key = None
            self.cipher = None
            print("⚠️ Running in fallback mode - encryption disabled")
    
    def load_or_create_key(self):
        """Load existing key or create new one"""
        if os.path.exists(self.key_file):
            with open(self.key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(key)
            # Set secure permissions
            try:
                os.chmod(self.key_file, 0o600)
            except:
                pass
            return key
    
    def encrypt_data(self, data):
        """Encrypt data (string or bytes)"""
        if not self.crypto_available:
            # Fallback: simple encoding (not secure, for development only)
            if isinstance(data, str):
                return data.encode()
            return data
        
        if isinstance(data, str):
            data = data.encode()
        return self.cipher.encrypt(data)
    
    def decrypt_data(self, encrypted_data):
        """Decrypt data"""
        if not self.crypto_available:
            return encrypted_data.decode() if isinstance(encrypted_data, bytes) else str(encrypted_data)
        
        return self.cipher.decrypt(encrypted_data).decode()
    
    def encrypt_file(self, input_file, output_file=None):
        """Encrypt a file"""
        if not self.crypto_available:
            print("Encryption not available - copying file")
            if output_file is None:
                output_file = input_file + ".copy"
            import shutil
            shutil.copy2(input_file, output_file)
            return output_file
        
        if output_file is None:
            output_file = input_file + ".encrypted"
        
        with open(input_file, 'rb') as f:
            data = f.read()
        
        encrypted = self.cipher.encrypt(data)
        
        with open(output_file, 'wb') as f:
            f.write(encrypted)
        
        return output_file
    
    def decrypt_file(self, encrypted_file, output_file=None):
        """Decrypt a file"""
        if not self.crypto_available:
            print("Decryption not available")
            return encrypted_file
        
        if output_file is None:
            output_file = encrypted_file.replace(".encrypted", "")
        
        with open(encrypted_file, 'rb') as f:
            encrypted_data = f.read()
        
        decrypted = self.cipher.decrypt(encrypted_data)
        
        with open(output_file, 'wb') as f:
            f.write(decrypted)
        
        return output_file
    
    def encrypt_csv(self, csv_file):
        """Encrypt CSV measurement file"""
        if os.path.exists(csv_file):
            return self.encrypt_file(csv_file, csv_file + ".enc")
        return None
    
    def secure_delete(self, file_path, passes=3):
        """Securely delete a file (overwrite before deletion)"""
        if not os.path.exists(file_path):
            return
        
        try:
            # Get file size
            with open(file_path, 'rb') as f:
                f.seek(0, 2)
                length = f.tell()
            
            # Overwrite with random data
            for _ in range(passes):
                with open(file_path, 'r+b') as f:
                    f.write(os.urandom(length))
            
            # Delete the file
            os.remove(file_path)
            print(f"✓ Securely deleted: {file_path}")
        except Exception as e:
            print(f"Secure delete failed: {e}")
            # Fallback: normal delete
            try:
                os.remove(file_path)
            except:
                pass