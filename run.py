"""
Точка входа в приложение PyQt6
"""
import sys
import os

project_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from main import main

if __name__ == "__main__":
    main()
