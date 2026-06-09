from __future__ import annotations

import os
import sys
import time

import cv2

from audio import AudioEngine
from config import COLOR_PRESETS, FRAME_H, FRAME_W, LANES, TARGET_FPS
from game import FREE_PLAY, GAME_OVER, MENU, PAUSED, PLAYING, RhythmGame, load_beatmap
from ui import GameUI
from vision import CALIB_WIN, MASK_WIN, MarkerDetector, apply_preset, close_mask_window, draw_calibration_panel, init_trackbars, sync_trackbars

MAIN_WIN = "Virtual Drum Hero"
BEATMAP_PATH = "beatmaps/demo.json"
MUSIC_PATH = "beatmaps/The Walters -- I Love You So - The Walters.mp3"


def open_camera() -> cv2.VideoCapture:
    if os.name == "nt":
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    else:
        cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ERROR] Cannot open webcam")
        print("[ERROR] On macOS, allow Camera access for your terminal app in System Settings > Privacy & Security > Camera.")
        print("[ERROR] Then run: conda activate cv && python rhythm_drum.py")
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)
    cap.set(cv2.CAP_PROP_FPS, TARGET_FPS)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


def handle_key(key: int, game: RhythmGame, audio: AudioEngine, ui: GameUI, detector: MarkerDetector, preset_name: str, show_mask: bool) -> tuple[bool, str, bool]:
    if key == 255:
        return True, preset_name, show_mask
    if key in (ord("q"), ord("Q")):
        return False, preset_name, show_mask
    if key == ord(" "):
        now = time.perf_counter()
        if game.state in (MENU, GAME_OVER, FREE_PLAY):
            game.start(now)
            audio.play_music()
            ui.reset_run_feedback()
        elif game.state == PLAYING:
            game.pause(now)
            audio.pause_music()
        elif game.state == PAUSED:
            game.resume(now)
            audio.unpause_music()
    elif key in (ord("f"), ord("F")):
        audio.stop_music()
        game.start_free_play(time.perf_counter())
        ui.reset_run_feedback()
    elif key in (ord("r"), ord("R")):
        now = time.perf_counter()
        audio.stop_music()
        if game.state == FREE_PLAY:
            game.start_free_play(now)
        else:
            game.restart(now)
            audio.play_music()
        ui.reset_run_feedback()
    elif key in (ord("c"), ord("C")):
        show_mask = not show_mask
        if not show_mask:
            close_mask_window()
    else:
        key_char = chr(key) if 32 <= key < 128 else ""
        if key_char in COLOR_PRESETS:
            preset_name = apply_preset(detector, key_char)
            print(f"[INFO] Marker preset: {preset_name}")
    return True, preset_name, show_mask


def main() -> None:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    detector = MarkerDetector()
    audio = AudioEngine(LANES)
    audio.load_music(MUSIC_PATH)
    game = RhythmGame(load_beatmap(BEATMAP_PATH))
    ui = GameUI()
    cap = open_camera()

    cv2.namedWindow(MAIN_WIN, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(MAIN_WIN, FRAME_W, FRAME_H)
    init_trackbars(detector)

    preset_name = COLOR_PRESETS["1"][0]
    show_mask = True
    running = True
    previous_time = time.perf_counter()

    try:
        while running:
            ok, frame = cap.read()
            if not ok:
                continue
            frame = cv2.flip(frame, 1)

            sync_trackbars(detector)
            centroids, mask = detector.detect(frame)
            active_lanes = ui.active_lanes_for_centroids(centroids)
            now = time.perf_counter()
            prev_state = game.state
            events = game.update(now, active_lanes)
            if prev_state == PLAYING and game.state == GAME_OVER:
                audio.stop_music()

            for event in events:
                if event.kind in ("Perfect", "Good", "Drum"):
                    audio.play_lane(event.lane)
            ui.add_events(events)

            fps = 1.0 / max(now - previous_time, 1e-9)
            previous_time = now

            ui.draw(frame, game, centroids, now, fps, preset_name, show_mask)
            cv2.imshow(MAIN_WIN, frame)
            cv2.imshow(CALIB_WIN, draw_calibration_panel(detector, preset_name, show_mask))
            if show_mask:
                cv2.imshow(MASK_WIN, mask)

            key = cv2.waitKey(1) & 0xFF
            running, preset_name, show_mask = handle_key(key, game, audio, ui, detector, preset_name, show_mask)
    finally:
        cap.release()
        audio.quit()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
