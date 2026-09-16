"""
Утилиты для работы с файлами
"""
import os
import csv
from typing import Optional, List, Tuple
import cv2

from .constants import SUPPORTED_VIDEO_FORMATS


class FileHandler:
    @staticmethod
    def open_video_file() -> Optional[str]:
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            None, "Выберите видео файл", "",
            "Video files (*.mp4 *.avi *.mov *.mkv *.wmv);;All files (*.*)"
        )
        return path if path else None

    @staticmethod
    def save_csv_data(data: List[Tuple], headers: List[str]) -> bool:
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(None, "Сохранить CSV", "", "CSV files (*.csv)")
        if not path:
            return False
        try:
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                writer.writerows(data)
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения CSV: {e}")
            return False

    @staticmethod
    def is_video_file(path: str) -> bool:
        return os.path.splitext(path)[1].lower() in SUPPORTED_VIDEO_FORMATS

    @staticmethod
    def get_video_properties(video_path: str) -> Optional[dict]:
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
                'fps': fps, 'frame_count': frame_count,
                'width': width, 'height': height, 'duration': duration
            }
        except Exception:
            return None
