"""
barcode_scanner.py - Barcode scanner using OpenCV (No pyzbar required)
Works without external DLL dependencies
"""

import cv2
import json
import os
import numpy as np


class BarcodeScanner:
    def __init__(self, database_file="product_dimensions.json"):
        """
        Initialize barcode scanner using OpenCV's QRCode detector
        
        Args:
            database_file: JSON file with product dimensions
        """
        self.database_file = database_file
        self.product_db = self.load_database()
        self.last_barcode = None
        self.last_product = None
        self.scan_history = []
        
        # Try OpenCV QRCode detector (works without external DLLs)
        try:
            self.qr_detector = cv2.QRCodeDetector()
            self.available = True
            print("✓ Barcode scanner initialized (OpenCV QRCode)")
        except Exception as e:
            print(f"⚠️ QRCode detector init failed: {e}")
            self.qr_detector = None
            self.available = False
        
        # Also try barcode detector if available (OpenCV contrib)
        try:
            self.barcode_detector = cv2.barcode_BarcodeDetector()
            self.has_barcode = True
            print("✓ Barcode detector also available")
        except:
            self.has_barcode = False
            self.barcode_detector = None
    
    def load_database(self):
        """Load product database from JSON file"""
        default_db = {
            "123456789012": {
                "name": "iPhone 15",
                "width_cm": 7.16,
                "height_cm": 14.76,
                "category": "Smartphone",
                "brand": "Apple"
            },
            "234567890123": {
                "name": "Samsung Galaxy S24",
                "width_cm": 7.06,
                "height_cm": 14.70,
                "category": "Smartphone",
                "brand": "Samsung"
            },
            "345678901234": {
                "name": "Google Pixel 8",
                "width_cm": 7.05,
                "height_cm": 15.00,
                "category": "Smartphone",
                "brand": "Google"
            },
            "456789012345": {
                "name": "Coca-Cola Can",
                "width_cm": 6.6,
                "height_cm": 12.3,
                "category": "Beverage",
                "brand": "Coca-Cola"
            },
            "https://www.amazon.com/dp/B0EXAMPLE": {
                "name": "Sample Product",
                "width_cm": 10.0,
                "height_cm": 15.0,
                "category": "General",
                "brand": "Generic"
            }
        }
        
        if os.path.exists(self.database_file):
            try:
                with open(self.database_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading database: {e}")
                return default_db
        else:
            with open(self.database_file, 'w', encoding='utf-8') as f:
                json.dump(default_db, f, indent=2, ensure_ascii=False)
            return default_db
    
    def save_database(self):
        """Save product database to file"""
        try:
            with open(self.database_file, 'w', encoding='utf-8') as f:
                json.dump(self.product_db, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving database: {e}")
            return False
    
    def scan_frame(self, frame):
        """
        Scan frame for QR codes and barcodes using OpenCV
        
        Args:
            frame: BGR image frame
            
        Returns:
            List of detected codes with data
        """
        results = []
        
        # Try QR Code detection first
        if self.qr_detector is not None:
            try:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                decoded_info, points, _ = self.qr_detector.detectAndDecode(gray)
                
                if decoded_info and points is not None:
                    points = points.astype(int)
                    if len(points) > 0:
                        x1, y1 = points[0][0][0], points[0][0][1]
                        x2, y2 = points[0][2][0], points[0][2][1]
                        
                        product = self.product_db.get(decoded_info, None)
                        
                        results.append({
                            "data": decoded_info,
                            "type": "QR_CODE",
                            "bbox": (x1, y1, x2, y2),
                            "product": product,
                            "timestamp": cv2.getTickCount()
                        })
                        
                        self.last_barcode = decoded_info
                        self.last_product = product
                        
                        # Add to history
                        self.scan_history.insert(0, results[-1])
                        self.scan_history = self.scan_history[:10]
            except Exception as e:
                pass
        
        # Try barcode detection if available
        if self.has_barcode and self.barcode_detector is not None:
            try:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                retval, decoded_info, decoded_type, points = self.barcode_detector.detectAndDecode(gray)
                
                if retval and decoded_info:
                    for i, info in enumerate(decoded_info):
                        if info and info not in [r.get("data") for r in results]:
                            if points is not None and len(points) > i:
                                pts = points[i].astype(int)
                                if len(pts) >= 4:
                                    x1, y1 = pts[0][0], pts[0][1]
                                    x2, y2 = pts[2][0], pts[2][1]
                                    
                                    product = self.product_db.get(info, None)
                                    
                                    results.append({
                                        "data": info,
                                        "type": decoded_type[i] if decoded_type else "BARCODE",
                                        "bbox": (x1, y1, x2, y2),
                                        "product": product,
                                        "timestamp": cv2.getTickCount()
                                    })
                                    
                                    self.last_barcode = info
                                    self.last_product = product
            except Exception as e:
                pass
        
        return results
    
    def add_product(self, barcode, name, width_cm, height_cm, category="General", brand=""):
        """Add or update product in database"""
        self.product_db[barcode] = {
            "name": name,
            "width_cm": float(width_cm),
            "height_cm": float(height_cm),
            "category": category,
            "brand": brand
        }
        return self.save_database()
    
    def delete_product(self, barcode):
        """Delete product from database"""
        if barcode in self.product_db:
            del self.product_db[barcode]
            return self.save_database()
        return False
    
    def get_product_info(self, barcode):
        """Get product info for barcode"""
        return self.product_db.get(barcode, None)
    
    def get_all_products(self):
        """Get all products in database"""
        return self.product_db
    
    def search_products(self, search_term):
        """Search products by name or brand"""
        search_term = search_term.lower()
        results = []
        
        for barcode, product in self.product_db.items():
            if (search_term in product['name'].lower() or 
                search_term in product.get('brand', '').lower() or
                search_term in product.get('category', '').lower()):
                results.append({
                    "barcode": barcode,
                    "product": product
                })
        
        return results
    
    def draw_barcode_overlay(self, frame, barcode_results):
        """Draw barcode detection overlay on frame"""
        if not barcode_results:
            return frame
        
        for result in barcode_results:
            x1, y1, x2, y2 = result["bbox"]
            
            # Draw rectangle
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 255), 2)
            
            # Draw corner markers
            corner_len = 15
            cv2.line(frame, (x1, y1), (x1 + corner_len, y1), (255, 0, 255), 2)
            cv2.line(frame, (x1, y1), (x1, y1 + corner_len), (255, 0, 255), 2)
            cv2.line(frame, (x2, y1), (x2 - corner_len, y1), (255, 0, 255), 2)
            cv2.line(frame, (x2, y1), (x2, y1 + corner_len), (255, 0, 255), 2)
            cv2.line(frame, (x1, y2), (x1 + corner_len, y2), (255, 0, 255), 2)
            cv2.line(frame, (x1, y2), (x1, y2 - corner_len), (255, 0, 255), 2)
            cv2.line(frame, (x2, y2), (x2 - corner_len, y2), (255, 0, 255), 2)
            cv2.line(frame, (x2, y2), (x2, y2 - corner_len), (255, 0, 255), 2)
            
            # Prepare label
            label = f"{result['type']}: {result['data'][:15]}"
            if result['product']:
                label += f" - {result['product']['name']}"
            
            # Draw label background
            (text_w, text_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
            cv2.rectangle(frame, (x1, y1 - text_h - 8), (x1 + text_w + 10, y1), (255, 0, 255), -1)
            
            # Draw label text
            cv2.putText(frame, label, (x1 + 5, y1 - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            
            # If product found, show dimensions
            if result['product']:
                dim_text = f"{result['product']['width_cm']} x {result['product']['height_cm']} cm"
                cv2.putText(frame, dim_text, (x1, y2 + 20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        
        return frame
    
    def get_statistics(self):
        """Get barcode scanner statistics"""
        return {
            "total_products": len(self.product_db),
            "last_barcode": self.last_barcode,
            "scan_history_count": len(self.scan_history),
            "available": self.available
        }