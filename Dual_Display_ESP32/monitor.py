#!/usr/bin/env python
"""
Desktop Monitoring Application for Dual ESP32 Projects
Shows live pupil tracking from DFRobot AI Camera and Robot Eyes displays.
Monitors two serial ports: COM5 (Robot Eyes) and COM14 (DFRobot AI Camera).
Displays pupil movement, FPS, and tracking status.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import serial
import struct
import time
import threading
import numpy as np
import cv2
import sys
import os

# Serial port configuration
ROBOT_EYES_PORT = 'COM5'
DFROBOT_CAMERA_PORT = 'COM14'  # DFRobot AI Camera
BAUD_RATE = 115200

# Eye position constants
EYE_IMAGE_WIDTH = 160
EYE_IMAGE_HEIGHT = 160
MAX_2D_OFFSET_PIXELS = 40

class PupilTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Dual Display Robot Eyes - Pupil Tracker Monitor")
        self.root.geometry("1000x600")
        self.root.resizable(False, False)
        
        # Eye positions (normalized -1.0 to 1.0)
        self.left_eye_pos = [0.0, 0.0]
        self.right_eye_pos = [0.0, 0.0]
        
        # Target positions (from DFRobot camera)
        self.target_x = 0.0
        self.target_y = 0.0
        self.target_valid = False
        
        # FPS counters
        self.fps = 0.0
        self.frame_counts = 0
        self.last_fps_time = time.time()
        
        # Serial threads
        self.running = True
        self.robot_data = ""
        self.dfrobot_data = ""
        
        # UI Setup
        self.setup_ui()
        
        # Start serial reading threads
        self.robot_thread = threading.Thread(target=self.read_robot_serial, daemon=True)
        self.dfrobot_thread = threading.Thread(target=self.read_dfrobot_serial, daemon=True)
        self.robot_thread.start()
        self.dfrobot_thread.start()
        
        # FPS update timer
        self.update_fps()
        
    def setup_ui(self):
        # Main frames
        left_frames = ttk.Frame(self.root, padding=5)
        left_frames.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        right_frames = ttk.Frame(self.root, padding=5)
        right_frames.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Left panels: Robot Eyes status
        ttk.Label(left_frames, text="Robot Eyes Displays", font=("Helvetica", 12, "bold")).pack(anchor=tk.W)
        
        # Left eye visualization
        left_eye_frame = ttk.LabelFrame(left_frames, text="Left Eye", padding=5)
        left_eye_frame.pack(fill=tk.X, pady=5)
        
        self.left_canvas = tk.Canvas(left_eye_frame, width=160, height=160, bg="black", highlightthickness=0)
        self.left_canvas.pack()
        
        # Right eye visualization
        right_eye_frame = ttk.LabelFrame(left_frames, text="Right Eye", padding=5)
        right_eye_frame.pack(fill=tk.X, pady=5)
        
        self.right_canvas = tk.Canvas(right_eye_frame, width=160, height=160, bg="black", highlightthickness=0)
        self.right_canvas.pack()
        
        # Status info
        info_frame = ttk.LabelFrame(left_frames, text="Status", padding=5)
        info_frame.pack(fill=tk.X, pady=10)
        
        self.status_text = scrolledtext.ScrolledText(info_frame, height=6, width=30, font=("Consolas", 9))
        self.status_text.pack()
        
        # Right panels: DFRobot Camera info
        ttk.Label(right_frames, text="DFRobot AI Camera Input", font=("Helvetica", 12, "bold")).pack(anchor=tk.W)
        
        # Target coordinates display
        target_frame = ttk.LabelFrame(right_frames, text="Target Gaze Position", padding=5)
        target_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(target_frame, text="X:").pack(anchor=tk.W)
        self.target_x_label = ttk.Label(target_frame, text="0.00", foreground="green")
        self.target_x_label.pack(anchor=tk.W)
        
        ttk.Label(target_frame, text="Y:").pack(anchor=tk.W)
        self.target_y_label = ttk.Label(target_frame, text="0.00", foreground="green")
        self.target_y_label.pack(anchor=tk.W)
        
        ttk.Label(target_frame, text="Valid:").pack(anchor=tk.W)
        self.target_valid_label = ttk.Label(target_frame, text="No", foreground="red")
        self.target_valid_label.pack(anchor=tk.W)
        
        # FPS display
        fps_frame = ttk.LabelFrame(right_frames, text="Performance", padding=5)
        fps_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(fps_frame, text="FPS:").pack(anchor=tk.W)
        self.fps_label = ttk.Label(fps_frame, text="0.0", foreground="")
        self.fps_label.pack(anchor=tk.W)
        
        # Raw data logs
        log_frame = ttk.LabelFrame(right_frames, text="Raw Serial Data Log", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, width=40, font=("Consolas", 8))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Control buttons
        control_frame = ttk.Frame(self.root, padding=5)
        control_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        ttk.Button(control_frame, text="Clear Log", command=self.clear_log).pack(side=tk.RIGHT, padx=5)
        ttk.Button(control_frame, text="Refresh Port", command=self.refresh_ports).pack(side=tk.RIGHT, padx=5)
        
        # Initial status - update_status called from main()
    
    def read_robot_serial(self):
        """Read from Robot Eyes ESP32 (COM5)"""
        try:
            ser = serial.Serial(ROBOT_EYES_PORT, BAUD_RATE, timeout=1)
            print(f"Robot Eyes serial opened: {ROBOT_EYES_PORT}")
            
            while self.running:
                try:
                    if ser.in_waiting:
                        data = ser.read(ser.in_waiting).decode('utf-8', errors='replace')
                        self.robot_data += data
                        # Process complete lines
                        while '\n' in self.robot_data:
                            line, self.robot_data = self.robot_data.split('\n', 1)
                            line = line.strip()
                            if line:
                                self.process_robot_serial(line)
                except Exception as e:
                    print(f"Robot serial error: {e}")
                    self.root.after(0, self.log_message, f"Robot Serial Error: {e}")
                time.sleep(0.01)
        except Exception as e:
            self.root.after(0, self.log_message, f"Could not open Robot Eyes port {ROBOT_EYES_PORT}: {e}")
    
    def read_dfrobot_serial(self):
        """Read from DFRobot AI Camera (COM14)"""
        try:
            ser = serial.Serial(DFROBOT_CAMERA_PORT, BAUD_RATE, timeout=1)
            print(f"DFRobot Camera serial opened: {DFROBOT_CAMERA_PORT}")
            
            while self.running:
                try:
                    if ser.in_waiting:
                        data = ser.read(ser.in_waiting).decode('utf-8', errors='replace')
                        self.dfrobot_data += data
                        # Process complete lines
                        while '\n' in self.dfrobot_data:
                            line, self.dfrobot_data = self.dfrobot_data.split('\n', 1)
                            line = line.strip()
                            if line:
                                self.process_dfrobot_serial(line)
                except Exception as e:
                    print(f"DFRobot serial error: {e}")
                    self.root.after(0, self.log_message, f"DFRobot Serial Error: {e}")
                time.sleep(0.01)
        except Exception as e:
            self.root.after(0, self.log_message, f"Could not open DFRobot port {DFROBOT_CAMERA_PORT}: {e}")
    
    def process_robot_serial(self, line):
        """Process Robot Eyes serial data - mainly FPS and status"""
        # Could log or parse robot-specific data
        if line.startswith("FPS:"):
            try:
                fps_val = float(line.replace("FPS:", "").strip())
                self.fps = fps_val
            except:
                pass
        elif line.startswith("Booting") or line.startswith("Initialization"):
            self.log_message(f"Robot: {line}")
    
    def process_dfrobot_serial(self, line):
        """Process DFRobot AI Camera serial data"""
        # Try new format: DFROBOT:x:y or dfrobot:x:y
        line_upper = line.upper()
        if line_upper.startswith("DFROBOT:") or line_upper.startswith("DFROBOT:"):
            # Parse: DFROBOT:x:y
            try:
                # Remove prefix and parse
                data_str = line.replace("DFROBOT:", "").replace("dfrobot:", "").strip()
                parts = data_str.split(":")
                
                if len(parts) >= 2:
                    x = float(parts[0])
                    y = float(parts[1])
                    
                    # Clamp to valid range
                    x = max(-1.0, min(1.0, x))
                    y = max(-1.0, min(1.0, y))
                    
                    # Update target
                    self.target_x = x
                    self.target_y = y
                    self.target_valid = True
                    
                    # Update UI labels
                    self.root.after(0, self.update_target_labels)
                    
                    # Log
                    self.root.after(0, self.log_message, f"DFRobot: x={x:.2f}, y={y:.2f}")
            except ValueError as e:
                self.root.after(0, self.log_message, f"DFRobot parse error: {e} - data: {line}")
        
        # Also try standard format: x,y
        elif "," in line and not line.startswith("FPS:"):
            try:
                parts = line.split(",")
                if len(parts) >= 2:
                    x = float(parts[0].strip())
                    y = float(parts[1].strip())
                    x = max(-1.0, min(1.0, x))
                    y = max(-1.0, min(1.0, y))
                    
                    self.target_x = x
                    self.target_y = y
                    self.target_valid = True
                    self.root.after(0, self.update_target_labels)
                    self.root.after(0, self.log_message, f"Standard: x={x:.2f}, y={y:.2f}")
            except ValueError:
                pass
    
    def update_target_labels(self):
        """Update the target coordinate display labels"""
        self.target_x_label.config(text=f"{self.target_x:.2f}")
        self.target_y_label.config(text=f"{self.target_y:.2f}")
        if self.target_valid:
            self.target_valid_label.config(text="Yes")
            self.target_valid_label.config(foreground="green")
        else:
            self.target_valid_label.config(text="No")
            self.target_valid_label.config(foreground="red")
    
    def update_fps(self):
        """Update FPS display"""
        current_time = time.time()
        self.frame_counts += 1
        
        if current_time - self.last_fps_time >= 1.0:
            self.fps = self.frame_counts / (current_time - self.last_fps_time)
            self.last_fps_time = current_time
            self.frame_counts = 0
        
        self.fps_label.config(text=f"{self.fps:.1f}")
        self.root.after(100, self.update_fps)
    
    def update_eye_positions(self):
        """Update the eye canvas visualizations"""
        # This is called periodically to animate eye movement toward target
        # Simple LERP interpolation toward target
        speed = 0.15  # Interpolation speed
        
        # Move eyes toward target
        if self.target_valid:
            # Left eye
            self.left_eye_pos[0] += (self.target_x - self.left_eye_pos[0]) * speed
            self.left_eye_pos[1] += (self.target_y - self.left_eye_pos[1]) * speed
            
            # Right eye (same tracking)
            self.right_eye_pos[0] += (self.target_x - self.right_eye_pos[0]) * speed
            self.right_eye_pos[1] += (self.target_y - self.right_eye_pos[1]) * speed
        else:
        # Idle: slowly drift/saccade
            import random
            if random.random() < 0.02:  # Every ~50 frames
                self.left_eye_pos = [random.uniform(-0.8, 0.8), random.uniform(-0.8, 0.8)]
                self.right_eye_pos = [random.uniform(-0.8, 0.8), random.uniform(-0.8, 0.8)]
        
        # Draw left eye
        self.draw_eye(self.left_canvas, self.left_eye_pos, "left")
        
        # Draw right eye
        self.draw_eye(self.right_canvas, self.right_eye_pos, "right")
        
        # Schedule next update
        self.root.after(33, self.update_eye_positions)  # ~30 FPS
    
    def draw_eye(self, canvas, pos, eye_name):
        """Draw a simplified eye visualization on canvas"""
        canvas.delete("all")
        
        cx, cy = 80, 80  # Center of
        radius = 70
        
        # Draw eye white/sclera
        canvas.create_oval(10, 10, 150, 150, outline="white", width=2, fill="black")
        
        # Draw iris area
        iris_radius = int(50 + abs(pos[0]) * 15 + abs(pos[1]) * 15)
        iris_x = cx + int(pos[0] * 25)
        iris_y = cy + int(pos[1] * 25)
        
        # Draw pupil (small circle)
        pupil_radius = 15
        canvas.create_oval(
            iris_x - pupil_radius, iris_y - pupil_radius,
            iris_x + pupil_radius, iris_y + pupil_radius,
            fill="black", outline="white", width=1
        )
        
        # Draw iris circle (semi-transparent effect with lines)
        for angle in range(0, 360, 30):
            rad = np.radians(angle)
            x2 = cx + int(40 * np.cos(rad))
            y2 = cy + int(40 * np.sin(rad))
            canvas.create_line(cx, cy, x2, y2, fill="gray", width=1)
    
    def update_status(self):
        """Periodic status update"""
        # Update FPS in status log
        self.status_text.delete(1.0, tk.END)
        self.status_text.insert(tk.END, f"FPS: {self.fps:.1f}\n")
        self.status_text.insert(tk.END, f"Target Valid: {'Yes' if self.target_valid else 'No'}\n")
        self.status_text.insert(tk.END, f"Target: ({self.target_x:.2f}, {self.target_y:.2f})\n")
        self.status_text.insert(tk.END, f"Left Eye: ({self.left_eye_pos[0]:.2f}, {self.left_eye_pos[1]:.2f})\n")
        self.status_text.insert(tk.END, f"Right Eye: ({self.right_eye_pos[0]:.2f}, {self.right_eye_pos[1]:.2f})\n")
        
        # Schedule next
        self.root.after(100, self.update_status)
    
    def log_message(self, message):
        """Add message to serial log"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
    
    def clear_log(self):
        """Clear the serial log"""
        self.log_text.delete(1.0, tk.END)
    
    def refresh_ports(self):
        """Refresh serial port connections"""
        self.root.after(500, self.root.quit)
        self.root.after(100, lambda: self.root.destroy())
    
    def on_closing(self):
        """Handle window close"""
        self.running = False
        self.root.destroy()


def main():
    root = tk.Tk()
    app = PupilTrackerApp(root)
    
    # Start eye animation
    app.update_eye_positions()
    
    # Start status updates
    app.update_status()
    
    # Handle window close
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    # Start GUI main loop
    root.mainloop()


if __name__ == "__main__":
    main()