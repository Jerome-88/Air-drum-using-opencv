# Virtual Drum System — OpenCV-Based Real-Time Gesture Recognition

**Course:** Computer Vision | BINUS University  
**Authors:** Jerome Maxcellino Budianto (2802412894) · Hibatullah Fawwaz Hana (2802485271)  
**Version:** 1.0

---

## Overview

A virtual drum simulator that uses your webcam and a bright-colored marker (e.g., green tape wrapped around a pen or chopstick) to play drum sounds in real-time. No special hardware required — runs on any laptop with a standard webcam.

**Pipeline:** Webcam → BGR→HSV → Color Mask → Morphological Clean-up → Contour Detection → Centroid → Collision with ROI → Audio Trigger

---

## Requirements

- Python 3.8 – 3.11
- Webcam (≥ 640×480)
- Windows 10/11, Ubuntu 20.04+, or macOS 12+

---

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Generate drum sound files (run once)
python generate_sounds.py

# 3. Start the system
python virtual_drum.py
```

---

## How to Play

1. Wrap **bright green tape** around the tip of a pen, chopstick, or drumstick.  
   Any single solid bright colour works — adjust the HSV trackbars to match.
2. Stand in front of your webcam with a **plain, contrasting background**.
3. Move the marker into one of the four coloured zones to trigger a drum sound.
4. Press **Q** to quit.

### Drum Zones (640×480 frame, mirrored)

```
┌───────────────────────────────────────────────────────────────┐
│  [Crash Cymbal]      [Tom-Tom]           [Snare]             │
│  x: 10–195  y: 20–175   x: 215–420 y: 20–175   x: 440–630 y: 20–175  │
│                                                               │
│               (swing area — move marker through zones)        │
│                                                               │
│          [Hi-Hat / Bass  —  x: 10–630  y: 295–460]           │
└───────────────────────────────────────────────────────────────┘
```

---

## Calibrating the Marker Color

The **HSV Calibration** window shows six sliders:

| Slider | Range | Meaning |
|--------|-------|---------|
| H Low / H High | 0–179 | Hue (colour family) |
| S Low / S High | 0–255 | Saturation (colour purity) |
| V Low / V High | 0–255 | Value (brightness) |

The Calibration window also shows the **binary mask** — the marker should appear as a solid white blob. If it flickers or disappears, adjust the sliders. No restart needed.

**Default (bright green):** H 35–85, S 100–255, V 80–255

Common marker colours and approximate HSV ranges:

| Color  | H Low | H High |
|--------|-------|--------|
| Green  | 35    | 85     |
| Yellow | 20    | 35     |
| Red    | 0/160 | 10/179 |
| Blue   | 100   | 130    |

---

## Architecture

| Component | Technology |
|-----------|-----------|
| Video capture | `cv2.VideoCapture` |
| Color space | `cv2.cvtColor` (BGR→HSV) |
| Masking | `cv2.inRange` |
| Morphology | `cv2.erode`, `cv2.dilate` |
| Contour + centroid | `cv2.findContours`, `cv2.moments` |
| Collision detection | Custom point-in-rect logic |
| Audio playback | `pygame.mixer` (non-blocking, 16 channels) |
| State management | Per-ROI boolean edge-trigger flags |
| Calibration UI | `cv2.createTrackbar` |

---

## Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Frame rate | ≥ 24 FPS | Displayed live in the bottom-left corner |
| Audio latency | ≤ 50 ms | pygame.mixer buffer set to 512 samples at 44100 Hz |
| Trigger accuracy | ≥ 95% | Edge trigger prevents double-fire while marker is stationary |
| Session stability | 30 min no crash | Single-thread video loop + separate mixer thread |

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Cannot open webcam" | Check camera index — try changing `VideoCapture(0)` to `VideoCapture(1)` |
| No sound | Run `generate_sounds.py` first; check system audio volume |
| Marker not detected | Improve lighting; use brighter tape; widen HSV range via trackbars |
| Low FPS | Close other applications; reduce `MIN_CONTOUR_AREA` threshold is not needed — check CPU load |
| False triggers | Narrow HSV range to exclude background colours |
