"""
Модуль для анализа данных трекинга
"""
import logging
import numpy as np
from typing import List, Dict, Optional
import matplotlib.pyplot as plt
from scipy import signal
import csv

logger = logging.getLogger(__name__)


class DataAnalyzer:
    def __init__(self):
        self.data: List[Dict] = []
        self.analysis_results: Dict = {}

    def load_data(self, tracking_data: List[Dict]):
        self.data = tracking_data

    def calculate_velocity(self) -> List[float]:
        if len(self.data) < 2:
            return []
        velocities = [0.0]
        for i in range(1, len(self.data)):
            dt = self.data[i]['timestamp'] - self.data[i-1]['timestamp']
            if dt <= 0:
                velocities.append(0.0)
                continue
            dx = self.data[i]['x'] - self.data[i-1]['x']
            dy = self.data[i]['y'] - self.data[i-1]['y']
            velocities.append(float(np.sqrt(dx**2 + dy**2) / dt))
        return velocities

    def calculate_acceleration(self, velocities: List[float]) -> List[float]:
        if len(velocities) < 2:
            return []
        accelerations = [0.0]
        for i in range(1, len(velocities)):
            dt = self.data[i]['timestamp'] - self.data[i-1]['timestamp']
            if dt <= 0:
                accelerations.append(0.0)
                continue
            if self.data[i-1].get('track_id') != self.data[i].get('track_id'):
                accelerations.append(0.0)
                continue
            dv = velocities[i] - velocities[i-1]
            accelerations.append(float(dv / dt))
        return accelerations

    def smooth_data(self, data: List[float], window_size: int = 5) -> List[float]:
        if len(data) < window_size:
            return data
        window = np.ones(window_size) / window_size
        return np.convolve(data, window, mode='same').tolist()

    def analyze_movement(self) -> Dict:
        if not self.data:
            return {}
        timestamps = [p['timestamp'] for p in self.data]
        velocities = self.calculate_velocity()
        accelerations = self.calculate_acceleration(velocities)
        smooth_v = self.smooth_data(velocities)
        smooth_a = self.smooth_data(accelerations)
        total_time = timestamps[-1] - timestamps[0] if timestamps else 0
        self.analysis_results = {
            'timestamps': timestamps,
            'x_coords': [p['x'] for p in self.data],
            'y_coords': [p['y'] for p in self.data],
            'velocities': smooth_v,
            'accelerations': smooth_a,
            'total_time': total_time,
            'total_distance': self.calculate_total_distance(),
            'max_velocity': float(max(smooth_v)) if smooth_v else 0,
            'max_acceleration': float(max(abs(a) for a in smooth_a)) if smooth_a else 0,
            'avg_velocity': float(np.mean(smooth_v)) if smooth_v else 0
        }
        return self.analysis_results

    def calculate_total_distance(self) -> float:
        if len(self.data) < 2:
            return 0.0
        d = 0.0
        for i in range(1, len(self.data)):
            dx = self.data[i]['x'] - self.data[i-1]['x']
            dy = self.data[i]['y'] - self.data[i-1]['y']
            d += np.sqrt(dx**2 + dy**2)
        return float(d)

    def export_analysis_csv(self, filename: str) -> bool:
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                w = csv.writer(f)
                w.writerow(['Timestamp', 'X', 'Y', 'Velocity', 'Acceleration'])
                vels = self.analysis_results.get('velocities', [0] * len(self.data))
                accs = self.analysis_results.get('accelerations', [0] * len(self.data))
                for i, p in enumerate(self.data):
                    w.writerow([p['timestamp'], p['x'], p['y'], vels[i], accs[i]])
            return True
        except Exception as e:
            logger.error(f"Ошибка экспорта CSV: {e}")
            return False

    def create_trajectory_plot(self) -> plt.Figure:
        fig, ax = plt.subplots(figsize=(10, 8))
        if self.data:
            xs = [p['x'] for p in self.data]
            ys = [p['y'] for p in self.data]
            ys_inv = [max(ys) - y for y in ys]
            ax.plot(xs, ys_inv, 'b-', alpha=0.7, linewidth=2)
            ax.scatter(xs, ys_inv, c=range(len(xs)), cmap='viridis', s=30, alpha=0.6)
            ax.set_xlabel('X координата')
            ax.set_ylabel('Y координата')
            ax.set_title('Траектория движения объекта')
            ax.grid(True, alpha=0.3)
            ax.set_aspect('equal', adjustable='datalim')
        return fig

    def create_velocity_plot(self) -> plt.Figure:
        fig, ax = plt.subplots(figsize=(10, 6))
        if self.analysis_results.get('velocities'):
            ts = self.analysis_results['timestamps']
            vs = self.analysis_results['velocities']
            ax.plot(ts, vs, 'r-', linewidth=2)
            ax.set_xlabel('Время (с)')
            ax.set_ylabel('Скорость (пикс/с)')
            ax.set_title('Скорость движения объекта')
            ax.grid(True, alpha=0.3)
        return fig

    def create_acceleration_plot(self) -> Optional[plt.Figure]:
        if not self.analysis_results.get('accelerations'):
            return None
        fig, ax = plt.subplots(figsize=(10, 6))
        ts = self.analysis_results['timestamps']
        ac = self.analysis_results['accelerations']
        ax.plot(ts, ac, 'g-', linewidth=2)
        ax.set_xlabel('Время (с)')
        ax.set_ylabel('Ускорение (пикс/с²)')
        ax.set_title('Ускорение движения объекта')
        ax.grid(True, alpha=0.3)
        return fig
