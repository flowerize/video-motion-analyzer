"""
Панель настроек трекинга
"""
import customtkinter as ctk
from typing import Dict, Callable
from utils.constants import COLORS, UI_SETTINGS


class TrackingPanel:
    """Панель настроек трекинга и статистики"""
    
    def __init__(self, parent, toggle_tracking_callback: Callable, 
                 apply_settings_callback: Callable):
        self.parent = parent
        self.toggle_tracking_callback = toggle_tracking_callback
        self.apply_settings_callback = apply_settings_callback
        self.is_tracking = False
        
        self.setup_ui()
        
    def setup_ui(self):
        """Настройка интерфейса трекинга"""
        self.main_frame = ctk.CTkFrame(self.parent, fg_color=COLORS["bg_light"])
        self.main_frame.pack(fill="x", padx=UI_SETTINGS["padding_medium"], 
                           pady=UI_SETTINGS["padding_small"])
        
        # Заголовок раздела
        section_label = ctk.CTkLabel(
            self.main_frame,
            text="Настройки трекинга",
            font=ctk.CTkFont(weight="bold"),
            text_color=COLORS["text"]
        )
        section_label.pack(anchor="w", pady=(0, UI_SETTINGS["padding_small"]))
        
        # Переключатель трекинга
        self.tracking_switch = ctk.CTkSwitch(
            self.main_frame,
            text="Включить трекинг",
            command=self.toggle_tracking,
            height=UI_SETTINGS["button_height"]
        )
        self.tracking_switch.pack(fill="x", pady=UI_SETTINGS["padding_small"])
        
        # Цветовые диапазоны
        self.setup_color_settings()
        
        # Кнопка применения настроек
        self.apply_btn = ctk.CTkButton(
            self.main_frame,
            text="Применить настройки",
            command=self.apply_settings,
            height=UI_SETTINGS["button_height"],
            fg_color=COLORS["accent"],
            hover_color="#268955"
        )
        self.apply_btn.pack(fill="x", pady=UI_SETTINGS["padding_small"])
        
        # Статистика трекинга
        self.setup_stats_section()
        
    def setup_color_settings(self):
        """Настройка цветовых параметров"""
        color_frame = ctk.CTkFrame(self.main_frame, fg_color=COLORS["bg_light"])
        color_frame.pack(fill="x", pady=UI_SETTINGS["padding_small"])
        
        # Hue
        hue_frame = ctk.CTkFrame(color_frame, fg_color="transparent")
        hue_frame.pack(fill="x", pady=2)
        
        ctk.CTkLabel(hue_frame, text="Hue диапазон:", width=120).pack(side="left")
        self.hue_low = ctk.CTkEntry(hue_frame, width=60, placeholder_text="0")
        self.hue_low.insert(0, "0")
        self.hue_low.pack(side="left", padx=2)
        ctk.CTkLabel(hue_frame, text="-").pack(side="left")
        self.hue_high = ctk.CTkEntry(hue_frame, width=60, placeholder_text="180")
        self.hue_high.insert(0, "180")
        self.hue_high.pack(side="left", padx=2)
        
        # Saturation
        sat_frame = ctk.CTkFrame(color_frame, fg_color="transparent")
        sat_frame.pack(fill="x", pady=2)
        
        ctk.CTkLabel(sat_frame, text="Saturation:", width=120).pack(side="left")
        self.sat_low = ctk.CTkEntry(sat_frame, width=60, placeholder_text="100")
        self.sat_low.insert(0, "100")
        self.sat_low.pack(side="left", padx=2)
        ctk.CTkLabel(sat_frame, text="-").pack(side="left")
        self.sat_high = ctk.CTkEntry(sat_frame, width=60, placeholder_text="255")
        self.sat_high.insert(0, "255")
        self.sat_high.pack(side="left", padx=2)
        
        # Value
        val_frame = ctk.CTkFrame(color_frame, fg_color="transparent")
        val_frame.pack(fill="x", pady=2)
        
        ctk.CTkLabel(val_frame, text="Value:", width=120).pack(side="left")
        self.val_low = ctk.CTkEntry(val_frame, width=60, placeholder_text="100")
        self.val_low.insert(0, "100")
        self.val_low.pack(side="left", padx=2)
        ctk.CTkLabel(val_frame, text="-").pack(side="left")
        self.val_high = ctk.CTkEntry(val_frame, width=60, placeholder_text="255")
        self.val_high.insert(0, "255")
        self.val_high.pack(side="left", padx=2)
        
    def setup_stats_section(self):
        """Настройка раздела статистики"""
        stats_frame = ctk.CTkFrame(self.main_frame, fg_color=COLORS["bg_light"])
        stats_frame.pack(fill="x", pady=UI_SETTINGS["padding_small"])
        
        # Заголовок
        section_label = ctk.CTkLabel(
            stats_frame,
            text="Статистика трекинга",
            font=ctk.CTkFont(weight="bold"),
            text_color=COLORS["text"]
        )
        section_label.pack(anchor="w", pady=(0, UI_SETTINGS["padding_small"]))
        
        # Показатели
        self.stats_text = ctk.CTkTextbox(
            stats_frame,
            height=120,
            fg_color=COLORS["bg_dark"],
            text_color=COLORS["text_secondary"],
            font=ctk.CTkFont(size=12)
        )
        self.stats_text.pack(fill="x", pady=UI_SETTINGS["padding_small"])
        self.stats_text.insert("1.0", "Трекинг не активен\n\n")
        self.stats_text.configure(state="disabled")
        
    def toggle_tracking(self):
        """Переключить состояние трекинга"""
        self.is_tracking = self.tracking_switch.get()
        self.toggle_tracking_callback(self.is_tracking)
        
    def apply_settings(self):
        """Применить настройки трекинга"""
        try:
            settings = {
                'hue_low': int(self.hue_low.get() or 0),
                'hue_high': int(self.hue_high.get() or 180),
                'saturation_low': int(self.sat_low.get() or 100),
                'saturation_high': int(self.sat_high.get() or 255),
                'value_low': int(self.val_low.get() or 100),
                'value_high': int(self.val_high.get() or 255)
            }
            self.apply_settings_callback(settings)
        except ValueError:
            # Callback должен обработать ошибку
            self.apply_settings_callback(None)
            
    def get_tracking_settings(self) -> Dict:
        """Получить текущие настройки трекинга"""
        try:
            return {
                'hue_low': int(self.hue_low.get() or 0),
                'hue_high': int(self.hue_high.get() or 180),
                'saturation_low': int(self.sat_low.get() or 100),
                'saturation_high': int(self.sat_high.get() or 255),
                'value_low': int(self.val_low.get() or 100),
                'value_high': int(self.val_high.get() or 255)
            }
        except ValueError:
            return {}
            
    def update_stats(self, point_count: int, current_time: float, 
                    current_position: tuple, current_velocity: float):
        """Обновить статистику трекинга"""
        try:
            self.stats_text.configure(state="normal")
            self.stats_text.delete("1.0", "end")
            
            stats_text = f"Точек: {point_count}\n"
            if point_count > 0:
                stats_text += f"Время: {current_time:.1f}с\n"
                if current_position:
                    stats_text += f"Позиция: ({current_position[0]}, {current_position[1]})\n"
                stats_text += f"Скорость: {current_velocity:.1f} px/s"
            else:
                stats_text += "Трекинг не активен\n\n"
            
            self.stats_text.insert("1.0", stats_text)
            self.stats_text.configure(state="disabled")
            
        except Exception as e:
            print(f"Ошибка обновления статистики: {e}")
            
    def set_tracking_state(self, is_tracking: bool):
        """Установить состояние трекинга"""
        self.is_tracking = is_tracking
        if is_tracking:
            self.tracking_switch.select()
        else:
            self.tracking_switch.deselect()
            
    def clear_stats(self):
        """Очистить статистику"""
        self.stats_text.configure(state="normal")
        self.stats_text.delete("1.0", "end")
        self.stats_text.insert("1.0", "Трекинг не активен\n\n")
        self.stats_text.configure(state="disabled")