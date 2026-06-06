from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set

from config import GOOD_WINDOW, LANE_BY_ID, PERFECT_WINDOW

MENU = "MENU"
PLAYING = "PLAYING"
PAUSED = "PAUSED"
FREE_PLAY = "FREE_PLAY"
GAME_OVER = "GAME_OVER"


@dataclass
class Note:
    time: float
    lane: str
    hit: bool = False
    missed: bool = False


@dataclass
class GameEvent:
    kind: str
    lane: str
    song_time: float
    delta: float = 0.0


class RhythmGame:
    def __init__(self, notes: Iterable[Note]) -> None:
        self.beatmap = sorted([Note(note.time, note.lane) for note in notes], key=lambda note: note.time)
        self.state = MENU
        self.notes: List[Note] = []
        self.start_perf: Optional[float] = None
        self.pause_started: Optional[float] = None
        self.paused_total = 0.0
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.perfect = 0
        self.good = 0
        self.miss = 0
        self._lane_inside: Dict[str, bool] = {lane_id: False for lane_id in LANE_BY_ID}
        self.reset_to_menu()

    def reset_to_menu(self) -> None:
        self._reset_run()
        self.state = MENU

    def start(self, now: float) -> None:
        self._reset_run()
        self.start_perf = now
        self.state = PLAYING

    def restart(self, now: float) -> None:
        self.start(now)

    def start_free_play(self, now: float) -> None:
        self._reset_run()
        self.notes = []
        self.start_perf = now
        self.state = FREE_PLAY

    def pause(self, now: float) -> None:
        if self.state == PLAYING:
            self.pause_started = now
            self.state = PAUSED

    def resume(self, now: float) -> None:
        if self.state == PAUSED and self.pause_started is not None:
            self.paused_total += now - self.pause_started
            self.pause_started = None
            self.state = PLAYING

    def current_song_time(self, now: float) -> float:
        if self.start_perf is None:
            return 0.0
        if self.state == PAUSED and self.pause_started is not None:
            return max(0.0, self.pause_started - self.start_perf - self.paused_total)
        return max(0.0, now - self.start_perf - self.paused_total)

    def update(self, now: float, active_lanes: Set[str]) -> List[GameEvent]:
        if self.state == FREE_PLAY:
            return self._handle_free_play_entries(active_lanes, self.current_song_time(now))

        if self.state != PLAYING:
            self._update_inside(active_lanes)
            return []

        song_time = self.current_song_time(now)
        events = self._handle_lane_entries(active_lanes, song_time)
        events.extend(self._mark_late_misses(song_time))

        if self.notes and all(note.hit or note.missed for note in self.notes):
            if song_time > self.notes[-1].time + 0.8:
                self.state = GAME_OVER
        return events

    def accuracy(self) -> float:
        judged = self.perfect + self.good + self.miss
        if judged == 0:
            return 100.0
        return ((self.perfect + 0.5 * self.good) / judged) * 100.0

    def total_notes(self) -> int:
        return len(self.notes)

    def judged_notes(self) -> int:
        return self.perfect + self.good + self.miss

    def _reset_run(self) -> None:
        self.notes = [Note(note.time, note.lane) for note in self.beatmap]
        self.start_perf = None
        self.pause_started = None
        self.paused_total = 0.0
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.perfect = 0
        self.good = 0
        self.miss = 0
        self._lane_inside = {lane_id: False for lane_id in LANE_BY_ID}

    def _handle_lane_entries(self, active_lanes: Set[str], song_time: float) -> List[GameEvent]:
        events: List[GameEvent] = []
        entering = [lane_id for lane_id in active_lanes if not self._lane_inside.get(lane_id, False)]
        self._update_inside(active_lanes)

        for lane_id in entering:
            note = self._nearest_hittable_note(lane_id, song_time)
            if note is None:
                events.append(GameEvent("Drum", lane_id, song_time, 0.0))
                continue
            delta = song_time - note.time
            note.hit = True
            if abs(delta) <= PERFECT_WINDOW:
                self.perfect += 1
                self.score += 1000 + self.combo * 10
                self.combo += 1
                events.append(GameEvent("Perfect", lane_id, song_time, delta))
            else:
                self.good += 1
                self.score += 500 + self.combo * 5
                self.combo += 1
                events.append(GameEvent("Good", lane_id, song_time, delta))
            self.max_combo = max(self.max_combo, self.combo)
        return events

    def _handle_free_play_entries(self, active_lanes: Set[str], song_time: float) -> List[GameEvent]:
        entering = [lane_id for lane_id in active_lanes if not self._lane_inside.get(lane_id, False)]
        self._update_inside(active_lanes)
        return [GameEvent("Drum", lane_id, song_time, 0.0) for lane_id in entering]

    def _nearest_hittable_note(self, lane_id: str, song_time: float) -> Optional[Note]:
        candidates = [
            note
            for note in self.notes
            if note.lane == lane_id and not note.hit and not note.missed and abs(song_time - note.time) <= GOOD_WINDOW
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda note: abs(song_time - note.time))

    def _mark_late_misses(self, song_time: float) -> List[GameEvent]:
        events: List[GameEvent] = []
        for note in self.notes:
            if note.hit or note.missed:
                continue
            if song_time - note.time > GOOD_WINDOW:
                note.missed = True
                self.miss += 1
                self.combo = 0
                events.append(GameEvent("Miss", note.lane, song_time, song_time - note.time))
        return events

    def _update_inside(self, active_lanes: Set[str]) -> None:
        for lane_id in self._lane_inside:
            self._lane_inside[lane_id] = lane_id in active_lanes


def load_beatmap(path: str) -> List[Note]:
    with open(path, "r", encoding="utf-8") as file:
        raw_notes = json.load(file)

    if not isinstance(raw_notes, list):
        raise ValueError("Beatmap must be a JSON array")

    notes: List[Note] = []
    for index, item in enumerate(raw_notes):
        if not isinstance(item, dict):
            raise ValueError(f"Beatmap note #{index} must be an object")
        lane = item.get("lane")
        target_time = item.get("time")
        if lane not in LANE_BY_ID:
            raise ValueError(f"Beatmap note #{index} has unknown lane: {lane}")
        if not isinstance(target_time, (int, float)) or target_time < 0:
            raise ValueError(f"Beatmap note #{index} has invalid time: {target_time}")
        notes.append(Note(float(target_time), lane))
    return sorted(notes, key=lambda note: note.time)
