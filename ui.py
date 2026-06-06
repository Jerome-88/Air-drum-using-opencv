from __future__ import annotations

from typing import Dict, Iterable, List, Set, Tuple

import cv2
import numpy as np

from config import FRAME_H, FRAME_W, HIT_LINE_Y, HIT_ZONE_BOTTOM, HIT_ZONE_TOP, LANES, NOTE_TRAVEL_TIME
from game import FREE_PLAY, GAME_OVER, MENU, PAUSED, GameEvent, RhythmGame

NOTE_RADIUS = 17
FLASH_FRAMES = 8
RIPPLE_FRAMES = 18
FLOAT_FRAMES = 30


class GameUI:
    def __init__(self) -> None:
        lane_width = FRAME_W // len(LANES)
        self.lane_rects: Dict[str, Tuple[int, int, int, int]] = {}
        self.hit_rects: Dict[str, Tuple[int, int, int, int]] = {}
        self.flash = {lane["id"]: 0 for lane in LANES}
        self.ripples: List[List] = []
        self.floats: List[List] = []

        for index, lane in enumerate(LANES):
            x1 = index * lane_width
            x2 = FRAME_W if index == len(LANES) - 1 else (index + 1) * lane_width
            self.lane_rects[lane["id"]] = (x1, 0, x2, FRAME_H)
            self.hit_rects[lane["id"]] = (x1 + 8, HIT_ZONE_TOP, x2 - 8, HIT_ZONE_BOTTOM)

    def reset_run_feedback(self) -> None:
        self.flash = {lane["id"]: 0 for lane in LANES}
        self.ripples.clear()
        self.floats.clear()

    def active_lanes_for_centroids(self, centroids: Iterable[Tuple[int, int]]) -> Set[str]:
        active: Set[str] = set()
        for cx, cy in centroids:
            for lane_id, (x1, y1, x2, y2) in self.hit_rects.items():
                if x1 <= cx <= x2 and y1 <= cy <= y2:
                    active.add(lane_id)
        return active

    def add_events(self, events: Iterable[GameEvent]) -> None:
        for event in events:
            lane = _lane(event.lane)
            x1, _, x2, _ = self.hit_rects[event.lane]
            cx = (x1 + x2) // 2
            color = lane["hit_color"] if event.kind != "Miss" else (40, 40, 245)
            self.flash[event.lane] = FLASH_FRAMES
            self.ripples.append([cx, HIT_LINE_Y, 0, color])
            if event.kind != "Drum":
                self.floats.append([event.kind.upper(), cx, HIT_LINE_Y - 12, 0, color])

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
        self._darken_camera(frame)
        self._draw_lanes(frame)
        if game.state != FREE_PLAY:
            self._draw_notes(frame, game, song_time)
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

    def _darken_camera(self, frame: np.ndarray) -> None:
        dark = np.full_like(frame, (16, 18, 26))
        cv2.addWeighted(frame, 0.18, dark, 0.82, 0, frame)

    def _draw_lanes(self, frame: np.ndarray) -> None:
        for lane in LANES:
            lane_id = lane["id"]
            x1, _, x2, _ = self.lane_rects[lane_id]
            hx1, hy1, hx2, hy2 = self.hit_rects[lane_id]
            color = lane["hit_color"] if self.flash[lane_id] > 0 else lane["color"]
            lane_overlay = frame.copy()
            cv2.rectangle(lane_overlay, (x1, 0), (x2, FRAME_H), color, -1)
            alpha = 0.18 if self.flash[lane_id] > 0 else 0.07
            cv2.addWeighted(lane_overlay, alpha, frame, 1.0 - alpha, 0, frame)
            cv2.line(frame, (x1, 0), (x1, FRAME_H), (55, 60, 70), 1)
            cv2.line(frame, (x2 - 1, 0), (x2 - 1, FRAME_H), (55, 60, 70), 1)
            cv2.rectangle(frame, (hx1, hy1), (hx2, hy2), color, 2, cv2.LINE_AA)
            cv2.line(frame, (x1 + 8, HIT_LINE_Y), (x2 - 8, HIT_LINE_Y), color, 3, cv2.LINE_AA)
            cv2.putText(frame, lane["label"], (x1 + 14, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.62, color, 2, cv2.LINE_AA)

    def _draw_notes(self, frame: np.ndarray, game: RhythmGame, song_time: float) -> None:
        travel_px = HIT_LINE_Y - 58
        for note in game.notes:
            if note.hit or note.missed:
                continue
            seconds_until_hit = note.time - song_time
            if seconds_until_hit > NOTE_TRAVEL_TIME or seconds_until_hit < -0.35:
                continue
            lane = _lane(note.lane)
            x1, _, x2, _ = self.lane_rects[note.lane]
            cx = (x1 + x2) // 2
            y = int(HIT_LINE_Y - (seconds_until_hit / NOTE_TRAVEL_TIME) * travel_px)
            color = lane["color"]
            cv2.circle(frame, (cx, y), NOTE_RADIUS + 5, tuple(max(c // 4, 0) for c in color), -1, cv2.LINE_AA)
            cv2.circle(frame, (cx, y), NOTE_RADIUS, color, -1, cv2.LINE_AA)
            cv2.circle(frame, (cx, y), NOTE_RADIUS, (245, 245, 245), 1, cv2.LINE_AA)

    def _draw_feedback(self, frame: np.ndarray) -> None:
        for cx, cy, age, color in self.ripples:
            t = age / RIPPLE_FRAMES
            radius = int(12 + t * 58)
            fade = 1.0 - t
            faded = tuple(int(c * fade) for c in color)
            cv2.circle(frame, (cx, cy), radius, faded, 2, cv2.LINE_AA)

        for text, cx, y0, age, color in self.floats:
            t = age / FLOAT_FRAMES
            y = int(y0 - t * 48)
            fade = 1.0 - t
            faded = tuple(int(c * fade) for c in color)
            scale = 0.82 if text != "MISS" else 0.74
            (tw, _), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, 2)
            cv2.putText(frame, text, (cx - tw // 2, y), cv2.FONT_HERSHEY_SIMPLEX, scale, faded, 2, cv2.LINE_AA)

    def _draw_markers(self, frame: np.ndarray, centroids: Iterable[Tuple[int, int]]) -> None:
        for cx, cy in centroids:
            glow = np.zeros_like(frame)
            cv2.circle(glow, (cx, cy), 20, (255, 180, 60), -1, cv2.LINE_AA)
            glow = cv2.GaussianBlur(glow, (0, 0), 8)
            cv2.add(frame, glow, frame)
            cv2.circle(frame, (cx, cy), 8, (255, 190, 65), -1, cv2.LINE_AA)
            cv2.circle(frame, (cx, cy), 8, (255, 255, 255), 1, cv2.LINE_AA)

    def _draw_hud(self, frame: np.ndarray, game: RhythmGame, fps: float, preset_name: str, show_mask: bool) -> None:
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, FRAME_H - 48), (FRAME_W, FRAME_H), (8, 9, 12), -1)
        cv2.addWeighted(overlay, 0.76, frame, 0.24, 0, frame)
        fps_color = (80, 230, 120) if fps >= 25 else (40, 185, 255) if fps >= 15 else (60, 60, 235)
        cv2.putText(frame, f"Score {game.score}", (10, FRAME_H - 28), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (235, 235, 235), 1, cv2.LINE_AA)
        cv2.putText(frame, f"Combo {game.combo}", (120, FRAME_H - 28), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (235, 235, 235), 1, cv2.LINE_AA)
        cv2.putText(frame, f"Acc {game.accuracy():5.1f}%", (224, FRAME_H - 28), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (235, 235, 235), 1, cv2.LINE_AA)
        cv2.putText(frame, f"Miss {game.miss}", (350, FRAME_H - 28), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (235, 235, 235), 1, cv2.LINE_AA)
        cv2.putText(frame, f"FPS {fps:4.0f}", (450, FRAME_H - 28), cv2.FONT_HERSHEY_SIMPLEX, 0.50, fps_color, 1, cv2.LINE_AA)
        if game.state == FREE_PLAY:
            cv2.putText(frame, "FREE PLAY", (540, FRAME_H - 28), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (80, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(frame, f"Marker: {preset_name}", (10, FRAME_H - 9), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (165, 175, 190), 1, cv2.LINE_AA)
        mask_hint = "mask on" if show_mask else "mask off"
        controls = f"Space rhythm | F free | R restart | 1-5 color | C {mask_hint} | Q quit"
        scale = 0.32
        (tw, _), _ = cv2.getTextSize(controls, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)
        x = max(150, FRAME_W - tw - 8)
        if x == 150 and tw > FRAME_W - 155:
            scale = 0.29
        cv2.putText(frame, controls, (x, FRAME_H - 9), cv2.FONT_HERSHEY_SIMPLEX, scale, (140, 145, 155), 1, cv2.LINE_AA)

    def _draw_menu(self, frame: np.ndarray) -> None:
        _screen_shade(frame)
        _center_text(frame, "Virtual Drum Hero", 168, 1.35, (245, 245, 245), 3)
        _center_text(frame, "Use a colored marker as your drumstick", 214, 0.58, (190, 205, 225), 1)
        _center_text(frame, "Space: Rhythm Mode", 268, 0.64, (80, 255, 255), 2)
        _center_text(frame, "F: Free Play Mode", 306, 0.58, (180, 210, 255), 1)
        _center_text(frame, "Q quits", 338, 0.48, (150, 155, 165), 1)

    def _draw_pause(self, frame: np.ndarray) -> None:
        _screen_shade(frame)
        _center_text(frame, "Paused", 210, 1.15, (245, 245, 245), 3)
        _center_text(frame, "Press Space to resume", 260, 0.62, (80, 255, 255), 2)

    def _draw_game_over(self, frame: np.ndarray, game: RhythmGame) -> None:
        _screen_shade(frame)
        _center_text(frame, "Game Over", 108, 1.18, (245, 245, 245), 3)
        lines = [
            f"Final Score: {game.score}",
            f"Max Combo: {game.max_combo}",
            f"Accuracy: {game.accuracy():.1f}%",
            f"Perfect: {game.perfect}   Good: {game.good}   Miss: {game.miss}",
            "Press R to restart    Q to quit",
        ]
        y = 168
        for index, line in enumerate(lines):
            color = (235, 235, 235) if index < 4 else (80, 255, 255)
            _center_text(frame, line, y, 0.60, color, 1 if index < 4 else 2)
            y += 38

    def _tick_effects(self) -> None:
        for lane_id in self.flash:
            if self.flash[lane_id] > 0:
                self.flash[lane_id] -= 1
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


def _screen_shade(frame: np.ndarray) -> None:
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (FRAME_W, FRAME_H), (8, 10, 16), -1)
    cv2.addWeighted(overlay, 0.70, frame, 0.30, 0, frame)


def _center_text(frame: np.ndarray, text: str, y: int, scale: float, color: Tuple[int, int, int], thickness: int) -> None:
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)
    cv2.putText(frame, text, ((FRAME_W - tw) // 2, y + th // 2), cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness, cv2.LINE_AA)
