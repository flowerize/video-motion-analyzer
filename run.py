"""
Точка входа в приложение
"""
import os
import sys

# Добавляем src в путь для импортов
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from main import main

if __name__ == "__main__":
    main()