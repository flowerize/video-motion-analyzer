"""
Элементы управления видео
"""
import customtkinter as ctk
from typing import Optional, Callable
from utils.constants import COLORS, UI_SETTINGS
from utils.file_handlers import FileHandler


class VideoControls:
    """Панель управления видео"""
    
    def __init__(self, parent, open_video_callback: Callable, play_callback: Callable, 
                 pause_callback: Callable, reset_callback: Callable):
        self.parent = parent
        self.open_video_callback = open_video_callback
        self.play_callback = play_callback
        self.pause_callback = pause_callback
        self.reset_callback = reset_callback
        
        self.current_video_path = None
        self.setup_ui()
        
    def setup_ui(self):
        """Настройка интерфейса управления видео"""
        self.main_frame = ctk.CTkFrame(self.parent, fg_color=COLORS["bg_light"])
        self.main_frame.pack(fill="x", padx=UI_SETTINGS["padding_medium"], 
                           pady=UI_SETTINGS["padding_small"])
        
        # Заголовок раздела
        section_label = ctk.CTkLabel(
            self.main_frame,
            text="Управление видео",
            font=ctk.CTkFont(weight="bold"),
            text_color=COLORS["text"]
        )
        section_label.pack(anchor="w", pady=(0, UI_SETTINGS["padding_small"]))
        
        # Кнопка открытия видео
        self.open_btn = ctk.CTkButton(
            self.main_frame,
            text="📁 Открыть видео",
            command=self.open_video_callback,
            height=UI_SETTINGS["button_height"],
            fg_color=COLORS["primary"],
            hover_color=COLORS["secondary"]
        )
        self.open_btn.pack(fill="x", pady=UI_SETTINGS["padding_small"])
        
        # Информация о видео
        self.video_info_label = ctk.CTkLabel(
            self.main_frame,
            text="Видео не загружено",
            text_color=COLORS["text_secondary"],
            wraplength=280
        )
        self.video_info_label.pack(fill="x", pady=UI_SETTINGS["padding_small"])
        
        # Кнопки воспроизведения
        control_btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        control_btn_frame.pack(fill="x", pady=UI_SETTINGS["padding_small"])
        
        self.play_btn = ctk.CTkButton(
            control_btn_frame,
            text="▶ Воспроизвести",
            command=self.play_callback,
            height=UI_SETTINGS["button_height"],
            state="disabled",
            fg_color=COLORS["success"],
            hover_color="#218838"
        )
        self.play_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        self.pause_btn = ctk.CTkButton(
            control_btn_frame,
            text="⏸ Пауза",
            command=self.pause_callback,
            height=UI_SETTINGS["button_height"],
            state="disabled",
            fg_color=COLORS["warning"],
            hover_color="#e0a800",
            text_color="black"
        )
        self.pause_btn.pack(side="right", fill="x", expand=True, padx=(5, 0))
        
        # Кнопка сброса
        self.reset_btn = ctk.CTkButton(
            self.main_frame,
            text="🔄 Сброс видео",
            command=self.reset_callback,
            height=UI_SETTINGS["button_height"],
            fg_color=COLORS["error"],
            hover_color="#c82333"
        )
        self.reset_btn.pack(fill="x", pady=UI_SETTINGS["padding_small"])
        
    def update_video_info(self, video_path: str):
        """Обновить информацию о видео"""
        self.current_video_path = video_path
        if video_path:
            props = FileHandler.get_video_properties(video_path)
            if props:
                info_text = f"Размер: {props['width']}x{props['height']}\n"
                info_text += f"FPS: {props['fps']:.1f}\n"
                info_text += f"Длительность: {props['duration']:.1f}с"
                self.video_info_label.configure(text=info_text)
        else:
            self.video_info_label.configure(text="Видео не загружено")
            
    def enable_controls(self):
        """Активировать элементы управления"""
        self.play_btn.configure(state="normal")
        self.pause_btn.configure(state="normal")
        
    def disable_controls(self):
        """Деактивировать элементы управления"""
        self.play_btn.configure(state="disabled")
        self.pause_btn.configure(state="disabled")
        self.video_info_label.configure(text="Видео не загружено")
        
    def set_playing_state(self, is_playing: bool):
        """Установить состояние воспроизведения"""
        if is_playing:
            self.play_btn.configure(state="disabled")
            self.pause_btn.configure(state="normal")
        else:
            self.play_btn.configure(state="normal")
            self.pause_btn.configure(state="disabled")