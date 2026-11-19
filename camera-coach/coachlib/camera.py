"""Where live frames come from, and how settings reach the camera.

  UsbStream     a7 IV in "USB Streaming" mode (shows up as a webcam). You change the dials,
                the coach tells you what to set.
  SonyBridge    fully automatic: talks to sony_bridge.exe (built from Sony's Camera Remote SDK,
                see sony_bridge/README.md), which reads live view and sets ISO/aperture/WB itself.
  SimCamera     a simulated camera built from a photo, to try the coach without hardware.
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, replace
from pathlib import Path

import cv2
import numpy as np

from .analysis import GAMMA


@dataclass(frozen=True)
class Settings:
    iso: int
    fnumber: float
    shutter: str      # "1/50"
    kelvin: int

    def shutter_seconds(self) -> float:
        num, _, den = self.shutter.partition("/")
        return float(num) / float(den) if den else float(num)

    def describe(self) -> str:
        return f"ISO {self.iso}  f/{self.fnumber:g}  {self.shutter}s  {self.kelvin}K"


def changes(old: Settings, new: Settings) -> list[str]:
    out = []
    if new.iso != old.iso:
        out.append(f"ISO           {old.iso} -> {new.iso}")
    if abs(new.fnumber - old.fnumber) > 1e-6:
        out.append(f"Aperture      f/{old.fnumber:g} -> f/{new.fnumber:g}")
    if new.shutter != old.shutter:
        out.append(f"Shutter       {old.shutter} -> {new.shutter}")
    if new.kelvin != old.kelvin:
        out.append(f"White balance {old.kelvin}K -> {new.kelvin}K")
    return out


class Camera:
    """Frame source + (optional) settings control."""
    automatic = False   # True when apply() really changes the camera

    def grab(self) -> np.ndarray:
        raise NotImplementedError

    def read_settings(self) -> Settings | None:
        return None

    def apply(self, old: Settings, new: Settings) -> None:
        raise NotImplementedError

    def close(self) -> None:
        pass


class ManualApply:
    """Tells you what to change on the camera and waits until you've done it."""

    def apply(self, old: Settings, new: Settings) -> None:
        print("\n  Change on the camera:")
        for line in changes(old, new):
            print("    " + line)
        input("  Press Enter when done... ")


class UsbStream(ManualApply, Camera):
    def __init__(self, index: int = 0):
        api = cv2.CAP_DSHOW if sys.platform.startswith("win") else cv2.CAP_ANY
        self.cap = cv2.VideoCapture(index, api)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        if not self.cap.isOpened():
            raise SystemExit(f"Can't open video device {index}. Run 'python coach.py devices' to list them.")

    def grab(self) -> np.ndarray:
        frame = None
        for _ in range(6):            # drop buffered frames so we see the current settings
            ok, f = self.cap.read()
            if ok:
                frame = f
        if frame is None:
            raise SystemExit("No picture from the camera (is USB Streaming on?)")
        return frame

    def close(self) -> None:
        self.cap.release()


class FileSource(ManualApply, Camera):
    """Reads frames from a video file (for testing the analysis on a recording)."""

    def __init__(self, path: str):
        self.cap = cv2.VideoCapture(path)
        if not self.cap.isOpened():
            raise SystemExit(f"Can't open {path}")

    def grab(self) -> np.ndarray:
        ok, f = self.cap.read()
        if not ok:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, f = self.cap.read()
        return f


class SimCamera(Camera):
    """A pretend camera: a photo lit by a lamp of `scene_kelvin`, needing ISO `correct_iso` at f/4 1/50."""
    automatic = True

    def __init__(self, photo: str, scene_kelvin: int = 3400, correct_iso: int = 1600):
        img = cv2.imread(photo)
        if img is None:
            raise SystemExit(f"Can't read {photo}")
        h, w = img.shape[:2]
        canvas = np.full((1080, 1920, 3), 205, np.uint8)       # light grey wall
        size = 900
        img = cv2.resize(img, (size, round(size * h / w)))
        ih = min(img.shape[0], 1080)
        canvas[1080 - ih:, 700:700 + size] = img[:ih]
        self.lin = np.power(canvas.astype(np.float32) / 255.0, GAMMA)
        self.scene_kelvin, self.correct_iso = scene_kelvin, correct_iso
        self.settings = Settings(400, 5.6, "1/50", 5600)
        self.rng = np.random.default_rng(1)

    def read_settings(self) -> Settings:
        return self.settings

    def apply(self, old: Settings, new: Settings) -> None:
        for line in changes(old, new):
            print("    set " + line)
        self.settings = new

    def grab(self) -> np.ndarray:
        s = self.settings
        gain = (s.iso / self.correct_iso) * (s.shutter_seconds() * 50) * (4.0 / s.fnumber) ** 2
        d = 1e6 / self.scene_kelvin - 1e6 / s.kelvin            # + = light warmer than the WB setting
        wb = np.array([math.exp(-d / 160), 1.0, math.exp(d / 160)], np.float32)   # B, G, R
        lin = self.lin * gain * wb
        lin += self.rng.normal(0, 0.002 * math.sqrt(s.iso / 100), lin.shape).astype(np.float32)
        return (np.power(np.clip(lin, 0, 1), 1 / GAMMA) * 255).astype(np.uint8)


class SonyBridge(Camera):
    """Fully automatic control through sony_bridge.exe (JSON lines over stdin/stdout)."""
    automatic = True

    def __init__(self, exe: str):
        if not Path(exe).exists():
            raise SystemExit(f"{exe} not found. Build it first: see sony_bridge/README.md")
        self.proc = subprocess.Popen([exe, "--serve"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     text=True, bufsize=1)
        self.tmp = Path(tempfile.gettempdir()) / "coach_liveview.jpg"
        self._call({"cmd": "hello"})

    def _call(self, req: dict) -> dict:
        self.proc.stdin.write(json.dumps(req) + "\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        if not line:
            raise SystemExit("sony_bridge stopped (camera disconnected?)")
        res = json.loads(line)
        if not res.get("ok"):
            raise SystemExit(f"sony_bridge error: {res.get('error')}")
        return res

    def read_settings(self) -> Settings:
        r = self._call({"cmd": "get"})
        return Settings(int(r["iso"]), float(r["fnumber"]), str(r["shutter"]), int(r["kelvin"]))

    def apply(self, old: Settings, new: Settings) -> None:
        for line in changes(old, new):
            print("    set " + line)
        self._call({"cmd": "set", "iso": new.iso, "fnumber": new.fnumber, "shutter": new.shutter, "kelvin": new.kelvin})
        time.sleep(1.0)  # let live view catch up

    def grab(self) -> np.ndarray:
        self._call({"cmd": "liveview", "path": str(self.tmp)})
        img = cv2.imread(str(self.tmp))
        if img is None:
            raise SystemExit("sony_bridge returned no live view image")
        return img

    def record(self, start: bool) -> None:
        self._call({"cmd": "record", "action": "start" if start else "stop"})

    def close(self) -> None:
        try:
            self._call({"cmd": "bye"})
        except SystemExit:
            pass
        self.proc.terminate()


def list_devices(max_index: int = 6) -> list[tuple[int, int, int]]:
    api = cv2.CAP_DSHOW if sys.platform.startswith("win") else cv2.CAP_ANY
    found = []
    for i in range(max_index):
        cap = cv2.VideoCapture(i, api)
        if cap.isOpened():
            ok, f = cap.read()
            if ok:
                found.append((i, f.shape[1], f.shape[0]))
        cap.release()
    return found


__all__ = ["Settings", "changes", "Camera", "UsbStream", "FileSource", "SimCamera", "SonyBridge", "list_devices", "replace"]
