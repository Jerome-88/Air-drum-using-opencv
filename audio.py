from __future__ import annotations

import os
from typing import Dict, Iterable

import pygame

class AudioEngine:
    def __init__(self, lanes: Iterable[Dict]) -> None:
        self.enabled = False
        self._sounds: Dict[str, pygame.mixer.Sound] = {}
        self._music_loaded = False

        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
        try:
            pygame.mixer.init()
            pygame.mixer.set_num_channels(16)
            self.enabled = True
        except pygame.error as exc:
            print(f"[WARN] Audio disabled: pygame mixer could not start ({exc})")
            return

        for lane in lanes:
            path = lane["sound"]
            if os.path.isfile(path):
                self._sounds[lane["id"]] = pygame.mixer.Sound(path)
            else:
                print(f"[WARN] Missing sound file: {path}. Run python generate_sounds.py")

    def load_music(self, path: str) -> None:
        if not self.enabled:
            return
        if not os.path.isfile(path):
            print(f"[WARN] Music file not found: {path}")
            return
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(0.7)
            self._music_loaded = True
        except pygame.error as exc:
            print(f"[WARN] Could not load music: {exc}")

    def play_music(self) -> None:
        if self.enabled and self._music_loaded:
            pygame.mixer.music.play()

    def pause_music(self) -> None:
        if self.enabled and self._music_loaded:
            pygame.mixer.music.pause()

    def unpause_music(self) -> None:
        if self.enabled and self._music_loaded:
            pygame.mixer.music.unpause()

    def stop_music(self) -> None:
        if self.enabled and self._music_loaded:
            pygame.mixer.music.stop()

    def play_lane(self, lane_id: str) -> None:
        if not self.enabled:
            return
        sound = self._sounds.get(lane_id)
        if sound is not None:
            sound.play()

    def quit(self) -> None:
        if self.enabled:
            pygame.mixer.music.stop()
            pygame.mixer.quit()
