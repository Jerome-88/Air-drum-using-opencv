# Virtual Drum Hero

**Course:** Computer Vision | BINUS University  
**Authors:**
- Jerome Maxcellino Budianto (2802412894)
- Hibatullah Fawwaz Hana (2802485271)
- Andrew Christiansho (2802515942)
- Kevin Kartanegara (2802526416)
- Ritchjhie Agusta (2802529102)
- Randy Fathoni (2802504604)

Virtual Drum Hero is a webcam-based drum rhythm game inspired by Guitar Hero. The default game shows four vertical drum lanes with notes falling toward hit zones. A separate new-layout version is also included with oval drum pads and a centered rhythm staff.

The project is still intentionally based on classic computer vision, not hand tracking or machine learning.

**Pipeline:** Webcam -> BGR to HSV -> HSV color mask -> Morphological clean-up -> Contour detection -> Centroid tracking -> Geometric collision -> Rhythm scoring -> Pygame audio

## Requirements

- Python 3.8 to 3.11
- Webcam at 640x480 or better
- Windows, macOS, or Linux

## Setup

```bash
pip install -r requirements.txt
python generate_sounds.py
python rhythm_drum.py
```

`python virtual_drum.py` also works as a compatibility launcher.

To run the separate new-style layout:

```bash
python rhythm_drum_new.py
```

## How to Play

1. Put bright green, yellow, orange, blue, or magenta tape on a pen, chopstick, or drumstick.
2. Stand in front of the webcam with a contrasting background.
3. Press Space on the menu to start rhythm mode, or press F for free-play mode.
4. In rhythm mode, move the marker into the correct lane hit zone when a note reaches the hit line.
5. In free-play mode, enter any lane or pad to play that drum without scoring or misses.

The new layout uses the same beatmap and scoring, but the marker enters oval drum pads while notes scroll toward the center receptor.

Free-play mode is available for practice and demos. Entering any lane or pad plays that drum sound; only rhythm-mode hits near a beatmap note affect score, combo, and accuracy.

Lanes:

- Hi-Hat
- Snare
- Tom
- Kick

Judgments:

- Perfect: within +/-100 ms
- Good: within +/-200 ms
- Miss: outside +/-200 ms or note passes the hit line

The included demo beatmap is intentionally slow and presentation-friendly so webcam latency and marker movement are easier to manage.

## Controls

| Key | Action |
|-----|--------|
| Space | Start, pause, or resume rhythm mode |
| F | Start free-play mode |
| R | Restart the current mode |
| Q | Quit |
| 1 | Green marker preset |
| 2 | Yellow marker preset |
| 3 | Orange marker preset |
| 4 | Blue marker preset |
| 5 | Pink / magenta marker preset |
| C | Show or hide the binary mask window |

Reference layout only:

| Key | Action |
|-----|--------|
| T | Show or hide the centered rhythm staff |

## Calibration

The **HSV Calibration** window keeps six live trackbars:

| Slider | Range | Meaning |
|--------|-------|---------|
| H Low / H High | 0-179 | Hue |
| S Low / S High | 0-255 | Saturation |
| V Low / V High | 0-255 | Brightness |

The marker should appear as a clean white blob in the mask window. If it flickers, widen the HSV range or improve lighting. If background objects are detected, narrow the range.

## Beatmaps

Beatmaps are JSON files in `beatmaps/`.

```json
[
  { "time": 1.0, "lane": "hihat" },
  { "time": 1.5, "lane": "snare" },
  { "time": 2.0, "lane": "tom" },
  { "time": 2.5, "lane": "kick" }
]
```

Each note uses seconds from the start of the game and one of these lane IDs:

- `hihat`
- `snare`
- `tom`
- `kick`

## Project Structure

| File or folder | Purpose |
|----------------|---------|
| `rhythm_drum.py` | Main webcam loop, controls, timing coordination |
| `rhythm_drum_new.py` | Separate new-style layout entry point |
| `vision.py` | HSV thresholding, morphology, contours, centroids, calibration |
| `audio.py` | Pygame mixer sound loading and playback |
| `game.py` | Beatmap loading, notes, scoring, combo, accuracy, game states |
| `ui.py` | Default four-lane falling-note UI |
| `ui_new.py` | Oval drum pads, centered rhythm staff, HUD, marker glow, hit effects |
| `config.py` | Shared constants, lanes, colors, timing windows |
| `beatmaps/demo.json` | Demo rhythm chart |
| `sounds/` | Generated `.wav` drum sounds |
| `generate_sounds.py` | Generates the `.wav` sound assets |

## Computer Vision Value

The interaction is powered by traditional CV steps that are easy to explain in a final project presentation:

- `cv2.VideoCapture` reads live webcam frames.
- `cv2.cvtColor` converts BGR frames to HSV.
- `cv2.inRange` isolates the selected marker color.
- `cv2.erode` and `cv2.dilate` clean the binary mask.
- `cv2.findContours` finds candidate marker blobs.
- `cv2.moments` calculates the marker centroid.
- The centroid is tested against rectangular lane zones in the default game or oval drum pad zones in the reference layout.
- Edge-trigger state prevents repeated hits while the marker stays inside a zone.

No MediaPipe, pose estimation, deep learning, or gesture model is used.

## Performance Notes

- Target frame rate: 30 FPS
- Webcam buffer is set low to reduce input latency.
- Audio is loaded before the game loop and played through `pygame.mixer`.
- Rendering uses lightweight OpenCV drawing primitives.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Cannot open webcam | Check camera permissions or try another camera index in `rhythm_drum.py` |
| No sound | Run `python generate_sounds.py`; confirm `.wav` files exist in `sounds/` |
| Marker not detected | Use brighter tape, improve lighting, or adjust HSV sliders |
| False detection | Narrow HSV thresholds and use a plain background |
| Low FPS | Close other apps and keep the mask window hidden with C if needed |
