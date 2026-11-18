"""Printable table card with ONE QR code for the whole room.

Every table gets the same card: the QR (the app's link), three steps, and a
seating diagram (the person facing the card is number 1, then clockwise).
Two identical A5 cards per A4 page: print one page per two tables and cut
along the dashed line.

Also writes the QR on its own (out/qr.png, out/qr.svg) for slides, posters
and invitations.

    pip install qrcode pillow
    python make_cards.py --url https://claude.ai/artifact/HF9xZzyCsDaFTbw6eo41fK

Writes out/table-cards.html and prints it to out/table-cards.pdf with headless
Chrome/Chromium (set CHROME=/path/to/chrome if it is not found).
"""
import argparse
import html
import io
import math
import os
import shutil
import subprocess
from pathlib import Path

import qrcode
import qrcode.image.svg

HERE = Path(__file__).parent
SUITS = ["#2D4AA3", "#2A7A5C", "#A2650E", "#AD3E29", "#723788"]


def qr_svg(data: str) -> str:
    img = qrcode.make(data, image_factory=qrcode.image.svg.SvgPathImage, border=2,
                      error_correction=qrcode.constants.ERROR_CORRECT_M)
    buf = io.BytesIO()
    img.save(buf)
    svg = buf.getvalue().decode("utf-8")
    return svg[svg.index("<svg"):]


def seating_svg(seats: int, color: str) -> str:
    """Round table seen from above: the card sits at the top edge, seat 1 faces it, then clockwise."""
    parts = [f'<svg class="seating" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">',
             f'<circle cx="60" cy="60" r="30" fill="{color}" fill-opacity=".12" stroke="{color}" stroke-width="1.4"/>',
             f'<rect x="49" y="33" width="22" height="11" rx="2" fill="{color}"/>',
             '<text x="60" y="41" text-anchor="middle" font-size="6.4" fill="#fff" font-family="Readex Pro, sans-serif">الكرت</text>']
    for i in range(seats):
        a = math.radians(-90 + i * 360 / seats)
        x, y = 60 + 45 * math.cos(a), 60 + 45 * math.sin(a)
        fill, ink = (color, "#fff") if i == 0 else ("#fff", color)
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="9" fill="{fill}" stroke="{color}" stroke-width="1.4"/>')
        parts.append(f'<text x="{x:.1f}" y="{y + 3.6:.1f}" text-anchor="middle" font-size="10" font-weight="700" '
                     f'fill="{ink}" font-family="Readex Pro, sans-serif">{i + 1}</text>')
    # clockwise arrow between seat 1 and seat 2
    parts.append(f'<path d="M72 13 A47 47 0 0 1 88 20" fill="none" stroke="{color}" stroke-width="1.4" '
                 f'marker-end="url(#ah{color[1:]})"/>')
    parts.append(f'<defs><marker id="ah{color[1:]}" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto">'
                 f'<path d="M0 0L6 3L0 6z" fill="{color}"/></marker></defs>')
    parts.append("</svg>")
    return "".join(parts)


def card(qr: str, seats: int, color: str) -> str:
    return f"""
  <div class="card" style="--c:{color}">
    <div class="col-info">
      <span class="logo">كلمة وراها حكاية</span>
      <ol class="steps">
        <li>امسحوا الرمز بكاميرا التلفون.</li>
        <li>اكتبوا اسمكم.</li>
        <li>اختاروا رقمكم حسب مكانكم: اللي قدّام هالكرت <b>رقم 1</b>، وبعده مع عقارب الساعة.</li>
      </ol>
    </div>
    <div class="col-qr">{qr}<span class="scan">امسحوا الرمز</span></div>
    <div class="col-seat">{seating_svg(seats, color)}</div>
  </div>"""


def build(url: str, pages: int, seats: int) -> str:
    qr = qr_svg(url)
    color = SUITS[0]
    sheet = f'<section class="sheet">{card(qr, seats, color)}{card(qr, seats, color)}</section>'
    return f"""<!doctype html>
<html lang="ar" dir="rtl"><head><meta charset="utf-8">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Aref+Ruqaa:wght@700&family=Lalezar&family=Readex+Pro:wght@400;600;700&display=swap">
<style>
@page {{ size: A4; margin: 0 }}
* {{ box-sizing: border-box }}
body {{ margin: 0; font-family: "Readex Pro", "Noto Sans Arabic", sans-serif; color: #14161E }}
.sheet {{ width: 210mm; height: 297mm; display: grid; grid-template-rows: 1fr 1fr; page-break-after: always; overflow: hidden }}
.card {{ padding: 10mm; display: grid; grid-template-columns: 1fr 58mm 52mm; gap: 6mm; align-items: center; border-bottom: 0.4mm dashed #9AA1B5 }}
.card:last-child {{ border-bottom: 0 }}
.col-info {{ display: flex; flex-direction: column; gap: 6mm; min-width: 0 }}
.logo {{ font-family: "Aref Ruqaa", serif; font-size: 13mm; line-height: 1.25; color: var(--c) }}
.steps {{ margin: 0; padding-inline-start: 6mm; font-size: 4.6mm; line-height: 1.55; display: flex; flex-direction: column; gap: 2mm }}
.steps b {{ color: var(--c) }}
.col-qr {{ display: flex; flex-direction: column; align-items: center; gap: 2mm }}
.col-qr svg {{ width: 58mm; height: 58mm }}
.scan {{ font-size: 4mm; font-weight: 600 }}
.seating {{ width: 52mm; height: 52mm }}
</style></head><body>{sheet * pages}</body></html>"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True, help="public link of the app, without #")
    ap.add_argument("--pages", type=int, default=1, help="pages in the PDF (2 identical cards per page)")
    ap.add_argument("--seats", type=int, default=8)
    a = ap.parse_args()
    url = a.url.split("#")[0]
    out = HERE / "out"
    out.mkdir(exist_ok=True)

    qrcode.make(url, border=2, box_size=24, error_correction=qrcode.constants.ERROR_CORRECT_M).save(out / "qr.png")
    (out / "qr.svg").write_text(qr_svg(url), encoding="utf-8")

    html_path = out / "table-cards.html"
    html_path.write_text(build(url, a.pages, a.seats), encoding="utf-8")
    chrome = os.environ.get("CHROME") or next(
        (c for c in ("/opt/pw-browsers/chromium", shutil.which("chromium"), shutil.which("google-chrome"),
                     shutil.which("chromium-browser"),
                     "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome") if c and Path(c).exists()),
        None)
    if not chrome:
        raise SystemExit(f"Chrome not found. Open {html_path} in a browser and print it to PDF (A4, no margins).")
    subprocess.run([chrome, "--headless", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
                    "--virtual-time-budget=20000", f"--print-to-pdf={out / 'table-cards.pdf'}",
                    html_path.resolve().as_uri()], check=True, capture_output=True)
    print(f"wrote {out / 'table-cards.pdf'} ({a.pages} page(s), 2 identical cards each), {out / 'qr.png'}, {out / 'qr.svg'}")


if __name__ == "__main__":
    main()
