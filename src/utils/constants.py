"""
Константы
"""
TRACKING_SETTINGS = {
    "min_area": 100, "max_area": 50000,
    "blur_size": 5, "morph_iters": 2,
    "hue_low": 0, "hue_high": 180,
    "saturation_low": 50, "saturation_high": 255,
    "value_low": 50, "value_high": 255,
    "max_tracks": 5
}

SUPPORTED_VIDEO_FORMATS = (".mp4", ".avi", ".mov", ".mkv", ".wmv")


def setup_theme():
    pass
