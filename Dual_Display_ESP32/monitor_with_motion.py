#!/usr/bin/env python
"""
Live Monitor: DFRobot AI Camera + Pupil Tracking with Motion Detection
Reads serial data from COM5 (Robot Eyes) and COM14 (DFRobot AI Camera).
Displays pupil tracking with motion detection indicators.
NO broken OpenCV video capture - visualizes DFRobot serial data with motion activity.
"""
import tkinter as tk
from tkinter import ttk, scrolledtext
import serial
import threading
import time
import numpy as np

ROBOT = 'COM5'
DFR = 'COM14'
BAUD = 115200


class MotionTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DFRobot AI Cam + Pupil Tracker + Motion Detection")
        self.root.geometry("1200x700")
        self.root.resizable(False, False)

        # Eye positions
        self.lx = self.ly = self.rx = self.ry = 0.0

        # Target positions from DFRobot
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
        self.serial_fps = 0.0
        self.sf_c = 0
        self.sf_t = time.time()

        # Serial data
        self.run = True
        self.rd = ""
        self.dd = ""

        # UI Setup
        self.setup()
        self.rt = threading.Thread(target=self.read_robot, daemon=True)
        self.dt = threading.Thread(target=self.read_dfrobot, daemon=True)
        self.rt.start()
        self.dt.start()
        self.root.after(100, self.update_fps)
        self.root.after(33, self.update_eyes)
        self.root.after(100, self.update_motion)

    def setup(self):
        # Main paned window
        p = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        p.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left panel: Eye visualizations + info
        left = ttk.Frame(p, padding=5)
        p.add(left, weight=30)

        # Title
        ttk.Label(left, text="Dual Display Robot Eyes", font=("Helvetica", 14, "bold")).pack(anchor=tk.W)

        # Camera status frame
        cam_frame = ttk.LabelFrame(left, text="DFRobot AI Camera", padding=5)
        cam_frame.pack(fill=tk.X, pady=5)

        self.cam_status = ttk.Label(cam_frame, text="Camera: Initializing...", foreground="orange")
        self.cam_status.pack(anchor=tk.W)

        # Motion detection indicator
        motion_frame = ttk.LabelFrame(left, text="Motion Detection", padding=5)
        motion_frame.pack(fill=tk.X, pady=5)

        self.motion_indicator = tk.Canvas(motion_frame, width=30, height=30, bg="gray", highlightthickness=0)
        self.motion_indicator.pack()
        self.motion_text = ttk.Label(motion_frame, text="No Motion", foreground="gray")
        self.motion_text.pack(anchor=tk.W)

        # Target coordinates
        ttk.Label(left, text="Target Gaze Position", font=("Helvetica", 12, "bold")).pack(anchor=tk.W, pady=5)

        ttk.Label(left, text="X:").pack(anchor=tk.W)
        self.txl = ttk.Label(left, text="0.00", foreground="green")
        self.txl.pack(anchor=tk.W)

        ttk.Label(left, text="Y:").pack(anchor=tk.W)
        self.tyl = ttk.Label(left, text="0.00", foreground="green")
        self.tyl.pack(anchor=tk.W)

        ttk.Label(left, text="Valid:").pack(anchor=tk.W)
        self.vl = ttk.Label(left, text="No", foreground="red")
        self.vl.pack(anchor=tk.W)

        # FPS displays
        fps_frame = ttk.LabelFrame(left, text="Performance", padding=5)
        fps_frame.pack(fill=tk.X, pady=5)

        ttk.Label(fps_frame, text="App FPS:").pack(anchor=tk.W)
        self.af = ttk.Label(fps_frame, text="0.0")
        self.af.pack(anchor=tk.W)

        ttk.Label(fps_frame, text="Serial FPS:").pack(anchor=tk.W)
        self.sf = ttk.Label(fps_frame, text="0.0")
        self.sf.pack(anchor=tk.W)

        # Raw data log
        log_frame = ttk.LabelFrame(left, text="Serial Data Log", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.log = scrolledtext.ScrolledText(log_frame, height=6, width=40, font=("Consolas", 8))
        self.log.pack(fill=tk.BOTH, expand=True)

        # Right panel: Eye canvases
        right = ttk.Frame(p, padding=5)
        p.add(right, weight=70)

        ttk.Label(right, text="Target Gaze Tracking", font=("Helvetica", 12, "bold")).pack(anchor=tk.W)

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

        ttk.Button(control_frame, text="Clear Log", command=self.clr).pack(side=tk.RIGHT, padx=5)
        ttk.Button(control_frame, text="Refresh Port", command=self.refresh).pack(side=tk.RIGHT, padx=5)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def clr(self):
        self.log.delete(1.0, tk.END)

    def refresh(self):
        self.root.after(500, self.root.quit)
        self.root.after(100, lambda: self.root.destroy())

    def read_robot(self):
        try:
            s = serial.Serial(ROBOT, BAUD, timeout=1)
            while self.run:
                if s.in_waiting:
                    d = s.read(s.in_waiting).decode('utf-8', errors='replace')
                    self.rd += d
                    while '\n' in self.rd:
                        l, self.rd = self.rd.split('\n', 1)
                        l = l.strip()
                        if l.startswith("FPS:"):
                            try:
                                self.app_fps = float(l.replace("FPS:", "").strip())
                            except:
                                pass
                time.sleep(0.01)
        except Exception as e:
            self.root.after(0, lambda: self.log(f"Robot: {e}"))

    def read_dfrobot(self):
        try:
            s = serial.Serial(DFR, BAUD, timeout=1)
            while self.run:
                if s.in_waiting:
                    d = s.read(s.in_waiting).decode('utf-8', errors='replace')
                    self.dd += d
                    while '\n' in self.dd:
                        l, self.dd = self.dd.split('\n', 1)
                        l = l.strip()
                        if l:
                            self.proc(l)
                time.sleep(0.01)
        except Exception as e:
            self.root.after(0, lambda: self.log(f"DFRobot: {e}"))

    def proc(self, l):
        up = l.upper()

        # Try DFRobot format first
        for pf in ["DFROBOT:", "dfrobot:"]:
            if up.startswith(pf):
                try:
                    parts = l.replace(pf, "").split(":")
                    if len(parts) >= 2:
                        x = max(-1.0, min(1.0, float(parts[0])))
                        y = max(-1.0, min(1.0, float(parts[1])))
                        self.tx, self.ty = x, y
                        self.valid = True
                        self.motion_counter += 1
                        self.root.after(0, self.update_t)
                        self.root.after(0, lambda: self.log(f"DFR: x={x:.2f}, y={y:.2f}"))
                except:
                    pass
                break

        # Try standard x,y format (fallback)
        if "," in l and not l.startswith("FPS:"):
            try:
                parts = l.split(",")
                if len(parts) >= 2:
                    x = max(-1.0, min(1.0, float(parts[0])))
                    y = max(-1.0, min(1.0, float(parts[1])))
                    self.tx, self.ty = x, y
                    self.valid = True
                    self.motion_counter += 1
                    self.root.after(0, self.update_t)
                    self.root.after(0, lambda: self.log(f"x={x:.2f}, y={y:.2f}"))
            except:
                pass

    def update_t(self):
        self.txl.config(text=f"{self.tx:.2f}")
        self.tyl.config(text=f"{self.ty:.2f}")
        self.vl.config(text="Yes" if self.valid else "No",
                       foreground="green" if self.valid else "red")

    def update_motion(self):
        """Update motion detection indicator based on gaze coordinate changes"""
        # Calculate motion based on target coordinate change
        if self.valid:
            dx = abs(self.tx - self.last_x)
            dy = abs(self.ty - self.last_y)
            self.last_x = self.tx
            self.last_y = self.ty

            # Motion detected if significant movement
            if dx > self.motion_threshold or dy > self.motion_threshold:
                self.motion_detected = True
                self.motion_counter += 1
            else:
                # Gradually fade motion if no significant movement
                if self.motion_counter > 0:
                    self.motion_counter -= 1
                if self.motion_counter <= 0:
                    self.motion_detected = False

            # Update motion indicator
            if self.motion_detected:
                self.motion_indicator.config(bg="red")
                self.motion_text.config(text="Motion Detected!", foreground="red")
            else:
                self.motion_indicator.config(bg="green")
                self.motion_text.config(text="Stable", foreground="green")
        else:
            self.motion_indicator.config(bg="gray")
            self.motion_text.config(text="No Data", foreground="gray")

        self.root.after(100, self.update_motion)

    def update_eyes(self):
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

    def update_fps(self):
        self.fc += 1
        now = time.time()
        if now - self.lft >= 1.0:
            self.app_fps = self.fc / (now - self.lft)
            self.lft = now
            self.fc = 0
        self.af.config(text=f"{self.app_fps:.1f}")
        self.sf.config(text=f"{self.app_fps:.1f}")
        self.root.after(100, self.update_fps)

    def log(self, m):
        ts = time.strftime("%H:%M:%S")
        self.log.insert(tk.END, f"[{ts}] {m}\n")
        self.log.see(tk.END)

    def on_close(self):
        self.run = False
        self.root.destroy()


def main():
    root = tk.Tk()
    app = MotionTrackerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()