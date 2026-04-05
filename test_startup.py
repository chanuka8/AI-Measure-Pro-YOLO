"""
test_startup.py - Application startup test
"""
import tkinter as tk
from app import AIMeasureV5App  # නිවැරදි class name එක

def test_startup():
    """Test application startup multiple times"""
    for i in range(1, 4):
        print(f'Run {i}')
        root = tk.Tk()
        try:
            app = AIMeasureV5App(root)
            root.after(100, root.destroy)  # Auto close after 100ms
            root.mainloop()
            print(f'OK {i}')
        except Exception as e:
            print(f'Error on run {i}: {e}')
        finally:
            try:
                root.destroy()
            except:
                pass

if __name__ == "__main__":
    test_startup()