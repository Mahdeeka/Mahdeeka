"""Camera coach for Instagram talking-head videos on a Sony a7 IV.

  python coach.py live                      before filming: measure, set, lock (camera on USB Streaming)
  python coach.py live --sony               same, fully automatic through sony_bridge.exe
  python coach.py demo PHOTO.jpg            try the live coach on a simulated camera
  python coach.py check C0001.MP4 ...       after filming: score clips, rank takes
  python coach.py fix C0001.MP4 ...         after filming: export Instagram-ready 1080x1920 versions
  python coach.py devices                   list video devices (to find the camera's number)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from coachlib.analysis import FACE_TARGET


def _print_report(rep) -> None:
    i = rep.info
    print(f"\n{rep.path.name}   score {rep.score}/100")
    print(f"  {i.width}x{i.height}  {i.fps:.2f} fps  {i.duration:.1f}s  {i.codec} {i.pix_fmt}"
          + (f"  {i.sony_gamma}" if i.sony_gamma else ""))
    for issue in rep.issues:
        mark = {"ok": "OK  ", "warn": "FIX ", "bad": "FIX!"}[issue.level]
        print(f"  [{mark}] {issue.message}")
        if issue.fix and issue.level != "ok":
            print(f"         -> {issue.fix}")


def _clips(paths: list[str]) -> list[Path]:
    out = []
    for p in paths:
        path = Path(p)
        if path.is_dir():
            out += sorted(q for q in path.iterdir() if q.suffix.lower() in (".mp4", ".mov", ".mxf"))
        elif path.exists():
            out.append(path)
        else:
            sys.exit(f"Not found: {p}")
    if not out:
        sys.exit("No video files given.")
    return out


def cmd_check(a) -> None:
    from coachlib.clips import check_clip
    reps = []
    for p in _clips(a.clips):
        print(f"Checking {p.name} ...", flush=True)
        reps.append(check_clip(p, face_target=a.face_target))
    for rep in reps:
        _print_report(rep)
    if len(reps) > 1:
        print("\nRanking (best first):")
        for n, rep in enumerate(sorted(reps, key=lambda r: -r.score), 1):
            print(f"  {n}. {rep.path.name:30s} {rep.score}/100")


def cmd_fix(a) -> None:
    from coachlib.clips import check_clip, fix_clip
    out_dir = Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    for p in _clips(a.clips):
        print(f"\nChecking {p.name} ...", flush=True)
        rep = check_clip(p, face_target=a.face_target)
        _print_report(rep)
        out = out_dir / f"{p.stem}_instagram.mp4"
        print(f"  Exporting {out} ...", flush=True)
        notes = fix_clip(p, out, rep, a.face_target, crop=not a.no_crop, punch_in=not a.no_zoom)
        print("  Done: " + (", ".join(notes) if notes else "no corrections needed, re-encoded for Instagram"))
        print("  Note: blur, clipped audio and blown highlights can't be repaired - see the FIX! lines for next time.")


def _settings(a):
    from coachlib.camera import Settings
    return Settings(a.iso, a.fnumber, a.shutter, a.kelvin)


def cmd_live(a) -> None:
    from coachlib import live
    from coachlib.camera import SonyBridge, UsbStream
    cam = SonyBridge(a.bridge) if a.sony else UsbStream(a.device)
    if not cam.automatic:
        print("Manual mode: the coach tells you what to change, you turn the dials.")
        print("Type the settings the camera is on now with --iso --fnumber --shutter --kelvin if they differ from:")
        print(f"  ISO {a.iso}  f/{a.fnumber:g}  {a.shutter}  {a.kelvin}K")
    try:
        live.run(cam, _settings(a), fps=a.fps, mains=a.mains, iso_min=a.iso_min, iso_max=a.iso_max,
                 f_widest=a.widest, face_target=a.face_target, white_card=a.white_card,
                 out_dir=Path(a.out), watch=a.watch)
    finally:
        cam.close()


def cmd_demo(a) -> None:
    from coachlib import live
    from coachlib.camera import SimCamera
    cam = SimCamera(a.photo, scene_kelvin=a.scene_kelvin, correct_iso=a.correct_iso)
    print(f"Simulated camera: room lit at {a.scene_kelvin}K, needs about ISO {a.correct_iso} at f/4.")
    live.run(cam, cam.read_settings(), fps=25, mains=50, face_target=a.face_target,
             white_card=False, out_dir=Path(a.out), interactive=False)


def cmd_devices(_a) -> None:
    from coachlib.camera import list_devices
    found = list_devices()
    if not found:
        print("No video devices found. Is the camera connected with USB Streaming on?")
    for i, w, h in found:
        print(f"  device {i}: {w}x{h}")
    print("Use the camera's number with:  python coach.py live --device N")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--face-target", type=float, default=FACE_TARGET,
                       help=f"face brightness 0-1 (default {FACE_TARGET}; try 0.45-0.5 for darker skin)")
        p.add_argument("--out", default="coach_output", help="output folder")

    p = sub.add_parser("check", help="score recorded clips")
    p.add_argument("clips", nargs="+", help="video files or a folder")
    common(p)
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("fix", help="export Instagram-ready versions")
    p.add_argument("clips", nargs="+")
    p.add_argument("--no-crop", action="store_true", help="keep the original framing (no 9:16 crop)")
    p.add_argument("--no-zoom", action="store_true", help="don't punch in when you're small in a 4K frame")
    common(p)
    p.set_defaults(func=cmd_fix)

    p = sub.add_parser("live", help="set up the camera before filming")
    p.add_argument("--device", type=int, default=0, help="video device number (see 'devices')")
    p.add_argument("--sony", action="store_true", help="fully automatic via sony_bridge.exe")
    p.add_argument("--bridge", default=str(Path(__file__).parent / "sony_bridge" / "sony_bridge.exe"))
    p.add_argument("--iso", type=int, default=400)
    p.add_argument("--fnumber", type=float, default=4.0)
    p.add_argument("--shutter", default="1/50")
    p.add_argument("--kelvin", type=int, default=5600)
    p.add_argument("--fps", type=float, default=25)
    p.add_argument("--mains", type=int, choices=(50, 60), default=50, help="mains frequency (Israel/Europe 50, US 60)")
    p.add_argument("--iso-min", type=int, default=100, help="100 for S-Cinetone, 800 for S-Log3")
    p.add_argument("--iso-max", type=int, default=3200)
    p.add_argument("--widest", type=float, default=2.8, help="widest aperture the coach may use")
    p.add_argument("--white-card", action="store_true", help="set white balance from a sheet of white paper")
    p.add_argument("--watch", action="store_true", help="keep watching the light after locking")
    common(p)
    p.set_defaults(func=cmd_live)

    p = sub.add_parser("demo", help="try the live coach on a simulated camera")
    p.add_argument("photo", help="a photo of a face")
    p.add_argument("--scene-kelvin", type=int, default=3400)
    p.add_argument("--correct-iso", type=int, default=1600)
    common(p)
    p.set_defaults(func=cmd_demo)

    p = sub.add_parser("devices", help="list video devices")
    p.set_defaults(func=cmd_devices)

    a = ap.parse_args(argv)
    a.func(a)


if __name__ == "__main__":
    main()
