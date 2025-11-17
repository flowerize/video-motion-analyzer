"""
Панель для отображения графиков анализа
"""
import customtkinter as ctk
import tkinter as tk
from typing import Optional, Callable
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np
import io
from PIL import Image

from utils.constants import COLORS, UI_SETTINGS
from core.data_analyzer import DataAnalyzer


class ResultsPanel:
    """Панель для отображения графиков анализа движения"""
    
    def __init__(self, parent):
        self.parent = parent
        self.data_analyzer = DataAnalyzer()
        self.current_figures = []
        
        self.setup_ui()
        
    def setup_ui(self):
        """Настройка интерфейса панели графиков"""
        self.main_frame = ctk.CTkFrame(self.parent, fg_color=COLORS["bg_dark"])
        self.main_frame.pack(fill="both", expand=True, padx=0, pady=0)
        
        # Заголовок
        title_label = ctk.CTkLabel(
            self.main_frame,
            text="Анализ движения",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS["text"]
        )
        title_label.pack(pady=UI_SETTINGS["padding_medium"])
        
        # Вкладки для разных типов графиков
        self.setup_tabs()
        
    def setup_tabs(self):
        """Настройка вкладок с графиками"""
        self.tabview = ctk.CTkTabview(self.main_frame, fg_color=COLORS["bg_light"])
        self.tabview.pack(fill="both", expand=True, padx=UI_SETTINGS["padding_medium"], 
                         pady=UI_SETTINGS["padding_small"])
        
        # Создаем вкладки
        self.tabview.add("Траектория")
        self.tabview.add("Скорость")
        self.tabview.add("Ускорение")
        self.tabview.add("Статистика")
        
        # Настраиваем каждую вкладку
        self.setup_trajectory_tab()
        self.setup_velocity_tab()
        self.setup_acceleration_tab()
        self.setup_stats_tab()
        
    def setup_trajectory_tab(self):
        """Настройка вкладки траектории"""
        tab = self.tabview.tab("Траектория")
        
        # Фрейм для графика
        plot_frame = ctk.CTkFrame(tab, fg_color=COLORS["bg_light"])
        plot_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Заглушка для графика
        self.trajectory_placeholder = ctk.CTkLabel(
            plot_frame,
            text="График траектории появится после анализа",
            font=ctk.CTkFont(size=14),
            text_color=COLORS["text_secondary"]
        )
        self.trajectory_placeholder.pack(expand=True)
        
        # Холст для matplotlib
        self.trajectory_canvas = None
        
    def setup_velocity_tab(self):
        """Настройка вкладки скорости"""
        tab = self.tabview.tab("Скорость")
        
        plot_frame = ctk.CTkFrame(tab, fg_color=COLORS["bg_light"])
        plot_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.velocity_placeholder = ctk.CTkLabel(
            plot_frame,
            text="График скорости появится после анализа",
            font=ctk.CTkFont(size=14),
            text_color=COLORS["text_secondary"]
        )
        self.velocity_placeholder.pack(expand=True)
        
        self.velocity_canvas = None
        
    def setup_acceleration_tab(self):
        """Настройка вкладки ускорения"""
        tab = self.tabview.tab("Ускорение")
        
        plot_frame = ctk.CTkFrame(tab, fg_color=COLORS["bg_light"])
        plot_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.acceleration_placeholder = ctk.CTkLabel(
            plot_frame,
            text="График ускорения появится после анализа",
            font=ctk.CTkFont(size=14),
            text_color=COLORS["text_secondary"]
        )
        self.acceleration_placeholder.pack(expand=True)
        
        self.acceleration_canvas = None
        
    def setup_stats_tab(self):
        """Настройка вкладки статистики"""
        tab = self.tabview.tab("Статистика")
        
        stats_frame = ctk.CTkFrame(tab, fg_color=COLORS["bg_light"])
        stats_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Текстовое поле для статистики
        self.stats_text = ctk.CTkTextbox(
            stats_frame,
            fg_color=COLORS["bg_dark"],
            text_color=COLORS["text"],
            font=ctk.CTkFont(size=12),
            wrap="word"
        )
        self.stats_text.pack(fill="both", expand=True, padx=5, pady=5)
        self.stats_text.insert("1.0", "Статистика появится после анализа данных...")
        self.stats_text.configure(state="disabled")
        
    def update_plots(self, tracking_data: list):
        """Обновить все графики на основе данных трекинга"""
        if not tracking_data:
            return
            
        # Загружаем данные в анализатор
        self.data_analyzer.load_data(tracking_data)
        analysis_results = self.data_analyzer.analyze_movement()
        
        # Обновляем графики
        self.update_trajectory_plot()
        self.update_velocity_plot()
        self.update_acceleration_plot()
        self.update_stats_text(analysis_results)
        
    def update_trajectory_plot(self):
        """Обновить график траектории"""
        fig = self.data_analyzer.create_trajectory_plot()
        if fig and self.tabview.tab("Траектория").winfo_exists():
            self._embed_plot(fig, "Траектория", self.trajectory_placeholder, self.trajectory_canvas)
        
    def update_velocity_plot(self):
        """Обновить график скорости"""
        fig = self.data_analyzer.create_velocity_plot()
        if fig and self.tabview.tab("Скорость").winfo_exists():
            self._embed_plot(fig, "Скорость", self.velocity_placeholder, self.velocity_canvas)
        
    def update_acceleration_plot(self):
        """Обновить график ускорения"""
        # Создаем график ускорения
        fig = self._create_acceleration_plot()
        if fig and self.tabview.tab("Ускорение").winfo_exists():
            self._embed_plot(fig, "Ускорение", self.acceleration_placeholder, self.acceleration_canvas)
        
    def _create_acceleration_plot(self) -> Optional[Figure]:
        """Создать график ускорения"""
        if not self.data_analyzer.analysis_results.get('accelerations'):
            return None
            
        fig, ax = plt.subplots(figsize=(8, 5))
        fig.patch.set_facecolor('#2a2a2a')
        ax.set_facecolor('#1a1a1a')
        
        timestamps = self.data_analyzer.analysis_results['timestamps']
        accelerations = self.data_analyzer.analysis_results['accelerations']
        
        ax.plot(timestamps, accelerations, 'g-', linewidth=2, label='Ускорение')
        ax.set_xlabel('Время (с)', color='white')
        ax.set_ylabel('Ускорение (пикс/с²)', color='white')
        ax.set_title('Ускорение движения объекта', color='white')
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        # Настраиваем цвета осей
        ax.tick_params(colors='white')
        for spine in ax.spines.values():
            spine.set_color('white')
            
        fig.tight_layout()
        return fig
        
    def _embed_plot(self, fig: Figure, tab_name: str, placeholder, canvas_var):
        """Встроить график matplotlib в интерфейс"""
        try:
            # Удаляем старый canvas если есть
            if canvas_var is not None and canvas_var.winfo_exists():
                canvas_var.get_tk_widget().destroy()
                
            # Убираем заглушку
            placeholder.pack_forget()
            
            # Создаем новый canvas
            tab = self.tabview.tab(tab_name)
            canvas = FigureCanvasTkAgg(fig, tab)
            canvas.draw()
            
            # Получаем tkinter виджет и размещаем его
            widget = canvas.get_tk_widget()
            widget.configure(bg=COLORS["bg_light"])
            widget.pack(fill="both", expand=True, padx=10, pady=10)
            
            # Сохраняем ссылку
            if tab_name == "Траектория":
                self.trajectory_canvas = canvas
            elif tab_name == "Скорость":
                self.velocity_canvas = canvas
            elif tab_name == "Ускорение":
                self.acceleration_canvas = canvas
                
            # Сохраняем figure для предотвращения сборки мусора
            self.current_figures.append(fig)
            
            # Ограничиваем количество хранимых figures
            if len(self.current_figures) > 5:
                old_fig = self.current_figures.pop(0)
                plt.close(old_fig)
                
        except Exception as e:
            print(f"Ошибка встраивания графика: {e}")
            
    def update_stats_text(self, analysis_results: dict):
        """Обновить текстовую статистику"""
        if not analysis_results:
            return
            
        self.stats_text.configure(state="normal")
        self.stats_text.delete("1.0", "end")
        
        stats_text = "=== СТАТИСТИКА АНАЛИЗА ===\n\n"
        stats_text += f"Общее время: {analysis_results['total_time']:.2f} с\n"
        stats_text += f"Общее расстояние: {analysis_results['total_distance']:.2f} px\n"
        stats_text += f"Макс. скорость: {analysis_results['max_velocity']:.2f} px/с\n"
        stats_text += f"Макс. ускорение: {analysis_results['max_acceleration']:.2f} px/с²\n"
        stats_text += f"Средняя скорость: {analysis_results['avg_velocity']:.2f} px/с\n"
        stats_text += f"Количество точек: {len(analysis_results['timestamps'])}\n"
        
        self.stats_text.insert("1.0", stats_text)
        self.stats_text.configure(state="disabled")
        
    def clear_plots(self):
        """Очистить все графики"""
        # Закрываем все figures
        for fig in self.current_figures:
            plt.close(fig)
        self.current_figures.clear()
        
        # Восстанавливаем заглушки
        self.trajectory_placeholder.pack(expand=True)
        self.velocity_placeholder.pack(expand=True)
        self.acceleration_placeholder.pack(expand=True)
        
        # Очищаем текстовую статистику
        self.stats_text.configure(state="normal")
        self.stats_text.delete("1.0", "end")
        self.stats_text.insert("1.0", "Статистика появится после анализа данных...")
        self.stats_text.configure(state="disabled")