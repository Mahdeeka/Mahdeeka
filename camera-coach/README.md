# Camera coach (Sony a7 IV, Instagram Reels)

> **Status: first version, not yet tested on real footage or a real camera.**

Analyzes your shot and sets the camera for the best talking-head clip, then locks the settings
so they don't drift like auto does. After filming, it scores clips and exports Instagram-ready versions.

## Install (Windows)
```
winget install Python.Python.3.12
winget install Gyan.FFmpeg
pip install -r requirements.txt
```

## Use
| Command | What it does |
|---|---|
| `python coach.py live` | Before filming. Camera on **USB Streaming** (acts as a webcam). The coach measures your face brightness, colour, focus and framing, tells you which settings to change, re-checks, then locks. |
| `python coach.py live --white-card` | Same, but sets white balance from a sheet of white paper (most accurate). |
| `python coach.py live --sony` | Fully automatic: the coach changes ISO / aperture / WB itself. Needs `sony_bridge.exe` (see `sony_bridge/README.md`). |
| `python coach.py demo photo.jpg` | Try the live coach on a simulated camera, no hardware needed. |
| `python coach.py check C0001.MP4 C0002.MP4` | After filming: score each clip, list what to fix, rank the takes. |
| `python coach.py fix C0001.MP4` | Export a 1080x1920 version: crop around your face, brightness/colour correction, audio at -14 LUFS. |
| `python coach.py devices` | Find the camera's device number. |

Defaults assume 25p and 50 Hz mains (Israel/Europe): shutter 1/50. Use `--fps 30 --mains 60` in the US.
For darker skin tones, add `--face-target 0.48`.

What it can't do: move your lights, or repair blur, distorted audio or blown highlights. It tells you what to change for the next take.
