"""
Модуль для анализа данных трекинга
"""
import numpy as np
from typing import List, Dict, Tuple, Optional
import matplotlib.pyplot as plt
from scipy import signal
import csv


class DataAnalyzer:
    """Класс для анализа данных движения"""
    
    def __init__(self):
        self.data = []
        self.analysis_results = {}
        
    def load_data(self, tracking_data: List[Dict]):
        """Загрузить данные для анализа"""
        self.data = tracking_data
        
    def calculate_velocity(self) -> List[float]:
        """Вычислить скорость движения"""
        if len(self.data) < 2:
            return []
            
        velocities = [0.0]  # Первая точка имеет скорость 0
        
        for i in range(1, len(self.data)):
            dt = self.data[i]['timestamp'] - self.data[i-1]['timestamp']
            if dt <= 0:
                velocities.append(0.0)
                continue
                
            dx = self.data[i]['x'] - self.data[i-1]['x']
            dy = self.data[i]['y'] - self.data[i-1]['y']
            distance = np.sqrt(dx**2 + dy**2)
            
            velocity = distance / dt
            velocities.append(velocity)
            
        return velocities
    
    def calculate_acceleration(self, velocities: List[float]) -> List[float]:
        """Вычислить ускорение"""
        if len(velocities) < 2:
            return []
            
        accelerations = [0.0]  # Первая точка имеет ускорение 0
        
        for i in range(1, len(velocities)):
            dt = self.data[i]['timestamp'] - self.data[i-1]['timestamp']
            if dt <= 0:
                accelerations.append(0.0)
                continue
                
            dv = velocities[i] - velocities[i-1]
            acceleration = dv / dt
            accelerations.append(acceleration)
            
        return accelerations
    
    def smooth_data(self, data: List[float], window_size: int = 5) -> List[float]:
        """Сгладить данные с помощью скользящего среднего"""
        if len(data) < window_size:
            return data
            
        window = np.ones(window_size) / window_size
        smoothed = np.convolve(data, window, mode='same')
        return smoothed.tolist()
    
    def analyze_movement(self) -> Dict:
        """Провести полный анализ движения"""
        if not self.data:
            return {}
            
        # Извлекаем координаты и временные метки
        timestamps = [point['timestamp'] for point in self.data]
        x_coords = [point['x'] for point in self.data]
        y_coords = [point['y'] for point in self.data]
        
        # Вычисляем производные
        velocities = self.calculate_velocity()
        accelerations = self.calculate_acceleration(velocities)
        
        # Сглаживаем данные
        smooth_velocities = self.smooth_data(velocities)
        smooth_accelerations = self.smooth_data(accelerations)
        
        # Основная статистика
        total_time = timestamps[-1] - timestamps[0] if timestamps else 0
        total_distance = self.calculate_total_distance()
        
        self.analysis_results = {
            'timestamps': timestamps,
            'x_coords': x_coords,
            'y_coords': y_coords,
            'velocities': smooth_velocities,
            'accelerations': smooth_accelerations,
            'total_time': total_time,
            'total_distance': total_distance,
            'max_velocity': max(smooth_velocities) if smooth_velocities else 0,
            'max_acceleration': max(smooth_accelerations) if smooth_accelerations else 0,
            'avg_velocity': np.mean(smooth_velocities) if smooth_velocities else 0
        }
        
        return self.analysis_results
    
    def calculate_total_distance(self) -> float:
        """Вычислить общее пройденное расстояние"""
        if len(self.data) < 2:
            return 0.0
            
        total_distance = 0.0
        for i in range(1, len(self.data)):
            dx = self.data[i]['x'] - self.data[i-1]['x']
            dy = self.data[i]['y'] - self.data[i-1]['y']
            total_distance += np.sqrt(dx**2 + dy**2)
            
        return total_distance
    
    def export_analysis_csv(self, filename: str) -> bool:
        """Экспортировать результаты анализа в CSV"""
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                
                # Заголовки
                writer.writerow([
                    'Timestamp', 'X', 'Y', 'Velocity', 'Acceleration'
                ])
                
                # Данные
                for i, point in enumerate(self.data):
                    writer.writerow([
                        point['timestamp'],
                        point['x'],
                        point['y'],
                        self.analysis_results.get('velocities', [0] * len(self.data))[i],
                        self.analysis_results.get('accelerations', [0] * len(self.data))[i]
                    ])
                    
            return True
        except Exception as e:
            print(f"Ошибка экспорта CSV: {e}")
            return False
    
    def create_trajectory_plot(self) -> plt.Figure:
        """Создать график траектории"""
        fig, ax = plt.subplots(figsize=(10, 8))
        
        if self.data:
            x_coords = [point['x'] for point in self.data]
            y_coords = [point['y'] for point in self.data]
            
            # Инвертируем Y для корректного отображения (изображение)
            y_coords_inv = [max(y_coords) - y for y in y_coords]
            
            ax.plot(x_coords, y_coords_inv, 'b-', alpha=0.7, linewidth=2)
            ax.scatter(x_coords, y_coords_inv, c=range(len(x_coords)), 
                      cmap='viridis', s=30, alpha=0.6)
            ax.set_xlabel('X координата')
            ax.set_ylabel('Y координата')
            ax.set_title('Траектория движения объекта')
            ax.grid(True, alpha=0.3)
            ax.set_aspect('equal', adjustable='datalim')
            
        return fig
    
    def create_velocity_plot(self) -> plt.Figure:
        """Создать график скорости"""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        if self.analysis_results.get('velocities'):
            timestamps = self.analysis_results['timestamps']
            velocities = self.analysis_results['velocities']
            
            ax.plot(timestamps, velocities, 'r-', linewidth=2)
            ax.set_xlabel('Время (с)')
            ax.set_ylabel('Скорость (пикс/с)')
            ax.set_title('Скорость движения объекта')
            ax.grid(True, alpha=0.3)
            
        return fig