"""
camera_intel.py - Camera Intelligence (Features 21-40)
"""
import time, logging
from typing import Dict, Any, List, Optional, Tuple
logger = logging.getLogger("tank.ai.camera_intel")
try:
    import cv2; CV2_AVAILABLE = True
except ImportError:
    cv2 = None; CV2_AVAILABLE = False

class CameraDevice:
    def __init__(self, device_id, name, source="usb"):
        self.device_id = device_id; self.name = name; self.source = source
        self.connected = False; self.fps = 0; self.latency_ms = 0
        self.resolution = (0,0); self.frame_count = 0; self.drop_count = 0; self.cap = None
    def connect(self):
        if not CV2_AVAILABLE: return False
        try:
            self.cap = cv2.VideoCapture(self.device_id)
            if self.cap.isOpened():
                self.connected = True
                self.resolution = (int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
                return True
        except Exception: pass
        return False
    def read_frame(self):
        if not self.cap or not self.connected: return None
        start = time.time()
        ret, frame = self.cap.read()
        if ret:
            self.frame_count += 1; self.latency_ms = (time.time()-start)*1000; return frame
        self.drop_count += 1; return None
    def disconnect(self):
        if self.cap: self.cap.release(); self.cap = None
        self.connected = False

class CameraIntelligence:
    def __init__(self):
        self.cameras = {}
        self._monitoring = False
    def discover_cameras(self):
        found = []
        for i in range(10):
            try:
                if CV2_AVAILABLE:
                    cap = cv2.VideoCapture(i)
                    if cap.isOpened():
                        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        cap.release()
                        cam = CameraDevice(i, f"cam_{i}")
                        cam.resolution = (w,h); cam.connected = True
                        self.cameras[i] = cam; found.append({"id": i, "resolution": (w,h)})
            except Exception: pass
        return found
    def score_quality(self, frame):
        if not CV2_AVAILABLE or frame is None: return {"quality_score": 0}
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
        brightness = float(sum(sum(gray))/gray.size)
        return {"quality_score": round(min(100, sharpness/5+brightness/2.55),1), "sharpness": round(sharpness,2), "brightness": round(brightness,1)}
    def detect_motion_blur(self, frame):
        if not CV2_AVAILABLE or frame is None: return {"blurred": False}
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        score = cv2.Laplacian(gray, cv2.CV_64F).var()
        return {"blur_score": round(score,2), "blurred": score < 100}
    def select_best_camera(self):
        best = None; best_score = -1
        for cid, cam in self.cameras.items():
            if cam.connected:
                score = cam.resolution[0] * 0.01 - cam.drop_count * 0.1
                if score > best_score: best_score = score; best = cid
        return best
    def get_status(self):
        return {"cameras_found": len(self.cameras), "cameras_connected": sum(1 for c in self.cameras.values() if c.connected), "devices": {str(k): {"connected": v.connected, "resolution": v.resolution} for k,v in self.cameras.items()}}
