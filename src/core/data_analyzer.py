"""
Модуль для анализа данных трекинга (по каждой частице отдельно)
"""
import logging
import numpy as np
from typing import List, Dict, Optional
import matplotlib.pyplot as plt
import csv

logger = logging.getLogger(__name__)


class DataAnalyzer:
    def __init__(self):
        self.data: List[Dict] = []
        self.tracks: Dict[int, List[Dict]] = {}
        self.analysis_results: Dict = {}
        self.selected_track: Optional[int] = None

    def load_data(self, tracking_data: List[Dict]):
        self.data = tracking_data
        self.tracks = {}
        for p in tracking_data:
            tid = p.get('track_id')
            self.tracks.setdefault(tid, []).append(p)
        for tid in self.tracks:
            self.tracks[tid].sort(key=lambda p: p['timestamp'])

    def get_track_ids(self) -> List[int]:
        return sorted([t for t in self.tracks.keys() if t is not None])

    def get_track_points(self, track_id: int) -> List[Dict]:
        return self.tracks.get(track_id, [])

    def select_track(self, track_id: int) -> Dict:
        self.selected_track = track_id
        self.analysis_results = self._analyze(self.get_track_points(track_id))
        return self.analysis_results

    @staticmethod
    def _velocity(pts: List[Dict]) -> List[float]:
        if len(pts) < 2:
            return [0.0] * len(pts)
        velocities = [0.0]
        for i in range(1, len(pts)):
            dt = pts[i]['timestamp'] - pts[i-1]['timestamp']
            if dt <= 0:
                velocities.append(0.0)
                continue
            dx = pts[i]['x'] - pts[i-1]['x']
            dy = pts[i]['y'] - pts[i-1]['y']
            velocities.append(float(np.hypot(dx, dy) / dt))
        return velocities

    @staticmethod
    def _total_distance(pts: List[Dict]) -> float:
        if len(pts) < 2:
            return 0.0
        d = 0.0
        for i in range(1, len(pts)):
            d += float(np.hypot(pts[i]['x'] - pts[i-1]['x'], pts[i]['y'] - pts[i-1]['y']))
        return d

    def smooth_data(self, data: List[float], window_size: int = 5) -> List[float]:
        if len(data) < window_size:
            return list(data)
        window = np.ones(window_size) / window_size
        return np.convolve(data, window, mode='same').tolist()

    def calculate_std(self, data: List[float]) -> float:
        """Среднеквадратичное отклонение (СКО) ряда"""
        if len(data) < 2:
            return 0.0
        return float(np.std(data))

    @staticmethod
    def _rolling_std(arr, window: int) -> np.ndarray:
        arr = np.asarray(arr, dtype=float)
        n = len(arr)
        if n == 0:
            return np.array([])
        if n < 3:
            return np.zeros(n)
        w = min(window, n)
        kernel = np.ones(w) / w
        mean = np.convolve(arr, kernel, mode='same')
        meansq = np.convolve(arr * arr, kernel, mode='same')
        var = np.maximum(meansq - mean ** 2, 0.0)
        return np.sqrt(var)

    def _analyze(self, pts: List[Dict]) -> Dict:
        if not pts:
            return {}
        timestamps = [p['timestamp'] for p in pts]
        xs = np.array([p['x'] for p in pts], dtype=float)
        ys = np.array([p['y'] for p in pts], dtype=float)
        velocities = self._velocity(pts)
        smooth_v = self.smooth_data(velocities)
        total_time = timestamps[-1] - timestamps[0] if timestamps else 0.0

        cx, cy = float(xs.mean()), float(ys.mean())
        radius = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2)
        window = min(15, max(3, len(pts) // 5))

        self.analysis_results = {
            'track_id': pts[0].get('track_id'),
            'timestamps': timestamps,
            'x_coords': xs.tolist(),
            'y_coords': ys.tolist(),
            'velocities': smooth_v,
            'std_series': self._rolling_std(radius, window).tolist(),
            'std_x_series': self._rolling_std(xs, window).tolist(),
            'std_y_series': self._rolling_std(ys, window).tolist(),
            'total_time': total_time,
            'total_distance': self._total_distance(pts),
            'max_velocity': float(max(smooth_v)) if smooth_v else 0.0,
            'avg_velocity': float(np.mean(smooth_v)) if smooth_v else 0.0,
            'std_velocity': self.calculate_std(velocities),
            'std_x': float(np.std(xs)),
            'std_y': float(np.std(ys)),
            'std_position': float(np.std(radius)),
            'n_points': len(pts),
        }
        return self.analysis_results

    def analyze_movement(self) -> Dict:
        track_ids = self.get_track_ids()
        if not track_ids:
            return {}
        tid = self.selected_track if self.selected_track in track_ids else track_ids[0]
        return self.select_track(tid)

    # ======================== ГРАФИКИ ========================

    def create_trajectory_plot(self) -> plt.Figure:
        fig, ax = plt.subplots(figsize=(10, 8))
        r = self.analysis_results
        xs = r.get('x_coords', [])
        ys = r.get('y_coords', [])
        if xs:
            mx = sum(xs) / len(xs)
            my = sum(ys) / len(ys)
            xs_c = [x - mx for x in xs]
            ys_c = [y - my for y in ys]
            ax.plot(xs_c, ys_c, 'b-', alpha=0.7, linewidth=2)
            ax.scatter(xs_c, ys_c, c=range(len(xs_c)), cmap='viridis', s=30, alpha=0.6)
            ax.scatter([0], [0], c='r', marker='x', s=80)
            ax.set_xlabel('X, пикс')
            ax.set_ylabel('Y, пикс')
            ax.set_title(f"Траектория частицы ID {r.get('track_id')} (относительно центра)")
            ax.grid(True, alpha=0.3)
            ax.set_aspect('equal', adjustable='datalim')
            ax.invert_yaxis()
        return fig

    def create_velocity_plot(self) -> plt.Figure:
        fig, ax = plt.subplots(figsize=(10, 6))
        r = self.analysis_results
        if r.get('velocities'):
            ax.plot(r['timestamps'], r['velocities'], 'r-', linewidth=2)
            ax.set_xlabel('Время (с)')
            ax.set_ylabel('Скорость (пикс/с)')
            ax.set_title(f"Скорость частицы ID {r.get('track_id')}")
            ax.grid(True, alpha=0.3)
        return fig

    def create_std_plot(self) -> plt.Figure:
        fig, ax = plt.subplots(figsize=(10, 6))
        r = self.analysis_results
        if r.get('std_series'):
            ts = r['timestamps']
            ax.plot(ts, r['std_x_series'], label='СКО координаты X', alpha=0.8)
            ax.plot(ts, r['std_y_series'], label='СКО координаты Y', alpha=0.8)
            ax.plot(ts, r['std_series'], label='СКО положения', linewidth=2)
            ax.set_xlabel('Время (с)')
            ax.set_ylabel('СКО (пикс)')
            ax.set_title(f"Среднеквадратичное отклонение частицы ID {r.get('track_id')}")
            ax.grid(True, alpha=0.3)
            ax.legend()
        return fig

    def export_analysis_csv(self, filename: str) -> bool:
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['TrackID', 'Timestamp', 'X', 'Y', 'Velocity'])
                for p in sorted(self.data, key=lambda p: (p.get('track_id') or 0, p['timestamp'])):
                    writer.writerow([p.get('track_id'), p['timestamp'], p['x'], p['y'],
                                     p.get('velocity', 0.0)])
            return True
        except Exception as e:
            logger.error(f"Ошибка экспорта CSV: {e}")
            return False
