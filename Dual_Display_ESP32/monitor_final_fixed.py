#!/usr/bin/env python
"""
Live Monitor: DFRobot AI Camera + Pupil Tracking
Reads serial data from COM5 (Robot Eyes) and COM14 (DFRobot AI Camera).
Displays live pupil tracking with camera feed status.
NO broken OpenCV video capture - works with serial DFRobot data only.
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


class App:
    def __init__(self, r):
        self.r = r
        self.r.title("DFRobot AI Cam + Pupil Tracker")
        self.r.geometry("1100x650")
        self.r.resizable(False, False)

        self.lx = self.ly = self.rx = self.ry = 0.0
        self.tx = self.ty = 0.0
        self.valid = False

        self.app_fps = 0.0
        self.fc = 0
        self.lft = time.time()

        self.cam_on = False
        self.ser_df = None

        self.run = True
        self.rd = ""
        self.dd = ""

        self.setup()
        self.rt = threading.Thread(target=self.read_robot, daemon=True)
        self.dt = threading.Thread(target=self.read_dfrobot, daemon=True)
        self.rt.start()
        self.dt.start()
        self.r.after(100, self.update_fps)
        self.r.after(33, self.update_eyes)
        self.r.after(33, self.update_cam_info)

    def setup(self):
        p = ttk.PanedWindow(self.r, orient=tk.HORIZONTAL)
        p.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        left = ttk.Frame(p, padding=5)
        p.add(left, weight=30)

        ttk.Label(left, text="Robot Eyes Displays", font=("Helvetica", 12, "bold")).pack(anchor=tk.W)

        ef = ttk.Frame(left)
        ef.pack()
        self.lc = tk.Canvas(ef, width=160, height=160, bg="black", highlightthickness=0)
        self.lc.pack(side=tk.LEFT, padx=5)
        self.rc = tk.Canvas(ef, width=160, height=160, bg="black", highlightthickness=0)
        self.rc.pack(side=tk.RIGHT, padx=5)

        right = ttk.Frame(p, padding=5)
        p.add(right, weight=70)

        ttk.Label(right, text="DFRobot AI Camera Input", font=("Helvetica", 12, "bold")).pack(anchor=tk.W)

        # Camera status instead of video feed
        self.cam_status = ttk.Label(right, text="Camera: Not Connected", foreground="red")
        self.cam_status.pack(anchor=tk.W, pady=5)

        ttk.Label(right, text="Target Gaze Position", font=("Helvetica", 12, "bold")).pack(anchor=tk.W)
        ttk.Label(right, text="X:").pack(anchor=tk.W)
        self.txl = ttk.Label(right, text="0.00", foreground="green")
        self.txl.pack(anchor=tk.W)
        ttk.Label(right, text="Y:").pack(anchor=tk.W)
        self.tyl = ttk.Label(right, text="0.00", foreground="green")
        self.tyl.pack(anchor=tk.W)
        ttk.Label(right, text="Valid:").pack(anchor=tk.W)
        self.vl = ttk.Label(right, text="No", foreground="red")
        self.vl.pack(anchor=tk.W)
        ttk.Label(right, text="App FPS:").pack(anchor=tk.W)
        self.af = ttk.Label(right, text="0.0")
        self.af.pack(anchor=tk.W)
        ttk.Label(right, text="Serial FPS:").pack(anchor=tk.W)
        self.sf = ttk.Label(right, text="0.0")
        self.sf.pack(anchor=tk.W)

        ttk.Label(right, text="Serial Log", font=("Helvetica", 10, "bold")).pack(anchor=tk.W, pady=5)
        self.log = scrolledtext.ScrolledText(right, height=8, width=50, font=("Consolas", 8))
        self.log.pack(fill=tk.BOTH, expand=True)
        ttk.Button(right, text="Clear", command=self.clr).pack(side=tk.RIGHT, padx=5)
        ttk.Button(right, text="Toggle Camera", command=self.tgl).pack(side=tk.LEFT, padx=5)

        self.r.protocol("WM_DELETE_WINDOW", self.on_close)

    def clr(self):
        self.log.delete(1.0, tk.END)

    def tgl(self):
        # Camera toggle - for DFRobot, this just shows status
        # Actual camera access requires DFRobot SDK, not OpenCV direct capture
        self.cam_on = not self.cam_on
        if self.cam_on:
            self.ser_df = serial.Serial(DFR, BAUD, timeout=1)
            self.cam_status.config(text="Camera: COM14 Connected", foreground="green")
            self.log("Camera connection opened on COM14")
        else:
            if self.ser_df and self.ser_df.isOpen():
                self.ser_df.close()
            self.cam_status.config(text="Camera: Disconnected", foreground="red")
            self.log("Camera connection closed")

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
            self.r.after(0, lambda: self.log(f"Robot: {e}"))

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
            self.r.after(0, lambda: self.log(f"DFRobot: {e}"))

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
                        self.r.after(0, self.update_t)
                        self.r.after(0, lambda: self.log(f"DFR: x={x:.2f}, y={y:.2f}"))
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
                    self.r.after(0, self.update_t)
                    self.r.after(0, lambda: self.log(f"x={x:.2f}, y={y:.2f}"))
            except:
                pass

    def update_t(self):
        self.txl.config(text=f"{self.tx:.2f}")
        self.tyl.config(text=f"{self.ty:.2f}")
        self.vl.config(text="Yes" if self.valid else "No",
                       foreground="green" if self.valid else "red")

    def update_fps(self):
        self.fc += 1
        now = time.time()
        if now - self.lft >= 1.0:
            self.app_fps = self.fc / (now - self.lft)
            self.lft = now
            self.fc = 0
        self.af.config(text=f"{self.app_fps:.1f}")
        self.sf.config(text=f"{self.app_fps:.1f}")  # Show serial FPS
        self.r.after(100, self.update_fps)

    def update_cam_info(self):
        # Update camera status display
        if self.ser_df and self.ser_df.isOpen():
            self.cam_status.config(text="Camera: COM14 Connected", foreground="green")
        else:
            self.cam_status.config(text="Camera: Not Connected", foreground="red")
        self.r.after(33, self.update_cam_info)

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
        self.r.after(33, self.update_eyes)

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

    def log(self, m):
        ts = time.strftime("%H:%M:%S")
        self.log.insert(tk.END, f"[{ts}] {m}\n")
        self.log.see(tk.END)

    def on_close(self):
        self.run = False
        if self.ser_df and self.ser_df.isOpen():
            self.ser_df.close()
        self.r.destroy()


def main():
    r = tk.Tk()
    a = App(r)
    r.mainloop()


if __name__ == "__main__":
    main()