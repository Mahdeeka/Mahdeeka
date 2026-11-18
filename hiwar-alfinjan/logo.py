"""Harmony logo: line-art (green on paper, like the event poster) or solid badge."""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SRC = "inputs/logo.jpg"
GREEN = (12, 108, 71)          # brand green sampled from the logo


def _geom(a_cream):
    ys, xs = np.nonzero(a_cream > 0.5)
    cx, cy = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2
    r = max(xs.max() - xs.min(), ys.max() - ys.min()) / 2
    return cx, cy, r


def logo(size, style="line"):
    im = Image.open(SRC).convert("RGB")
    a = np.asarray(im, np.float32)
    lum = a @ np.array([0.299, 0.587, 0.114], np.float32)
    cream = np.clip((lum - 95) / (215 - 95), 0, 1)
    cx, cy, r = _geom(cream)
    pad = 14
    if style == "line":
        rgba = np.zeros((*cream.shape, 4), np.uint8)
        rgba[..., :3] = GREEN
        rgba[..., 3] = (cream * 255).astype(np.uint8)
        out = Image.fromarray(rgba, "RGBA")
        box = (int(cx - r - 2), int(cy - r - 2), int(cx + r + 3), int(cy + r + 3))
        out = out.crop(box)
    else:  # badge: green disc with a thin green rim outside the cream ring
        big = Image.new("RGB", (im.width + 2 * pad, im.height + 2 * pad), GREEN)
        big.paste(im, (pad, pad))
        S = 4
        m = Image.new("L", (big.width * S, big.height * S), 0)
        R = (r + 9) * S; X = (cx + pad) * S; Y = (cy + pad) * S
        ImageDraw.Draw(m).ellipse((X - R, Y - R, X + R, Y + R), fill=255)
        m = m.resize(big.size, Image.LANCZOS)
        out = big.convert("RGBA"); out.putalpha(m)
        out = out.crop(out.getchannel("A").getbbox())
    return out.resize((size, size), Image.LANCZOS)


def place(img, center, size, style="line"):
    lg = logo(size, style)
    if style == "badge":   # soft drop shadow so the badge sits on the paper
        sh = Image.new("RGBA", lg.size, (40, 28, 10, 0))
        sh.putalpha(lg.getchannel("A").filter(ImageFilter.GaussianBlur(6)).point(lambda v: v * 0.35))
        img.alpha_composite(sh, (int(center[0] - size / 2 + 2), int(center[1] - size / 2 + 5)))
    img.alpha_composite(lg, (int(center[0] - size / 2), int(center[1] - size / 2)))
