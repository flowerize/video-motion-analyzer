"""
Утилиты для работы с файлами
"""
import os
import csv
from tkinter import filedialog, messagebox
from typing import Optional, List, Tuple
import cv2

from .constants import SUPPORTED_VIDEO_FORMATS


class FileHandler:
    """Класс для работы с файлами"""
    
    @staticmethod
    def open_video_file() -> Optional[str]:
        """Открыть диалог выбора видео файла"""
        file_path = filedialog.askopenfilename(
            title="Выберите видео файл",
            filetypes=[
                ("Video files", "*.mp4 *.avi *.mov *.mkv *.wmv"),
                ("All files", "*.*")
            ]
        )
        return file_path if file_path else None
    
    @staticmethod
    def save_csv_data(data: List[Tuple], headers: List[str]) -> bool:
        """Сохранить данные в CSV файл"""
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")]
            )
            
            if not file_path:
                return False
                
            with open(file_path, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(headers)
                writer.writerows(data)
                
            return True
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить файл: {str(e)}")
            return False
    
    @staticmethod
    def is_video_file(file_path: str) -> bool:
        """Проверить, что файл является поддерживаемым видео"""
        return os.path.splitext(file_path)[1].lower() in SUPPORTED_VIDEO_FORMATS
    
    @staticmethod
    def get_video_properties(video_path: str) -> Optional[dict]:
        """Получить свойства видео файла"""
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return None
                
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration = frame_count / fps if fps > 0 else 0
            
            cap.release()
            
            return {
                'fps': fps,
                'frame_count': frame_count,
                'width': width,
                'height': height,
                'duration': duration
            }
        except Exception:
            return None