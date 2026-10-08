"""
Менеджер конфигурации
"""
import json
import logging
import os
from typing import Dict, Optional

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "tracking": {
        "hue_low": 0, "hue_high": 180,
        "saturation_low": 50, "saturation_high": 255,
        "value_low": 50, "value_high": 255,
        "min_area": 100, "max_area": 50000,
        "blur_size": 5, "morph_iters": 2,
        "use_background_subtraction": True,
        "background_learning_rate": 0.01,
        "max_tracks": 5,
        "max_track_distance": 15
    },
    "recent_files": []
}

CONFIG_FILENAME = "config.json"


class ConfigManager:
    def __init__(self):
        self.config_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "..", CONFIG_FILENAME
        )
        self.config = dict(DEFAULT_CONFIG)
        self._load()

    def _load(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                    self._merge(self.config, saved)
                logger.info("Конфигурация загружена")
            except Exception as e:
                logger.error(f"Ошибка загрузки конфига: {e}")

    def _merge(self, base: Dict, override: Dict):
        for k, v in override.items():
            if k in base and isinstance(base[k], dict) and isinstance(v, dict):
                self._merge(base[k], v)
            else:
                base[k] = v

    def save(self):
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Ошибка сохранения конфига: {e}")

    def get_tracking_settings(self) -> Dict:
        return dict(self.config.get('tracking', DEFAULT_CONFIG['tracking']))

    def set_tracking_settings(self, settings: Dict):
        self.config.setdefault('tracking', {}).update(settings)

    def add_recent_file(self, path: str):
        recent = self.config.get('recent_files', [])
        if path in recent:
            recent.remove(path)
        recent.insert(0, path)
        self.config['recent_files'] = recent[:5]
