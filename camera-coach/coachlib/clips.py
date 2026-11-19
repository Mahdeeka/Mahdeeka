"""After the shoot: check recorded clips, rank takes, export Instagram-ready versions."""
from __future__ import annotations

import json
import math
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from .analysis import (FACE_TARGET, GAMMA, FrameReport, Issue, analyze_frame, assess, combine, score)

IG_W, IG_H = 1080, 1920


def _need(tool: str) -> str:
    path = shutil.which(tool)
    if not path:
        raise SystemExit(f"'{tool}' not found. Install ffmpeg (Windows: winget install Gyan.FFmpeg) and reopen the terminal.")
    return path


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")


@dataclass
class ClipInfo:
    width: int
    height: int
    fps: float
    duration: float
    codec: str
    pix_fmt: str
    transfer: str
    has_audio: bool
    sony_gamma: str = ""


def probe(path: Path) -> ClipInfo:
    res = _run([_need("ffprobe"), "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(path)])
    if res.returncode != 0:
        raise SystemExit(f"Can't read {path}: {res.stderr.strip()}")
    data = json.loads(res.stdout)
    v = next((s for s in data["streams"] if s.get("codec_type") == "video"), None)
    if v is None:
        raise SystemExit(f"{path} has no video stream")
    w, h = int(v["width"]), int(v["height"])
    rot = 0
    for sd in v.get("side_data_list", []):
        if "rotation" in sd:
            rot = int(sd["rotation"])
    rot = int(v.get("tags", {}).get("rotate", rot))
    if abs(rot) % 180 == 90:
        w, h = h, w
    num, _, den = v.get("avg_frame_rate", "0/1").partition("/")
    fps = float(num) / float(den or 1) if float(den or 1) else 0.0
    dur = float(v.get("duration") or data["format"].get("duration") or 0)
    info = ClipInfo(w, h, fps, dur, v.get("codec_name", ""), v.get("pix_fmt", ""),
                    v.get("color_transfer", ""), any(s.get("codec_type") == "audio" for s in data["streams"]))
    # Sony cameras write C0001M01.XML next to C0001.MP4 with the picture profile gamma
    for xml in (path.with_name(path.stem + "M01.XML"), path.with_suffix(".XML")):
        if xml.exists():
            m = re.search(r'CaptureGammaEquation"\s+value="([^"]+)"', xml.read_text(errors="ignore"))
            if m:
                info.sony_gamma = m.group(1)
            break
    return info


def grab_frame(path: Path, t: float) -> np.ndarray | None:
    """One frame at time t, scaled to at most 1080 px tall, via ffmpeg (handles rotation and 10-bit)."""
    res = subprocess.run([_need("ffmpeg"), "-v", "error", "-ss", f"{t:.3f}", "-i", str(path), "-frames:v", "1",
                          "-vf", "scale=-2:'min(1080,ih)'", "-f", "image2pipe", "-vcodec", "png", "-"],
                         capture_output=True)
    if res.returncode != 0 or not res.stdout:
        return None
    return cv2.imdecode(np.frombuffer(res.stdout, np.uint8), cv2.IMREAD_COLOR)


def loudness(path: Path) -> dict | None:
    """EBU R128 measurement (also the first pass of loudnorm)."""
    res = _run([_need("ffmpeg"), "-hide_banner", "-nostats", "-i", str(path), "-map", "0:a:0", "-vn",
                "-af", "loudnorm=I=-14:TP=-1:LRA=11:print_format=json", "-f", "null", "-"])
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", res.stderr)
    if not m:
        return None
    data = json.loads(m.group(0))
    try:
        if not math.isfinite(float(data["input_i"])):
            return None
    except (ValueError, KeyError):
        return None
    return data


@dataclass
class ClipReport:
    path: Path
    info: ClipInfo
    frames: FrameReport | None
    face_luma_spread: float
    audio: dict | None
    issues: list[Issue] = field(default_factory=list)
    score: int = 0


def check_clip(path: Path, samples: int = 12, face_target: float = FACE_TARGET) -> ClipReport:
    info = probe(path)
    span = max(info.duration, 0.1)
    times = [span * (0.05 + 0.9 * i / max(samples - 1, 1)) for i in range(samples)]
    reports = [analyze_frame(f) for t in times if (f := grab_frame(path, t)) is not None]
    frames = combine(reports)
    lum = [r.face_luma for r in reports if r.face_luma is not None]
    spread = GAMMA * float(np.log2(max(lum) / max(min(lum), 1e-3))) if len(lum) > 1 else 0.0
    audio = loudness(path) if info.has_audio else None

    issues = assess(frames, face_target) if frames else [Issue("bad", "file", "Couldn't read any frames.", "", 100)]
    if spread > 0.5:
        issues.append(Issue("warn", "exposure", f"Brightness on your face changes by {spread:.1f} stops during the clip.",
                            "Auto ISO / auto exposure was probably on - use manual (M) with a fixed ISO.", 8))
    if info.transfer in ("arib-std-b67", "smpte2084"):
        issues.append(Issue("warn", "file", "Clip is HDR (HLG); Instagram often shows it washed out.",
                            "Fix will convert it to normal SDR. Next time use S-Cinetone, not HLG.", 5))
    if "log" in info.sony_gamma.lower():
        issues.append(Issue("warn", "file", f"Recorded in {info.sony_gamma} (needs color grading).",
                            "For ready-to-post clips use PP11 S-Cinetone.", 6))
    if info.has_audio and audio is None:
        issues.append(Issue("warn", "audio", "Audio track is silent.", "Check the mic is connected and switched on.", 15))
    elif not info.has_audio:
        issues.append(Issue("warn", "audio", "No audio track.", "", 10))
    if audio:
        lufs, tp = float(audio["input_i"]), float(audio["input_tp"])
        if tp > -0.5:
            issues.append(Issue("bad", "audio", f"Audio is clipping (peak {tp:+.1f} dBTP) - distortion can't be fixed later.",
                                "Lower the mic/record level so peaks stay around -12 dB.", 12))
        elif lufs < -32:
            issues.append(Issue("warn", "audio", f"Audio is very quiet ({lufs:.0f} LUFS).",
                                "Raise the mic level; boosting later also boosts noise.", 6))
        else:
            issues.append(Issue("ok", "audio", f"Audio level usable ({lufs:.0f} LUFS; fix brings it to -14)."))
    if min(info.width, info.height) < 1080:
        issues.append(Issue("warn", "file", f"Low resolution ({info.width}x{info.height}).", "Record 4K or at least 1080p.", 8))
    if info.duration > 180:
        issues.append(Issue("warn", "file", f"Clip is {info.duration / 60:.1f} min; Reels are up to 3 min.", "Trim it.", 0))
    return ClipReport(path, info, frames, spread, audio, issues, score(issues))


def _even(v: float) -> int:
    return max(2, int(round(v / 2)) * 2)


def plan_crop(info: ClipInfo, fr: FrameReport | None, punch_in: bool = True):
    """9:16 crop window (w, h, x, y) in source pixels, following the face."""
    W, H = info.width, info.height
    scale = W / fr.width if fr else 1.0  # analysis frames were downscaled
    face = tuple(v * scale for v in fr.face) if fr and fr.face else None
    if W / H <= 9 / 16 + 0.01:      # already vertical (or taller)
        ch = min(H, _even(W * 16 / 9))
        cw = W
    else:
        ch = H
        cw = _even(H * 9 / 16)
    if punch_in and face and H >= W:  # vertical source: no punch-in logic needed
        punch_in = False
    if punch_in and face:
        fh = face[3]
        want = fh / 0.22                    # face about 22% of frame height
        if want < ch and ch > IG_H:          # only zoom if we keep >= 1920 px of real detail
            ch = _even(max(IG_H, want))
            cw = _even(ch * 9 / 16)
    if face:
        cx = face[0] + face[2] / 2
        eye = face[1] + 0.4 * face[3]
    else:
        cx, eye = W / 2, H * 0.35
    x = int(min(max(cx - cw / 2, 0), W - cw))
    y = int(min(max(eye - 0.35 * ch, 0), H - ch))
    return cw, ch, x - x % 2, y - y % 2


def build_filters(info: ClipInfo, rep: ClipReport, face_target: float, crop: bool, punch_in: bool) -> tuple[str, list[str]]:
    notes = []
    vf = []
    if info.transfer in ("arib-std-b67", "smpte2084"):
        vf.append("zscale=t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,"
                  "zscale=t=bt709:m=bt709:r=tv,format=yuv420p")
        notes.append("HDR -> SDR")
    fr = rep.frames
    if crop:
        cw, ch, x, y = plan_crop(info, fr, punch_in)
        if (cw, ch) != (info.width, info.height):
            vf.append(f"crop={cw}:{ch}:{x}:{y}")
            notes.append(f"9:16 crop {cw}x{ch} centred on face")
    if fr:
        b, g, r = fr.wb_rgb
        if abs(fr.wb_mired_error) > 12 and min(b, g, r) > 0 and fr.wb_source != "estimate":
            y_lin = 0.0722 * b + 0.7152 * g + 0.2126 * r
            gains = [min(1.2, max(0.85, (y_lin / c) ** (0.8 / GAMMA))) for c in (r, g, b)]
            vf.append("colorchannelmixer=rr={:.3f}:gg={:.3f}:bb={:.3f}".format(*gains))
            notes.append("white balance corrected")
        e = fr.exposure_stops(face_target)
        if e is not None and abs(e) > 0.2 and fr.face_luma:
            gamma = math.log(fr.face_luma) / math.log(face_target)
            gamma = min(1.5, max(0.75, gamma))
            vf.append(f"eq=gamma={gamma:.3f}")
            notes.append(f"face {'brightened' if e > 0 else 'darkened'} ~{abs(e):.1f} stop")
    if crop:
        vf.append(f"scale={IG_W}:{IG_H}:flags=lanczos")
    vf += ["setsar=1", "format=yuv420p"]
    return ",".join(vf), notes


def fix_clip(path: Path, out: Path, rep: ClipReport, face_target: float = FACE_TARGET,
             crop: bool = True, punch_in: bool = True) -> list[str]:
    info = rep.info
    vf, notes = build_filters(info, rep, face_target, crop, punch_in)
    cmd = [_need("ffmpeg"), "-y", "-hide_banner", "-loglevel", "error", "-stats", "-i", str(path), "-map", "0:v:0"]
    a = rep.audio
    if a:
        cmd += ["-map", "0:a:0", "-af",
                f"loudnorm=I=-14:TP=-1:LRA=11:measured_I={a['input_i']}:measured_TP={a['input_tp']}:"
                f"measured_LRA={a['input_lra']}:measured_thresh={a['input_thresh']}:offset={a['target_offset']}:linear=true",
                "-ar", "48000", "-c:a", "aac", "-b:a", "192k"]
        notes.append("audio -> -14 LUFS")
    elif info.has_audio:
        cmd += ["-map", "0:a:0", "-c:a", "aac", "-b:a", "192k"]
    fps = info.fps if 23 <= info.fps <= 60 else 30
    cmd += ["-vf", vf, "-r", f"{fps:.3f}", "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-profile:v", "high",
            "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
            "-movflags", "+faststart", str(out)]
    res = subprocess.run(cmd)
    if res.returncode != 0:
        raise SystemExit(f"ffmpeg failed on {path}")
    return notes
