import tkinter as tk
from app import AIMeasureYOLOApp

for i in range(1,4):
    print('Run', i)
    root = tk.Tk()
    app = AIMeasureYOLOApp(root)
    root.destroy()
    print('OK', i)
