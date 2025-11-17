"""
Модуль для трекинга объектов по цвету
"""
import cv2
import numpy as np
from typing import Optional, Tuple, List, Dict
import json
import time


class ObjectTracker:
    """Класс для трекинга объектов по цвету"""
    
    def __init__(self):
        self.tracking_enabled = False
        self.tracking_data = []
        self.current_position = None
        self.tracking_history = []
        self.settings = {
            'hue_low': 0,
            'hue_high': 180,
            'saturation_low': 100,
            'saturation_high': 255,
            'value_low': 100,
            'value_high': 255,
            'min_area': 100,
            'max_area': 50000,
            'blur_size': 5,
            'morph_iters': 2
        }
        
    def update_settings(self, new_settings: Dict):
        """Обновить настройки трекинга"""
        self.settings.update(new_settings)
        
    def process_frame(self, frame: np.ndarray) -> Optional[Tuple[int, int, float]]:
        """
        Обработать кадр и найти объект
        
        Returns:
            Tuple (x, y, area) или None если объект не найден
        """
        if not self.tracking_enabled:
            return None
            
        try:
            # Конвертируем в HSV
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            
            # Создаем маску по заданному диапазону
            lower_bound = np.array([
                self.settings['hue_low'],
                self.settings['saturation_low'], 
                self.settings['value_low']
            ])
            upper_bound = np.array([
                self.settings['hue_high'],
                self.settings['saturation_high'],
                self.settings['value_high']
            ])
            
            mask = cv2.inRange(hsv, lower_bound, upper_bound)
            
            # Морфологические операции для улучшения маски
            kernel = np.ones((5, 5), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, 
                                  iterations=self.settings['morph_iters'])
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, 
                                  iterations=self.settings['morph_iters'])
            
            # Размытие для сглаживания
            if self.settings['blur_size'] > 0:
                mask = cv2.GaussianBlur(mask, (self.settings['blur_size'], 
                                             self.settings['blur_size']), 0)
            
            # Находим контуры
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, 
                                         cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                return None
                
            # Находим самый большой контур
            largest_contour = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(largest_contour)
            
            # Проверяем площадь
            if (area < self.settings['min_area'] or 
                area > self.settings['max_area']):
                return None
                
            # Вычисляем центр масс
            M = cv2.moments(largest_contour)
            if M["m00"] == 0:
                return None
                
            x = int(M["m10"] / M["m00"])
            y = int(M["m01"] / M["m00"])
            
            self.current_position = (x, y, area)
            return self.current_position
            
        except Exception as e:
            print(f"Ошибка обработки кадра: {e}")
            return None
    
    def draw_tracking_info(self, frame: np.ndarray, position: Tuple[int, int, float]) -> np.ndarray:
        """Нарисовать информацию о трекинге на кадре"""
        if position is None:
            return frame
            
        x, y, area = position
        
        # Рисуем круг в центре объекта
        cv2.circle(frame, (x, y), 8, (0, 255, 0), -1)
        cv2.circle(frame, (x, y), 12, (0, 255, 0), 2)
        
        # Рисуем крест
        cv2.line(frame, (x-15, y), (x+15, y), (0, 255, 0), 2)
        cv2.line(frame, (x, y-15), (x, y+15), (0, 255, 0), 2)
        
        # Добавляем информацию
        info_text = f"({x}, {y})"
        cv2.putText(frame, info_text, (x+20, y-10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        # Рисуем площадь
        area_text = f"Area: {area:.0f}"
        cv2.putText(frame, area_text, (x+20, y+15), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return frame
    
    def start_tracking(self):
        """Начать трекинг"""
        self.tracking_enabled = True
        self.tracking_data = []
        self.tracking_history = []
        
    def stop_tracking(self):
        """Остановить трекинг"""
        self.tracking_enabled = False
        
    def add_tracking_point(self, position: Tuple[int, int, float], timestamp: float):
        """Добавить точку трекинга в историю"""
        if position:
            x, y, area = position
            self.tracking_data.append({
                'timestamp': timestamp,
                'x': x,
                'y': y,
                'area': area
            })
            self.tracking_history.append((x, y))
    
    def get_tracking_data(self) -> List[Dict]:
        """Получить все данные трекинга"""
        return self.tracking_data.copy()
    
    def clear_tracking_data(self):
        """Очистить данные трекинга"""
        self.tracking_data = []
        self.tracking_history = []
        self.current_position = None
    
    def export_data(self, filename: str) -> bool:
        """Экспортировать данные в JSON файл"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({
                    'settings': self.settings,
                    'tracking_data': self.tracking_data,
                    'timestamp': time.time()
                }, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Ошибка экспорта: {e}")
            return False