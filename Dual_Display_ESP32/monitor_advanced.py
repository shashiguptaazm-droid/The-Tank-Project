#!/usr/bin/env python
"""
Live Monitor: DFRobot AI Camera + Pupil Tracking with Motion Detection + Camera Feed
Reads serial data from COM5 (Robot Eyes) and COM14 (DFRobot AI Camera).
Displays pupil tracking with motion detection and optional live camera feed.
"""
import tkinter as tk
from tkinter import ttk, scrolledtext
import serial
import threading
import time
import numpy as np
import cv2
from PIL import Image, ImageTk

ROBOT = 'COM5'
DFR = 'COM14'
BAUD = 115200


class AdvancedMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DFRobot AI Cam + Pupil Tracker + Motion Detection")
        self.root.geometry("1400x800")
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

        # Camera state
        self.cam_on = False
        self.cap = None
        self.use_serial_camera = True
        self.serial_frame_count = 0
        self.serial_last_time = time.time()

        # Serial data
        self.run = True
        self.rd = ""
        self.dd = ""

        # Exception messages stored as strings for lambdas
        self._last_robot_err = ""
        self._last_dfrobot_err = ""

        # UI Setup
        self.setup()
        self.rt = threading.Thread(target=self.read_robot, daemon=True)
        self.dt = threading.Thread(target=self.read_dfrobot, daemon=True)
        self.rt.start()
        self.dt.start()
        self.root.after(100, self.update_fps)
        self.root.after(33, self.update_eyes)
        self.root.after(100, self.update_motion)
        self.root.after(33, self.update_camera_feed)

    def setup(self):
        # Main paned window
        p = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        p.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left panel: Controls + info
        left = ttk.Frame(p, padding=5)
        p.add(left, weight=30)

        # Title
        ttk.Label(left, text="Dual Display Robot Eyes", font=("Helvetica", 14, "bold")).pack(anchor=tk.W)

        # Camera control frame
        cam_frame = ttk.LabelFrame(left, text="Camera Control", padding=5)
        cam_frame.pack(fill=tk.X, pady=5)

        # Camera toggle
        self.cam_tgl = ttk.Button(cam_frame, text="Camera: Serial Mode", command=self.toggle_camera)
        self.cam_tgl.pack(fill=tk.X, pady=2)

        self.cam_status = ttk.Label(cam_frame, text="Camera: Serial gaze data active", foreground="blue")
        self.cam_status.pack(fill=tk.X, pady=2)

        # Camera type info
        ttk.Label(cam_frame, text="Mode: DFRobot AI Camera via Serial (COM14)", font=("Helvetica", 8)).pack(anchor=tk.W)
        ttk.Label(cam_frame, text="Note: Full video requires DFRobot USB connection or SDK", font=("Helvetica", 8), foreground="gray").pack(anchor=tk.W)

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

        # Right panel: Eye canvases + camera feed
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

        # Camera feed area
        cam_feed_frame = ttk.LabelFrame(right, text="Camera Feed", padding=5)
        cam_feed_frame.pack(fill=tk.BOTH, expand=True, pady=5, side=tk.BOTTOM)

        self.cam_label = ttk.Label(cam_feed_frame, text="Camera: Serial mode\n(gaze data only)", background="black", foreground="yellow")
        self.cam_label.pack(fill=tk.BOTH, expand=True)

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

    def toggle_camera(self):
        self.use_serial_camera = not self.use_serial_camera
        if self.use_serial_camera:
            self.cam_on = False
            if self.cap:
                try:
                    self.cap.release()
                except:
                    pass
                self.cap = None
            self._set_cam_text("Serial Mode", "blue", "Camera: Serial gaze data active", "Camera: Serial mode\n(gaze data only)")
        else:
            # Try to open PC webcam
            try:
                self.cam_on = True
                self.cap = cv2.VideoCapture(0)
                if self.cap.isOpened():
                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
                    self._set_cam_text("PC Webcam Mode", "green", "Camera: PC webcam active", "Camera Feed: PC Webcam active\nPress 'C' to toggle back to Serial mode")
                else:
                    self.cap.release()
                    self.cap = None
                    self.use_serial_camera = True
                    self._set_cam_text("Serial Mode", "blue", "Camera: Serial gaze data active", "Camera Feed: Serial mode\n(gaze data only)")
                    self.log("Failed to open PC webcam - falling back to serial mode")
            except Exception as e:
                self._set_cam_text("Serial Mode", "blue", "Camera: Serial gaze data active", "Camera Feed: Serial mode\n(gaze data only)")
                self.log(f"Camera error: {e}")

    def _set_cam_text(self, tgl_text, tgl_fg, status_text, label_text):
        """Helper to update camera UI from lambda closures"""
        self.cam_tgl.config(text=tgl_text)
        self.cam_status.config(text=status_text, foreground=tgl_fg)
        self.cam_label.config(text=label_text, background="black" if "Serial" in tgl_text else "black", foreground="yellow" if "Serial" in tgl_text else "green")

    def read_robot(self):
        try:
            s = serial.Serial(ROBOT, BAUD, timeout=1)
            while self.run:
                if s.in_waiting:
                    d = s.read(s.in_waiting).decode('utf-8', errors='replace')
                    self.rd += d
                    while '\n' in self.rd:
                        line, self.rd = self.rd.split('\n', 1)
                        line = line.strip()
                        if line.startswith("FPS:"):
                            try:
                                self.app_fps = float(line.replace("FPS:", "").strip())
                            except:
                                pass
                        # Store exception for lambda
                        elif "ERROR" in line.upper():
                            self._last_robot_err = line
                time.sleep(0.01)
        except Exception as e:
            self._last_robot_err = str(e)

    def read_dfrobot(self):
        try:
            s = serial.Serial(DFR, BAUD, timeout=1)
            while self.run:
                if s.in_waiting:
                    d = s.read(s.in_waiting).decode('utf-8', errors='replace')
                    self.dd += d
                    while '\n' in self.dd:
                        line, self.dd = self.dd.split('\n', 1)
                        line = line.strip()
                        if line:
                            self.proc(line)
                time.sleep(0.01)
        except Exception as e:
            self._last_dfrobot_err = str(e)

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
                        self.root.after(0, lambda msg=f"DFR: x={x:.2f}, y={y:.2f}": self.log(msg))
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
                    self.root.after(0, lambda msg=f"x={x:.2f}, y={y:.2f}": self.log(msg))
            except:
                pass

    def update_t(self):
        self.txl.config(text=f"{self.tx:.2f}")
        self.tyl.config(text=f"{self.ty:.2f}")
        self.vl.config(text="Yes" if self.valid else "No",
                       foreground="green" if self.valid else "red")

    def update_motion(self):
        """Update motion detection indicator based on gaze coordinate changes"""
        if self.valid:
            dx = abs(self.tx - self.last_x)
            dy = abs(self.ty - self.last_y)
            self.last_x = self.tx
            self.last_y = self.ty

            if dx > self.motion_threshold or dy > self.motion_threshold:
                self.motion_detected = True
                self.motion_counter += 1
            else:
                if self.motion_counter > 0:
                    self.motion_counter -= 1
                if self.motion_counter <= 0:
                    self.motion_detected = False

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

    def update_camera_feed(self):
        """Update the camera feed label area"""
        if self.use_serial_camera:
            self._set_cam_text("Serial Mode", "blue", "Camera: Serial gaze data active", "Camera Feed: Serial mode\n(gaze data only)")
        elif self.cam_on and self.cap:
            try:
                r, f = self.cap.read()
                if r:
                    f = cv2.resize(f, (320, 240))
                    f = cv2.cvtColor(f, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(f)
                    im = ImageTk.PhotoImage(image=img)
                    self.cam_label.imgtk = im
                    self.cam_label.config(image=im, text="")
                else:
                    self.cam_label.config(text="Camera: No feed", foreground="red")
            except Exception:
                self.cam_label.config(text="Camera: Error", foreground="red")
                self.use_serial_camera = True
            self.root.after(33, self.update_camera_feed)
        else:
            self._set_cam_text("Serial Mode", "blue", "Camera: Serial gaze data active", "Camera Feed: Serial mode\n(gaze data only)")

    def log(self, m):
        ts = time.strftime("%H:%M:%S")
        self.log.insert(tk.END, f"[{ts}] {m}\n")
        self.log.see(tk.END)

    def on_close(self):
        self.run = False
        if self.cap:
            try:
                self.cap.release()
            except:
                pass
        self.root.destroy()


def main():
    root = tk.Tk()
    app = AdvancedMonitorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()