"""
Модуль для трекинга объектов по цвету
"""
import cv2
import numpy as np
from typing import Optional, Tuple, List, Dict
import json
import time
import logging
from scipy.optimize import linear_sum_assignment

logger = logging.getLogger(__name__)


class KalmanFilter2D:
    """Фильтр Калмана с моделью постоянной скорости для координат частицы"""

    def __init__(self, x: float, y: float, measure_var: float = 1.0,
                 process_pos: float = 1.0, process_vel: float = 4.0):
        self.x = np.array([x, y, 0.0, 0.0], dtype=float)
        self.P = np.diag([10.0, 10.0, 100.0, 100.0]).astype(float)
        self.I = np.eye(4)
        self.H = np.array([[1.0, 0.0, 0.0, 0.0],
                           [0.0, 1.0, 0.0, 0.0]])
        self.R = np.eye(2) * measure_var
        self.Q = np.diag([process_pos, process_pos, process_vel, process_vel])

    def predict(self, dt: float) -> np.ndarray:
        if dt <= 0:
            dt = 1.0
        F = np.array([[1.0, 0.0, dt, 0.0],
                      [0.0, 1.0, 0.0, dt],
                      [0.0, 0.0, 1.0, 0.0],
                      [0.0, 0.0, 0.0, 1.0]])
        self.x = F @ self.x
        self.P = F @ self.P @ F.T + self.Q
        return self.x[:2]

    def update(self, z: np.ndarray) -> np.ndarray:
        z = np.asarray(z, dtype=float)
        y = z - self.H @ self.x
        S = self.H @ self.P @ self.H.T + self.R
        K = self.P @ self.H.T @ np.linalg.inv(S)
        self.x = self.x + K @ y
        self.P = (self.I - K @ self.H) @ self.P
        return self.x[:2]

    def mahalanobis(self, z: np.ndarray) -> float:
        z = np.asarray(z, dtype=float)
        y = z - self.H @ self.x
        S = self.H @ self.P @ self.H.T + self.R
        try:
            return float(np.sqrt(y @ np.linalg.inv(S) @ y))
        except np.linalg.LinAlgError:
            return float('inf')


class ObjectTracker:
    def __init__(self):
        self.tracking_enabled = False
        self.track_histories: Dict[int, List[Dict]] = {}
        self.tracks: Dict[int, Dict] = {}
        self.settings = {
            'hue_low': 0, 'hue_high': 180,
            'saturation_low': 50, 'saturation_high': 255,
            'value_low': 50, 'value_high': 255,
            'min_area': 100, 'max_area': 50000,
            'blur_size': 5, 'morph_iters': 2,
            'max_track_distance': 10.0,
            'gate_mahalanobis': 9.21,
            'app_weight': 40.0,
            'app_gate': 0.45,
            'motion_penalty': 40.0,
            'ref_alpha': 0.05,
            'reacquire_after': 4,
            'reacquire_radius': 60.0,
            'min_separation': 8.0,
            'dup_velocity_gate': 5.0,
            'min_hits': 3,
            'max_missed_frames': 30,
            'kf_measure_var': 1.0,
            'kf_process_pos': 0.5,
            'kf_process_vel': 2.0,
        }
        self.background_subtractor = cv2.createBackgroundSubtractorMOG2(detectShadows=True)
        self.use_background_subtraction = True
        self.background_learning_rate = 0.01
        self._kernels = {}
        self.max_tracks = 5
        self._last_frame_time = None

    # ======================== НАСТРОЙКИ ========================

    def update_settings(self, new: Dict):
        self.settings.update(new)

    def set_use_background_subtraction(self, val: bool):
        self.use_background_subtraction = val

    def set_background_learning_rate(self, rate: float):
        self.background_learning_rate = rate

    def set_max_track_distance(self, distance: float):
        self.settings['max_track_distance'] = max(1.0, float(distance))

    def set_max_tracks(self, count: int):
        """Задать предельное число одновременно отслеживаемых точек (ID строго 1..count)"""
        self.max_tracks = max(1, int(count))
        if len(self.tracks) > self.max_tracks:
            for tid in [t['id'] for t in self.tracks.values() if not t['confirmed']]:
                if len(self.tracks) <= self.max_tracks:
                    break
                self._remove(tid)
            while len(self.tracks) > self.max_tracks:
                self._remove(next(reversed(self.tracks)))

    def _alloc_id(self) -> Optional[int]:
        """Наименьший свободный ID из пула 1..max_tracks"""
        for tid in range(1, self.max_tracks + 1):
            if tid not in self.tracks:
                return tid
        return None

    # ======================== ОБРАБОТКА ========================

    def _kernel(self, size: int) -> np.ndarray:
        if size not in self._kernels:
            self._kernels[size] = np.ones((size, size), np.uint8)
        return self._kernels[size]

    def process_frame(self, frame: np.ndarray, timestamp: float) -> List[Dict]:
        if not self.tracking_enabled:
            return []
        try:
            if self._last_frame_time is not None and timestamp - self._last_frame_time > 1.0:
                self.clear_tracking_data()
            self._last_frame_time = timestamp

            detections = self._detect(frame)
            self._update_tracks(detections, timestamp)
            return [t.copy() for t in self.tracks.values() if t['confirmed']]
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
            x = float(M["m10"] / M["m00"])
            y = float(M["m01"] / M["m00"])
            detections.append({
                'x': x, 'y': y, 'area': area,
                'app': self._appearance(hsv, mask, cnt, area)
            })

        detections.sort(key=lambda d: d['area'], reverse=True)
        return detections

    def _appearance(self, hsv: np.ndarray, mask: np.ndarray,
                    cnt: np.ndarray, area: float) -> Optional[Dict]:
        """Признак внешнего вида: нормированная 2D-гистограмма H×S и площадь"""
        bx, by, bw, bh = cv2.boundingRect(cnt)
        sub_mask = mask[by:by + bh, bx:bx + bw]
        sub = hsv[by:by + bh, bx:bx + bw]
        selected = sub_mask > 0
        if not selected.any():
            return None
        h = sub[..., 0][selected]
        s = sub[..., 1][selected]
        hist, _, _ = np.histogram2d(h, s, bins=[6, 4], range=[[0, 180], [0, 256]])
        hist = hist.astype(float)
        total = hist.sum()
        if total <= 0:
            return None
        hist /= total
        return {'hist': hist, 'area': float(area)}

    @staticmethod
    def _app_distance(a: Optional[Dict], b: Optional[Dict]) -> float:
        if a is None or b is None:
            return 0.0
        hist_d = 1.0 - float(np.minimum(a['hist'], b['hist']).sum())
        aa, ab = a['area'], b['area']
        area_d = abs(aa - ab) / max(aa, ab, 1.0)
        return 0.85 * hist_d + 0.15 * area_d

    # ======================== СВЯЗЫВАНИЕ ========================

    def _associate(self, track_list: List[Dict], det_list: List[Dict]):
        if not track_list or not det_list:
            return [], []
        max_dist = self.settings['max_track_distance']
        gate_md = self.settings['gate_mahalanobis']
        app_w = self.settings['app_weight']
        app_gate = self.settings['app_gate']
        motion_penalty = self.settings['motion_penalty']
        cost = np.full((len(track_list), len(det_list)), 1e9)
        for i, track in enumerate(track_list):
            px, py = track['pred']
            vx, vy = float(track['kf'].x[2]), float(track['kf'].x[3])
            speed = float(np.hypot(vx, vy))
            for j, det in enumerate(det_list):
                dist = float(np.hypot(det['x'] - px, det['y'] - py))
                if dist > max_dist:
                    continue
                if track['kf'].mahalanobis((det['x'], det['y'])) > gate_md:
                    continue
                app_dist = self._app_distance(track.get('app'), det.get('app'))
                if app_gate > 0 and app_dist > app_gate:
                    continue
                c = dist + app_w * app_dist
                if motion_penalty > 0 and speed > 1e-3 and dist > 1e-3:
                    cosang = ((det['x'] - px) * vx + (det['y'] - py) * vy) / (speed * dist)
                    if cosang < 0:
                        c += motion_penalty * (-cosang)
                cost[i, j] = c

        rows, cols = linear_sum_assignment(cost)
        matched_tracks, matched_dets = [], []
        for r, c in zip(rows, cols):
            if cost[r, c] >= 1e9:
                continue
            matched_tracks.append(r)
            matched_dets.append(c)
        return matched_tracks, matched_dets

    def _update_tracks(self, detections: List[Dict], timestamp: float):
        tracks = list(self.tracks.values())

        for track in tracks:
            dt = timestamp - track['last_timestamp'] if track['last_timestamp'] is not None else 1.0
            if dt <= 0:
                dt = 1.0
            px, py = track['kf'].predict(dt)
            track['pred'] = (float(px), float(py))
            track['time_since_update'] += 1

        confirmed = [t for t in tracks if t['confirmed']]
        tentative = [t for t in tracks if not t['confirmed']]
        matched_dets = set()

        rows, cols = self._associate(confirmed, detections)
        for r, c in zip(rows, cols):
            self._update_track(confirmed[r], detections[c], timestamp)
            matched_dets.add(c)

        remaining = [(j, d) for j, d in enumerate(detections) if j not in matched_dets]
        rows2, cols2 = self._associate(tentative, [d for _, d in remaining])
        for r, c in zip(rows2, cols2):
            self._update_track(tentative[r], remaining[c][1], timestamp)
            matched_dets.add(remaining[c][0])

        self._reacquire(confirmed, detections, matched_dets, timestamp)

        for track in tracks:
            if track['time_since_update'] == 0:
                continue
            if track['confirmed']:
                if track['time_since_update'] > self.settings['max_missed_frames']:
                    self._remove(track['id'])
            elif track['time_since_update'] > 1:
                self._remove(track['id'])

        for j, det in enumerate(detections):
            if j in matched_dets:
                continue
            if len(self.tracks) >= self.max_tracks:
                break
            if self._too_close_to_existing(det):
                continue
            if self._create(det, timestamp) is None:
                break

        self._suppress_duplicates()

    def _too_close_to_existing(self, det: Dict) -> bool:
        min_sep = self.settings['min_separation']
        app_gate = self.settings['app_gate']
        for track in self.tracks.values():
            dist = float(np.hypot(det['x'] - track['x'], det['y'] - track['y']))
            if dist >= min_sep:
                continue
            if self._app_distance(track.get('app'), det.get('app')) <= app_gate:
                return True
        return False

    def _suppress_duplicates(self):
        """Убрать треки-дубликаты на одной частице (совпадают положение, вид и скорость)"""
        min_sep = self.settings['min_separation']
        app_gate = self.settings['app_gate']
        vel_gate = self.settings['dup_velocity_gate']
        items = sorted(self.tracks.values(), key=lambda t: (t['confirmed'], t['hits']), reverse=True)
        keep = []
        for track in items:
            duplicate = False
            for other in keep:
                dist = float(np.hypot(track['x'] - other['x'], track['y'] - other['y']))
                if dist >= min_sep:
                    continue
                if self._app_distance(track.get('app'), other.get('app')) > app_gate:
                    continue
                vdx = float(track['kf'].x[2] - other['kf'].x[2])
                vdy = float(track['kf'].x[3] - other['kf'].x[3])
                if np.hypot(vdx, vdy) > vel_gate:
                    continue
                duplicate = True
                break
            if duplicate:
                self._remove(track['id'])
            else:
                keep.append(track)

    def _reacquire(self, confirmed: List[Dict], detections: List[Dict],
                   matched_dets: set, timestamp: float):
        """Повторный захват потерянной частицы по внешнему виду в расширенной области"""
        threshold = self.settings['reacquire_after']
        radius = self.settings['reacquire_radius']
        app_gate = self.settings['app_gate']
        app_w = self.settings['app_weight']
        lost = [t for t in confirmed if t['time_since_update'] > threshold]
        lost.sort(key=lambda t: -t['time_since_update'])
        for track in lost:
            best, best_cost, best_j = None, 1e9, None
            for j, det in enumerate(detections):
                if j in matched_dets:
                    continue
                app_dist = self._app_distance(track.get('app'), det.get('app'))
                if app_dist > app_gate:
                    continue
                dist = float(np.hypot(det['x'] - track['ref'][0], det['y'] - track['ref'][1]))
                if dist > radius:
                    continue
                cost = dist + app_w * app_dist
                if cost < best_cost:
                    best, best_cost, best_j = det, cost, j
            if best is not None:
                self._reacquire_track(track, best, timestamp)
                matched_dets.add(best_j)

    def _update_track(self, track: Dict, det: Dict, timestamp: float):
        track['kf'].update((det['x'], det['y']))
        track['x'] = float(track['kf'].x[0])
        track['y'] = float(track['kf'].x[1])
        track['area'] = det['area']
        track['missed_frames'] = 0
        track['timestamp'] = timestamp
        track['last_timestamp'] = timestamp
        track['time_since_update'] = 0
        track['hits'] += 1
        track['age'] += 1
        alpha = self.settings['ref_alpha']
        track['ref'] = track['ref'] * (1.0 - alpha) + np.array([det['x'], det['y']]) * alpha
        self._update_appearance(track, det)
        vx, vy = track['kf'].x[2], track['kf'].x[3]
        track['velocity'] = float(np.hypot(vx, vy))
        if not track['confirmed'] and track['hits'] >= self.settings['min_hits']:
            if sum(1 for t in self.tracks.values() if t['confirmed']) < self.max_tracks:
                track['confirmed'] = True
                self.track_histories.setdefault(track['id'], []).extend(track.get('pending', []))
                track['pending'] = []
        point = self._make_point(track, timestamp)
        if track['confirmed']:
            self.track_histories.setdefault(track['id'], []).append(point)
        else:
            track.setdefault('pending', []).append(point)

    def _update_appearance(self, track: Dict, det: Dict):
        det_app = det.get('app')
        if det_app is None:
            return
        if track.get('app') is None:
            track['app'] = det_app
            return
        hist = 0.85 * track['app']['hist'] + 0.15 * det_app['hist']
        total = hist.sum()
        if total > 0:
            hist = hist / total
        track['app'] = {
            'hist': hist,
            'area': 0.85 * track['app']['area'] + 0.15 * det_app['area'],
        }

    def _reacquire_track(self, track: Dict, det: Dict, timestamp: float):
        track['kf'] = KalmanFilter2D(
            det['x'], det['y'],
            measure_var=self.settings['kf_measure_var'],
            process_pos=self.settings['kf_process_pos'],
            process_vel=self.settings['kf_process_vel'],
        )
        track['x'] = float(det['x'])
        track['y'] = float(det['y'])
        track['ref'] = np.array([det['x'], det['y']])
        track['app'] = det.get('app')
        track['area'] = det['area']
        track['timestamp'] = timestamp
        track['last_timestamp'] = timestamp
        track['time_since_update'] = 0
        track['missed_frames'] = 0
        track['hits'] += 1
        track['velocity'] = 0.0
        self.track_histories.setdefault(track['id'], []).append(self._make_point(track, timestamp))

    def _create(self, det: Dict, timestamp: float) -> Optional[int]:
        tid = self._alloc_id()
        if tid is None:
            return None
        track = {
            'id': tid, 'x': float(det['x']), 'y': float(det['y']), 'area': det['area'],
            'app': det.get('app'), 'ref': np.array([det['x'], det['y']]),
            'kf': KalmanFilter2D(
                det['x'], det['y'],
                measure_var=self.settings['kf_measure_var'],
                process_pos=self.settings['kf_process_pos'],
                process_vel=self.settings['kf_process_vel'],
            ),
            'timestamp': timestamp, 'last_timestamp': timestamp,
            'time_since_update': 0, 'missed_frames': 0,
            'hits': 1, 'age': 1, 'confirmed': False, 'velocity': 0.0,
            'pred': (float(det['x']), float(det['y'])),
            'pending': [],
        }
        self.tracks[tid] = track
        track['pending'].append(self._make_point(track, timestamp))
        return tid

    @staticmethod
    def _make_point(track: Dict, timestamp: float) -> Dict:
        return {
            'timestamp': timestamp, 'x': track['x'], 'y': track['y'],
            'area': track['area'], 'velocity': track.get('velocity', 0.0),
            'track_id': track['id']
        }

    def _remove(self, tid: int):
        self.tracks.pop(tid, None)
        self.track_histories.pop(tid, None)

    # ======================== ОТОБРАЖЕНИЕ ========================

    def _color(self, idx: int) -> Tuple[int, int, int]:
        colors = [(0, 255, 0), (0, 200, 255), (255, 200, 0), (255, 0, 200),
                  (200, 0, 255), (0, 128, 255), (128, 0, 255)]
        return colors[idx % len(colors)]

    def draw_tracking_info(self, frame: np.ndarray) -> np.ndarray:
        idx = 0
        for track in self.tracks.values():
            if not track['confirmed']:
                continue
            x, y = int(track['x']), int(track['y'])
            color = self._color(idx)
            idx += 1
            cv2.circle(frame, (x, y), 6, color, -1)
            cv2.circle(frame, (x, y), 12, color, 2)
            cv2.line(frame, (x-12, y), (x+12, y), color, 2)
            cv2.line(frame, (x, y-12), (x, y+12), color, 2)
            cv2.putText(frame, f"ID {track['id']} ({x}, {y})", (x+15, y-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            cv2.putText(frame, f"v={track.get('velocity', 0):.1f}", (x+15, y+12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        return frame

    # ======================== УПРАВЛЕНИЕ ========================

    def start_tracking(self):
        self.tracking_enabled = True
        self.clear_tracking_data()

    def stop_tracking(self):
        self.tracking_enabled = False

    def get_active_tracks(self) -> List[Dict]:
        return [t.copy() for t in self.tracks.values() if t['confirmed']]

    def get_tracking_data(self) -> List[Dict]:
        all_pts = []
        for hist in self.track_histories.values():
            all_pts.extend(hist)
        return sorted(all_pts, key=lambda p: p['timestamp'])

    def clear_tracking_data(self):
        self.tracks.clear()
        self.track_histories.clear()
        self._last_frame_time = None

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
