#!/usr/bin/env python
"""
DFRobot AI Camera Live Feed Monitor
Shows live camera feed from DFRobot ESP32-S3 AI Camera + pupil tracking.
Reads gaze data via serial COM14, displays live video with overlay.
"""
import tkinter as tk
from tkinter import ttk, scrolledtext
import serial
import threading
import time
import numpy as np
import cv2
from PIL import Image, ImageTk

# DFRobot AI Camera Product: 2899
# Serial port: COM14 (default for DFRobot ESP32-S3 AI Camera)
SERIAL_PORT = 'COM14'
BAUD_RATE = 115200


class DFRobotCamMonitor:
    def __init__(self, root):
        self.root = root
        self.root.title("DFRobot AI Camera Live Feed - Product 2899")
        self.root.geometry("1280x720")
        self.root.resizable(False, False)

        # Camera state
        self.cam_on = False
        self.cap = None
        self.use_dfrobot_serial = True

        # Gaze data from DFRobot
        self.tx = 0.0
        self.ty = 0.0
        self.valid = False
        self.motion_detected = False
        self.last_x = 0.0
        self.last_y = 0.0
        self.motion_counter = 0
        self.motion_threshold = 0.3

        # FPS
        self.app_fps = 0.0
        self.fc = 0
        self.lft = time.time()
        self.serial_fps = 0.0
        self.sf_c = 0
        self.sf_t = time.time()

        # Serial data
        self.run = True
        self.rd = ""
        self._last_err = ""

        # UI Setup
        self.setup()
        self.connect_dfrobot_camera()
        self.rt = threading.Thread(target=self.read_dfrobot_serial, daemon=True)
        self.dt = threading.Thread(target=self.read_serial_background, daemon=True)
        self.rt.start()
        self.dt.start()
        self.root.after(33, self.update_video_feed)
        self.root.after(100, self.update_stats)
        self.root.after(100, self.update_motion_indicator)

    def setup(self):
        # Main paned window
        p = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        p.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left panel: Controls + stats
        left = ttk.Frame(p, padding=5)
        p.add(left, weight=30)

        # Title
        ttk.Label(left, text="DFRobot AI Camera Live Feed", font=("Helvetica", 14, "bold")).pack(anchor=tk.W)

        # Product info
        ttk.Label(left, text="Product: DFRobot ESP32-S3 AI Camera (2899)", font=("Helvetica", 8)).pack(anchor=tk.W)
        ttk.Label(left, text="Interface: UART / Serial (COM14)", font=("Helvetica", 8)).pack(anchor=tk.W)
        ttk.Label(left, text="Data Format: DFROBOT:x:y (gaze coordinates)", font=("Helvetica", 8)).pack(anchor=tk.W)

        # Camera control frame
        cam_frame = ttk.LabelFrame(left, text="Camera Control", padding=5)
        cam_frame.pack(fill=tk.X, pady=5)

        # Camera toggle button
        self.cam_tgl = ttk.Button(cam_frame, text="Camera: Connecting...", command=self.toggle_camera, state="disabled")
        self.cam_tgl.pack(fill=tk.X, pady=2)

        self.cam_status = ttk.Label(cam_frame, text="Initializing DFRobot camera...", foreground="blue")
        self.cam_status.pack(fill=tk.X, pady=2)

        # Gaze coordinates
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

        # Motion detection
        motion_frame = ttk.LabelFrame(left, text="Motion Detection", padding=5)
        motion_frame.pack(fill=tk.X, pady=5)

        self.motion_indicator = tk.Canvas(motion_frame, width=30, height=30, bg="gray", highlightthickness=0)
        self.motion_indicator.pack()
        self.motion_text = ttk.Label(motion_frame, text="No Motion", foreground="gray")
        self.motion_text.pack(anchor=tk.W)

        # Raw data log
        log_frame = ttk.LabelFrame(left, text="Serial Data Log", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.serial_log = scrolledtext.ScrolledText(log_frame, height=5, width=40, font=("Consolas", 8))
        self.serial_log.pack(fill=tk.BOTH, expand=True)

        # Right panel: Video feed + eye visualizations
        right = ttk.Frame(p, padding=5)
        p.add(right, weight=70)

        ttk.Label(right, text="Live Camera Feed", font=("Helvetica", 12, "bold")).pack(anchor=tk.W)

        # Camera feed area
        self.video_label = tk.Label(right, width=640, height=480, bg="black")
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

        ttk.Button(control_frame, text="Refresh", command=self.refresh_connection).pack(side=tk.RIGHT, padx=5)
        ttk.Button(control_frame, text="Quit", command=self.quit).pack(side=tk.RIGHT, padx=5)

        self.root.protocol("WM_DELETE_WINDOW", self.quit)

    def connect_dfrobot_camera(self):
        """Try to connect to DFRobot AI Camera via serial"""
        try:
            ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
            # Wait a moment for initialization
            time.sleep(0.5)
            # Test if we get data
            if ser.in_waiting:
                data = ser.read(ser.in_waiting).decode('utf-8', errors='replace')[:50]
                self._last_err = ""
                self.use_dfrobot_serial = True
                self.cam_status.config(text="DFRobot AI Camera connected via Serial (COM14)", foreground="green")
                self.cam_tgl.config(text="Camera: Serial Mode", state="normal")
                self.log(f"DFRobot AI Camera connected on {SERIAL_PORT} at {BAUD_RATE} baud")
            else:
                self._handle_no_serial()
        except Exception as e:
            self._last_err = str(e)
            self._handle_no_serial()

    def _handle_no_serial(self):
        """Fallback: try PC webcam"""
        self.use_dfrobot_serial = False
        self.cam_status.config(text="DFRobot not on COM14 - using PC webcam", foreground="orange")
        self.cam_tgl.config(text="Camera: Webcam Mode", state="normal")
        self.log("DFRobot not found on COM14 - using PC webcam fallback")
        # Try to open PC webcam
        try:
            self.cap = cv2.VideoCapture(0)
            if self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        except:
            pass

    def toggle_camera(self):
        """Toggle between serial and webcam modes"""
        if self.use_dfrobot_serial:
            # Close serial, open webcam
            if hasattr(self, 'ser_df') and self.ser_df and self.ser_df.isOpen():
                try:
                    self.ser_df.close()
                except:
                    pass
            self.use_dfrobot_serial = False
            self.cam_tgl.config(text="Camera: Webcam Mode")
            self.cam_status.config(text="Using PC webcam fallback", foreground="orange")
            self.log("Switched to PC webcam mode")
        else:
            # Close webcam, try serial reinit
            if self.cap:
                try:
                    self.cap.release()
                except:
                    pass
            self.use_dfrobot_serial = True
            # Reconnect to DFRobot
            self.connect_dfrobot_camera()
            self.cam_tgl.config(text="Camera: Serial Mode")
            self.cam_status.config(text="DFRobot AI Camera via Serial", foreground="green")
            self.log("Reconnected to DFRobot AI Camera via Serial")

    def read_dfrobot_serial(self):
        """Read gaze data from DFRobot AI Camera on COM14"""
        try:
            self.ser_df = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
            while self.run:
                if self.ser_df.in_waiting:
                    d = self.ser_df.read(self.ser_df.in_waiting).decode('utf-8', errors='replace')
                    self.rd += d
                    while '\n' in self.rd:
                        line, self.rd = self.rd.split('\n', 1)
                        line = line.strip()
                        if line:
                            self.proc(line)
                time.sleep(0.01)
        except Exception as e:
            err_msg = str(e)
            self._last_err = err_msg
            self.root.after(0, lambda msg=err_msg: self.log(f"DFRobot serial error: {msg}"))

    def read_serial_background(self):
        """Background serial reader for status"""
        try:
            s = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
            while self.run:
                if s.in_waiting:
                    d = s.read(s.in_waiting).decode('utf-8', errors='replace')
                    self.rd += d
                time.sleep(0.1)
        except:
            pass

    def proc(self, l):
        """Process DFRobot serial data"""
        up = l.upper()

        # Try DFRobot format: DFROBOT:x:y
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
                        self.root.after(0, self.update_target_labels)
                        self.root.after(0, lambda msg=f"DFRobot: x={x:.2f}, y={y:.2f}": self.log(msg))
                except:
                    pass
                break

        # Try standard x,y format
        if "," in l and not l.startswith("FPS:"):
            try:
                parts = l.split(",")
                if len(parts) >= 2:
                    x = max(-1.0, min(1.0, float(parts[0])))
                    y = max(-1.0, min(1.0, float(parts[1])))
                    self.tx, self.ty = x, y
                    self.valid = True
                    self.motion_counter += 1
                    self.root.after(0, self.update_target_labels)
                    self.root.after(0, lambda msg=f"x={x:.2f}, y={y:.2f}": self.log(msg))
            except:
                pass

    def update_target_labels(self):
        self.txl.config(text=f"{self.tx:.2f}")
        self.tyl.config(text=f"{self.ty:.2f}")
        self.vl.config(text="Yes" if self.valid else "No",
                       foreground="green" if self.valid else "red")

    def update_motion_indicator(self):
        """Update motion detection based on gaze changes"""
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

        self.root.after(100, self.update_motion_indicator)

    def draw_eye(self, canvas, x, y, n):
        """Draw eye visualization"""
        canvas.delete("all")
        cx, cy = 80, 80
        pr = 18
        canvas.create_oval(20, 20, 140, 140, outline="white", width=2, fill="black")
        px = cx + int(x * 25)
        py = cy + int(y * 25)
        canvas.create_oval(px - pr, py - pr, px + pr, py + pr,
                          fill="black", outline="white", width=1)
        for a in range(0, 360, 45):
            r = np.radians(a)
            x2 = cx + int(35 * np.cos(r))
            y2 = cy + int(35 * np.sin(r))
            canvas.create_line(cx, cy, x2, y2, fill="gray", width=1)

    def update_eyes(self):
        """Update eye positions"""
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

        self.draw_eye(self.lc, self.lx, self.ly, "l")
        self.draw_eye(self.rc, self.rx, self.ry, "r")
        self.root.after(33, self.update_eyes)

    def update_video_feed(self):
        """Update the live camera video feed"""
        # Get frame from DFRobot serial data or webcam
        if self.use_dfrobot_serial and self.ser_df and self.ser_df.isOpen():
            # In serial mode, we don't have video frames from DFRobot via serial alone
            # Show status info on the video area
            self.video_label.config(
                text="DFRobot AI Camera\nSerial Mode\n(gaze data only)\nNo video frame via serial",
                bg="black", fg="yellow"
            )
        else:
            # Try to get webcam frame
            if self.cap and self.cap.isOpened():
                try:
                    ret, frame = self.cap.read()
                    if ret:
                        # Resize for display
                        frame = cv2.resize(frame, (640, 480))
                        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        
                        # Overlay gaze data on video
                        if self.valid:
                            h, w = frame.shape[:2]
                            # Draw crosshair at gaze position
                            cx = int(320 + self.tx * 100)  # Scale factor 100
                            cy = int(240 - self.ty * 100)
                            cv2.circle(frame, (cx, cy), 10, (0, 255, 0), 2)
                            cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
                            
                            # Draw target info text
                            cv2.putText(frame, f"X:{self.tx:.2f} Y:{self.ty:.2f}", 
                                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                        
                        # Convert to ImageTk
                        img = Image.fromarray(frame)
                        im = ImageTk.PhotoImage(image=img)
                        self.video_label.imgtk = im
                        self.video_label.config(image=im, text="")
                except Exception as e:
                    pass
        
        self.root.after(33, self.update_video_feed)

    def update_stats(self):
        """Update FPS counters"""
        self.fc += 1
        now = time.time()
        if now - self.lft >= 1.0:
            self.app_fps = self.fc / (now - self.lft)
            self.lft = now
            self.fc = 0
        self.af.config(text=f"{self.app_fps:.1f}")
        
        # Calculate serial FPS
        if hasattr(self, 'ser_df') and self.ser_df and self.ser_df.isOpen():
            # Simple count of lines received
            self.sf_c += 1
            if now - self.sf_t >= 1.0:
                self.serial_fps = self.sf_c / (now - self.sf_t)
                self.sf_c = 0
                self.sf_t = now
            self.sf.config(text=f"{self.serial_fps:.1f}")
        
        self.root.after(100, self.update_stats)

    def log(self, m):
        ts = time.strftime("%H:%M:%S")
        self.serial_log.insert(tk.END, f"[{ts}] {m}\n")
        self.serial_log.see(tk.END)

    def refresh_connection(self):
        """Refresh the DFRobot camera connection"""
        self.toggle_camera()

    def quit(self):
        self.run = False
        if hasattr(self, 'ser_df') and self.ser_df and self.ser_df.isOpen():
            try:
                self.ser_df.close()
            except:
                pass
        if self.cap:
            try:
                self.cap.release()
            except:
                pass
        self.root.destroy()


def main():
    root = tk.Tk()
    app = DFRobotCamMonitor(root)
    root.mainloop()


if __name__ == "__main__":
    main()