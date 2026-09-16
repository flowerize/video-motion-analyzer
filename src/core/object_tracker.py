"""
Модуль для трекинга объектов по цвету
"""
import cv2
import numpy as np
from typing import Optional, Tuple, List, Dict
import json
import time
import logging

logger = logging.getLogger(__name__)


class ObjectTracker:
    def __init__(self):
        self.tracking_enabled = False
        self.track_histories: Dict[int, List[Dict]] = {}
        self.tracks: Dict[int, Dict] = {}
        self.next_track_id = 1
        self.settings = {
            'hue_low': 0, 'hue_high': 180,
            'saturation_low': 50, 'saturation_high': 255,
            'value_low': 50, 'value_high': 255,
            'min_area': 100, 'max_area': 50000,
            'blur_size': 5, 'morph_iters': 2
        }
        self.background_subtractor = cv2.createBackgroundSubtractorMOG2(detectShadows=True)
        self.use_background_subtraction = True
        self.background_learning_rate = 0.01
        self._kernels = {}
        self.max_track_distance = 60.0
        self.max_missed_frames = 10
        self.max_tracks = 10

    def update_settings(self, new: Dict):
        self.settings.update(new)

    def set_use_background_subtraction(self, val: bool):
        self.use_background_subtraction = val

    def set_background_learning_rate(self, rate: float):
        self.background_learning_rate = rate

    def _kernel(self, size: int) -> np.ndarray:
        if size not in self._kernels:
            self._kernels[size] = np.ones((size, size), np.uint8)
        return self._kernels[size]

    def process_frame(self, frame: np.ndarray, timestamp: float) -> List[Dict]:
        if not self.tracking_enabled:
            return []
        try:
            detections = self._detect(frame)
            self._update_tracks(detections, timestamp)
            return list(self.tracks.values())
        except Exception as e:
            logger.error(f"Ошибка обработки кадра: {e}")
            return []

    def _detect(self, frame: np.ndarray) -> List[Dict]:
        k5 = self._kernel(5)
        if self.use_background_subtraction:
            fg = self.background_subtractor.apply(frame, learningRate=self.background_learning_rate)
            fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, k5, iterations=2)
            fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, k5, iterations=2)
            masked = cv2.bitwise_and(frame, frame, mask=fg)
            hsv = cv2.cvtColor(masked, cv2.COLOR_BGR2HSV)
        else:
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            fg = None

        lower = np.array([self.settings['hue_low'], self.settings['saturation_low'], self.settings['value_low']])
        upper = np.array([self.settings['hue_high'], self.settings['saturation_high'], self.settings['value_high']])
        color_mask = cv2.inRange(hsv, lower, upper)
        mask = cv2.bitwise_and(fg, color_mask) if fg is not None else color_mask

        mi = self.settings['morph_iters']
        if mi > 0:
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k5, iterations=mi)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k5, iterations=mi)
        bs = self.settings['blur_size']
        if bs > 0:
            mask = cv2.GaussianBlur(mask, (bs, bs), 0)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        detections = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < self.settings['min_area'] or area > self.settings['max_area']:
                continue
            M = cv2.moments(cnt)
            if M["m00"] == 0:
                continue
            x = int(M["m10"] / M["m00"])
            y = int(M["m01"] / M["m00"])
            detections.append({'x': x, 'y': y, 'area': area})

        detections.sort(key=lambda d: d['area'], reverse=True)
        return detections[:self.max_tracks]

    def _update_tracks(self, detections: List[Dict], timestamp: float):
        for track in self.tracks.values():
            track['missed_frames'] += 1

        unmatched = [d.copy() for d in detections]
        active = list(self.tracks.values())

        for track in active:
            best_det, best_dist = None, float('inf')
            for det in unmatched:
                dist = np.linalg.norm([det['x'] - track['x'], det['y'] - track['y']])
                if dist < best_dist:
                    best_dist, best_det = dist, det
            if best_det and best_dist <= self.max_track_distance:
                unmatched.remove(best_det)
                self._update(track, best_det, timestamp)
            elif track['missed_frames'] > self.max_missed_frames:
                self.tracks.pop(track['id'], None)

        for det in unmatched:
            self._create(det, timestamp)

    def _update(self, track: Dict, det: Dict, timestamp: float):
        prev_x, prev_y = track['x'], track['y']
        dt = timestamp - track['timestamp'] if track['timestamp'] is not None else 0.0
        track['x'], track['y'], track['area'] = det['x'], det['y'], det['area']
        track['timestamp'] = timestamp
        track['missed_frames'] = 0
        if dt > 0:
            track['velocity'] = float(np.sqrt((track['x'] - prev_x)**2 + (track['y'] - prev_y)**2) / dt)
        else:
            track['velocity'] = 0.0
        self.track_histories.setdefault(track['id'], []).append({
            'timestamp': timestamp, 'x': track['x'], 'y': track['y'],
            'area': track['area'], 'velocity': track['velocity'], 'track_id': track['id']
        })

    def _create(self, det: Dict, timestamp: float):
        tid = self.next_track_id
        self.next_track_id += 1
        track = {'id': tid, 'x': det['x'], 'y': det['y'], 'area': det['area'],
                 'timestamp': timestamp, 'missed_frames': 0, 'velocity': 0.0}
        self.tracks[tid] = track
        self.track_histories.setdefault(tid, []).append({
            'timestamp': timestamp, 'x': det['x'], 'y': det['y'],
            'area': det['area'], 'velocity': 0.0, 'track_id': tid
        })

    def _color(self, idx: int) -> Tuple[int, int, int]:
        colors = [(0, 255, 0), (0, 200, 255), (255, 200, 0), (255, 0, 200),
                  (200, 0, 255), (0, 128, 255), (128, 0, 255)]
        return colors[idx % len(colors)]

    def draw_tracking_info(self, frame: np.ndarray) -> np.ndarray:
        for idx, track in enumerate(self.tracks.values()):
            x, y = int(track['x']), int(track['y'])
            color = self._color(idx)
            cv2.circle(frame, (x, y), 6, color, -1)
            cv2.circle(frame, (x, y), 12, color, 2)
            cv2.line(frame, (x-12, y), (x+12, y), color, 2)
            cv2.line(frame, (x, y-12), (x, y+12), color, 2)
            cv2.putText(frame, f"ID {track['id']} ({x}, {y})", (x+15, y-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            cv2.putText(frame, f"v={track.get('velocity', 0):.1f}", (x+15, y+12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        return frame

    def start_tracking(self):
        self.tracking_enabled = True
        self.clear_tracking_data()

    def stop_tracking(self):
        self.tracking_enabled = False

    def get_active_tracks(self) -> List[Dict]:
        return [t.copy() for t in self.tracks.values()]

    def get_tracking_data(self) -> List[Dict]:
        all_pts = []
        for hist in self.track_histories.values():
            all_pts.extend(hist)
        return sorted(all_pts, key=lambda p: p['timestamp'])

    def clear_tracking_data(self):
        self.tracks.clear()
        self.track_histories.clear()
        self.next_track_id = 1

    def reset_background_model(self):
        self.background_subtractor = cv2.createBackgroundSubtractorMOG2(detectShadows=True)

    def export_data(self, filename: str) -> bool:
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({
                    'settings': self.settings,
                    'tracks': self.track_histories,
                    'exported_at': time.time()
                }, f, indent=2, ensure_ascii=False)
            logger.info(f"Данные экспортированы в {filename}")
            return True
        except Exception as e:
            logger.error(f"Ошибка экспорта: {e}")
            return False
