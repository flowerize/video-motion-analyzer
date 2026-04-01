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
        
        # Дополнительные настройки
        self.setup_advanced_settings()
        
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
        
    def setup_advanced_settings(self):
        """Настройка дополнительных параметров"""
        advanced_frame = ctk.CTkFrame(self.main_frame, fg_color=COLORS["bg_light"])
        advanced_frame.pack(fill="x", pady=UI_SETTINGS["padding_small"])
        
        # Заголовок
        section_label = ctk.CTkLabel(
            advanced_frame,
            text="Дополнительные настройки",
            font=ctk.CTkFont(weight="bold"),
            text_color=COLORS["text"]
        )
        section_label.pack(anchor="w", pady=(0, UI_SETTINGS["padding_small"]))
        
        # Переключатель использования вычитания фона
        self.bg_subtract_switch = ctk.CTkSwitch(
            advanced_frame,
            text="Использовать вычитание фона",
            variable=ctk.BooleanVar(value=True)
        )
        self.bg_subtract_switch.pack(fill="x", pady=2)
        
        # Поле для настройки скорости обучения
        learning_rate_frame = ctk.CTkFrame(advanced_frame, fg_color="transparent")
        learning_rate_frame.pack(fill="x", pady=2)
        
        ctk.CTkLabel(learning_rate_frame, text="Скорость обучения фона:", width=150).pack(side="left")
        self.learning_rate_entry = ctk.CTkEntry(learning_rate_frame, width=60, placeholder_text="0.01")
        self.learning_rate_entry.insert(0, "0.01")
        self.learning_rate_entry.pack(side="left", padx=2)
        
        # Кнопка сброса модели фона
        self.reset_bg_btn = ctk.CTkButton(
            advanced_frame,
            text="🔄 Сбросить модель фона",
            command=self.reset_background_model,
            height=UI_SETTINGS["button_height"],
            fg_color=COLORS["secondary"],
            hover_color=COLORS["primary"]
        )
        self.reset_bg_btn.pack(fill="x", pady=UI_SETTINGS["padding_small"])
        
        
    def toggle_tracking(self):
        """Переключить состояние трекинга"""
        self.is_tracking = self.tracking_switch.get()
        self.toggle_tracking_callback(self.is_tracking)
        
    def reset_background_model(self):
        """Сбросить модель фона"""
        # Вызываем callback для сброса модели фона
        if hasattr(self, 'reset_bg_callback'):
            self.reset_bg_callback()
        
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
            
            # Добавляем дополнительные настройки
            bg_subtract_enabled = self.bg_subtract_switch.get()
            try:
                learning_rate = float(self.learning_rate_entry.get() or 0.01)
            except ValueError:
                learning_rate = 0.01
                
            settings['use_background_subtraction'] = bool(bg_subtract_enabled)
            settings['background_learning_rate'] = learning_rate
            
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
            
    def set_tracking_state(self, is_tracking: bool):
        """Установить состояние трекинга"""
        self.is_tracking = is_tracking
        if is_tracking:
            self.tracking_switch.select()
        else:
            self.tracking_switch.deselect()
