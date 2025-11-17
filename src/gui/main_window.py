"""
Главное окно приложения
"""
import customtkinter as ctk
import tkinter as tk
from typing import Optional, Callable
import cv2
from PIL import Image, ImageTk
import numpy as np
import time
from tkinter import filedialog

from utils.constants import COLORS, UI_SETTINGS, APP_SETTINGS
from utils.file_handlers import FileHandler
from core.video_processor import VideoProcessor
from core.object_tracker import ObjectTracker
from core.data_analyzer import DataAnalyzer
from gui.video_controls import VideoControls
from gui.tracking_panel import TrackingPanel
from gui.results_panel import ResultsPanel


class MainWindow:
    """Главное окно приложения"""
    
    def __init__(self, parent):
        self.parent = parent
        self.video_processor = VideoProcessor()
        self.object_tracker = ObjectTracker()
        self.data_analyzer = DataAnalyzer()
        
        self.current_video_path = None
        self.is_playing = False
        self.is_tracking = False
        self.video_frame = None
        self.start_time = 0
        
        self.setup_ui()
        self.setup_bindings()
        
    def setup_ui(self):
        """Настройка пользовательского интерфейса"""
        self.setup_main_frames()
        self.setup_sidebar()
        self.setup_video_area()
        self.setup_control_panel()
        self.setup_status_bar()
        self.setup_results_panel()
        
    def setup_main_frames(self):
        """Настройка основных фреймов"""
        # Главный контейнер
        self.main_container = ctk.CTkFrame(self.parent, fg_color=COLORS["bg_dark"])
        self.main_container.pack(fill="both", expand=True, padx=0, pady=0)
        
        # Боковая панель
        self.sidebar_frame = ctk.CTkFrame(
            self.main_container, 
            width=300,
            fg_color=COLORS["bg_light"],
            corner_radius=0
        )
        self.sidebar_frame.pack(side="left", fill="y", padx=0, pady=0)
        self.sidebar_frame.pack_propagate(False)
        
        # Основная область контента
        self.content_frame = ctk.CTkFrame(
            self.main_container,
            fg_color=COLORS["bg_dark"]
        )
        self.content_frame.pack(side="right", fill="both", expand=True, padx=0, pady=0)
        
    def setup_sidebar(self):
        """Настройка боковой панели"""
        # Заголовок
        title_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="Video Motion\nAnalyzer",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=COLORS["text"]
        )
        title_label.pack(pady=UI_SETTINGS["padding_large"])
        
        # Разделитель
        separator = ctk.CTkFrame(
            self.sidebar_frame,
            height=2,
            fg_color=COLORS["primary"]
        )
        separator.pack(fill="x", padx=UI_SETTINGS["padding_medium"], pady=UI_SETTINGS["padding_small"])
        
        # Панель управления видео
        self.video_controls = VideoControls(
            self.sidebar_frame,
            self.open_video,
            self.play_video,
            self.pause_video,
            self.reset_analysis
        )
        
        # Панель настроек трекинга
        self.tracking_panel = TrackingPanel(
            self.sidebar_frame,
            self.toggle_tracking,
            self.apply_tracking_settings
        )
        
    def setup_video_area(self):
        """Настройка области отображения видео"""
        self.video_container = ctk.CTkFrame(self.content_frame, fg_color=COLORS["bg_dark"])
        self.video_container.pack(fill="both", expand=True, padx=UI_SETTINGS["padding_medium"], 
                                pady=UI_SETTINGS["padding_medium"])
        
        # Метка для отображения видео
        self.video_label = ctk.CTkLabel(
            self.video_container,
            text="Загрузите видео для начала анализа",
            font=ctk.CTkFont(size=16),
            text_color=COLORS["text_secondary"],
            fg_color=COLORS["bg_light"],
            corner_radius=UI_SETTINGS["corner_radius"]
        )
        self.video_label.pack(fill="both", expand=True, padx=0, pady=0)
        
    def setup_control_panel(self):
        """Настройка панели управления"""
        self.control_panel = ctk.CTkFrame(self.content_frame, fg_color=COLORS["bg_light"])
        self.control_panel.pack(fill="x", padx=UI_SETTINGS["padding_medium"], 
                              pady=(0, UI_SETTINGS["padding_medium"]))
        
        # Прогресс-бар
        self.progress_bar = ctk.CTkProgressBar(self.control_panel, height=8)
        self.progress_bar.pack(fill="x", padx=UI_SETTINGS["padding_medium"], 
                             pady=UI_SETTINGS["padding_small"])
        self.progress_bar.set(0)
        
        # Кнопки анализа
        btn_frame = ctk.CTkFrame(self.control_panel, fg_color="transparent")
        btn_frame.pack(fill="x", padx=UI_SETTINGS["padding_medium"], 
                     pady=UI_SETTINGS["padding_small"])
        
        self.analyze_btn = ctk.CTkButton(
            btn_frame,
            text="🎯 Анализ и графики",
            command=self.start_analysis,
            height=UI_SETTINGS["button_height"],
            state="disabled",
            fg_color=COLORS["accent"],
            hover_color="#268955"
        )
        self.analyze_btn.pack(side="left", padx=(0, 5))
        
        self.export_btn = ctk.CTkButton(
            btn_frame,
            text="📊 Экспорт данных",
            command=self.export_data,
            height=UI_SETTINGS["button_height"],
            state="disabled",
            fg_color=COLORS["primary"],
            hover_color=COLORS["secondary"]
        )
        self.export_btn.pack(side="left", padx=5)
        
    def setup_results_panel(self):
        """Настройка панели результатов (изначально скрыта)"""
        self.results_frame = ctk.CTkFrame(self.content_frame, fg_color=COLORS["bg_dark"])
        # Изначально скрыта, показывается по нажатию кнопки анализа
        
        self.results_panel = ResultsPanel(self.results_frame)
        
    def setup_status_bar(self):
        """Настройка строки состояния"""
        self.status_frame = ctk.CTkFrame(self.main_container, height=30, corner_radius=0)
        self.status_frame.pack(side="bottom", fill="x", padx=0, pady=0)
        self.status_frame.pack_propagate(False)
        
        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="Готов к работе",
            text_color=COLORS["text_secondary"]
        )
        self.status_label.pack(side="left", padx=UI_SETTINGS["padding_medium"])
        
        # Информация о трекинге
        self.tracking_status_label = ctk.CTkLabel(
            self.status_frame,
            text="Трекинг: выключен",
            text_color=COLORS["text_secondary"]
        )
        self.tracking_status_label.pack(side="right", padx=UI_SETTINGS["padding_medium"])
        
    def setup_bindings(self):
        """Настройка привязок событий"""
        # Регистрируем callback для обновления видео
        self.video_processor.add_frame_callback(self.process_video_frame)
        
    def process_video_frame(self, frame: np.ndarray):
        """Обработать кадр видео с трекингом"""
        try:
            display_frame = frame.copy()
            current_time = time.time() - self.start_time
            
            # Применяем трекинг если включен
            if self.is_tracking:
                position = self.object_tracker.process_frame(frame)
                if position:
                    self.object_tracker.add_tracking_point(position, current_time)
                    display_frame = self.object_tracker.draw_tracking_info(display_frame, position)
                    
                    # Обновляем статистику
                    self.update_tracking_stats(position, current_time)
            
            # Обновляем отображение
            self.update_video_display(display_frame)
            
            # Обновляем прогресс
            if self.video_processor.is_opened():
                current_frame = self.video_processor.get_current_frame_number()
                total_frames = self.video_processor.get_total_frames()
                if total_frames > 0:
                    progress = current_frame / total_frames
                    self.progress_bar.set(progress)
                    
        except Exception as e:
            print(f"Ошибка обработки видео: {e}")
            
    def update_video_display(self, frame: np.ndarray):
        """Обновить отображение видео в интерфейсе"""
        try:
            # Конвертируем BGR в RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Конвертируем в формат для CTkImage
            img = Image.fromarray(rgb_frame)
            
            # Масштабируем изображение под размер метки
            label_width = self.video_label.winfo_width()
            label_height = self.video_label.winfo_height()
            
            if label_width > 1 and label_height > 1:
                img = img.resize((label_width, label_height), Image.Resampling.LANCZOS)
            
            ctk_image = ctk.CTkImage(
                light_image=img,
                dark_image=img,
                size=(label_width, label_height)
            )
            
            # Обновляем метку
            self.video_label.configure(image=ctk_image, text="")
            
        except Exception as e:
            print(f"Ошибка обновления видео: {e}")
            
    def update_tracking_stats(self, position: tuple, current_time: float):
        """Обновить статистику трекинга"""
        data = self.object_tracker.get_tracking_data()
        point_count = len(data)
        current_velocity = self.calculate_current_velocity()
        
        self.tracking_panel.update_stats(point_count, current_time, position, current_velocity)
        
    def calculate_current_velocity(self) -> float:
        """Вычислить текущую скорость"""
        data = self.object_tracker.get_tracking_data()
        if len(data) < 2:
            return 0.0
            
        # Берем последние 2 точки
        p1 = data[-2]
        p2 = data[-1]
        
        dt = p2['timestamp'] - p1['timestamp']
        if dt <= 0:
            return 0.0
            
        dx = p2['x'] - p1['x']
        dy = p2['y'] - p1['y']
        distance = np.sqrt(dx**2 + dy**2)
        
        return distance / dt
        
    # === ОСНОВНЫЕ МЕТОДЫ УПРАВЛЕНИЯ ===
    
    def open_video(self):
        """Открыть видео файл"""
        file_path = FileHandler.open_video_file()
        if file_path:
            self.current_video_path = file_path
            if self.video_processor.open_video(file_path):
                self.video_controls.update_video_info(file_path)
                self.video_controls.enable_controls()
                self.analyze_btn.configure(state="normal")
                self.export_btn.configure(state="normal")
                self.update_status(f"Видео загружено: {file_path}")
            else:
                self.update_status("Ошибка загрузки видео", is_error=True)
                
    def play_video(self):
        """Воспроизвести видео"""
        if self.video_processor.is_opened():
            self.video_processor.start_playback()
            self.is_playing = True
            self.video_controls.set_playing_state(True)
            self.update_status("Воспроизведение видео")
            
    def pause_video(self):
        """Приостановить видео"""
        if self.video_processor.is_playing():
            self.video_processor.stop_playback()
            self.is_playing = False
            self.video_controls.set_playing_state(False)
            self.update_status("Видео приостановлено")
            
    def toggle_tracking(self, is_tracking: bool):
        """Включить/выключить трекинг"""
        self.is_tracking = is_tracking
        
        if self.is_tracking:
            self.object_tracker.start_tracking()
            self.start_time = time.time()
            self.tracking_status_label.configure(text="Трекинг: включен", 
                                               text_color=COLORS["success"])
            self.update_status("Трекинг активирован")
        else:
            self.object_tracker.stop_tracking()
            self.tracking_status_label.configure(text="Трекинг: выключен",
                                               text_color=COLORS["text_secondary"])
            self.update_status("Трекинг остановлен")
            
    def apply_tracking_settings(self, settings: dict):
        """Применить настройки трекинга"""
        if settings:
            self.object_tracker.update_settings(settings)
            self.update_status("Настройки трекинга применены")
        else:
            self.update_status("Ошибка: проверьте значения настроек", is_error=True)
            
    def start_analysis(self):
        """Начать анализ движения"""
        tracking_data = self.object_tracker.get_tracking_data()
        if not tracking_data:
            self.update_status("Нет данных для анализа", is_error=True)
            return
            
        self.update_status("Анализ движения начат")
        
        # Загружаем данные в анализатор
        self.data_analyzer.load_data(tracking_data)
        results = self.data_analyzer.analyze_movement()
        
        # Показываем панель результатов
        self.show_results_panel()
        
        # Обновляем графики
        self.results_panel.update_plots(tracking_data)
        
        self.update_status(f"Анализ завершен: {len(tracking_data)} точек")
        
    def show_results_panel(self):
        """Показать панель результатов"""
        # Скрываем видео панель
        self.video_container.pack_forget()
        self.control_panel.pack_forget()
        
        # Показываем панель результатов
        self.results_frame.pack(fill="both", expand=True, padx=UI_SETTINGS["padding_medium"], 
                              pady=UI_SETTINGS["padding_medium"])
        
        # Добавляем кнопку возврата к видео
        self.add_back_to_video_button()
        
    def add_back_to_video_button(self):
        """Добавить кнопку возврата к видео"""
        if hasattr(self, 'back_btn'):
            return
            
        back_frame = ctk.CTkFrame(self.content_frame, fg_color=COLORS["bg_light"])
        back_frame.pack(fill="x", padx=UI_SETTINGS["padding_medium"], 
                       pady=(0, UI_SETTINGS["padding_medium"]))
        
        self.back_btn = ctk.CTkButton(
            back_frame,
            text="← Назад к видео",
            command=self.show_video_panel,
            height=UI_SETTINGS["button_height"],
            fg_color=COLORS["primary"],
            hover_color=COLORS["secondary"]
        )
        self.back_btn.pack(side="left", padx=5, pady=5)
        
    def show_video_panel(self):
        """Показать панель видео"""
        # Скрываем панель результатов
        self.results_frame.pack_forget()
        if hasattr(self, 'back_btn'):
            self.back_btn.master.pack_forget()
            delattr(self, 'back_btn')
        
        # Показываем видео панель
        self.video_container.pack(fill="both", expand=True, padx=UI_SETTINGS["padding_medium"], 
                                pady=UI_SETTINGS["padding_medium"])
        self.control_panel.pack(fill="x", padx=UI_SETTINGS["padding_medium"], 
                              pady=(0, UI_SETTINGS["padding_medium"]))
        
    def export_data(self):
        """Экспорт данных анализа"""
        try:
            # Экспорт сырых данных
            raw_file = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json")]
            )
            if raw_file and self.object_tracker.export_data(raw_file):
                self.update_status(f"Данные экспортированы в {raw_file}")
                
            # Экспорт анализа
            analysis_file = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")]
            )
            if analysis_file and self.data_analyzer.export_analysis_csv(analysis_file):
                self.update_status(f"Анализ экспортирован в {analysis_file}")
                
        except Exception as e:
            self.update_status(f"Ошибка экспорта: {str(e)}", is_error=True)
        
    def reset_analysis(self):
        """Сбросить анализ"""
        self.video_processor.close_video()
        self.object_tracker.clear_tracking_data()
        self.current_video_path = None
        self.is_playing = False
        self.is_tracking = False
        
        # Сброс интерфейса
        self.video_label.configure(image="", text="Загрузите видео для начала анализа")
        self.video_controls.disable_controls()
        self.tracking_panel.set_tracking_state(False)
        self.tracking_panel.clear_stats()
        self.analyze_btn.configure(state="disabled")
        self.export_btn.configure(state="disabled")
        self.tracking_status_label.configure(text="Трекинг: выключен")
        self.progress_bar.set(0)
        
        # Очищаем графики
        self.results_panel.clear_plots()
        
        # Возвращаемся к видео панели
        if hasattr(self, 'back_btn'):
            self.show_video_panel()
        
        self.update_status("Готов к работе")
        
    def update_status(self, message: str, is_error: bool = False):
        """Обновить статус"""
        color = COLORS["error"] if is_error else COLORS["text_secondary"]
        self.status_label.configure(text=message, text_color=color)
        
    def on_closing(self):
        """Обработка закрытия приложения"""
        self.video_processor.close_video()
        print("Приложение закрыто")