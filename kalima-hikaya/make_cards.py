"""Printable table cards: one A5 card per table with that table's own QR code.

Scanning a table's QR opens the app with the table already filled in, so a
person only types their name and gets the next free number automatically.
Two cards per A4 page, cut along the dashed line. Also writes the general QR
(out/qr.png, out/qr.svg) for the projector or a poster.

    pip install qrcode pillow
    python make_cards.py --url https://mahdeeka.github.io/Mahdeeka/kalima-hikaya/ --tables 25

Writes out/table-cards.html and prints it to out/table-cards.pdf with headless
Chrome/Chromium (set CHROME=/path/to/chrome if it is not found).
"""
import argparse
import html
import io
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


def card(n: int, url: str) -> str:
    color = SUITS[(n - 1) % len(SUITS)]
    return f"""
  <div class="card" style="--c:{color}">
    <div class="col-info">
      <span class="logo">كلمة وراها حكاية</span>
      <div class="table"><span class="table-label">طاولة</span><span class="table-num">{n}</span></div>
      <ol class="steps">
        <li>امسحوا الرمز بكاميرا التلفون.</li>
        <li>اكتبوا اسمكم.</li>
        <li>خلص! رقمكم ودوركم بالحكي بيطلعوا لحالهم.</li>
      </ol>
      <p class="mgr">مدير الطاولة: امسح نفس الرمز واختار «مدير طاولة». إنت رقم 1.</p>
    </div>
    <div class="col-qr">{qr_svg(f"{url}#table-{n}")}<span class="scan">رمز طاولة {n}</span></div>
  </div>"""


def build(url: str, tables: int) -> str:
    cards = [card(n, url) for n in range(1, tables + 1)]
    sheets = "".join(f'<section class="sheet">{"".join(cards[i:i + 2])}</section>' for i in range(0, len(cards), 2))
    return f"""<!doctype html>
<html lang="ar" dir="rtl"><head><meta charset="utf-8">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Aref+Ruqaa:wght@700&family=Lalezar&family=Readex+Pro:wght@400;600;700&display=swap">
<style>
@page {{ size: A4; margin: 0 }}
* {{ box-sizing: border-box }}
body {{ margin: 0; font-family: "Readex Pro", "Noto Sans Arabic", sans-serif; color: #14161E }}
.sheet {{ width: 210mm; height: 297mm; display: grid; grid-template-rows: 1fr 1fr; page-break-after: always; overflow: hidden }}
.card {{ padding: 10mm 12mm; display: grid; grid-template-columns: 1fr 70mm; gap: 10mm; align-items: center; border-bottom: 0.4mm dashed #9AA1B5 }}
.card:last-child {{ border-bottom: 0 }}
.col-info {{ display: flex; flex-direction: column; gap: 3.5mm; min-width: 0 }}
.logo {{ font-family: "Aref Ruqaa", serif; font-size: 9mm; line-height: 1.2 }}
.table {{ display: flex; align-items: baseline; gap: 3mm; color: var(--c) }}
.table-label {{ font-family: "Lalezar", sans-serif; font-size: 12mm }}
.table-num {{ font-family: "Lalezar", sans-serif; font-size: 34mm; line-height: .9 }}
.steps {{ margin: 0; padding-inline-start: 6mm; font-size: 4.6mm; line-height: 1.5; display: flex; flex-direction: column; gap: 1.6mm }}
.mgr {{ margin: 0; font-size: 3.6mm; color: #596074 }}
.col-qr {{ display: flex; flex-direction: column; align-items: center; gap: 2.5mm }}
.col-qr svg {{ width: 70mm; height: 70mm }}
.scan {{ font-size: 4mm; font-weight: 700; color: var(--c) }}
</style></head><body>{sheets}</body></html>"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True, help="public link of the app, without #")
    ap.add_argument("--tables", type=int, default=25, help="number of tables (2 cards per A4 page)")
    ap.add_argument("--seats", type=int, default=8)
    a = ap.parse_args()
    url = a.url.split("#")[0]
    out = HERE / "out"
    out.mkdir(exist_ok=True)

    qrcode.make(url, border=2, box_size=24, error_correction=qrcode.constants.ERROR_CORRECT_M).save(out / "qr.png")
    (out / "qr.svg").write_text(qr_svg(url), encoding="utf-8")

    html_path = out / "table-cards.html"
    html_path.write_text(build(url, a.tables), encoding="utf-8")
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
    print(f"wrote {out / 'table-cards.pdf'} ({a.tables} tables, one QR per table, 2 per page), {out / 'qr.png'}, {out / 'qr.svg'}")


if __name__ == "__main__":
    main()
