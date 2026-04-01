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
        self.track_histories: Dict[int, List[Dict]] = {}
        self.tracks: Dict[int, Dict] = {}
        self.next_track_id = 1
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
        
        # Добавляем переменные для вычитания фона
        self.background_subtractor = cv2.createBackgroundSubtractorMOG2(detectShadows=True)
        self.use_background_subtraction = True
        self.background_learning_rate = 0.01
        
        # Параметры трекинга нескольких объектов
        self.max_track_distance = 60.0
        self.max_missed_frames = 10
        self.max_tracks = 10
        
    def update_settings(self, new_settings: Dict):
        """Обновить настройки трекинга"""
        self.settings.update(new_settings)
        
    def set_use_background_subtraction(self, use_bg_subtraction: bool):
        """Включить/выключить использование вычитания фона"""
        self.use_background_subtraction = use_bg_subtraction
        
    def set_background_learning_rate(self, learning_rate: float):
        """Установить скорость обучения алгоритма вычитания фона"""
        self.background_learning_rate = learning_rate
        
    def process_frame(self, frame: np.ndarray, timestamp: float) -> List[Dict]:
        """Обработать кадр и вернуть список активных треков"""
        if not self.tracking_enabled:
            return []
        
        try:
            detections = self._detect_particles(frame)
            self._update_tracks(detections, timestamp)
            return self.get_active_tracks()
        except Exception as e:
            print(f"Ошибка обработки кадра: {e}")
            return []

    # === Детекция и обновление треков ===
    def _detect_particles(self, frame: np.ndarray) -> List[Dict]:
        """Вернуть список детекций (x, y, area, contour)"""
        if self.use_background_subtraction:
            fg_mask = self.background_subtractor.apply(frame, learningRate=self.background_learning_rate)
            kernel = np.ones((5, 5), np.uint8)
            fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel, iterations=2)
            fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
            masked_frame = cv2.bitwise_and(frame, frame, mask=fg_mask)
            hsv = cv2.cvtColor(masked_frame, cv2.COLOR_BGR2HSV)
        else:
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            fg_mask = None

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
        color_mask = cv2.inRange(hsv, lower_bound, upper_bound)
        if fg_mask is not None:
            mask = cv2.bitwise_and(fg_mask, color_mask)
        else:
            mask = color_mask

        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=self.settings['morph_iters'])
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=self.settings['morph_iters'])
        if self.settings['blur_size'] > 0:
            mask = cv2.GaussianBlur(mask, (self.settings['blur_size'], self.settings['blur_size']), 0)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        detections = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < self.settings['min_area'] or area > self.settings['max_area']:
                continue
            M = cv2.moments(contour)
            if M["m00"] == 0:
                continue
            x = int(M["m10"] / M["m00"])
            y = int(M["m01"] / M["m00"])
            detections.append({'x': x, 'y': y, 'area': area})

        detections.sort(key=lambda d: d['area'], reverse=True)
        if self.max_tracks:
            detections = detections[: self.max_tracks]
        return detections

    def _update_tracks(self, detections: List[Dict], timestamp: float):
        """Обновить существующие треки и добавить новые"""
        # Маркируем все треки как пропущенные
        for track in self.tracks.values():
            track['missed_frames'] += 1

        unmatched_detections = detections.copy()

        # Пытаемся сопоставить детекции с существующими треками
        for track in list(self.tracks.values()):
            best_detection = None
            best_distance = float('inf')
            for detection in unmatched_detections:
                dist = np.linalg.norm([
                    detection['x'] - track['x'],
                    detection['y'] - track['y']
                ])
                if dist < best_distance:
                    best_distance = dist
                    best_detection = detection
            if best_detection and best_distance <= self.max_track_distance:
                unmatched_detections.remove(best_detection)
                self._update_track_with_detection(track, best_detection, timestamp)
            else:
                if track['missed_frames'] > self.max_missed_frames:
                    self._archive_track(track['id'])

        # Создаем новые треки для оставшихся детекций
        for detection in unmatched_detections:
            self._create_new_track(detection, timestamp)

    def _update_track_with_detection(self, track: Dict, detection: Dict, timestamp: float):
        """Обновить трек на основе новой детекции"""
        prev_x, prev_y = track['x'], track['y']
        dt = timestamp - track['timestamp'] if track['timestamp'] is not None else 0.0
        track['x'] = detection['x']
        track['y'] = detection['y']
        track['area'] = detection['area']
        track['timestamp'] = timestamp
        track['missed_frames'] = 0
        if dt > 0:
            dx = track['x'] - prev_x
            dy = track['y'] - prev_y
            track['velocity'] = float(np.sqrt(dx**2 + dy**2) / dt)
        else:
            track['velocity'] = 0.0

        self.track_histories.setdefault(track['id'], []).append({
            'timestamp': timestamp,
            'x': track['x'],
            'y': track['y'],
            'area': track['area'],
            'velocity': track['velocity'],
            'track_id': track['id']
        })

    def _create_new_track(self, detection: Dict, timestamp: float):
        """Создать новый трек"""
        track_id = self.next_track_id
        self.next_track_id += 1
        track = {
            'id': track_id,
            'x': detection['x'],
            'y': detection['y'],
            'area': detection['area'],
            'timestamp': timestamp,
            'missed_frames': 0,
            'velocity': 0.0
        }
        self.tracks[track_id] = track
        self.track_histories.setdefault(track_id, []).append({
            'timestamp': timestamp,
            'x': track['x'],
            'y': track['y'],
            'area': track['area'],
            'velocity': track['velocity'],
            'track_id': track_id
        })

    def _archive_track(self, track_id: int):
        """Удалить трек из активных при потере"""
        if track_id in self.tracks:
            del self.tracks[track_id]

    def _color_for_track(self, idx: int) -> Tuple[int, int, int]:
        """Получить цвет для визуализации трека"""
        colors = [
            (0, 255, 0),
            (0, 200, 255),
            (255, 200, 0),
            (255, 0, 200),
            (200, 0, 255),
            (0, 128, 255),
            (128, 0, 255)
        ]
        return colors[idx % len(colors)]

    def draw_tracking_info(self, frame: np.ndarray) -> np.ndarray:
        """Нарисовать информацию о всех активных треках"""
        for idx, track in enumerate(self.tracks.values()):
            x, y = int(track['x']), int(track['y'])
            area = track['area']
            color = self._color_for_track(idx)
            cv2.circle(frame, (x, y), 6, color, -1)
            cv2.circle(frame, (x, y), 12, color, 2)
            cv2.line(frame, (x-12, y), (x+12, y), color, 2)
            cv2.line(frame, (x, y-12), (x, y+12), color, 2)
            info_text = f"ID {track['id']} ({x}, {y})"
            cv2.putText(frame, info_text, (x+15, y-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            velocity = track.get('velocity', 0.0)
            velocity_text = f"v={velocity:.1f}"
            cv2.putText(frame, velocity_text, (x+15, y+12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        return frame
    
    def start_tracking(self):
        """Начать трекинг"""
        self.tracking_enabled = True
        self.clear_tracking_data()
        
    def stop_tracking(self):
        """Остановить трекинг"""
        self.tracking_enabled = False
        
    def get_active_tracks(self) -> List[Dict]:
        """Получить список активных треков"""
        return [track.copy() for track in self.tracks.values()]
    
    def get_tracking_data(self) -> List[Dict]:
        """Получить плоский список всех точек трекинга для анализа"""
        all_points: List[Dict] = []
        for history in self.track_histories.values():
            all_points.extend(history)
        return sorted(all_points, key=lambda item: item['timestamp'])
    
    def clear_tracking_data(self):
        """Очистить данные трекинга"""
        self.tracks = {}
        self.track_histories = {}
        self.next_track_id = 1
        
    def reset_background_model(self):
        """Сбросить модель фона"""
        self.background_subtractor = cv2.createBackgroundSubtractorMOG2(detectShadows=True)
        
    def export_data(self, filename: str) -> bool:
        """Экспортировать данные в JSON файл"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({
                    'settings': self.settings,
                    'tracks': self.track_histories,
                    'exported_at': time.time()
                }, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Ошибка экспорта: {e}")
            return False
