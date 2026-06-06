from __future__ import annotations

from typing import Dict, List

import numpy as np

FRAME_W = 640
FRAME_H = 480
TARGET_FPS = 30

MORPH_KERNEL = np.ones((5, 5), np.uint8)
MIN_CONTOUR_AREA = 200

HIT_LINE_Y = 370
HIT_ZONE_TOP = 325
HIT_ZONE_BOTTOM = 430

STAFF_Y = 235
STAFF_CENTER_X = 320
STAFF_BAND_TOP = 188
STAFF_BAND_BOTTOM = 282
NOTE_TRAVEL_TIME = 2.0

PERFECT_WINDOW = 0.100
GOOD_WINDOW = 0.200

COLOR_PRESETS = {
    "1": ("Green", np.array([35, 80, 60], np.uint8), np.array([85, 255, 255], np.uint8)),
    "2": ("Yellow", np.array([18, 80, 80], np.uint8), np.array([38, 255, 255], np.uint8)),
    "3": ("Orange", np.array([5, 120, 80], np.uint8), np.array([20, 255, 255], np.uint8)),
    "4": ("Blue", np.array([100, 80, 60], np.uint8), np.array([135, 255, 255], np.uint8)),
    "5": ("Pink / Magenta", np.array([140, 80, 60], np.uint8), np.array([175, 255, 255], np.uint8)),
}

LANES: List[Dict] = [
    {
        "id": "hihat",
        "label": "Hi-Hat",
        "sound": "sounds/hihat.wav",
        "pad": (10, 20, 205, 185),
        "icon": "hihat",
        "color": (40, 205, 230),
        "hit_color": (80, 255, 255),
    },
    {
        "id": "snare",
        "label": "Snare",
        "sound": "sounds/snare.wav",
        "pad": (225, 20, 415, 185),
        "icon": "snare",
        "color": (245, 130, 55),
        "hit_color": (255, 180, 95),
    },
    {
        "id": "tom",
        "label": "Tom",
        "sound": "sounds/tom.wav",
        "pad": (435, 20, 630, 185),
        "icon": "tom",
        "color": (210, 95, 210),
        "hit_color": (255, 135, 255),
    },
    {
        "id": "kick",
        "label": "Kick",
        "sound": "sounds/kick.wav",
        "pad": (10, 295, 630, 460),
        "icon": "kick",
        "color": (55, 65, 245),
        "hit_color": (80, 100, 255),
    },
]

LANE_BY_ID = {lane["id"]: lane for lane in LANES}
