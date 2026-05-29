"""Virtual Drum System — OpenCV-Based Real-Time Gesture Recognition

Course  : Computer Vision
Authors : Jerome Maxcellino Budianto (2802412894)
          Hibatullah Fawwaz Hana     (2802485271)

Run generate_sounds.py once before starting to create the .wav files.
Usage   : python virtual_drum.py
Controls: Q = quit | HSV Calibration window = tune marker color range | 1-5 = switch color preset
"""

from __future__ import annotations

import os
import sys
import time
from typing import Dict, List, Tuple

import cv2
import numpy as np
import pygame

#config buat ukuran layar dan lainnya
FRAME_W, FRAME_H = 640, 480

MORPH_KERNEL     = np.ones((5, 5), np.uint8)
MIN_CONTOUR_AREA = 200
HIT_FLASH_FRAMES = 10
RIPPLE_FRAMES    = 22
RIPPLE_MAX_R     = 72
FLOAT_FRAMES     = 28

COLOR_PRESETS = {
    "1": ("Hijau / Green",   np.array([35,  80,  60], np.uint8), np.array([85,  255, 255], np.uint8)),
    "2": ("Kuning / Yellow", np.array([18,  80,  80], np.uint8), np.array([38,  255, 255], np.uint8)),
    "3": ("Orange",          np.array([5,  120,  80], np.uint8), np.array([20,  255, 255], np.uint8)),
    "4": ("Biru / Blue",     np.array([100, 80,  60], np.uint8), np.array([135, 255, 255], np.uint8)),
    "5": ("Pink / Magenta",  np.array([140, 80,  60], np.uint8), np.array([175, 255, 255], np.uint8)),
}
HSV_LOWER_DEFAULT  = COLOR_PRESETS["1"][1]
HSV_UPPER_DEFAULT  = COLOR_PRESETS["1"][2]
ACTIVE_PRESET_NAME = COLOR_PRESETS["1"][0]

# (label, x1, y1, x2, y2, sound_path, idle_BGR, hit_BGR, drum_type)
ROI_DEFS: List[Tuple] = [
    ("Hi-Hat",  10,  20, 205, 185, "sounds/hihat.mp3", (140, 140,   0), (255, 255,   0), "hihat"),
    ("Snare",  225,  20, 415, 185, "sounds/snare.mp3", (  0, 130, 200), (  0, 200, 255), "snare"),
    ("Tom",    435,  20, 630, 185, "sounds/tom.mp3",   (160,   0, 160), (255,  50, 255), "tom"),
    ("Kick",    10, 295, 630, 460, "sounds/kick.mp3",  ( 30,  30, 180), ( 50,  50, 255), "kick"),
]


#ini buat load suara audio yang gw ambil dari free source, pake pygame

class AudioEngine:

    def __init__(self, paths: List[str]) -> None:
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
        pygame.mixer.init()
        pygame.mixer.set_num_channels(16)

        self._sounds: Dict[str, pygame.mixer.Sound] = {}
        for p in paths:
            if os.path.isfile(p):
                self._sounds[p] = pygame.mixer.Sound(p)
            else:
                print(f"generate_sounds.py")

    def play(self, path: str) -> None:
        sound = self._sounds.get(path)
        if sound:
            sound.play()

    def quit(self) -> None:
        pygame.mixer.quit()


#marker detector jadi disini dia deteksi warna pake hsv yang beda dengan background, trus dari hsv itu nanti di process lagi biar makin akurat

class MarkerDetector:

    def __init__(self) -> None:
        self.lower = HSV_LOWER_DEFAULT.copy()
        self.upper = HSV_UPPER_DEFAULT.copy()

    def set_hsv_range(self, lower: np.ndarray, upper: np.ndarray) -> None:
        self.lower = lower
        self.upper = upper

    def detect(self, bgr: np.ndarray) -> Tuple[List[Tuple[int, int]], np.ndarray]:
        hsv  = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.lower, self.upper)
        mask = cv2.erode (mask, MORPH_KERNEL, iterations=1)
        mask = cv2.dilate(mask, MORPH_KERNEL, iterations=2)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        centroids: List[Tuple[int, int]] = []
        for cnt in contours:
            if cv2.contourArea(cnt) < MIN_CONTOUR_AREA:
                continue
            M = cv2.moments(cnt)
            if M["m00"] == 0:
                continue
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            centroids.append((cx, cy))

        return centroids, mask

#animasi buat UI nya gw juga kurang ngerti la karena gw suruh AI buat enchance

class ROIManager:

    def __init__(self, defs: List[Tuple], audio: AudioEngine) -> None:
        self._defs   = defs
        self._audio  = audio
        n = len(defs)
        self._inside = [False] * n
        self._flash  = [0]    * n
        self._hits   = [0]    * n
        # ripple: [cx, cy, age_frames, color_BGR]
        self._ripples: List[List] = []
        # float:  [text, cx, y_start, age_frames, color_BGR]
        self._floats:  List[List] = []
        self._vignette = self._make_vignette(FRAME_H, FRAME_W)

    @staticmethod
    def _make_vignette(h: int, w: int) -> np.ndarray:
        X  = np.linspace(-1.0, 1.0, w, dtype=np.float32)
        Y  = np.linspace(-1.0, 1.0, h, dtype=np.float32)
        xv, yv = np.meshgrid(X, Y)
        dark = np.clip(np.sqrt(xv**2 + yv**2) * 0.40, 0.0, 0.50)
        ch   = (dark * 255).astype(np.uint8)
        return np.dstack([ch, ch, ch])

    @staticmethod
    def _point_in_rect(cx: int, cy: int, x1: int, y1: int, x2: int, y2: int) -> bool:
        return x1 <= cx <= x2 and y1 <= cy <= y2

    @staticmethod
    def _rounded_rect(
        img: np.ndarray, x1: int, y1: int, x2: int, y2: int,
        color: Tuple, thickness: int, r: int = 10,
    ) -> None:
        r = max(1, min(r, (x2 - x1) // 4, (y2 - y1) // 4))
        cv2.line(img, (x1 + r, y1), (x2 - r, y1), color, thickness)
        cv2.line(img, (x1 + r, y2), (x2 - r, y2), color, thickness)
        cv2.line(img, (x1, y1 + r), (x1, y2 - r), color, thickness)
        cv2.line(img, (x2, y1 + r), (x2, y2 - r), color, thickness)
        cv2.ellipse(img, (x1 + r, y1 + r), (r, r), 180,   0, 90, color, thickness)
        cv2.ellipse(img, (x2 - r, y1 + r), (r, r), 270,   0, 90, color, thickness)
        cv2.ellipse(img, (x1 + r, y2 - r), (r, r),  90,   0, 90, color, thickness)
        cv2.ellipse(img, (x2 - r, y2 - r), (r, r),   0,   0, 90, color, thickness)

    @staticmethod
    def _drum_icon(
        img: np.ndarray, x1: int, y1: int, x2: int, y2: int,
        drum_type: str, idle_color: Tuple,
    ) -> None:
        cx  = (x1 + x2) // 2
        cy  = (y1 + y2) // 2
        w   = x2 - x1
        h   = y2 - y1
        dim = tuple(max(c // 3, 0) for c in idle_color)

        if drum_type == "hihat":
            aw = w // 5
            ah = max(h // 14, 3)
            cv2.ellipse(img, (cx, cy - h // 10), (aw, ah), 0, 0, 360, dim, 1)
            cv2.ellipse(img, (cx, cy + h // 10), (aw, ah), 0, 0, 360, dim, 1)
            cv2.line(img, (cx, cy - h // 10 + ah), (cx, cy + h // 10 - ah), dim, 1)
        elif drum_type in ("snare", "tom"):
            r = min(w, h) // 5
            cv2.circle(img, (cx, cy), r, dim, 1)
            if drum_type == "snare":
                for dy in (-3, 0, 3):
                    cv2.line(img, (cx - r + 6, cy + r // 2 + dy),
                             (cx + r - 6, cy + r // 2 + dy), dim, 1)
        elif drum_type == "kick":
            rw = w // 5
            rh = h // 4
            cv2.ellipse(img, (cx, cy), (rw, rh), 0, 0, 360, dim, 2)
            cv2.ellipse(img, (cx, cy), (rw // 2, rh // 2), 0, 0, 360, dim, 1)

    def total_hits(self) -> int:
        return sum(self._hits)

    def update(self, centroids: List[Tuple[int, int]]) -> None:
        for i, (label, x1, y1, x2, y2, snd, c_idle, c_hit, *_) in enumerate(self._defs):
            hit = any(self._point_in_rect(cx, cy, x1, y1, x2, y2) for cx, cy in centroids)

            if hit and not self._inside[i]:
                self._audio.play(snd)
                self._flash[i]  = HIT_FLASH_FRAMES
                self._hits[i]  += 1
                self._inside[i] = True
                rcx = (x1 + x2) // 2
                rcy = (y1 + y2) // 2
                self._ripples.append([rcx, rcy, 0, c_hit])
                self._floats.append([label.upper(), rcx, y1, 0, c_hit])
            elif not hit:
                self._inside[i] = False

            if self._flash[i] > 0:
                self._flash[i] -= 1

        self._ripples = [r for r in self._ripples if r[2] < RIPPLE_FRAMES]
        for r in self._ripples:
            r[2] += 1

        self._floats = [f for f in self._floats if f[3] < FLOAT_FRAMES]
        for f in self._floats:
            f[3] += 1

    def draw(self, frame: np.ndarray) -> None:
        # Subtle edge vignette
        frame[:] = cv2.subtract(frame, self._vignette)

        for i, (label, x1, y1, x2, y2, _, c_idle, c_hit, drum_type) in enumerate(self._defs):
            active = self._flash[i] > 0
            color  = c_hit if active else c_idle
            alpha  = 0.30  if active else 0.08

            # Semi-transparent tinted fill
            fill = np.zeros((y2 - y1, x2 - x1, 3), dtype=np.uint8)
            fill[:] = color
            frame[y1:y2, x1:x2] = cv2.addWeighted(
                frame[y1:y2, x1:x2], 1.0 - alpha, fill, alpha, 0,
            )

            # Drum shape icon (very dim guide)
            self._drum_icon(frame, x1, y1, x2, y2, drum_type, c_idle)

            # Rounded border
            self._rounded_rect(frame, x1, y1, x2, y2, color, 3 if active else 1, r=10)

            # Drum label
            font_scale = 0.9 if drum_type == "kick" else 0.65
            lbl_thick  = 2
            label_y    = y1 + 38 if drum_type == "kick" else y1 + 28
            cv2.putText(
                frame, label, (x1 + 12, label_y),
                cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, lbl_thick, cv2.LINE_AA,
            )

            # Hit counter, top-right corner
            hit_str = str(self._hits[i])
            (tw, _), _ = cv2.getTextSize(hit_str, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.putText(
                frame, hit_str, (x2 - tw - 10, y1 + 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA,
            )

        # Expanding ripple circles
        for rcx, rcy, age, color in self._ripples:
            t      = age / RIPPLE_FRAMES
            radius = max(1, int(t * RIPPLE_MAX_R))
            alpha  = 1.0 - t
            thick  = max(1, int(3 * (1.0 - t)))
            c = tuple(int(v * alpha) for v in color)
            cv2.circle(frame, (rcx, rcy), radius, c, thick, cv2.LINE_AA)

        # Floating label text rising upward
        for text, tx, y_start, age, color in self._floats:
            t = age / FLOAT_FRAMES
            y = y_start - int(t * 55) - 5
            if 0 < y < FRAME_H:
                alpha = 1.0 - t
                c = tuple(int(v * alpha) for v in color)
                (tw, _), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2)
                cv2.putText(
                    frame, text, (tx - tw // 2, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, c, 2, cv2.LINE_AA,
                )

# HSV CALIBRATION TRACKBARS

CALIB_WIN = "HSV Calibration  (tune marker color)"


def init_trackbars(det: MarkerDetector) -> None:
    cv2.namedWindow(CALIB_WIN, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(CALIB_WIN, 440, 240)
    nop = lambda _: None
    cv2.createTrackbar("H Low",  CALIB_WIN, int(det.lower[0]), 179, nop)
    cv2.createTrackbar("S Low",  CALIB_WIN, int(det.lower[1]), 255, nop)
    cv2.createTrackbar("V Low",  CALIB_WIN, int(det.lower[2]), 255, nop)
    cv2.createTrackbar("H High", CALIB_WIN, int(det.upper[0]), 179, nop)
    cv2.createTrackbar("S High", CALIB_WIN, int(det.upper[1]), 255, nop)
    cv2.createTrackbar("V High", CALIB_WIN, int(det.upper[2]), 255, nop)


def sync_trackbars(det: MarkerDetector) -> None:
    lo = np.array([
        cv2.getTrackbarPos("H Low",  CALIB_WIN),
        cv2.getTrackbarPos("S Low",  CALIB_WIN),
        cv2.getTrackbarPos("V Low",  CALIB_WIN),
    ], dtype=np.uint8)
    hi = np.array([
        cv2.getTrackbarPos("H High", CALIB_WIN),
        cv2.getTrackbarPos("S High", CALIB_WIN),
        cv2.getTrackbarPos("V High", CALIB_WIN),
    ], dtype=np.uint8)
    det.set_hsv_range(lo, hi)


    #ini buat draw marker nya pake blur biar keliatan smooth

def draw_markers(frame: np.ndarray, centroids: List[Tuple[int, int]]) -> None:
    glow_color = (255, 160, 30) 
    for cx, cy in centroids:
        # Soft glow: draw a circle on a patch then blur it and add back
        r  = 22
        px1 = max(cx - r, 0);  py1 = max(cy - r, 0)
        px2 = min(cx + r, frame.shape[1]);  py2 = min(cy + r, frame.shape[0])
        patch = frame[py1:py2, px1:px2].copy()
        glow  = np.zeros_like(patch)
        cv2.circle(glow, (cx - px1, cy - py1), r // 2, glow_color, -1)
        glow = cv2.GaussianBlur(glow, (0, 0), 5)
        frame[py1:py2, px1:px2] = cv2.add(patch, glow)
        # Solid core dot
        cv2.circle(frame, (cx, cy), 7, glow_color, -1, cv2.LINE_AA)
        cv2.circle(frame, (cx, cy), 7, (255, 255, 255), 1, cv2.LINE_AA)
        # Small specular highlight
        cv2.circle(frame, (cx - 2, cy - 3), 2, (255, 255, 255), -1, cv2.LINE_AA)


#ini buat hud yang di bawah

def draw_hud(frame: np.ndarray, fps: float, preset_name: str, total_hits: int) -> None:
    h, w = frame.shape[:2]

    #buat transparant di bawah
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, h - 52), (w, h), (10, 10, 10), -1)
    cv2.addWeighted(overlay, 0.60, frame, 0.40, 0, frame)
    cv2.line(frame, (0, h - 52), (w, h - 52), (55, 55, 55), 1)

    # FPS with color indicator (green/yellow/red)
    fps_color = (0, 220, 80) if fps >= 25 else (0, 165, 255) if fps >= 15 else (0, 50, 220)
    cv2.putText(frame, f"FPS {fps:4.0f}", (8, h - 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.50, fps_color, 1, cv2.LINE_AA)

    # Total hit count
    cv2.putText(frame, f"HITS  {total_hits}", (90, h - 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.50, (200, 200, 200), 1, cv2.LINE_AA)

    # Active marker preset
    cv2.putText(frame, f"Marker: {preset_name}", (8, h - 11),
                cv2.FONT_HERSHEY_SIMPLEX, 0.40, (130, 130, 130), 1, cv2.LINE_AA)

    # Controls hint (rata kanan)
    hint = "1-5 = ganti warna   Q = keluar"
    (tw, _), _ = cv2.getTextSize(hint, cv2.FONT_HERSHEY_SIMPLEX, 0.36, 1)
    cv2.putText(frame, hint, (w - tw - 6, h - 11),
                cv2.FONT_HERSHEY_SIMPLEX, 0.36, (100, 100, 100), 1, cv2.LINE_AA)



#ini buat main loop nya

def main() -> None:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    sound_paths = [d[5] for d in ROI_DEFS]
    audio   = AudioEngine(sound_paths)
    det     = MarkerDetector()
    roi_mgr = ROIManager(ROI_DEFS, audio)

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("mengeror")
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  FRAME_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)
    cap.set(cv2.CAP_PROP_FPS, 30)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    MAIN_WIN = "Virtual Drum - Press Q to quit"
    cv2.namedWindow(MAIN_WIN, cv2.WINDOW_NORMAL)
    init_trackbars(det)

    preset_name = ACTIVE_PRESET_NAME
    t_prev = time.perf_counter()

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        frame = cv2.flip(frame, 1)

        sync_trackbars(det)
        centroids, mask = det.detect(frame)
        roi_mgr.update(centroids)

        roi_mgr.draw(frame)
        draw_markers(frame, centroids)

        t_now  = time.perf_counter()
        fps    = 1.0 / max(t_now - t_prev, 1e-9)
        t_prev = t_now
        draw_hud(frame, fps, preset_name, roi_mgr.total_hits())

        cv2.imshow(MAIN_WIN, frame)
        cv2.imshow(CALIB_WIN, mask)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break

        key_char = chr(key) if 32 <= key < 128 else ""
        if key_char in COLOR_PRESETS:
            preset_name, lo, hi = COLOR_PRESETS[key_char]
            det.set_hsv_range(lo.copy(), hi.copy())
            cv2.setTrackbarPos("H Low",  CALIB_WIN, int(lo[0]))
            cv2.setTrackbarPos("S Low",  CALIB_WIN, int(lo[1]))
            cv2.setTrackbarPos("V Low",  CALIB_WIN, int(lo[2]))
            cv2.setTrackbarPos("H High", CALIB_WIN, int(hi[0]))
            cv2.setTrackbarPos("S High", CALIB_WIN, int(hi[1]))
            cv2.setTrackbarPos("V High", CALIB_WIN, int(hi[2]))
            print(f"[INFO] Preset: {preset_name}")

    cap.release()
    audio.quit()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
