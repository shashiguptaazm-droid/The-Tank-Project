"""
spatial_ai.py - Depth/3D/Spatial AI (Features 101-120)
"""
import time, math, logging
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

logger = logging.getLogger('tank.ai.depth')

class SpatialAI:
    def __init__(self, grid_resolution=0.1, grid_size=100):
        self.grid_resolution = grid_resolution
        self.grid_size = grid_size
        self.occupancy_grid = np.zeros((grid_size, grid_size), dtype=np.float32)
        self.voxel_map = {}
        self.static_obstacles = []
        self.dynamic_obstacles = []
        self.spatial_memory = []

    def process_depth_frame(self, depth_frame):
        if depth_frame is None: return {'status': 'no_frame'}
        valid = depth_frame[depth_frame > 0]
        return {'min_depth': float(np.min(valid)) if len(valid) > 0 else 999,
                'max_depth': float(np.max(depth_frame)),
                'mean_depth': float(np.mean(valid)) if len(valid) > 0 else 0,
                'confidence': float(1.0 - np.std(valid)/5.0) if len(valid) > 0 else 0}

    def generate_depth_map(self, frame):
        if frame is None: return None
        import cv2
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return gray.astype(np.float32) / 255.0 * 10.0

    def filter_depth(self, depth):
        if depth is None: return depth
        import cv2
        filtered = depth.copy()
        filtered[filtered <= 0] = np.inf
        return cv2.medianBlur(filtered.astype(np.float32), 3)

    def extract_3d_obstacles(self, depth, camera_matrix=None):
        obstacles = []
        if depth is None: return obstacles
        h, w = depth.shape[:2]
        for y in range(0, h, 20):
            for x in range(0, w, 20):
                d = depth[y, x]
                if 0 < d < 5.0:
                    obstacles.append({'x': x, 'y': y, 'depth': float(d)})
        return obstacles

    def fuse_camera_lidar(self, detections, lidar_points):
        fused = []
        for det in detections:
            cx, cy = det.get('center', (0, 0))
            nearby = [p[2] for p in (lidar_points or []) if len(p) >= 3 and abs(p[0]-cx) < 50 and abs(p[1]-cy) < 50]
            det['fused_depth'] = float(np.mean(nearby)) if nearby else None
            fused.append(det)
        return fused

    def update_occupancy_grid(self, lidar_points, robot_pose=(0,0,0)):
        if lidar_points is None: return
        rx, ry, rt = robot_pose
        for pt in lidar_points:
            if len(pt) < 2: continue
            angle = math.atan2(pt[1], pt[0])
            dist = math.sqrt(pt[0]**2 + pt[1]**2)
            wx = int((rx + dist*math.cos(angle+rt))/self.grid_resolution + self.grid_size//2)
            wy = int((ry + dist*math.sin(angle+rt))/self.grid_resolution + self.grid_size//2)
            if 0 <= wx < self.grid_size and 0 <= wy < self.grid_size:
                self.occupancy_grid[wy, wx] = min(1.0, self.occupancy_grid[wy, wx]+0.1)

    def update_voxel_map(self, point, value=1.0):
        vs = 0.2
        key = (int(point[0]/vs), int(point[1]/vs), int(point[2]/vs))
        self.voxel_map[key] = min(1.0, self.voxel_map.get(key,0)+value)

    def classify_obstacles(self, lidar_points, prev_points=None):
        self.static_obstacles = []
        if lidar_points is None: return {'static': 0, 'dynamic': 0}
        for pt in lidar_points:
            if len(pt) >= 2:
                self.static_obstacles.append({'x': float(pt[0]), 'y': float(pt[1])})
        return {'static': len(self.static_obstacles), 'dynamic': len(self.dynamic_obstacles)}

    def add_spatial_memory(self, position, label, confidence=1.0):
        self.spatial_memory.append({'pos': position, 'label': label, 'confidence': confidence, 'time': time.time()})

    def query_spatial_memory(self, label):
        return [m for m in self.spatial_memory if m['label'] == label]

    def filter_point_cloud(self, points, min_range=0.1, max_range=10.0):
        if points is None or len(points) == 0: return np.array([])
        dists = np.linalg.norm(points[:,:3], axis=1) if points.shape[1] >= 3 else np.array([])
        return points[(dists >= min_range) & (dists <= max_range)]

    def estimate_ground_plane(self, points):
        if points is None or len(points) < 10: return {'ground_height': 0}
        return {'ground_height': float(np.percentile(points[:,2], 20))}

    def estimate_free_space(self, depth):
        if depth is None: return 0
        valid = depth[depth > 0]
        return round(float(np.sum(valid > 1.0) / max(1, len(valid)) * 100), 1)

    def benchmark(self, points, iterations=100):
        start = time.time()
        for _ in range(iterations):
            self.filter_point_cloud(points)
        elapsed = (time.time()-start)*1000
        return {'iterations': iterations, 'total_ms': round(elapsed,2), 'per_iter_ms': round(elapsed/iterations,3)}

    def get_visualization_data(self):
        return {'occupancy_occupied': int(np.sum(self.occupancy_grid > 0.5)),
                'voxel_count': len(self.voxel_map), 'static_obstacles': len(self.static_obstacles),
                'spatial_memory': len(self.spatial_memory)}

    def get_status(self):
        return {'grid_size': self.grid_size, 'voxel_count': len(self.voxel_map),
                'spatial_memory': len(self.spatial_memory), 'static_obstacles': len(self.static_obstacles)}
