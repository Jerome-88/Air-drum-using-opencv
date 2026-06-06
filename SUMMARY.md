# Virtual Drum Hero Project Summary

## 1. Project Overview

Virtual Drum Hero is a webcam-based drum rhythm game built with Python, OpenCV, NumPy, and Pygame. The primary demo/new version is `rhythm_drum_new.py`, which presents four oval drum pads and a centered rhythm staff where notes scroll toward a timing receptor.

The player uses a bright colored marker as a virtual drumstick. The camera detects the marker, calculates its centroid, checks whether the centroid enters a drum pad, and then either plays a drum sound freely or scores the hit against the beatmap timing.

The project remains a classic Computer Vision project. It does not use MediaPipe, hand tracking, pose estimation, deep learning, or gesture classification. The interaction is powered by HSV color segmentation, morphology, contour detection, centroid tracking, and geometric collision.

## 2. Main Goal

The system demonstrates that a normal webcam can become a real-time musical input device. It combines:

- Webcam capture
- HSV marker detection
- Contour and centroid calculation
- Ellipse collision against drum pads
- Rhythm-game timing logic
- Non-blocking drum audio playback
- Live visual feedback

The new game is demo-friendly: the beatmap is intentionally slow, off-beat pad entries still play drum sounds, and scoring only applies when the marker hits near an active note.

## 3. Current Entry Points

| File | Purpose |
|---|---|
| `rhythm_drum_new.py` | Primary new/demo app with oval drum pads and centered rhythm staff. |
| `rhythm_drum.py` | Alternate default app with four vertical falling-note lanes. |
| `virtual_drum.py` | Compatibility launcher for the default app. |

For the presentation and project reference, use:

```bash
conda activate cv
python rhythm_drum_new.py
```

## 4. Repository Structure

| File / Folder | Responsibility |
|---|---|
| `vision.py` | HSV presets, calibration trackbars, BGR-to-HSV conversion, color masking, morphology, contour detection, centroid extraction. |
| `game.py` | Beatmap loading, game states, timing windows, score, combo, accuracy, misses, edge-trigger lane entry. |
| `audio.py` | Pygame mixer setup, `.wav` sound loading, non-blocking playback, graceful audio fallback. |
| `ui_new.py` | Premium new UI: oval pads, centered rhythm staff, notes, HUD, marker glow, ripples, overlays. |
| `ui.py` | Alternate vertical-lane UI for `rhythm_drum.py`. |
| `config.py` | Shared constants, lane metadata, colors, pad coordinates, timing windows, sound paths. |
| `beatmaps/demo.json` | Slow demo beatmap using JSON note timing and lane IDs. |
| `sounds/` | Runtime drum samples. The app uses `.wav` files. |
| `generate_sounds.py` | Generates synthetic `.wav` drum sounds. |
| `presentation/` | HTML/CSS presentation deck. |

## 5. Technologies Used

### Python
Python coordinates the webcam loop, vision pipeline, game state, UI drawing, and audio playback.

### OpenCV
OpenCV is used for:

- `cv2.VideoCapture` webcam input
- `cv2.cvtColor` BGR-to-HSV conversion
- `cv2.inRange` HSV thresholding
- `cv2.erode` and `cv2.dilate` mask cleanup
- `cv2.findContours` contour extraction
- `cv2.moments` centroid calculation
- UI rendering with OpenCV drawing primitives
- `cv2.imshow` output windows and calibration display

### NumPy
NumPy stores HSV bounds, morphology kernels, image arrays, and synthesized waveform samples in `generate_sounds.py`.

### Pygame
Pygame is used for `pygame.mixer` audio. Drum samples are loaded before gameplay and played without blocking the camera loop.

## 6. Computer Vision Pipeline

Each frame follows this process:

1. Read webcam frame.
2. Flip the frame horizontally for mirror-like interaction.
3. Convert BGR image to HSV.
4. Create a binary mask from the selected HSV marker range.
5. Clean the mask using erosion and dilation.
6. Find contours in the mask.
7. Ignore contours smaller than `MIN_CONTOUR_AREA`.
8. Compute centroid with image moments.
9. Treat the centroid as the drumstick tip.
10. Test the centroid against each drum pad.
11. Trigger free-play sound or rhythm scoring from edge-triggered pad entry.

This is intentionally explainable and lightweight. It uses no trained model.

## 7. HSV Calibration

The project keeps a live HSV calibration window with six sliders:

- `H Low`
- `S Low`
- `V Low`
- `H High`
- `S High`
- `V High`

Preset keys `1` to `5` switch between marker colors:

- Green
- Yellow
- Orange
- Blue
- Pink / Magenta

The mask window helps users verify that the marker appears as a solid white blob while the background stays black.

## 8. New Layout

The new layout in `ui_new.py` uses fixed 640x480 geometry:

| Drum | Pad Coordinates | Lane ID | Sound |
|---|---:|---|---|
| Hi-Hat | `x: 10-205`, `y: 20-185` | `hihat` | `sounds/hihat.wav` |
| Snare | `x: 225-415`, `y: 20-185` | `snare` | `sounds/snare.wav` |
| Tom | `x: 435-630`, `y: 20-185` | `tom` | `sounds/tom.wav` |
| Kick | `x: 10-630`, `y: 295-460` | `kick` | `sounds/kick.wav` |

The visual shape is oval, and collision is tested with a point-in-ellipse calculation:

```text
((cx - center_x) / radius_x)^2 + ((cy - center_y) / radius_y)^2 <= 1
```

This keeps the layout close to drum pads while still using simple geometry.

## 9. Rhythm Game Logic

The rhythm system reads notes from `beatmaps/demo.json`.

Example:

```json
{ "time": 1.90, "lane": "hihat" }
```

Each note has:

- a target time in seconds
- a lane ID: `hihat`, `snare`, `tom`, or `kick`

The new UI draws notes moving right-to-left toward the centered receptor at `x=320`, `y=235`.

Timing windows:

- **Perfect:** within +/-100 ms
- **Good:** within +/-200 ms
- **Miss:** note passes beyond the Good window

The demo beatmap is slowed for presentation reliability, giving users more time to move the marker between pads.

## 10. Free-Play Drum Behavior

The drum remains playable in two ways: explicit free-play mode and off-beat rhythm-mode drum response.

Pressing F starts `FREE_PLAY` mode. In this mode, the game hides rhythm notes, ignores score and accuracy, and plays a drum whenever the marker enters a pad.

When the marker enters a pad:

- If a matching note is inside the timing window, the game returns `Perfect` or `Good`, plays sound, updates score, combo, and accuracy.
- If no note is hittable, the game returns `Drum`, plays the lane sound, and shows visual feedback without changing score or accuracy.
- If a note passes the hit window, it becomes `Miss` and resets combo.

This makes the demo feel responsive while preserving rhythm-game scoring.

## 11. Edge-Triggering

The game stores whether the marker is already inside each lane or pad. A hit triggers only when the marker enters from outside.

This prevents repeated playback when the marker stays still inside a pad. To trigger again, the marker must leave the pad and re-enter.

## 12. Audio System

The runtime uses `.wav` assets:

- `sounds/hihat.wav`
- `sounds/snare.wav`
- `sounds/tom.wav`
- `sounds/kick.wav`

`generate_sounds.py` creates these files. `audio.py` loads them through `pygame.mixer.Sound` and plays them asynchronously.

The audio engine also handles mixer startup failure gracefully. If CoreAudio or another audio backend fails, the game can still run visually for CV demonstration.

## 13. Controls

Shared controls:

| Key | Action |
|---|---|
| Space | Start, pause, or resume rhythm mode |
| F | Start free-play mode |
| R | Restart the current mode |
| Q | Quit |
| 1-5 | Switch marker color preset |
| C | Show or hide mask window |

New-only control:

| Key | Action |
|---|---|
| T | Show or hide the centered rhythm staff |

## 14. Strengths

- Clear classic-CV pipeline
- No machine learning dependency
- Real-time webcam interaction
- Live HSV calibration
- Edge-triggered collision
- Free-play drum response
- Rhythm-game scoring
- Lightweight OpenCV UI
- `.wav` sound assets match the generation script

## 15. Limitations

- Color segmentation depends on lighting and marker-background contrast.
- The system tracks only 2D image position, not depth.
- Hit intensity or striking velocity is not measured.
- Pad positions are fixed for a 640x480 frame.
- Calibration is live but not persisted between runs.
- The game depends on webcam and audio permissions from the operating system.

## 16. Conclusion

Virtual Drum Hero demonstrates how traditional computer vision can power a playable real-time rhythm game. The new version, `rhythm_drum_new.py`, combines HSV marker tracking, contour-based centroid detection, ellipse collision, beatmap timing, audio playback, and polished visual feedback into a demo-ready Computer Vision final project.
