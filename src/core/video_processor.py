"""
Модуль для обработки видео
"""
import cv2
import numpy as np
from typing import Optional, Tuple, Callable
import threading
import time


class VideoProcessor:
    """Класс для работы с видео"""
    
    def __init__(self):
        self.cap = None
        self.current_frame = None
        self.playing = False
        self.processing = False
        self.frame_callbacks = []
        self.processing_thread = None
        
    def open_video(self, video_path: str) -> bool:
        """Открыть видео файл"""
        self.close_video()
        
        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            return False
            
        return True
    
    def close_video(self):
        """Закрыть видео"""
        self.stop_playback()
        
        if self.cap:
            self.cap.release()
            self.cap = None
            
        self.current_frame = None
    
    def get_frame(self, frame_num: Optional[int] = None) -> Optional[np.ndarray]:
        """Получить конкретный кадр"""
        if not self.cap:
            return None
            
        if frame_num is not None:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            
        ret, frame = self.cap.read()
        if ret:
            self.current_frame = frame
            return frame
        return None
    
    def get_current_frame_number(self) -> int:
        """Получить номер текущего кадра"""
        if not self.cap:
            return 0
        return int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
    
    def get_total_frames(self) -> int:
        """Получить общее количество кадров"""
        if not self.cap:
            return 0
        return int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    def get_fps(self) -> float:
        """Получить FPS видео"""
        if not self.cap:
            return 0
        return self.cap.get(cv2.CAP_PROP_FPS)
    
    def add_frame_callback(self, callback: Callable):
        """Добавить callback при получении нового кадра"""
        self.frame_callbacks.append(callback)
    
    def _processing_loop(self):
        """Основной цикл обработки видео"""
        frame_delay = 1.0 / self.get_fps() if self.get_fps() > 0 else 0.033
        
        while self.playing and self.cap:
            start_time = time.time()
            
            ret, frame = self.cap.read()
            if not ret:
                self.playing = False
                break
                
            self.current_frame = frame
            
            # Вызываем все зарегистрированные callback'и
            for callback in self.frame_callbacks:
                callback(frame)
            
            # Поддерживаем правильную скорость воспроизведения
            processing_time = time.time() - start_time
            sleep_time = max(0, frame_delay - processing_time)
            time.sleep(sleep_time)
    
    def start_playback(self):
        """Начать воспроизведение"""
        if not self.cap or self.playing:
            return
            
        self.playing = True
        self.processing_thread = threading.Thread(target=self._processing_loop)
        self.processing_thread.daemon = True
        self.processing_thread.start()
    
    def stop_playback(self):
        """Остановить воспроизведение"""
        self.playing = False
        if self.processing_thread:
            self.processing_thread.join(timeout=1.0)
            self.processing_thread = None
    
    def is_playing(self) -> bool:
        """Проверить, воспроизводится ли видео"""
        return self.playing
    
    def is_opened(self) -> bool:
        """Проверить, открыто ли видео"""
        return self.cap is not None and self.cap.isOpened()