"""
Главный модуль приложения
"""
import os
import sys

# Добавляем текущую директорию в путь для импортов
sys.path.insert(0, os.path.dirname(__file__))

import customtkinter as ctk
from gui.main_window import MainWindow
from utils.constants import setup_theme, APP_SETTINGS


def main():
    """Запуск главного окна приложения"""
    # Настройка темы
    setup_theme()
    
    # Создание главного окна
    root = ctk.CTk()
    root.title("Video Motion Analyzer")
    root.geometry(APP_SETTINGS["window_size"])
    root.minsize(*APP_SETTINGS["min_window_size"])
    
    # Создаем и запускаем главное окно
    app = MainWindow(root)
    
    # Обработка закрытия окна
    def on_closing():
        app.on_closing()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()