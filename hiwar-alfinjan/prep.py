"""Prepare real assets from the original posters (nothing is redrawn):
- cut the two speakers out of the flat beige background of the cover (real photo pixels only)
- lift the 'حوار الفنجان' and 'مركنتيل' logos off the beige as one-colour transparent PNGs
- Harmony logo (line style) from the kit
Outputs go to assets/.
"""
import os
import cv2
import numpy as np
from PIL import Image

import logo

os.makedirs("assets", exist_ok=True)
BG = np.array([242, 230, 218], np.float32)          # flat poster beige (sampled, exact)


def lab(a):
    return cv2.cvtColor(np.clip(a, 0, 255).astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32)


def bgdist(a):
    L = lab(a)
    b = lab(BG.reshape(1, 1, 3))[0, 0]
    return np.sqrt(((L - b) ** 2).sum(-1))


def cut_person(src, box, keep, name, grade=True):
    """box = crop in the cover; keep(x,y,rgb) -> bool mask of pixels allowed to belong to this person."""
    im = np.asarray(Image.open(src).convert("RGB"), np.float32)
    x0, y0, x1, y1 = box
    a = im[y0:y1, x0:x1].copy()
    d = bgdist(a)
    lowbg = (d < 9).astype(np.uint8)
    # background = beige region connected to the top row of the crop
    ff = np.zeros((a.shape[0] + 2, a.shape[1] + 2), np.uint8)
    reg = lowbg.copy() * 255
    for x in range(0, a.shape[1], 4):
        if reg[0, x] == 255:
            cv2.floodFill(reg, ff, (x, 0), 128)
    for y in range(0, a.shape[0], 4):           # also from the side edges
        for x in (0, a.shape[1] - 1):
            if reg[y, x] == 255:
                cv2.floodFill(reg, ff, (x, y), 128)
    bgmask = (reg == 128)
    fg = ~bgmask
    yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]]
    fg &= keep(xx + x0, yy + y0, a)
    fg = fg.astype(np.uint8)
    # keep only the big component(s) touching the bottom
    n, lbl, st, _ = cv2.connectedComponentsWithStats(fg, 8)
    keepl = [i for i in range(1, n) if st[i, cv2.CC_STAT_AREA] > 5000]
    fg = np.isin(lbl, keepl).astype(np.uint8)
    # soft edge: interior = 1, 2px band uses colour distance
    fg = cv2.erode(fg, np.ones((3, 3), np.uint8), iterations=1)   # drop the light halo left by the old cut-out
    inner = cv2.erode(fg, np.ones((3, 3), np.uint8), iterations=2)
    Lb = lab(BG.reshape(1, 1, 3))[0, 0, 0]
    soft = np.clip((d - 5) / 22, 0, 1) * (lab(a)[..., 0] < Lb + 2)
    alpha = np.where(inner > 0, 1.0, soft * fg)
    alpha = cv2.GaussianBlur(alpha.astype(np.float32), (0, 0), 0.7)
    alpha = np.clip(alpha, 0, 1) * (cv2.dilate(fg, np.ones((3, 3), np.uint8)) > 0)
    # decontaminate the beige from semi-transparent edge pixels
    A = alpha[..., None]
    F = np.where(A > 0.04, (a - (1 - A) * BG) / np.maximum(A, 0.04), a)
    F = np.clip(F, 0, 255)
    # edge colour extension: the outer ~4px take the colour of the solid interior next to them,
    # which removes the light halo the earlier cut-out left around the hair
    core = cv2.erode(fg, np.ones((3, 3), np.uint8), iterations=4).astype(np.float32)
    wsum = cv2.GaussianBlur(core, (0, 0), 2.5)
    csum = cv2.GaussianBlur(F * core[..., None], (0, 0), 2.5)
    ext = csum / np.maximum(wsum, 1e-4)[..., None]
    band = ((fg > 0) | (alpha > 0)) & (core == 0) & (wsum > 0.03)
    F = np.where(band[..., None], ext, F)
    # light specks a few px inside dark hair edges (left by the old cut-out): give them the hair colour
    core7 = cv2.erode(fg, np.ones((3, 3), np.uint8), iterations=8).astype(np.float32)
    w7 = cv2.GaussianBlur(core7, (0, 0), 4)
    ext7 = cv2.GaussianBlur(F * core7[..., None], (0, 0), 4) / np.maximum(w7, 1e-4)[..., None]
    lum = F.mean(-1); lum7 = ext7.mean(-1)
    speck = (fg > 0) & (core7 == 0) & (w7 > 0.02) & (lum7 < 95) & (lum > lum7 + 28)
    F = np.where(speck[..., None], ext7, F)
    # trim 3px off dark (hair) outlines only, then re-feather: the old cut-out's grey rim goes away
    dist = cv2.distanceTransform(fg, cv2.DIST_L2, 5)
    trim = (dist < 3.2) & (lum7 < 95) & (w7 > 0.02)
    alpha = np.where(trim, 0.0, alpha).astype(np.float32)
    alpha = np.minimum(alpha, cv2.GaussianBlur(alpha, (0, 0), 0.8) * 1.15)
    alpha = np.clip(alpha, 0, 1)
    if grade:   # very slight grade only: a touch less saturation, 4% toward warm cream
        g = F.mean(-1, keepdims=True)
        F = g + (F - g) * 0.95
        F = F * 0.96 + np.array([244, 236, 224], np.float32) * 0.04
    out = np.dstack([F, alpha * 255]).astype(np.uint8)[:-2]   # last row of the original is lighter: drop it
    Image.fromarray(out, "RGBA").save(f"assets/{name}.png")
    print(name, out.shape)


def is_red(rgb):
    return (rgb[..., 0] - rgb[..., 1] > 60) & (rgb[..., 0] > 120)


# Moderator (left, red shirt) and guest (right, dark jacket). They touch around x~550 at the bottom.
SEAM = 549
def is_dark(rgb):
    return rgb.sum(-1) < 330


cut_person("inputs/orig_1_cover.jpg", (0, 780, 600, 1350),
           lambda X, Y, rgb: (X < 552) & ~((X > 528) & is_dark(rgb)), "p_moataz")
cut_person("inputs/orig_1_cover.jpg", (500, 780, 1080, 1350),
           lambda X, Y, rgb: (X >= 546) & ~((X < 580) & is_red(rgb)), "p_hassan")


def lift_logo(src, box, name, ink, lo=10, hi=None):
    im = np.asarray(Image.open(src).convert("RGB"), np.float32)
    x0, y0, x1, y1 = box
    a = im[y0:y1, x0:x1]
    d = bgdist(a)
    full = bgdist(np.array(ink, np.float32).reshape(1, 1, 3))[0, 0] if hi is None else hi
    alpha = np.clip((d - lo) / (full * 0.85 - lo), 0, 1)
    rgba = np.zeros((*alpha.shape, 4), np.uint8)
    rgba[..., :3] = ink
    rgba[..., 3] = (alpha * 255).astype(np.uint8)
    out = Image.fromarray(rgba, "RGBA")
    out = out.crop(out.getchannel("A").point(lambda v: 255 if v > 20 else 0).getbbox())
    out.save(f"assets/{name}.png")
    print(name, out.size)


lift_logo("inputs/orig_1_cover.jpg", (690, 50, 1030, 260), "logo_finjan", (53, 97, 61))
lift_logo("inputs/orig_2_moderator.jpg", (820, 1190, 1020, 1285), "logo_mercantil", (69, 114, 73))

# Harmony logo: line art in brand green (same artwork as the original posters)
lg = logo.logo(600, "line")
lg.save("assets/logo_harmony.png")
print("logo_harmony", lg.size)
