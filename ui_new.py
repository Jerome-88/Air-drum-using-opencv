from __future__ import annotations

from typing import Dict, Iterable, List, Set, Tuple

import cv2
import numpy as np

from config import (
    FRAME_H,
    FRAME_W,
    LANES,
    NOTE_TRAVEL_TIME,
    STAFF_BAND_BOTTOM,
    STAFF_BAND_TOP,
    STAFF_CENTER_X,
    STAFF_Y,
)
from game import FREE_PLAY, GAME_OVER, MENU, PAUSED, GameEvent, RhythmGame

NOTE_RADIUS = 11
FLASH_FRAMES = 10
RIPPLE_FRAMES = 20
FLOAT_FRAMES = 30
PAD_ENTRY_FLASH = 4

BG = (10, 12, 18)
PANEL = (18, 21, 30)
PANEL_EDGE = (70, 78, 94)
TEXT = (236, 240, 246)
MUTED = (144, 153, 168)
GOLD = (55, 205, 255)


class GameUI:
    def __init__(self) -> None:
        self.pad_rects: Dict[str, Tuple[int, int, int, int]] = {
            lane["id"]: lane["pad"] for lane in LANES
        }
        self.pad_flash = {lane["id"]: 0 for lane in LANES}
        self.pad_entry_flash = {lane["id"]: 0 for lane in LANES}
        self.pad_hits = {lane["id"]: 0 for lane in LANES}
        self.ripples: List[List] = []
        self.floats: List[List] = []
        self.rhythm_visible = True
        self._vignette = self._make_vignette(FRAME_H, FRAME_W)

    def toggle_rhythm(self) -> None:
        self.rhythm_visible = not self.rhythm_visible

    def reset_run_feedback(self) -> None:
        self.pad_hits = {lane["id"]: 0 for lane in LANES}
        self.pad_flash = {lane["id"]: 0 for lane in LANES}
        self.pad_entry_flash = {lane["id"]: 0 for lane in LANES}
        self.ripples.clear()
        self.floats.clear()

    def active_lanes_for_centroids(self, centroids: Iterable[Tuple[int, int]]) -> Set[str]:
        active: Set[str] = set()
        for cx, cy in centroids:
            for lane_id, rect in self.pad_rects.items():
                if _point_in_ellipse(cx, cy, rect):
                    active.add(lane_id)
        for lane_id in active:
            self.pad_entry_flash[lane_id] = max(self.pad_entry_flash[lane_id], PAD_ENTRY_FLASH)
        return active

    def add_events(self, events: Iterable[GameEvent]) -> None:
        for event in events:
            lane = _lane(event.lane)
            cx, cy, _, _ = _ellipse_metrics(self.pad_rects[event.lane])
            color = lane["hit_color"] if event.kind != "Miss" else (45, 55, 235)
            self.pad_flash[event.lane] = FLASH_FRAMES
            if event.kind not in ("Miss", "Drum"):
                self.pad_hits[event.lane] += 1
            self.ripples.append([cx, cy, 0, color, 82])
            self.ripples.append([STAFF_CENTER_X, STAFF_Y, 0, color, 34])
            if event.kind != "Drum":
                self.floats.append([event.kind.upper(), STAFF_CENTER_X, STAFF_Y - 18, 0, color])

    def draw(
        self,
        frame: np.ndarray,
        game: RhythmGame,
        centroids: List[Tuple[int, int]],
        now: float,
        fps: float,
        preset_name: str,
        show_mask: bool,
    ) -> None:
        song_time = game.current_song_time(now)
        self._prepare_camera(frame)
        self._draw_drum_pads(frame)
        if self.rhythm_visible and game.state != FREE_PLAY:
            self._draw_staff(frame, game, song_time)
        self._draw_feedback(frame)
        self._draw_markers(frame, centroids)
        self._draw_hud(frame, game, fps, preset_name, show_mask)

        if game.state == MENU:
            self._draw_menu(frame)
        elif game.state == PAUSED:
            self._draw_pause(frame)
        elif game.state == GAME_OVER:
            self._draw_game_over(frame, game)

        self._tick_effects()

    @staticmethod
    def _make_vignette(h: int, w: int) -> np.ndarray:
        x = np.linspace(-1.0, 1.0, w, dtype=np.float32)
        y = np.linspace(-1.0, 1.0, h, dtype=np.float32)
        xv, yv = np.meshgrid(x, y)
        dark = np.clip(np.sqrt(xv**2 + yv**2) * 0.48, 0.0, 0.58)
        channel = (dark * 255).astype(np.uint8)
        return np.dstack([channel, channel, channel])

    def _prepare_camera(self, frame: np.ndarray) -> None:
        base = np.full_like(frame, BG)
        cv2.addWeighted(frame, 0.28, base, 0.72, 0, frame)
        frame[:] = cv2.subtract(frame, self._vignette)
        for x in range(0, FRAME_W, 80):
            cv2.line(frame, (x, 0), (x, FRAME_H), (22, 25, 34), 1)
        for y in range(0, FRAME_H, 80):
            cv2.line(frame, (0, y), (FRAME_W, y), (22, 25, 34), 1)

    def _draw_drum_pads(self, frame: np.ndarray) -> None:
        for lane in LANES:
            lane_id = lane["id"]
            rect = self.pad_rects[lane_id]
            cx, cy, rx, ry = _ellipse_metrics(rect)
            active = self.pad_flash[lane_id] > 0
            marker_inside = self.pad_entry_flash[lane_id] > 0
            base_color = lane["color"]
            hit_color = lane["hit_color"]
            color = hit_color if active or marker_inside else base_color
            intensity = 1.0 if active else 0.68 if marker_inside else 0.40

            _blend_ellipse(frame, (cx + 4, cy + 8), (rx, ry), (0, 0, 0), 0.34)
            _blend_ellipse(frame, (cx, cy), (rx + 13, ry + 13), _dim(color, 0.42), 0.18 * intensity)
            _blend_ellipse(frame, (cx, cy), (rx + 5, ry + 5), _dim(color, 0.65), 0.20 * intensity)
            _blend_ellipse(frame, (cx, cy), (rx, ry), color, 0.16 + 0.18 * intensity)
            _blend_ellipse(frame, (cx, cy - ry // 3), (max(rx - 16, 1), max(ry // 3, 1)), (255, 255, 255), 0.035)

            cv2.ellipse(frame, (cx, cy), (rx + 5, ry + 5), 0, 0, 360, _dim(color, 0.52), 1, cv2.LINE_AA)
            cv2.ellipse(frame, (cx, cy), (rx, ry), 0, 0, 360, color, 3 if active else 2, cv2.LINE_AA)
            cv2.ellipse(frame, (cx, cy), (max(rx - 7, 1), max(ry - 7, 1)), 0, 205, 335, _dim((255, 255, 255), 0.38), 1, cv2.LINE_AA)

            self._draw_drum_icon(frame, rect, lane["icon"], color)
            self._draw_pad_label(frame, lane, color)
            self._draw_pad_count(frame, lane_id, color)

    def _draw_staff(self, frame: np.ndarray, game: RhythmGame, song_time: float) -> None:
        _blend_rect(frame, (0, STAFF_BAND_TOP - 8, FRAME_W, STAFF_BAND_BOTTOM + 8), (0, 0, 0), 0.18)
        _blend_rect(frame, (0, STAFF_BAND_TOP, FRAME_W, STAFF_BAND_BOTTOM), PANEL, 0.84)
        _blend_rect(frame, (0, STAFF_BAND_TOP, FRAME_W, STAFF_BAND_TOP + 22), (42, 48, 62), 0.16)
        cv2.line(frame, (0, STAFF_BAND_TOP), (FRAME_W, STAFF_BAND_TOP), PANEL_EDGE, 1, cv2.LINE_AA)
        cv2.line(frame, (0, STAFF_BAND_BOTTOM), (FRAME_W, STAFF_BAND_BOTTOM), PANEL_EDGE, 1, cv2.LINE_AA)

        cv2.line(frame, (10, STAFF_Y), (FRAME_W - 10, STAFF_Y), (126, 132, 145), 1, cv2.LINE_AA)
        for tick in range(STAFF_CENTER_X + 80, FRAME_W, 80):
            cv2.line(frame, (tick, STAFF_Y - 9), (tick, STAFF_Y + 9), (58, 65, 78), 1, cv2.LINE_AA)
        for tick in range(STAFF_CENTER_X - 80, 0, -80):
            cv2.line(frame, (tick, STAFF_Y - 6), (tick, STAFF_Y + 6), (42, 48, 60), 1, cv2.LINE_AA)

        _blend_circle(frame, (STAFF_CENTER_X, STAFF_Y), 30, (255, 255, 255), 0.045)
        cv2.circle(frame, (STAFF_CENTER_X, STAFF_Y), 19, TEXT, 1, cv2.LINE_AA)
        cv2.circle(frame, (STAFF_CENTER_X, STAFF_Y), 12, (42, 48, 62), 2, cv2.LINE_AA)
        cv2.circle(frame, (STAFF_CENTER_X, STAFF_Y), 5, GOLD, -1, cv2.LINE_AA)
        cv2.line(frame, (STAFF_CENTER_X, STAFF_BAND_TOP + 8), (STAFF_CENTER_X, STAFF_BAND_BOTTOM - 8), (92, 104, 122), 1, cv2.LINE_AA)

        scroll_speed = (FRAME_W - STAFF_CENTER_X - 18) / NOTE_TRAVEL_TIME
        for note in game.notes:
            if note.hit or note.missed:
                continue
            seconds_until_hit = note.time - song_time
            if seconds_until_hit > NOTE_TRAVEL_TIME or seconds_until_hit < -0.45:
                continue
            lane = _lane(note.lane)
            x = STAFF_CENTER_X + int(seconds_until_hit * scroll_speed)
            if x < STAFF_CENTER_X - 42 or x > FRAME_W + 18:
                continue
            color = lane["color"]
            _blend_circle(frame, (x, STAFF_Y), NOTE_RADIUS + 10, _dim(color, 0.8), 0.32)
            cv2.circle(frame, (x, STAFF_Y), NOTE_RADIUS + 4, _dim(color, 0.55), -1, cv2.LINE_AA)
            cv2.circle(frame, (x, STAFF_Y), NOTE_RADIUS, color, -1, cv2.LINE_AA)
            cv2.circle(frame, (x, STAFF_Y), NOTE_RADIUS, (255, 255, 255), 1, cv2.LINE_AA)
            letter = lane["label"][0]
            _text_center(frame, letter, (x, STAFF_Y + 1), 0.36, (4, 5, 8), 1)

        score = f"SCORE {game.score:06d}"
        _text_shadow(frame, score, (10, STAFF_BAND_TOP - 15), 0.54, GOLD, 1)
        if game.combo > 0:
            _text_shadow(frame, f"{game.combo} COMBO", (142, STAFF_BAND_TOP - 15), 0.54, (70, 245, 255), 1)
        _text_shadow(frame, "JSON BEATMAP", (FRAME_W - 138, STAFF_BAND_TOP - 15), 0.42, MUTED, 1)

    def _draw_feedback(self, frame: np.ndarray) -> None:
        for cx, cy, age, color, max_radius in self.ripples:
            t = age / RIPPLE_FRAMES
            radius = int(8 + t * max_radius)
            fade = 1.0 - t
            faded = _dim(color, fade)
            _blend_circle(frame, (cx, cy), radius + 5, faded, 0.08 * fade)
            cv2.circle(frame, (cx, cy), radius, faded, max(1, int(4 * fade)), cv2.LINE_AA)

        for text, cx, y0, age, color in self.floats:
            t = age / FLOAT_FRAMES
            y = int(y0 - t * 50)
            fade = 1.0 - t
            scale = 0.78 if text != "MISS" else 0.72
            _text_center(frame, text, (cx, y), scale, _dim(color, fade), 2)

    def _draw_markers(self, frame: np.ndarray, centroids: Iterable[Tuple[int, int]]) -> None:
        for cx, cy in centroids:
            _blend_circle(frame, (cx, cy), 30, (255, 175, 65), 0.28)
            _blend_circle(frame, (cx, cy), 16, (255, 220, 130), 0.30)
            cv2.circle(frame, (cx, cy), 8, (255, 188, 62), -1, cv2.LINE_AA)
            cv2.circle(frame, (cx, cy), 8, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.circle(frame, (cx - 2, cy - 3), 2, (255, 255, 255), -1, cv2.LINE_AA)

    def _draw_hud(self, frame: np.ndarray, game: RhythmGame, fps: float, preset_name: str, show_mask: bool) -> None:
        _blend_rect(frame, (0, FRAME_H - 58, FRAME_W, FRAME_H), (5, 6, 10), 0.82)
        cv2.line(frame, (0, FRAME_H - 58), (FRAME_W, FRAME_H - 58), PANEL_EDGE, 1, cv2.LINE_AA)
        fps_color = (80, 230, 120) if fps >= 25 else (40, 185, 255) if fps >= 15 else (60, 60, 235)
        self._hud_chip(frame, "FPS", f"{fps:02.0f}", (8, FRAME_H - 50), fps_color)
        self._hud_chip(frame, "HITS", str(sum(self.pad_hits.values())), (84, FRAME_H - 50), TEXT)
        rhythm_value = "FREE" if game.state == FREE_PLAY else "ON" if self.rhythm_visible else "OFF"
        rhythm_color = (80, 255, 255) if game.state == FREE_PLAY else (80, 230, 120) if self.rhythm_visible else MUTED
        self._hud_chip(frame, "MODE", rhythm_value, (176, FRAME_H - 50), rhythm_color)
        self._hud_chip(frame, "ACC", f"{game.accuracy():.1f}%", (294, FRAME_H - 50), TEXT)
        self._hud_chip(frame, "MISS", str(game.miss), (410, FRAME_H - 50), (95, 120, 255) if game.miss else TEXT)
        _text_shadow(frame, f"Marker: {preset_name}", (10, FRAME_H - 10), 0.38, MUTED, 1)
        mask_hint = "mask on" if show_mask else "mask off"
        controls = f"Space rhythm | F free | T staff | R restart | 1-5 color | C {mask_hint} | Q quit"
        (tw, _), _ = cv2.getTextSize(controls, cv2.FONT_HERSHEY_SIMPLEX, 0.30, 1)
        _text_shadow(frame, controls, (FRAME_W - tw - 8, FRAME_H - 10), 0.30, (132, 140, 154), 1)

    def _hud_chip(self, frame: np.ndarray, label: str, value: str, origin: Tuple[int, int], color: Tuple[int, int, int]) -> None:
        x, y = origin
        cv2.rectangle(frame, (x, y), (x + 68, y + 22), (20, 24, 34), -1, cv2.LINE_AA)
        cv2.rectangle(frame, (x, y), (x + 68, y + 22), (54, 61, 76), 1, cv2.LINE_AA)
        _text_shadow(frame, label, (x + 6, y + 8), 0.28, MUTED, 1)
        _text_shadow(frame, value, (x + 6, y + 19), 0.36, color, 1)

    def _draw_drum_icon(self, frame: np.ndarray, rect: Tuple[int, int, int, int], drum_type: str, color: Tuple[int, int, int]) -> None:
        cx, cy, rx, ry = _ellipse_metrics(rect)
        dim = _dim(color, 0.36)
        if drum_type == "hihat":
            aw = max(rx // 4, 14)
            ah = max(ry // 14, 3)
            cv2.ellipse(frame, (cx, cy - ry // 8), (aw, ah), 0, 0, 360, dim, 1, cv2.LINE_AA)
            cv2.ellipse(frame, (cx, cy + ry // 8), (aw, ah), 0, 0, 360, dim, 1, cv2.LINE_AA)
            cv2.line(frame, (cx, cy - ry // 8 + ah), (cx, cy + ry // 8 - ah), dim, 1, cv2.LINE_AA)
        elif drum_type in ("snare", "tom"):
            radius = min(rx, ry) // 4
            cv2.circle(frame, (cx, cy), radius, dim, 1, cv2.LINE_AA)
            if drum_type == "snare":
                for dy in (-4, 0, 4):
                    cv2.line(frame, (cx - radius + 5, cy + radius // 2 + dy), (cx + radius - 5, cy + radius // 2 + dy), dim, 1, cv2.LINE_AA)
        elif drum_type == "kick":
            cv2.ellipse(frame, (cx, cy), (max(rx // 4, 45), max(ry // 3, 26)), 0, 0, 360, dim, 2, cv2.LINE_AA)
            cv2.ellipse(frame, (cx, cy), (max(rx // 8, 22), max(ry // 6, 12)), 0, 0, 360, dim, 1, cv2.LINE_AA)

    def _draw_pad_label(self, frame: np.ndarray, lane: Dict, color: Tuple[int, int, int]) -> None:
        cx, cy, _, ry = _ellipse_metrics(self.pad_rects[lane["id"]])
        scale = 0.78 if lane["id"] == "kick" else 0.62
        (tw, th), _ = cv2.getTextSize(lane["label"], cv2.FONT_HERSHEY_SIMPLEX, scale, 2)
        y = cy - ry + th + (24 if lane["id"] == "kick" else 18)
        _text_shadow(frame, lane["label"], (cx - tw // 2, y), scale, color, 2)

    def _draw_pad_count(self, frame: np.ndarray, lane_id: str, color: Tuple[int, int, int]) -> None:
        cx, cy, _, ry = _ellipse_metrics(self.pad_rects[lane_id])
        text = str(self.pad_hits[lane_id])
        (tw, _), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.48, 1)
        _text_shadow(frame, text, (cx - tw // 2, cy + ry - 14), 0.48, _dim(color, 0.9), 1)

    def _draw_menu(self, frame: np.ndarray) -> None:
        _screen_shade(frame)
        _blend_rect(frame, (78, 132, 562, 318), (18, 22, 32), 0.72)
        cv2.rectangle(frame, (78, 132), (562, 318), (58, 68, 86), 1, cv2.LINE_AA)
        _center_text(frame, "Virtual Drum Hero", 154, 1.30, TEXT, 3)
        _center_text(frame, "New Layout", 194, 0.55, GOLD, 1)
        _center_text(frame, "Use a colored marker as your drumstick", 226, 0.52, (190, 205, 225), 1)
        _center_text(frame, "Space: Rhythm Mode", 270, 0.62, (80, 255, 255), 2)
        _center_text(frame, "F: Free Play Mode", 300, 0.52, (180, 210, 255), 1)

    def _draw_pause(self, frame: np.ndarray) -> None:
        _screen_shade(frame)
        _center_text(frame, "Paused", 210, 1.15, TEXT, 3)
        _center_text(frame, "Press Space to resume", 260, 0.62, (80, 255, 255), 2)

    def _draw_game_over(self, frame: np.ndarray, game: RhythmGame) -> None:
        _screen_shade(frame)
        _blend_rect(frame, (88, 78, 552, 332), (18, 22, 32), 0.74)
        cv2.rectangle(frame, (88, 78), (552, 332), (58, 68, 86), 1, cv2.LINE_AA)
        _center_text(frame, "Game Over", 108, 1.16, TEXT, 3)
        lines = [
            f"Final Score: {game.score}",
            f"Max Combo: {game.max_combo}",
            f"Accuracy: {game.accuracy():.1f}%",
            f"Perfect: {game.perfect}   Good: {game.good}   Miss: {game.miss}",
            "Press R to restart    Q to quit",
        ]
        y = 166
        for index, line in enumerate(lines):
            color = TEXT if index < 4 else (80, 255, 255)
            _center_text(frame, line, y, 0.60, color, 1 if index < 4 else 2)
            y += 36

    def _tick_effects(self) -> None:
        for lane_id in self.pad_flash:
            if self.pad_flash[lane_id] > 0:
                self.pad_flash[lane_id] -= 1
            if self.pad_entry_flash[lane_id] > 0:
                self.pad_entry_flash[lane_id] -= 1
        self.ripples = [ripple for ripple in self.ripples if ripple[2] < RIPPLE_FRAMES]
        for ripple in self.ripples:
            ripple[2] += 1
        self.floats = [floating for floating in self.floats if floating[3] < FLOAT_FRAMES]
        for floating in self.floats:
            floating[3] += 1


def _lane(lane_id: str) -> Dict:
    for lane in LANES:
        if lane["id"] == lane_id:
            return lane
    raise KeyError(lane_id)


def _ellipse_metrics(rect: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
    x1, y1, x2, y2 = rect
    rx = max((x2 - x1) // 2, 1)
    ry = max((y2 - y1) // 2, 1)
    return x1 + rx, y1 + ry, rx, ry


def _point_in_ellipse(cx: int, cy: int, rect: Tuple[int, int, int, int]) -> bool:
    ecx, ecy, rx, ry = _ellipse_metrics(rect)
    return ((cx - ecx) / rx) ** 2 + ((cy - ecy) / ry) ** 2 <= 1.0


def _dim(color: Tuple[int, int, int], factor: float) -> Tuple[int, int, int]:
    return tuple(max(0, min(255, int(c * factor))) for c in color)


def _blend_rect(frame: np.ndarray, rect: Tuple[int, int, int, int], color: Tuple[int, int, int], alpha: float) -> None:
    x1, y1, x2, y2 = rect
    overlay = frame.copy()
    cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
    cv2.addWeighted(overlay, alpha, frame, 1.0 - alpha, 0, frame)


def _blend_ellipse(frame: np.ndarray, center: Tuple[int, int], axes: Tuple[int, int], color: Tuple[int, int, int], alpha: float) -> None:
    overlay = frame.copy()
    cv2.ellipse(overlay, center, axes, 0, 0, 360, color, -1, cv2.LINE_AA)
    cv2.addWeighted(overlay, alpha, frame, 1.0 - alpha, 0, frame)


def _blend_circle(frame: np.ndarray, center: Tuple[int, int], radius: int, color: Tuple[int, int, int], alpha: float) -> None:
    overlay = frame.copy()
    cv2.circle(overlay, center, radius, color, -1, cv2.LINE_AA)
    cv2.addWeighted(overlay, alpha, frame, 1.0 - alpha, 0, frame)


def _text_shadow(frame: np.ndarray, text: str, origin: Tuple[int, int], scale: float, color: Tuple[int, int, int], thickness: int) -> None:
    x, y = origin
    cv2.putText(frame, text, (x + 1, y + 1), cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), thickness + 2, cv2.LINE_AA)
    cv2.putText(frame, text, origin, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness, cv2.LINE_AA)


def _text_center(frame: np.ndarray, text: str, center: Tuple[int, int], scale: float, color: Tuple[int, int, int], thickness: int) -> None:
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)
    x = center[0] - tw // 2
    y = center[1] + th // 2
    _text_shadow(frame, text, (x, y), scale, color, thickness)


def _screen_shade(frame: np.ndarray) -> None:
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (FRAME_W, FRAME_H), (5, 7, 12), -1)
    cv2.addWeighted(overlay, 0.72, frame, 0.28, 0, frame)


def _center_text(frame: np.ndarray, text: str, y: int, scale: float, color: Tuple[int, int, int], thickness: int) -> None:
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)
    _text_shadow(frame, text, ((FRAME_W - tw) // 2, y + th // 2), scale, color, thickness)
