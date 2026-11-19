"""Before the shoot: measure the live picture, set the camera, lock it, then watch for changes."""
from __future__ import annotations

import json
import math
import time
from dataclasses import replace
from datetime import datetime
from pathlib import Path

import cv2

from .analysis import FACE_TARGET, GAMMA, FrameReport, analyze_frame, assess, combine, kelvin_after, score
from .camera import Camera, Settings, changes

ISO_STEPS = [100, 125, 160, 200, 250, 320, 400, 500, 640, 800, 1000, 1250, 1600, 2000, 2500, 3200,
             4000, 5000, 6400, 8000, 10000, 12800]
F_STEPS = [1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.5, 2.8, 3.2, 3.5, 4.0, 4.5, 5.0, 5.6, 6.3, 7.1, 8.0, 9.0, 10.0, 11.0]


def shutter_for(fps: float, mains_hz: int) -> str:
    """180-degree shutter, nudged so lights powered at 50/60 Hz don't flicker."""
    if mains_hz == 50:
        return "1/100" if fps > 40 else "1/50"
    return "1/120" if fps > 40 else "1/60"


def _nearest(steps, value, lo, hi):
    pool = [s for s in steps if lo - 1e-6 <= s <= hi + 1e-6] or steps
    return min(pool, key=lambda s: abs(math.log2(s / value)))


def plan_exposure(s: Settings, need: float, iso_min: int, iso_max: int, f_widest: float,
                  f_sweet=(2.8, 4.0), f_darkest: float = 5.6) -> tuple[Settings, float]:
    """Spend `need` stops (+ brighter / - darker) on aperture and ISO.

    Order when brightening: open to f/4 -> raise ISO -> open further.  When darkening:
    close to f/2.8 -> lower ISO -> close to f/5.6.  Returns new settings and the stops still missing.
    """
    iso, f, left = float(s.iso), float(s.fnumber), need

    def move_f(target):
        nonlocal f, left
        avail = 2 * math.log2(f / target)          # + means opening up (brighter)
        d = min(left, avail) if left > 0 and avail > 0 else max(left, avail) if left < 0 and avail < 0 else 0
        f *= 2 ** (-d / 2)
        left -= d

    def move_iso(target):
        nonlocal iso, left
        avail = math.log2(target / iso)
        d = min(left, avail) if left > 0 and avail > 0 else max(left, avail) if left < 0 and avail < 0 else 0
        iso *= 2 ** d
        left -= d

    if left > 0:
        move_f(min(f, f_sweet[1]))
        move_iso(iso_max)
        move_f(f_widest)
    else:
        move_f(max(f, f_sweet[0]))
        move_iso(iso_min)
        move_f(max(f, f_darkest))
    new_iso = _nearest(ISO_STEPS, iso, iso_min, iso_max)
    new_f = _nearest(F_STEPS, f, f_widest, 22)
    missing = need - (math.log2(new_iso / s.iso) - 2 * math.log2(new_f / s.fnumber))
    return replace(s, iso=int(new_iso), fnumber=new_f), missing


def measure(cam: Camera, frames: int = 3, white_card: bool = False) -> tuple[FrameReport | None, object]:
    reps, last = [], None
    for _ in range(frames):
        last = cam.grab()
        reps.append(analyze_frame(last, white_card=white_card))
    return combine(reps), last


def _status(r: FrameReport, target: float) -> str:
    e = r.exposure_stops(target)
    exp = "no face" if e is None else f"face {e:+.1f} stop to go"
    return f"{exp}, WB off by {r.wb_mired_error:+.0f} mired ({r.wb_source})"


def calibrate_wb_with_card(cam: Camera, s: Settings, interactive: bool) -> Settings:
    if interactive:
        input("\n  Hold a plain white sheet of paper so it fills the MIDDLE of the frame, then press Enter... ")
    for _ in range(4):
        r, _ = measure(cam, 2, white_card=True)
        if abs(r.wb_mired_error) <= 6:
            break
        new = replace(s, kelvin=kelvin_after(s.kelvin, r.wb_mired_error, 0.9))
        if new == s:
            break
        cam.apply(s, new)
        s = new
    print(f"  White balance set from the paper: {s.kelvin}K")
    if interactive:
        input("  Put the paper away and sit in your filming position, then press Enter... ")
    return s


def run(cam: Camera, start: Settings, fps: float = 25, mains: int = 50, iso_min: int = 100, iso_max: int = 3200,
        f_widest: float = 2.8, face_target: float = FACE_TARGET, white_card: bool = False,
        max_rounds: int = 8, out_dir: Path = Path("coach_output"), watch: bool = False,
        interactive: bool = True) -> dict:
    s = cam.read_settings() or start
    print(f"\nStarting from: {s.describe()}")
    want_shutter = shutter_for(fps, mains)
    if s.shutter != want_shutter:
        new = replace(s, shutter=want_shutter)
        print(f"Shutter to {want_shutter} for {fps:g}p with {mains} Hz lights (natural motion, no flicker).")
        cam.apply(s, new)
        s = new
    if white_card:
        s = calibrate_wb_with_card(cam, s, interactive)

    leftover = 0.0
    for rnd in range(1, max_rounds + 1):
        r, frame = measure(cam)
        if r.face is None:
            print(f"  Round {rnd}: no face found.")
            if interactive:
                input("  Sit in your filming position facing the camera, then press Enter... ")
                continue
            break
        print(f"  Round {rnd}: {_status(r, face_target)}")
        need = r.exposure_stops(face_target)
        new, leftover = s, 0.0
        if abs(need) > 1 / 6:
            new, leftover = plan_exposure(s, need, iso_min, iso_max, f_widest)
        if not white_card and abs(r.wb_mired_error) > 10 and r.wb_source != "estimate":
            new = replace(new, kelvin=kelvin_after(s.kelvin, r.wb_mired_error, 0.8))
        if new == s:
            break
        cam.apply(s, new)
        s = new

    r, frame = measure(cam)
    issues = assess(r, face_target)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    snap = out_dir / f"live_{stamp}.jpg"
    cv2.imwrite(str(snap), frame)

    print("\n=== LOCKED: record with these settings ===")
    print(f"  {s.describe()}")
    if abs(leftover) > 1 / 3:
        if leftover > 0:
            print(f"  ! Still ~{leftover:.1f} stop(s) too dark at ISO {iso_max}: add light on your face.")
        else:
            print(f"  ! Still ~{-leftover:.1f} stop(s) too bright: use an ND filter or dim the light.")
    print("\nWhat the coach sees:")
    for i in issues:
        mark = {"ok": "OK  ", "warn": "FIX ", "bad": "FIX!"}[i.level]
        print(f"  [{mark}] {i.message}" + (f"\n         -> {i.fix}" if i.fix and i.level != "ok" else ""))
    print(f"\nShot score: {score(issues)}/100   (snapshot: {snap})")

    result = {"settings": s.__dict__, "score": score(issues), "leftover_stops": leftover,
              "issues": [i.__dict__ for i in issues], "measurements": r.to_dict(), "snapshot": str(snap)}
    (out_dir / f"live_{stamp}.json").write_text(json.dumps(result, indent=2, default=str))

    if watch:
        _watch(cam, r, face_target)
    return result


def _watch(cam: Camera, locked: FrameReport, target: float, every: float = 2.0) -> None:
    print("\nWatching the light while you record (Ctrl+C to stop). Settings stay locked.")
    try:
        while True:
            time.sleep(every)
            r, _ = measure(cam, 1)
            if r.face_luma is None or locked.face_luma is None:
                continue
            drift = GAMMA * math.log2(r.face_luma / locked.face_luma)
            wb = r.wb_mired_error - locked.wb_mired_error
            if abs(drift) > 0.5:
                print(f"  ! Light on your face changed by {drift:+.1f} stops - recalibrate before the next take.")
            if abs(wb) > 25:
                print(f"  ! Light colour changed ({'warmer' if wb > 0 else 'cooler'}) - recalibrate before the next take.")
    except KeyboardInterrupt:
        print("\nStopped watching.")
