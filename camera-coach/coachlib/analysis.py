"""Frame analysis: exposure on the face, white balance, focus, framing, lighting.

Everything works on 8-bit BGR frames (what OpenCV and ffmpeg give us).
Numbers are approximate on purpose: the live coach works in a closed loop
(change a setting, measure again), so small model errors only cost an extra round.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import cv2
import numpy as np

GAMMA = 2.2                 # display gamma used to turn pixel values into "stops"
FACE_TARGET = 0.56          # mean brightness (0-1) of cheeks/nose for a well-exposed face
MIRED_PER_LOG_RB = 80.0     # approx. white-balance shift per unit ln(R/B) in linear light

_CASCADE = None


def _cascade():
    global _CASCADE
    if _CASCADE is None:
        path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        cascade = cv2.CascadeClassifier(path)
        if cascade.empty():
            raise RuntimeError("OpenCV face model missing - install opencv-python 4.x (see requirements.txt)")
        _CASCADE = cascade
    return _CASCADE


def _luma(img: np.ndarray) -> np.ndarray:
    """Rec.709 luma of a float BGR image."""
    return 0.0722 * img[..., 0] + 0.7152 * img[..., 1] + 0.2126 * img[..., 2]


def find_face(bgr: np.ndarray):
    """Largest frontal face as (x, y, w, h) in pixel coordinates, or None."""
    h, w = bgr.shape[:2]
    scale = min(1.0, 640.0 / max(w, h))
    small = cv2.resize(bgr, (round(w * scale), round(h * scale)), interpolation=cv2.INTER_AREA) if scale < 1 else bgr
    gray = cv2.equalizeHist(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY))
    faces = _cascade().detectMultiScale(gray, scaleFactor=1.1, minNeighbors=6, minSize=(36, 36))
    if len(faces) == 0:
        return None
    x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])
    return tuple(int(round(v / scale)) for v in (x, y, fw, fh))


def _box(face, fx0, fx1, fy0, fy1):
    x, y, w, h = face
    return int(x + fx0 * w), int(x + fx1 * w), int(y + fy0 * h), int(y + fy1 * h)


@dataclass
class FrameReport:
    width: int
    height: int
    face: tuple | None              # (x, y, w, h)
    face_luma: float | None         # cheeks/nose brightness, 0-1
    frame_luma: float
    background_luma: float | None
    face_clipped: float             # share of face pixels with a blown channel
    frame_clipped: float
    crushed: float                  # share of pure-black pixels
    wb_mired_error: float           # + image too warm (lower Kelvin), - too cool (raise Kelvin)
    wb_tint: float                  # + green, - magenta
    wb_source: str                  # neutral | estimate | card
    wb_rgb: tuple                   # linear B, G, R of the pixels used for white balance
    sharpness: float                # variance of Laplacian on the face, size-normalised
    face_side_stops: float | None   # brightness difference left vs right half of the face
    face_height: float | None       # face box height / frame height
    face_cx: float | None           # face centre, 0 (left) - 1 (right)
    eye_y: float | None             # eye line, 0 (top) - 1 (bottom)
    luma_p1: float
    luma_p99: float

    def exposure_stops(self, target: float = FACE_TARGET) -> float | None:
        """How many stops to ADD to reach the target (+ = brighten, - = darken)."""
        if self.face_luma is None:
            return None
        return GAMMA * math.log2(target / max(self.face_luma, 1e-3))

    def to_dict(self) -> dict:
        return asdict(self)


def estimate_wb(img: np.ndarray, exclude: np.ndarray | None = None, card_box=None):
    """White balance from the most neutral-looking pixels (or from a white card in the centre).

    Returns (mired_error, tint, source, linear_bgr_mean).
    """
    lin = np.power(img, GAMMA)
    if card_box is not None:
        x0, x1, y0, y1 = card_box
        region = img[y0:y1, x0:x1]
        ok = region.max(axis=2) < 0.97
        sel_lin = lin[y0:y1, x0:x1][ok]
        source = "card"
    else:
        mx, mn = img.max(axis=2), img.min(axis=2)
        y = _luma(img)
        sat = (mx - mn) / np.maximum(mx, 1e-4)
        valid = (y > 0.25) & (y < 0.92) & (mx < 0.97)
        if exclude is not None:
            valid &= ~exclude
        if valid.sum() < 500:  # dark scene: fall back to everything that isn't black or blown
            valid = (y > 0.05) & (mx < 0.97)
        cand = sat[valid]
        if cand.size == 0:
            return 0.0, 0.0, "estimate", (0.0, 0.0, 0.0)
        thr = np.percentile(cand, 5)
        sel = valid & (sat <= thr)
        sel_lin = lin[sel]
        source = "neutral" if np.median(sat[sel]) < 0.12 else "estimate"
    if sel_lin.size == 0:
        return 0.0, 0.0, source, (0.0, 0.0, 0.0)
    b, g, r = (float(v) for v in sel_lin.mean(axis=0))
    b, g, r = max(b, 1e-5), max(g, 1e-5), max(r, 1e-5)
    mired = MIRED_PER_LOG_RB * math.log(r / b)
    tint = math.log(g / math.sqrt(r * b))
    return mired, tint, source, (b, g, r)


def analyze_frame(bgr: np.ndarray, white_card: bool = False) -> FrameReport:
    full_h, full_w = bgr.shape[:2]
    face_full = find_face(bgr)

    # statistics on a working copy no larger than 1280 px
    scale = min(1.0, 1280.0 / max(full_w, full_h))
    work = cv2.resize(bgr, (round(full_w * scale), round(full_h * scale)), interpolation=cv2.INTER_AREA) if scale < 1 else bgr
    img = work.astype(np.float32) / 255.0
    h, w = img.shape[:2]
    y = _luma(img)
    clipped = img.max(axis=2) >= 0.98
    face = tuple(int(round(v * scale)) for v in face_full) if face_full else None

    face_luma = background_luma = side = face_height = face_cx = eye_y = None
    face_clipped = 0.0
    exclude = np.zeros((h, w), bool)
    if face:
        x0, x1, y0, y1 = _box(face, 0.22, 0.78, 0.35, 0.8)  # cheeks, nose, mouth: skips hair and eyes
        face_luma = float(y[y0:y1, x0:x1].mean())
        face_clipped = float(clipped[y0:y1, x0:x1].mean())
        mid = (x0 + x1) // 2
        left, right = float(y[y0:y1, x0:mid].mean()), float(y[y0:y1, mid:x1].mean())
        side = GAMMA * math.log2(max(left, 1e-3) / max(right, 1e-3))
        # person = face plus shoulders/body below it; the rest counts as background
        px0, px1, py0, _ = _box(face, -0.8, 1.8, -0.5, 1.0)
        exclude[max(py0, 0):, max(px0, 0):max(px1, 0)] = True
        if (~exclude).mean() > 0.1:
            background_luma = float(y[~exclude].mean())
        fx, fy, fw, fh = face
        face_height = fh / h
        face_cx = (fx + fw / 2) / w
        eye_y = (fy + 0.4 * fh) / h

    card_box = None
    if white_card:
        card_box = (int(w * 0.35), int(w * 0.65), int(h * 0.35), int(h * 0.65))
    mired, tint, wb_source, wb_rgb = estimate_wb(img, exclude if face else None, card_box)

    # sharpness on the face at a fixed size so different resolutions compare
    if face_full:
        fx, fy, fw, fh = face_full
        crop = bgr[max(fy, 0):fy + fh, max(fx, 0):fx + fw]
    else:
        crop = bgr[int(full_h * 0.3):int(full_h * 0.7), int(full_w * 0.3):int(full_w * 0.7)]
    crop = cv2.resize(crop, (256, max(1, round(256 * crop.shape[0] / max(crop.shape[1], 1)))), interpolation=cv2.INTER_AREA)
    sharpness = float(cv2.Laplacian(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var())

    p1, p99 = (float(v) for v in np.percentile(y, [1, 99]))
    return FrameReport(
        width=full_w, height=full_h, face=face_full, face_luma=face_luma,
        frame_luma=float(y.mean()), background_luma=background_luma,
        face_clipped=face_clipped, frame_clipped=float(clipped.mean()),
        crushed=float((y <= 0.02).mean()),
        wb_mired_error=mired, wb_tint=tint, wb_source=wb_source, wb_rgb=wb_rgb,
        sharpness=sharpness, face_side_stops=side, face_height=face_height,
        face_cx=face_cx, eye_y=eye_y, luma_p1=p1, luma_p99=p99,
    )


def combine(reports: list[FrameReport]) -> FrameReport | None:
    """Median of several frame reports (face fields only from frames that found a face)."""
    if not reports:
        return None
    with_face = [r for r in reports if r.face is not None] or reports

    def med(attr, pool=with_face):
        vals = [getattr(r, attr) for r in pool if getattr(r, attr) is not None]
        return float(np.median(vals)) if vals else None

    face = None
    if any(r.face for r in with_face):
        boxes = np.array([r.face for r in with_face if r.face])
        face = tuple(int(v) for v in np.median(boxes, axis=0))
    rgb = np.median(np.array([r.wb_rgb for r in reports]), axis=0)
    sources = [r.wb_source for r in reports]
    return FrameReport(
        width=reports[0].width, height=reports[0].height, face=face,
        face_luma=med("face_luma"), frame_luma=med("frame_luma", reports),
        background_luma=med("background_luma"), face_clipped=med("face_clipped") or 0.0,
        frame_clipped=med("frame_clipped", reports), crushed=med("crushed", reports),
        wb_mired_error=med("wb_mired_error", reports), wb_tint=med("wb_tint", reports),
        wb_source=max(set(sources), key=sources.count), wb_rgb=tuple(float(v) for v in rgb),
        sharpness=med("sharpness"), face_side_stops=med("face_side_stops"),
        face_height=med("face_height"), face_cx=med("face_cx"), eye_y=med("eye_y"),
        luma_p1=med("luma_p1", reports), luma_p99=med("luma_p99", reports),
    )


@dataclass
class Issue:
    level: str      # ok | warn | bad
    area: str       # exposure, color, focus, light, framing, audio, file
    message: str
    fix: str = ""
    penalty: float = 0.0


def kelvin_after(kelvin: float, mired_error: float, strength: float = 1.0) -> int:
    """Kelvin setting that cancels a measured white-balance error."""
    new = 1e6 / (1e6 / kelvin + strength * mired_error)
    return int(round(min(max(new, 2500), 9900) / 100.0) * 100)


def assess(r: FrameReport, face_target: float = FACE_TARGET, vertical_output: bool = True) -> list[Issue]:
    """Turn measurements into plain-language findings."""
    out: list[Issue] = []
    if r.face is None:
        out.append(Issue("bad", "framing", "No face found in the shot.",
                         "Sit in your filming position, facing the camera.", 30))
    else:
        e = r.exposure_stops(face_target)
        if abs(e) <= 1 / 3:
            out.append(Issue("ok", "exposure", "Face exposure is right."))
        else:
            word = "dark" if e > 0 else "bright"
            fix = (f"Add about {abs(e):.1f} stop(s): roughly x{2 ** abs(e):.1f} ISO, or more light on your face."
                   if e > 0 else
                   f"Remove about {abs(e):.1f} stop(s): roughly /{2 ** abs(e):.1f} ISO, close the aperture a little, or an ND filter.")
            level = "warn" if abs(e) <= 2 / 3 else "bad"
            out.append(Issue(level, "exposure", f"Face is {abs(e):.1f} stop(s) too {word}.", fix,
                             8 if level == "warn" else min(35, 15 * abs(e))))
        if r.face_clipped > 0.02:
            out.append(Issue("bad", "exposure", f"{r.face_clipped:.0%} of your face is blown out (shiny or over-lit).",
                             "Lower exposure, soften/move the key light, or use matte powder.", 15))
        if r.sharpness < 40:
            out.append(Issue("bad", "focus", "Face looks soft / out of focus.",
                             "Use AF-C with Eye AF (Human), check the focus area, avoid f/1.4-f/2 when moving.", 20))
        elif r.sharpness < 80:
            out.append(Issue("warn", "focus", "Face is slightly soft.",
                             "Check Eye AF is on and locked to your eye; stop down to f/2.8-f/4.", 8))
        if r.face_side_stops is not None and abs(r.face_side_stops) > 1.5:
            side = "right" if r.face_side_stops > 0 else "left"
            out.append(Issue("warn", "light",
                             f"The {side} side of your face (as seen on screen) is {abs(r.face_side_stops):.1f} stops darker.",
                             "Add a fill light or a white reflector on that side, or turn a little toward the light.", 5))
        if r.background_luma is not None and r.face_luma:
            bg = GAMMA * math.log2(max(r.background_luma, 1e-3) / max(r.face_luma, 1e-3))
            if bg > 1.0:
                out.append(Issue("warn", "light", f"Background is {bg:.1f} stops brighter than your face.",
                                 "Avoid sitting with a window behind you; light your face or close the blinds.", 6))
        if r.face_height is not None:
            if r.face_height < 0.12:
                out.append(Issue("warn", "framing", "You look small in the frame.",
                                 "Move the camera closer or zoom in (face about 20-30% of frame height).", 5))
            elif r.face_height > 0.5:
                out.append(Issue("warn", "framing", "Framing is very tight.", "Move the camera back a little.", 5))
        if r.eye_y is not None:
            if r.eye_y > 0.5:
                out.append(Issue("warn", "framing", "Your eyes are low in the frame.",
                                 "Tilt the camera down slightly so your eyes sit about a third from the top.", 4))
            elif r.eye_y < 0.18:
                out.append(Issue("warn", "framing", "Your head is too close to the top edge.",
                                 "Tilt the camera up slightly.", 4))
        if vertical_output and r.face_cx is not None and r.width > r.height:
            half = (r.height * 9 / 16) / r.width / 2
            if r.face_cx < half or r.face_cx > 1 - half:
                out.append(Issue("warn", "framing", "You are near the edge; a 9:16 crop can't centre you.",
                                 "Sit nearer the middle of the frame.", 5))

    m = r.wb_mired_error
    weak = r.wb_source == "estimate"
    limit = 30 if weak else 12
    if abs(m) <= limit:
        out.append(Issue("ok", "color", "White balance looks right."))
    else:
        word = "warm/orange" if m > 0 else "cool/blue"
        level = "bad" if abs(m) > 30 and not weak else "warn"
        out.append(Issue(level, "color", f"Image is too {word}{' (estimate - no white surface in shot)' if weak else ''}.",
                         f"If you used 5600K, try about {kelvin_after(5600, m)}K. Don't use Auto WB.",
                         min(20, abs(m) / 3) if level == "bad" else 6))
    if abs(r.wb_tint) > 0.06:
        word = "green" if r.wb_tint > 0 else "magenta"
        out.append(Issue("warn", "color", f"Image has a {word} tint (common with cheap LED/fluorescent light).",
                         f"In the WB fine-adjust grid, shift toward {'M' if word == 'green' else 'G'}, or use better lights.", 5))
    if r.frame_clipped > 0.08:
        out.append(Issue("warn", "exposure", f"{r.frame_clipped:.0%} of the frame is blown out (window or lamp?).",
                         "Keep bright windows/lamps out of the shot or reduce them.", 5))
    if r.crushed > 0.15:
        out.append(Issue("warn", "exposure", f"{r.crushed:.0%} of the frame is pure black.",
                         "Add some light to the background.", 5))
    if r.luma_p1 > 0.06 and r.luma_p99 < 0.8:
        out.append(Issue("warn", "color", "Picture looks flat/grey (S-Log or a flat profile?).",
                         "For ready-to-post clips use PP11 S-Cinetone instead of S-Log3.", 6))
    return out


def score(issues: list[Issue]) -> int:
    return int(max(0, round(100 - sum(i.penalty for i in issues))))
