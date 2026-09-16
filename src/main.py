"""
Главный модуль приложения PyQt6
"""
import sys
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    logger.info("Запуск Video Motion Analyzer")
    
    app = QApplication(sys.argv)
    app.setApplicationName("Video Motion Analyzer")
    app.setStyle("Fusion")  # Кроссплатформенный стиль
    
    from gui.main_window import MainWindow
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
