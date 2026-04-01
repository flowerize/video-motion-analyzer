"""
Тестовый скрипт для проверки настроек трекинга на зеленом фоне
"""

import cv2
import numpy as np

def create_test_video_with_green_background(output_path, duration=10, fps=30):
    """
    Создает тестовое видео с зеленым фоном и движущимся объектом
    """
    width, height = 640, 480
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    # Зеленый фон (в HSV: H~60, S~100-255, V~100-255)
    green_background_hsv = np.full((height, width, 3), (60, 200, 200), dtype=np.uint8)
    green_background_bgr = cv2.cvtColor(green_background_hsv, cv2.COLOR_HSV2BGR)
    
    for frame_idx in range(duration * fps):
        # Создаем копию фона
        frame = green_background_bgr.copy()
        
        # Добавляем движущийся белый шар (для демонстрации трекинга)
        center_x = int(width/2 + width/4 * np.cos(frame_idx * 0.1))
        center_y = int(height/2 + height/4 * np.sin(frame_idx * 0.1))
        
        # Рисуем белый шар (в HSV: H~0, S~0, V~255)
        cv2.circle(frame, (center_x, center_y), 20, (255, 255, 255), -1)
        
        out.write(frame)
    
    out.release()
    print(f"Тестовое видео создано: {output_path}")

def test_color_filtering():
    """
    Тестирует различные настройки HSV фильтрации
    """
    # Пример HSV значений для различных цветов
    colors = {
        "green_background": {"h": 60, "s": 200, "v": 200},
        "white_object": {"h": 0, "s": 0, "v": 255},
        "red_object": {"h": 0, "s": 200, "v": 200},
        "blue_object": {"h": 120, "s": 200, "v": 200},
        "yellow_object": {"h": 30, "s": 200, "v": 200}
    }
    
    print("Рекомендуемые диапазоны HSV для трекинга объектов на зеленом фоне:")
    print("-" * 60)
    print("Для трекинга всех цветных объектов (кроме зеленого):")
    print("  Hue: 0-50 ИЛИ 70-180 (исключаем зеленый цвет H~60)")
    print("  Saturation: 50-255 (отсекаем не насыщенные области)")
    print("  Value: 50-255 (отсекаем очень темные области)")
    print()
    print("Для трекинга конкретных цветов:")
    
    for name, color in colors.items():
        h, s, v = color["h"], color["s"], color["v"]
        print(f"  {name}: H={h}±10, S={s}±50, V={v}±50")
    
    print()
    print("Для трекинга только движущихся объектов (рекомендуемый подход):")
    print("  Используйте широкий диапазон HSV и включите вычитание фона")
    print("  Hue: 0-180 (весь спектр)")
    print("  Saturation: 50-255 (отсекаем не насыщенные области)")
    print("  Value: 50-255 (отсекаем темные области)")
    print("  Включите вычитание фона для игнорирования статичного зеленого фона")

if __name__ == "__main__":
    print("Тестирование настроек трекинга для зеленого фона")
    print("=" * 50)
    
    # Показать рекомендации по настройке
    test_color_filtering()
    
    print("\n" + "=" * 50)
    print("Создание тестового видео...")
    create_test_video_with_green_background("test_green_background.mp4")
    
    print("\nДля тестирования трекинга:")
    print("1. Запустите приложение: python run.py")
    print("2. Загрузите созданный файл: test_green_background.mp4")
    print("3. Установите следующие настройки:")
    print("   - Hue: 0 - 180")
    print("   - Saturation: 50 - 255") 
    print("   - Value: 50 - 255")
    print("   - Включите 'Использовать вычитание фона'")
    print("   - Установите 'Скорость обучения фона': 0.01")
    print("4. Нажмите 'Сбросить модель фона'")
    print("5. Включите трекинг и воспроизведите видео")