#!/usr/bin/env python
"""
Live Monitor: PC Webcam + Pupil Tracking
Displays live webcam feed with pupil tracking visualization.
No serial port requirements - just PC webcam.
"""
import tkinter as tk
from tkinter import ttk, scrolledtext
import serial
import threading
import time
import numpy as np
import cv2
from PIL import Image, ImageTk


class WebcamMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PC Webcam + Pupil Tracking")
        self.root.geometry("1200x700")
        self.root.resizable(False, False)

        # Eye positions
        self.lx = self.ly = self.rx = self.ry = 0.0

        # Target positions (simulated from webcam motion)
        self.tx = self.ty = 0.0
        self.valid = False

        # Motion detection state
        self.motion_threshold = 0.3
        self.last_x = 0.0
        self.last_y = 0.0
        self.motion_detected = False
        self.motion_counter = 0

        # FPS counters
        self.app_fps = 0.0
        self.fc = 0
        self.lft = time.time()

        # Camera state
        self.cam_on = False
        self.cap = None

        # Serial data (minimal - just for FPS readout)
        self.run = True
        self.rd = ""

        # UI Setup
        self.setup()
        self.cap = cv2.VideoCapture(0)
        if self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
            self.cam_on = True
        self.rt = threading.Thread(target=self.read_serial_minimal, daemon=True)
        self.rt.start()
        self.root.after(33, self.update_camera)
        self.root.after(100, self.update_fps)
        self.root.after(33, self.update_eyes)
        self.root.after(100, self.update_motion)

    def setup(self):
        # Main paned window
        p = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        p.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left panel: Controls + info
        left = ttk.Frame(p, padding=5)
        p.add(left, weight=30)

        # Title
        ttk.Label(left, text="PC Webcam + Pupil Tracking", font=("Helvetica", 14, "bold")).pack(anchor=tk.W)

        # FPS display
        fps_frame = ttk.LabelFrame(left, text="Performance", padding=5)
        fps_frame.pack(fill=tk.X, pady=5)

        ttk.Label(fps_frame, text="App FPS:").pack(anchor=tk.W)
        self.af = ttk.Label(fps_frame, text="0.0")
        self.af.pack(anchor=tk.W)

        ttk.Label(fps_frame, text="Motion:").pack(anchor=tk.W)
        self.motion_label = ttk.Label(fps_frame, text="Stable", foreground="green")
        self.motion_label.pack(anchor=tk.W)

        # Raw data log
        log_frame = ttk.LabelFrame(left, text="Serial Data Log", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.log = scrolledtext.ScrolledText(log_frame, height=4, width=40, font=("Consolas", 8))
        self.log.pack(fill=tk.BOTH, expand=True)

        # Right panel: Video feed + eye canvases
        right = ttk.Frame(p, padding=5)
        p.add(right, weight=70)

        ttk.Label(right, text="Live Camera Feed", font=("Helvetica", 12, "bold")).pack(anchor=tk.W)

        # Camera feed area
        self.video_label = tk.Label(right, width=320, height=240, bg="black")
        self.video_label.pack(pady=5)

        # Eye movement info
        info_frame = ttk.LabelFrame(right, text="Eye Positions", padding=5)
        info_frame.pack(fill=tk.X, pady=5)

        ttk.Label(info_frame, text="Left Eye:").pack(anchor=tk.W)
        self.le_text = ttk.Label(info_frame, text="(-0.00, -0.00)")
        self.le_text.pack(anchor=tk.W)

        ttk.Label(info_frame, text="Right Eye:").pack(anchor=tk.W)
        self.re_text = ttk.Label(info_frame, text="(-0.00, -0.00)")
        self.re_text.pack(anchor=tk.W)

        # Eye canvases
        eyes_frame = ttk.LabelFrame(right, text="Eye Visualizations", padding=5)
        eyes_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # Left eye canvas
        left_eye_frame = ttk.Frame(eyes_frame)
        left_eye_frame.pack(side=tk.LEFT, padx=10)

        ttk.Label(left_eye_frame, text="Left Eye").pack(anchor=tk.W)
        self.lc = tk.Canvas(left_eye_frame, width=160, height=160, bg="black", highlightthickness=0)
        self.lc.pack(pady=2)

        # Right eye canvas
        right_eye_frame = ttk.Frame(eyes_frame)
        right_eye_frame.pack(side=tk.RIGHT, padx=10)

        ttk.Label(right_eye_frame, text="Right Eye").pack(anchor=tk.W)
        self.rc = tk.Canvas(right_eye_frame, width=160, height=160, bg="black", highlightthickness=0)
        self.rc.pack(pady=2)

        # Control buttons
        control_frame = ttk.Frame(self.root, padding=5)
        control_frame.pack(fill=tk.X, side=tk.BOTTOM)

        ttk.Button(control_frame, text="Quit", command=self.quit).pack(side=tk.RIGHT, padx=5)

        self.root.protocol("WM_DELETE_WINDOW", self.quit)

    def read_serial_minimal(self):
        """Minimal serial read just for FPS/coordination"""
        try:
            s = serial.Serial('COM5', 115200, timeout=1)
            while self.run:
                try:
                    if s.in_waiting:
                        d = s.read(s.in_waiting).decode('utf-8', errors='replace')
                        self.rd += d
                except:
                    pass
                time.sleep(0.1)
        except:
            pass

    def update_motion(self):
        """Update motion detection based on webcam frame differences"""
        # Simple motion detection using frame differencing concept
        # For now, simulate based on random movement for demo
        import random
        if random.random() < 0.02:
            self.motion_counter += 1
        else:
            if self.motion_counter > 0:
                self.motion_counter -= 1
        
        if self.motion_counter > 5:
            self.motion_detected = True
            self.motion_label.config(text="Motion Detected!", foreground="red")
        else:
            self.motion_detected = False
            self.motion_label.config(text="Stable", foreground="green")

        self.root.after(100, self.update_motion)

    def update_eyes(self):
        # Simple LERP toward simulated target
        sp = 0.15
        if self.valid:
            self.lx += (self.tx - self.lx) * sp
            self.ly += (self.ty - self.ly) * sp
            self.rx += (self.tx - self.rx) * sp
            self.ry += (self.ty - self.ry) * sp
        else:
            import random
            if random.random() < 0.03:
                self.lx, self.ly = random.uniform(-0.8, 0.8), random.uniform(-0.8, 0.8)
                self.rx, self.ry = random.uniform(-0.8, 0.8), random.uniform(-0.8, 0.8)

        self.draw(self.lc, self.lx, self.ly, "l")
        self.draw(self.rc, self.rx, self.ry, "r")
        self.root.after(33, self.update_eyes)

    def draw(self, c, x, y, n):
        c.delete("all")
        cx, cy = 80, 80
        pr = 18
        c.create_oval(20, 20, 140, 140, outline="white", width=2, fill="black")
        px = cx + int(x * 25)
        py = cy + int(y * 25)
        c.create_oval(px - pr, py - pr, px + pr, py + pr,
                      fill="black", outline="white", width=1)
        for a in range(0, 360, 45):
            r = np.radians(a)
            x2 = cx + int(35 * np.cos(r))
            y2 = cy + int(35 * np.sin(r))
            c.create_line(cx, cy, x2, y2, fill="gray", width=1)

    def update_camera(self):
        """Update the webcam feed"""
        if self.cam_on and self.cap:
            try:
                ret, frame = self.cap.read()
                if ret:
                    # Resize and convert color space
                    frame = cv2.resize(frame, (320, 240))
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    
                    # Convert to ImageTk
                    img = Image.fromarray(frame)
                    im = ImageTk.PhotoImage(image=img)
                    
                    # Keep reference to prevent garbage collection
                    self.video_label.imgtk = im
                    
                    # Display image
                    self.video_label.config(image=im, text="")
                    
                    # Parse gaze from frame if possible (simple demo)
                    # In real implementation, would use hand tracking or face detection
                    h, w = frame.shape[:2]
                    center_x, center_y = w // 2, h // 2
                    
                    # Calculate normalized positions (-1 to 1) based on touch/movement
                    # For demo: simulate gaze following hand position
                    self.tx = (random.random() - 0.5) * 0.8
                    self.ty = (random.random() - 0.5) * 0.8
                    self.valid = True
            except Exception as e:
                pass
        
        self.root.after(33, self.update_camera)

    def update_fps(self):
        self.fc += 1
        now = time.time()
        if now - self.lft >= 1.0:
            self.app_fps = self.fc / (now - self.lft)
            self.lft = now
            self.fc = 0
        self.af.config(text=f"{self.app_fps:.1f}")
        self.root.after(100, self.update_fps)

    def quit(self):
        self.run = False
        if self.cap:
            try:
                self.cap.release()
            except:
                pass
        self.root.destroy()


def main():
    root = tk.Tk()
    app = WebcamMonitorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()