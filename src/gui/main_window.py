"""
Главное окно приложения — PyQt6
"""
import logging
import sys
import os
import time
from typing import Optional

import cv2
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QCheckBox, QSpinBox, QDoubleSpinBox,
    QSplitter, QFrame, QSlider, QTabWidget, QTextEdit, QMessageBox,
    QFileDialog, QProgressBar, QGroupBox, QFormLayout, QGridLayout,
    QSizePolicy, QComboBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QImage, QPixmap, QFont, QColor

# Core modules
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from core.video_processor import VideoProcessor
from core.object_tracker import ObjectTracker
from core.data_analyzer import DataAnalyzer
from utils.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class VideoWorker(QThread):
    """Фоновый поток для воспроизведения видео"""
    frame_ready = pyqtSignal(np.ndarray)
    finished = pyqtSignal()

    def __init__(self, processor: VideoProcessor):
        super().__init__()
        self.processor = processor
        self._running = False

    def run(self):
        self._running = True
        while self._running and self.processor.is_opened():
            ret, frame = self.processor.cap.read()
            if not ret:
                break
            self.frame_ready.emit(frame)
            # Sleep to match FPS
            fps = self.processor.cap.get(cv2.CAP_PROP_FPS)
            if fps > 0:
                delay = int((1.0 / fps) * 1000)
                self.msleep(delay)
        self.finished.emit()

    def stop(self):
        self._running = False
        self.quit()
        self.wait()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Motion Analyzer")
        self.resize(1200, 800)

        self.config = ConfigManager()
        self.video_processor = VideoProcessor()
        self.object_tracker = ObjectTracker()
        self.data_analyzer = DataAnalyzer()

        self.current_video_path = None
        self.is_playing = False
        self.is_tracking = False
        self.start_time = 0.0

        # Video display cache
        self._last_img_size = None
        self._cached_pixmap = None

        # Worker thread
        self.worker = VideoWorker(self.video_processor)
        self.worker.frame_ready.connect(self._on_frame_ready)
        self.worker.finished.connect(self._on_playback_finished)

        self._setup_ui()
        self._load_saved_settings()

    # ======================== UI ========================

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Splitter: sidebar | content
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # --- Sidebar ---
        sidebar = QWidget()
        sidebar.setFixedWidth(320)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 10, 10, 10)
        sidebar_layout.setSpacing(10)

        # Title
        title = QLabel("Video Motion\nAnalyzer")
        title.setFont(QFont("Helvetica", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: #4a9eff;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(title)

        # Open video button
        self.open_btn = QPushButton("📁 Открыть видео")
        self.open_btn.clicked.connect(self.open_video)
        self.open_btn.setMinimumHeight(40)
        sidebar_layout.addWidget(self.open_btn)

        # Video info
        self.video_info = QLabel("Видео не загружено")
        self.video_info.setStyleSheet("color: gray;")
        self.video_info.setWordWrap(True)
        sidebar_layout.addWidget(self.video_info)

        # Play/Pause buttons
        btn_row = QHBoxLayout()
        self.play_btn = QPushButton("▶ Воспроизвести")
        self.play_btn.setEnabled(False)
        self.play_btn.clicked.connect(self.play_video)
        self.pause_btn = QPushButton("⏸ Пауза")
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self.pause_video)
        btn_row.addWidget(self.play_btn)
        btn_row.addWidget(self.pause_btn)
        sidebar_layout.addLayout(btn_row)

        # Reset button
        reset_btn = QPushButton("🔄 Сброс")
        reset_btn.clicked.connect(self.reset_analysis)
        sidebar_layout.addWidget(reset_btn)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        sidebar_layout.addWidget(separator)

        # Tracking settings group
        tracking_group = QGroupBox("Настройки трекинга")
        tracking_layout = QFormLayout(tracking_group)

        self.track_check = QCheckBox("Включить трекинг")
        self.track_check.stateChanged.connect(self.toggle_tracking)
        tracking_layout.addRow(self.track_check)

        self.points_spin = QSpinBox()
        self.points_spin.setRange(1, 5)
        self.points_spin.setValue(5)
        self.points_spin.setToolTip("Сколько точек отслеживать одновременно (1–5)")
        self.points_spin.valueChanged.connect(self._on_points_changed)
        tracking_layout.addRow("Кол-во точек:", self.points_spin)

        self.dist_spin = QSpinBox()
        self.dist_spin.setRange(2, 100)
        self.dist_spin.setValue(15)
        self.dist_spin.setSuffix(" px")
        self.dist_spin.setToolTip("Максимальное смещение частицы между кадрами (гейт сопоставления)")
        self.dist_spin.valueChanged.connect(self._on_distance_changed)
        tracking_layout.addRow("Макс. смещение:", self.dist_spin)

        # HSV
        hsv_layout = QGridLayout()
        self.hue_low_spin = QSpinBox(); self.hue_low_spin.setRange(0, 180); self.hue_low_spin.setValue(0)
        self.hue_high_spin = QSpinBox(); self.hue_high_spin.setRange(0, 180); self.hue_high_spin.setValue(180)
        self.sat_low_spin = QSpinBox(); self.sat_low_spin.setRange(0, 255); self.sat_low_spin.setValue(50)
        self.sat_high_spin = QSpinBox(); self.sat_high_spin.setRange(0, 255); self.sat_high_spin.setValue(255)
        self.val_low_spin = QSpinBox(); self.val_low_spin.setRange(0, 255); self.val_low_spin.setValue(50)
        self.val_high_spin = QSpinBox(); self.val_high_spin.setRange(0, 255); self.val_high_spin.setValue(255)

        hsv_layout.addWidget(QLabel("Hue:"), 0, 0)
        hsv_layout.addWidget(self.hue_low_spin, 0, 1)
        hsv_layout.addWidget(QLabel("-"), 0, 2)
        hsv_layout.addWidget(self.hue_high_spin, 0, 3)
        hsv_layout.addWidget(QLabel("Sat:"), 1, 0)
        hsv_layout.addWidget(self.sat_low_spin, 1, 1)
        hsv_layout.addWidget(QLabel("-"), 1, 2)
        hsv_layout.addWidget(self.sat_high_spin, 1, 3)
        hsv_layout.addWidget(QLabel("Val:"), 2, 0)
        hsv_layout.addWidget(self.val_low_spin, 2, 1)
        hsv_layout.addWidget(QLabel("-"), 2, 2)
        hsv_layout.addWidget(self.val_high_spin, 2, 3)
        tracking_layout.addRow(hsv_layout)

        apply_btn = QPushButton("Применить настройки")
        apply_btn.clicked.connect(self.apply_tracking_settings)
        tracking_layout.addRow(apply_btn)

        sidebar_layout.addWidget(tracking_group)

        # Advanced settings
        adv_group = QGroupBox("Дополнительно")
        adv_layout = QFormLayout(adv_group)

        self.bg_check = QCheckBox("Вычитание фона")
        self.bg_check.setChecked(True)
        adv_layout.addRow(self.bg_check)

        self.lr_spin = QDoubleSpinBox()
        self.lr_spin.setRange(0.001, 1.0)
        self.lr_spin.setValue(0.01)
        self.lr_spin.setSingleStep(0.001)
        adv_layout.addRow("Скорость обучения:", self.lr_spin)

        reset_bg_btn = QPushButton("🔄 Сбросить модель фона")
        reset_bg_btn.clicked.connect(self.reset_background_model)
        adv_layout.addRow(reset_bg_btn)

        sidebar_layout.addWidget(adv_group)
        sidebar_layout.addStretch()

        splitter.addWidget(sidebar)

        # --- Content area ---
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(10, 10, 10, 10)

        # Video display
        self.video_label = QLabel("Загрузите видео для начала анализа")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet(
            "background-color: #1a1a1a; color: gray; border: 1px solid #333;"
        )
        self.video_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        content_layout.addWidget(self.video_label)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setMaximumHeight(8)
        content_layout.addWidget(self.progress)

        # Action buttons
        act_row = QHBoxLayout()
        self.analyze_btn = QPushButton("🎯 Анализ и графики")
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.clicked.connect(self.start_analysis)
        self.export_btn = QPushButton("📊 Экспорт данных")
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self.export_data)
        act_row.addWidget(self.analyze_btn)
        act_row.addWidget(self.export_btn)
        content_layout.addLayout(act_row)

        # Particle selector (hidden until analysis)
        self.particle_row = QWidget()
        particle_layout = QHBoxLayout(self.particle_row)
        particle_layout.setContentsMargins(0, 0, 0, 0)
        particle_layout.addWidget(QLabel("Статистика частицы:"))
        self.particle_combo = QComboBox()
        self.particle_combo.setMinimumWidth(160)
        self.particle_combo.currentIndexChanged.connect(self._on_particle_changed)
        particle_layout.addWidget(self.particle_combo)
        particle_layout.addStretch()
        self.particle_row.setVisible(False)
        content_layout.addWidget(self.particle_row)

        # Results panel (hidden initially)
        self.results_tabs = QTabWidget()
        self.results_tabs.setVisible(False)
        content_layout.addWidget(self.results_tabs)

        # Add placeholder tabs with proper parent
        for name in ("Траектория", "Скорость", "СКО", "Статистика"):
            container = QWidget()
            container.setLayout(QVBoxLayout())
            self.results_tabs.addTab(container, name)

        self.back_btn = QPushButton("← Назад к видео")
        self.back_btn.setVisible(False)
        self.back_btn.clicked.connect(self._show_video)
        content_layout.addWidget(self.back_btn)

        splitter.addWidget(content)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        main_layout.addWidget(splitter)

        # Status bar
        self.statusBar().showMessage("Готов к работе")
        self.tracking_status_lbl = QLabel("Трекинг: выкл")
        self.statusBar().addPermanentWidget(self.tracking_status_lbl)

    # ======================== VIDEO DISPLAY ========================

    def _numpy_to_qimage(self, frame: np.ndarray) -> QImage:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w
        return QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)

    def _update_video_display(self, frame: np.ndarray):
        try:
            qimg = self._numpy_to_qimage(frame)
            pixmap = QPixmap.fromImage(qimg)

            # Scale to fit label
            available = self.video_label.size()
            if available.width() < 10 or available.height() < 10:
                return

            scaled = pixmap.scaled(
                available.width() - 4, available.height() - 4,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

            self.video_label.setPixmap(scaled)
        except Exception as e:
            logger.error(f"Ошибка обновления видео: {e}")

    # ======================== EVENTS ========================

    def _on_frame_ready(self, frame: np.ndarray):
        """Получен кадр из потока воспроизведения"""
        try:
            display = frame.copy()

            if self.is_tracking and self.video_processor.is_opened():
                # Use real video timestamp based on frame position and FPS
                cur_frame = int(self.video_processor.cap.get(cv2.CAP_PROP_POS_FRAMES))
                fps = self.video_processor.cap.get(cv2.CAP_PROP_FPS)
                t = cur_frame / fps if fps > 0 else float(cur_frame)
                tracks = self.object_tracker.process_frame(frame, t)
                if tracks:
                    display = self.object_tracker.draw_tracking_info(display)

            # Update via event loop (thread-safe)
            self._update_video_display(display)

            # Progress
            if self.video_processor.is_opened():
                cur = int(self.video_processor.cap.get(cv2.CAP_PROP_POS_FRAMES))
                tot = int(self.video_processor.cap.get(cv2.CAP_PROP_FRAME_COUNT))
                if tot > 0:
                    self.progress.setValue(int((cur / tot) * 100))
        except Exception as e:
            logger.error(f"Ошибка обработки кадра: {e}")

    def _on_playback_finished(self):
        self.is_playing = False
        self.play_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.statusBar().showMessage("Воспроизведение завершено")

    def resizeEvent(self, event):
        """Пересчёт при изменении размера окна"""
        self._last_img_size = None  # сброс кэша
        super().resizeEvent(event)

    # ======================== ACTIONS ========================

    def open_video(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите видео файл", "",
            "Video (*.mp4 *.avi *.mov *.mkv *.wmv);;All (*)"
        )
        if not path:
            return

        self.current_video_path = path
        try:
            self.config.add_recent_file(path)
        except Exception:
            pass

        if self.video_processor.open_video(path):
            props = self.video_processor.cap
            fps = props.get(cv2.CAP_PROP_FPS)
            w = int(props.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(props.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fc = int(props.get(cv2.CAP_PROP_FRAME_COUNT))
            dur = fc / fps if fps > 0 else 0
            self.video_info.setText(
                f"{path}\n{w}x{h}, {fps:.1f} FPS, {fc} кадров, {dur:.1f}с"
            )
            self.play_btn.setEnabled(True)
            self.pause_btn.setEnabled(True)
            self.analyze_btn.setEnabled(True)
            self.export_btn.setEnabled(True)
            self.statusBar().showMessage(f"Видео загружено: {path}")
        else:
            self.statusBar().showMessage("Ошибка загрузки видео", 3000)
            self.statusBar().currentWidget().setStyleSheet("color: red;")

    def play_video(self):
        if not self.video_processor.is_opened():
            return
        self.video_processor.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        self.worker.start()
        self.is_playing = True
        self.play_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.statusBar().showMessage("Воспроизведение")

    def pause_video(self):
        if self.is_playing:
            self.worker.stop()
            self.is_playing = False
            self.play_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
            self.statusBar().showMessage("Пауза")

    def toggle_tracking(self, state):
        self.is_tracking = state == Qt.CheckState.Checked.value
        if self.is_tracking:
            self.object_tracker.start_tracking()
            self.start_time = time.time()
            self.tracking_status_lbl.setText("Трекинг: вкл")
            self.tracking_status_lbl.setStyleSheet("color: green;")
            self.statusBar().showMessage("Трекинг активирован")
        else:
            self.object_tracker.stop_tracking()
            self.tracking_status_lbl.setText("Трекинг: выкл")
            self.tracking_status_lbl.setStyleSheet("")
            self.statusBar().showMessage("Трекинг остановлен")

    def _on_points_changed(self, value: int):
        self.object_tracker.set_max_tracks(value)
        self.statusBar().showMessage(f"Отслеживаемых точек: {value}")

    def _on_distance_changed(self, value: int):
        self.object_tracker.set_max_track_distance(value)
        self.statusBar().showMessage(f"Макс. смещение: {value} px")

    def apply_tracking_settings(self):
        settings = {
            'hue_low': self.hue_low_spin.value(),
            'hue_high': self.hue_high_spin.value(),
            'saturation_low': self.sat_low_spin.value(),
            'saturation_high': self.sat_high_spin.value(),
            'value_low': self.val_low_spin.value(),
            'value_high': self.val_high_spin.value(),
            'use_background_subtraction': self.bg_check.isChecked(),
            'background_learning_rate': self.lr_spin.value(),
            'max_tracks': self.points_spin.value(),
            'max_track_distance': self.dist_spin.value(),
        }
        self.object_tracker.update_settings({
            k: v for k, v in settings.items()
            if k not in ('use_background_subtraction', 'background_learning_rate',
                         'max_tracks', 'max_track_distance')
        })
        self.object_tracker.set_use_background_subtraction(settings['use_background_subtraction'])
        self.object_tracker.set_background_learning_rate(settings['background_learning_rate'])
        self.object_tracker.set_max_tracks(settings['max_tracks'])
        self.object_tracker.set_max_track_distance(settings['max_track_distance'])

        try:
            self.config.set_tracking_settings(settings)
        except Exception:
            pass

        self.statusBar().showMessage("Настройки применены")

    def reset_background_model(self):
        self.object_tracker.reset_background_model()
        self.statusBar().showMessage("Модель фона сброшена")

    def start_analysis(self):
        data = self.object_tracker.get_tracking_data()
        if not data:
            QMessageBox.warning(self, "Нет данных", "Нет данных для анализа. Включите трекинг и воспроизведите видео.")
            return

        self.data_analyzer.load_data(data)
        track_ids = self.data_analyzer.get_track_ids()
        if not track_ids:
            QMessageBox.warning(self, "Нет данных", "Не найдено ни одной частицы.")
            return

        self.particle_combo.blockSignals(True)
        self.particle_combo.clear()
        for tid in track_ids:
            self.particle_combo.addItem(f"Частица {tid}", tid)
        self.particle_combo.setCurrentIndex(0)
        self.particle_combo.blockSignals(False)

        # Hide video, show results
        self.video_label.setVisible(False)
        self.progress.setVisible(False)
        self.back_btn.setVisible(True)
        self.particle_row.setVisible(True)
        self.results_tabs.setVisible(True)

        self._update_analysis_view()

        self.statusBar().showMessage(f"Частиц: {len(track_ids)}, точек: {len(data)}")

    def _on_particle_changed(self, index: int):
        if index >= 0:
            self._update_analysis_view()

    def _update_analysis_view(self):
        track_id = self.particle_combo.currentData()
        if track_id is None:
            return
        results = self.data_analyzer.select_track(track_id)
        if not results:
            return

        fig = self.data_analyzer.create_trajectory_plot()
        self._embed_plot(fig, 0)
        plt.close(fig)

        fig = self.data_analyzer.create_velocity_plot()
        self._embed_plot(fig, 1)
        plt.close(fig)

        fig = self.data_analyzer.create_std_plot()
        self._embed_plot(fig, 2)
        plt.close(fig)

        self._update_stats(results)

    def _embed_plot(self, fig, tab_index: int):
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as Canvas
        container = self.results_tabs.widget(tab_index)
        layout = container.layout()
        # Remove old canvases safely
        for i in reversed(range(layout.count())):
            child = layout.itemAt(i)
            if child and child.widget():
                child.widget().deleteLater()
        canvas = Canvas(fig)
        canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(canvas)
        fig.tight_layout()
        canvas.draw()

    def _update_stats(self, results: dict):
        container = self.results_tabs.widget(3)
        layout = container.layout()
        # Remove old widgets safely
        for i in reversed(range(layout.count())):
            child = layout.itemAt(i)
            if child and child.widget():
                child.widget().deleteLater()

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)

        lines = [
            f"=== СТАТИСТИКА ЧАСТИЦЫ ID {results.get('track_id')} ===",
            f"Количество точек: {results.get('n_points', 0)}",
            f"Время наблюдения: {results.get('total_time', 0):.2f} с",
            f"Пройденный путь: {results.get('total_distance', 0):.2f} px",
            f"Средняя скорость: {results.get('avg_velocity', 0):.2f} px/с",
            f"Макс. скорость: {results.get('max_velocity', 0):.2f} px/с",
            f"СКО скорости: {results.get('std_velocity', 0):.2f} px/с",
            f"СКО координаты X: {results.get('std_x', 0):.2f} px",
            f"СКО координаты Y: {results.get('std_y', 0):.2f} px",
            f"СКО положения: {results.get('std_position', 0):.2f} px",
        ]

        text_edit.setPlainText("\n".join(lines))
        layout.addWidget(text_edit)

    def _show_video(self):
        self.results_tabs.setVisible(False)
        self.particle_row.setVisible(False)
        self.back_btn.setVisible(False)
        self.video_label.setVisible(True)
        self.progress.setVisible(True)
        # Clear plots from each tab container safely
        for i in range(4):
            container = self.results_tabs.widget(i)
            layout = container.layout()
            for j in reversed(range(layout.count())):
                child = layout.itemAt(j)
                if child and child.widget():
                    child.widget().deleteLater()

    def export_data(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить данные", "", "JSON (*.json)"
        )
        if path and self.object_tracker.export_data(path):
            self.statusBar().showMessage(f"Экспортировано: {path}")

        path2, _ = QFileDialog.getSaveFileName(
            self, "Сохранить анализ", "", "CSV (*.csv)"
        )
        if path2 and self.data_analyzer.export_analysis_csv(path2):
            self.statusBar().showMessage(f"Анализ экспортирован: {path2}")

    def reset_analysis(self):
        self.video_processor.close_video()
        self.object_tracker.clear_tracking_data()
        self.current_video_path = None
        self.is_playing = False
        self.is_tracking = False

        self.video_label.setText("Загрузите видео для начала анализа")
        self.video_label.clear()
        self.video_info.setText("Видео не загружено")
        self.play_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        self.analyze_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        self.progress.setValue(0)
        self.track_check.setChecked(False)
        self.tracking_status_lbl.setText("Трекинг: выкл")

        self._show_video()
        self.statusBar().showMessage("Готов к работе")

    def _load_saved_settings(self):
        try:
            t = self.config.get_tracking_settings()
            self.hue_low_spin.setValue(t.get('hue_low', 0))
            self.hue_high_spin.setValue(t.get('hue_high', 180))
            self.sat_low_spin.setValue(t.get('saturation_low', 50))
            self.sat_high_spin.setValue(t.get('saturation_high', 255))
            self.val_low_spin.setValue(t.get('value_low', 50))
            self.val_high_spin.setValue(t.get('value_high', 255))
            self.lr_spin.setValue(t.get('background_learning_rate', 0.01))
            self.bg_check.setChecked(t.get('use_background_subtraction', True))
            self.points_spin.setValue(int(t.get('max_tracks', 5)))
            self.dist_spin.setValue(int(t.get('max_track_distance', 15)))
        except Exception as e:
            logger.error(f"Ошибка загрузки настроек: {e}")

    def closeEvent(self, event):
        self.video_processor.close_video()
        event.accept()
