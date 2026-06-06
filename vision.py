from __future__ import annotations

from typing import List, Tuple

import cv2
import numpy as np

from config import COLOR_PRESETS, MIN_CONTOUR_AREA, MORPH_KERNEL

CALIB_WIN = "HSV Calibration"
MASK_WIN = "Marker Mask"


class MarkerDetector:

    def __init__(self) -> None:
        _, lower, upper = COLOR_PRESETS["1"]
        self.lower = lower.copy()
        self.upper = upper.copy()

    def set_hsv_range(self, lower: np.ndarray, upper: np.ndarray) -> None:
        self.lower = lower.copy()
        self.upper = upper.copy()

    def detect(self, bgr: np.ndarray) -> Tuple[List[Tuple[int, int]], np.ndarray]:
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.lower, self.upper)
        mask = cv2.erode(mask, MORPH_KERNEL, iterations=1)
        mask = cv2.dilate(mask, MORPH_KERNEL, iterations=2)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        blobs = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < MIN_CONTOUR_AREA:
                continue
            moments = cv2.moments(contour)
            if moments["m00"] == 0:
                continue
            cx = int(moments["m10"] / moments["m00"])
            cy = int(moments["m01"] / moments["m00"])
            blobs.append((area, (cx, cy)))

        blobs.sort(reverse=True, key=lambda item: item[0])
        return [centroid for _, centroid in blobs], mask


def init_trackbars(detector: MarkerDetector) -> None:
    cv2.namedWindow(CALIB_WIN, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(CALIB_WIN, 460, 230)
    noop = lambda _: None
    cv2.createTrackbar("H Low", CALIB_WIN, int(detector.lower[0]), 179, noop)
    cv2.createTrackbar("S Low", CALIB_WIN, int(detector.lower[1]), 255, noop)
    cv2.createTrackbar("V Low", CALIB_WIN, int(detector.lower[2]), 255, noop)
    cv2.createTrackbar("H High", CALIB_WIN, int(detector.upper[0]), 179, noop)
    cv2.createTrackbar("S High", CALIB_WIN, int(detector.upper[1]), 255, noop)
    cv2.createTrackbar("V High", CALIB_WIN, int(detector.upper[2]), 255, noop)


def sync_trackbars(detector: MarkerDetector) -> None:
    lower = np.array(
        [
            cv2.getTrackbarPos("H Low", CALIB_WIN),
            cv2.getTrackbarPos("S Low", CALIB_WIN),
            cv2.getTrackbarPos("V Low", CALIB_WIN),
        ],
        dtype=np.uint8,
    )
    upper = np.array(
        [
            cv2.getTrackbarPos("H High", CALIB_WIN),
            cv2.getTrackbarPos("S High", CALIB_WIN),
            cv2.getTrackbarPos("V High", CALIB_WIN),
        ],
        dtype=np.uint8,
    )
    detector.set_hsv_range(lower, upper)


def apply_preset(detector: MarkerDetector, preset_key: str) -> str:
    preset_name, lower, upper = COLOR_PRESETS[preset_key]
    detector.set_hsv_range(lower, upper)
    cv2.setTrackbarPos("H Low", CALIB_WIN, int(lower[0]))
    cv2.setTrackbarPos("S Low", CALIB_WIN, int(lower[1]))
    cv2.setTrackbarPos("V Low", CALIB_WIN, int(lower[2]))
    cv2.setTrackbarPos("H High", CALIB_WIN, int(upper[0]))
    cv2.setTrackbarPos("S High", CALIB_WIN, int(upper[1]))
    cv2.setTrackbarPos("V High", CALIB_WIN, int(upper[2]))
    return preset_name


def draw_calibration_panel(detector: MarkerDetector, preset_name: str, show_mask: bool) -> np.ndarray:
    panel = np.zeros((120, 460, 3), dtype=np.uint8)
    cv2.putText(panel, "HSV marker calibration", (12, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (235, 235, 235), 1, cv2.LINE_AA)
    cv2.putText(
        panel,
        f"Preset: {preset_name}",
        (12, 54),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.48,
        (170, 210, 255),
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        panel,
        f"Low HSV {detector.lower.tolist()}   High HSV {detector.upper.tolist()}",
        (12, 80),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.42,
        (180, 180, 180),
        1,
        cv2.LINE_AA,
    )
    mask_text = "C: hide mask" if show_mask else "C: show mask"
    cv2.putText(panel, "1-5 presets   " + mask_text, (12, 104), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (135, 135, 135), 1, cv2.LINE_AA)
    return panel


def close_mask_window() -> None:
    try:
        cv2.destroyWindow(MASK_WIN)
    except cv2.error:
        pass
