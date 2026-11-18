"""Printable table cards: one A4 page per table.

Top half: the table card (table number + a QR code that opens the app with
that table already filled in). Bottom half: seat numbers 1..N to cut out
and hand to each person at the table.

    pip install qrcode
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
    svg = svg[svg.index("<svg"):]
    return svg.replace("<svg", '<svg class="qr"', 1)


def page(n: int, url: str, seats: int) -> str:
    link = f"{url}#table-{n}"
    color = SUITS[(n - 1) % len(SUITS)]
    seat_cells = "".join(
        f'<div class="seat"><span class="seat-num">{s}</span><span class="seat-t">طاولة {n}</span></div>'
        for s in range(1, seats + 1)
    )
    return f"""
<section class="sheet" style="--c:{color}">
  <div class="card">
    <div class="card-head">
      <span class="logo">كلمة وراها حكاية</span>
      <span class="table">طاولة {n}</span>
    </div>
    <div class="card-body">
      {qr_svg(link)}
      <ol class="steps">
        <li>امسحوا الرمز بكاميرا التلفون.</li>
        <li>اكتبوا اسمكم. رقم الطاولة بتعبّى لحاله.</li>
        <li>اختاروا الرقم اللي على ورقتكم.</li>
      </ol>
    </div>
    <p class="url">{html.escape(link)}</p>
  </div>
  <p class="cut-note">قصّوا الأرقام ووزّعوا رقم لكل مشارك. كل رقم على نفس الطاولة بتطلعله كلمة مختلفة.</p>
  <div class="seats">{seat_cells}</div>
</section>"""


def build(url: str, tables: int, seats: int) -> str:
    pages = "".join(page(n, url, seats) for n in range(1, tables + 1))
    return f"""<!doctype html>
<html lang="ar" dir="rtl"><head><meta charset="utf-8">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Aref+Ruqaa:wght@700&family=Lalezar&family=Readex+Pro:wght@400;600&display=swap">
<style>
@page {{ size: A4; margin: 0 }}
* {{ box-sizing: border-box }}
body {{ margin: 0; font-family: "Readex Pro", "Noto Sans Arabic", sans-serif; color: #14161E }}
.sheet {{ width: 210mm; height: 297mm; padding: 12mm; display: flex; flex-direction: column; gap: 6mm; page-break-after: always; overflow: hidden }}
.card {{ height: 150mm; border: 1.2mm solid var(--c); border-radius: 8mm; padding: 9mm 10mm; display: flex; flex-direction: column; gap: 5mm }}
.card-head {{ display: flex; justify-content: space-between; align-items: center }}
.logo {{ font-family: "Aref Ruqaa", serif; font-size: 13mm; line-height: 1.2 }}
.table {{ font-family: "Lalezar", sans-serif; font-size: 20mm; line-height: 1.1; color: #fff; background: var(--c); border-radius: 5mm; padding: 2mm 7mm 0 }}
.card-body {{ display: flex; align-items: center; gap: 9mm; flex: 1 }}
.qr {{ width: 78mm; height: 78mm; flex: none }}
.steps {{ margin: 0; padding-inline-start: 7mm; font-size: 5.6mm; line-height: 1.6; display: flex; flex-direction: column; gap: 3mm }}
.url {{ margin: 0; direction: ltr; text-align: left; font-size: 3.2mm; color: #596074 }}
.cut-note {{ margin: 0; font-size: 4mm; color: #596074; text-align: center }}
.seats {{ flex: 1; display: grid; grid-template-columns: repeat(4, 1fr); grid-auto-rows: 1fr; border-top: 0.4mm dashed #9AA1B5; border-inline-start: 0.4mm dashed #9AA1B5 }}
.seat {{ border-bottom: 0.4mm dashed #9AA1B5; border-inline-end: 0.4mm dashed #9AA1B5; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 1mm }}
.seat-num {{ font-family: "Lalezar", sans-serif; font-size: 30mm; line-height: 1; color: var(--c) }}
.seat-t {{ font-size: 4mm; color: #596074 }}
</style></head><body>{pages}</body></html>"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True, help="public link of the app, without #")
    ap.add_argument("--tables", type=int, default=25)
    ap.add_argument("--seats", type=int, default=8)
    a = ap.parse_args()
    url = a.url.split("#")[0]
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    html_path = out / "table-cards.html"
    html_path.write_text(build(url, a.tables, a.seats), encoding="utf-8")

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
    print(f"wrote {out / 'table-cards.pdf'} ({a.tables} tables, {a.seats} seats each)")


if __name__ == "__main__":
    main()
