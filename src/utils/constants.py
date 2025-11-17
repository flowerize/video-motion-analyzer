"""
Константы и настройки приложения
"""
import customtkinter as ctk

# Настройки приложения
APP_SETTINGS = {
    "window_size": "1200x800",
    "theme": "dark",
    "color_theme": "blue",
    "min_window_size": (800, 600)
}

# Цветовая схема
COLORS = {
    "primary": "#1f538d",
    "secondary": "#14375e", 
    "accent": "#2fa572",
    "success": "#28a745",
    "warning": "#ffc107",
    "error": "#dc3545",
    "text": "#ffffff",
    "text_secondary": "#b0b0b0",
    "bg_dark": "#1a1a1a",
    "bg_light": "#2a2a2a",
    "bg_lighter": "#3a3a3a"
}

# Настройки трекинга по умолчанию
TRACKING_SETTINGS = {
    "min_area": 100,
    "max_area": 50000,
    "blur_size": 5,
    "morph_iters": 2,
    "hue_low": 0,
    "hue_high": 180,
    "saturation_low": 100,
    "saturation_high": 255,
    "value_low": 100,
    "value_high": 255
}

# Поддерживаемые форматы видео
SUPPORTED_VIDEO_FORMATS = (".mp4", ".avi", ".mov", ".mkv", ".wmv")

# Настройки интерфейса
UI_SETTINGS = {
    "corner_radius": 8,
    "button_height": 40,
    "input_height": 35,
    "padding_small": 5,
    "padding_medium": 10,
    "padding_large": 20
}

def setup_theme():
    """Настройка темы customtkinter"""
    ctk.set_appearance_mode(APP_SETTINGS["theme"])
    ctk.set_default_color_theme(APP_SETTINGS["color_theme"])