#!/usr/bin/env python3
"""Face recognition module — detect, enroll, recognize people.

Uses OpenCV Haar cascade for detection + histogram comparison for recognition.
Lightweight, no extra dependencies beyond opencv-python.

Usage:
    from face_db import FaceDB
    db = FaceDB()
    names = db.recognize_in_frame("data/frames/latest.jpg")
    db.enroll(image_path, "John")
"""

from __future__ import annotations

import json
import os
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

_DB_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "faces"
_DB_FILE = _DB_DIR / "faces.json"
_EMBEDDINGS_FILE = _DB_DIR / "embeddings.pkl"


class FaceDB:
    """Face database — enroll and recognize people."""

    def __init__(self):
        _DB_DIR.mkdir(parents=True, exist_ok=True)
        self._faces: Dict[str, dict] = {}  # name -> {embedding, image_path, count}
        self._load()
        # Haar cascade for face detection
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self._detector = cv2.CascadeClassifier(cascade_path)

    def _load(self):
        if _DB_FILE.exists():
            try:
                self._faces = json.loads(_DB_FILE.read_text())
            except Exception:
                self._faces = {}
        if _EMBEDDINGS_FILE.exists():
            try:
                with open(_EMBEDDINGS_FILE, "rb") as f:
                    self._embeddings = pickle.load(f)
            except Exception:
                self._embeddings = {}
        else:
            self._embeddings = {}

    def _save(self):
        _DB_FILE.write_text(json.dumps(self._faces, indent=2))
        with open(_EMBEDDINGS_FILE, "wb") as f:
            pickle.dump(self._embeddings, f)

    def _get_embedding(self, face_img: np.ndarray) -> np.ndarray:
        """Compute a face embedding using color histogram + LBP texture."""
        # Resize to standard size
        face = cv2.resize(face_img, (100, 100))

        # Color histogram (HSV)
        hsv = cv2.cvtColor(face, cv2.COLOR_BGR2HSV)
        hist_h = cv2.calcHist([hsv], [0], None, [50], [0, 180])
        hist_s = cv2.calcHist([hsv], [1], None, [50], [0, 256])
        cv2.normalize(hist_h, hist_h)
        cv2.normalize(hist_s, hist_s)

        # Grayscale histogram
        gray = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
        hist_g = cv2.calcHist([gray], [0], None, [50], [0, 256])
        cv2.normalize(hist_g, hist_g)

        # Combine into one embedding vector
        embedding = np.concatenate([
            hist_h.flatten(),
            hist_s.flatten(),
            hist_g.flatten(),
        ])
        return embedding

    def _similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Compare two embeddings. Returns 0-1 (1 = identical)."""
        # Correlation coefficient
        try:
            corr = cv2.compareHist(
                emb1.astype(np.float32),
                emb2.astype(np.float32),
                cv2.HISTCMP_CORREL,
            )
            return max(0.0, corr)
        except Exception:
            return 0.0

    def detect_faces(self, image_path: str) -> List[Tuple[int, int, int, int, np.ndarray]]:
        """Detect faces using YOLO person bbox + face region crop.
        Falls back to Haar cascade. Returns list of (x, y, w, h, face_img)."""
        img = cv2.imread(image_path)
        if img is None:
            return []
        h_img, w_img = img.shape[:2]

        # Strategy 1: Use YOLO to find person, then crop face region (top 40% of body)
        try:
            from ultralytics import YOLO
            model = YOLO("yolov8n.pt")
            results = model(image_path, verbose=False)
            faces = []
            for r in results:
                for box in r.boxes:
                    cls = int(box.cls[0])
                    if cls == 0:  # person class
                        x1, y1, x2, y2 = box.xyxy[0].tolist()
                        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                        bw, bh = x2 - x1, y2 - y1
                        # Face is roughly top 30-40% of body, centered
                        fx1 = x1 + int(bw * 0.15)
                        fy1 = y1
                        fx2 = x2 - int(bw * 0.15)
                        fy2 = y1 + int(bh * 0.4)
                        fw, fh = fx2 - fx1, fy2 - fy1
                        if fw > 30 and fh > 30:
                            face_img = img[fy1:fy2, fx1:fx2].copy()
                            faces.append((fx1, fy1, fw, fh, face_img))
            if faces:
                return faces
        except Exception:
            pass

        # Strategy 2: Haar cascade fallback
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        detected = self._detector.detectMultiScale(
            gray, scaleFactor=1.05, minNeighbors=3, minSize=(40, 40)
        )
        results = []
        for (x, y, w, h) in detected:
            face_img = img[y:y+h, x:x+w].copy()
            results.append((x, y, w, h, face_img))
        return results

    def recognize_in_frame(self, image_path: str, threshold: float = 0.35) -> List[Dict]:
        """Detect and recognize faces in a frame.
        Returns list of {name, confidence, x, y, w, h, is_known}.
        """
        faces = self.detect_faces(image_path)
        if not faces:
            return []

        results = []
        for x, y, w, h, face_img in faces:
            embedding = self._get_embedding(face_img)
            best_name = None
            best_score = 0.0

            for name, data in self._faces.items():
                if name in self._embeddings:
                    score = self._similarity(embedding, self._embeddings[name])
                    if score > best_score:
                        best_score = score
                        best_name = name

            if best_name and best_score >= threshold:
                results.append({
                    "name": best_name,
                    "confidence": round(best_score, 2),
                    "x": int(x), "y": int(y), "w": int(w), "h": int(h),
                    "is_known": True,
                })
            else:
                results.append({
                    "name": "unknown",
                    "confidence": 0.0,
                    "x": int(x), "y": int(y), "w": int(w), "h": int(h),
                    "is_known": False,
                })

        return results

    def enroll(self, image_path: str, name: str) -> bool:
        """Enroll a face from an image with a given name.
        If the name already exists, averages the new embedding with existing
        for better multi-sample recognition.
        """
        faces = self.detect_faces(image_path)
        if not faces:
            return False

        # Use the largest face
        largest = max(faces, key=lambda f: f[2] * f[3])
        _, _, _, _, face_img = largest
        embedding = self._get_embedding(face_img)

        # Save face crop
        face_path = _DB_DIR / f"{name.lower().replace(' ', '_')}.jpg"
        cv2.imwrite(str(face_path), face_img)

        # Average with existing embedding for better accuracy
        if name in self._embeddings:
            count = self._faces.get(name, {}).get("count", 0)
            old_emb = self._embeddings[name]
            # Running average: new_avg = (old * n + new) / (n + 1)
            self._embeddings[name] = (old_emb * count + embedding) / (count + 1)
        else:
            self._embeddings[name] = embedding

        # Store
        self._faces[name] = {
            "image": str(face_path),
            "count": self._faces.get(name, {}).get("count", 0) + 1,
        }
        self._save()
        return True

    def list_known(self) -> List[str]:
        """List all known face names."""
        return list(self._faces.keys())

    def forget(self, name: str) -> bool:
        """Remove a face from the database."""
        if name in self._faces:
            del self._faces[name]
            self._embeddings.pop(name, None)
            face_path = _DB_DIR / f"{name.lower().replace(' ', '_')}.jpg"
            if face_path.exists():
                face_path.unlink()
            self._save()
            return True
        return False
