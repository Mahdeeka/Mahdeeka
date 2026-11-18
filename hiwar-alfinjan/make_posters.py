"""حوار الفنجان · PROFESSIONALS — redesigned 3-slide carousel (cover, moderator, guest), 1080x1350.

Layers: cream paper (code noise) -> geometric star lattice (SVG) -> logos (lifted from the originals,
never redrawn) -> green arches with the REAL photos (cut out, only scaled + very slight grade) ->
typed Arabic text (Chrome shapes it) -> icons (inline SVG).
Run:  python prep.py  (once)  then  python make_posters.py   -> out/01_cover.png, 02_moderator.png, 03_guest.png
"""
import os
import subprocess

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
CHROME = "/usr/bin/google-chrome"
W, H = 1080, 1350
os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
os.makedirs(os.path.join(HERE, "work"), exist_ok=True)


# ---------------------------------------------------------------- paper
def make_paper():
    p = os.path.join(HERE, "assets/paper.png")
    rnd = np.random.default_rng(7)
    base = np.array([243, 235, 222], np.float32)
    low = rnd.normal(0, 1, (H // 30 + 2, W // 30 + 2)).astype(np.float32)
    low = np.asarray(Image.fromarray(low).resize((W, H), Image.BICUBIC), np.float32)
    grain = rnd.normal(0, 1, (H, W)).astype(np.float32)
    yy, xx = np.mgrid[0:H, 0:W]
    vig = 1 - 0.035 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    img = base[None, None, :] * vig[..., None] + (low * 2.2 + grain * 2.0)[..., None]
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(p)


# ---------------------------------------------------------------- icons (24x24, stroke)
def ic(paths, cls="ic"):
    return (f'<svg class="{cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
            f'stroke-linecap="round" stroke-linejoin="round">{paths}</svg>')


I = {
    "cal": '<rect x="3" y="4.5" width="18" height="16.5" rx="2.5"/><path d="M3 9.5h18M8 2.5v4M16 2.5v4"/>'
           '<path d="M7.5 13.5h.01M12 13.5h.01M16.5 13.5h.01M7.5 17h.01M12 17h.01"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.2 2"/>',
    "pin": '<path d="M12 21.5s-7-6.2-7-12a7 7 0 0 1 14 0c0 5.8-7 12-7 12z"/><circle cx="12" cy="9.5" r="2.6"/>',
    "cup": '<path d="M4 10h12v4.5A5.5 5.5 0 0 1 10.5 20h-1A5.5 5.5 0 0 1 4 14.5z"/><path d="M16 11h1.6a2.6 2.6 0 0 1 0 5.2H15.5"/>'
           '<path d="M8 3.5c-.8 1 .8 1.8 0 3M12 3.5c-.8 1 .8 1.8 0 3"/>',
    "mic": '<rect x="9" y="2.5" width="6" height="11" rx="3"/><path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21M8.5 21h7"/>',
    "landmark": '<path d="M3 21h18M5 18V10.5M9.5 18V10.5M14.5 18V10.5M19 18V10.5M2.5 10.5h19L12 4z"/>',
    "chart": '<path d="M3.5 3.5v17h17"/><path d="M7.5 15l4-4.2 3 3 5.5-6.3"/><path d="M15.5 7.5H20V12"/>',
    "building": '<path d="M4 21V5.5A1.5 1.5 0 0 1 5.5 4h7A1.5 1.5 0 0 1 14 5.5V21M14 10h4.5A1.5 1.5 0 0 1 20 11.5V21M2.5 21h19"/>'
                '<path d="M7.5 8h3M7.5 12h3M7.5 16h3M16.5 14h.01M16.5 17.5h.01"/>',
    "rocket": '<path d="M5 15.5c-1.6 1-2.3 3.6-2.3 5.8 2.2 0 4.8-.7 5.8-2.3"/><path d="M14.5 4.5c2-1.3 4.4-1.9 6.8-1.8.1 2.4-.5 4.8-1.8 6.8L13 16l-5-5z"/>'
              '<path d="M8 11H4.5L7 8h4.5M13 16v3.5L16 17v-4.5"/><circle cx="16.3" cy="7.7" r="1.4"/>',
    "users": '<circle cx="9" cy="8" r="3.6"/><path d="M2.5 20.5v-1.2A4.8 4.8 0 0 1 7.3 14.5h3.4a4.8 4.8 0 0 1 4.8 4.8v1.2"/>'
             '<path d="M16 4.6a3.6 3.6 0 0 1 0 6.8M18.5 14.7a4.8 4.8 0 0 1 3 4.6v1.2"/>',
    "cap": '<path d="M22 9.5 12 4.5 2 9.5l10 5 10-5z"/><path d="M6 11.5v5c3.4 2.6 8.6 2.6 12 0v-5M22 9.5v5.5"/>',
    "award": '<circle cx="12" cy="9" r="6"/><path d="m12 6.2 1 2 2.2.3-1.6 1.5.4 2.2-2-1-2 1 .4-2.2-1.6-1.5 2.2-.3z"/>'
             '<path d="M8.5 14 7 21.5l5-2.8 5 2.8-1.5-7.5"/>',
    "scale": '<path d="M12 3.5v17M7.5 20.5h9M4.5 7h15M12 3.5v3.5"/><path d="M4.5 7 2 13.2a2.6 2.6 0 0 0 5 0L4.5 7zM19.5 7 17 13.2a2.6 2.6 0 0 0 5 0L19.5 7z"/>',
    "hourglass": '<path d="M6 2.5h12M6 21.5h12M7 2.5c0 5 5 6 5 9.5s-5 4.5-5 9.5M17 2.5c0 5-5 6-5 9.5s5 4.5 5 9.5"/>',
}


# ---------------------------------------------------------------- geometric lattice (8-point stars)
def lattice(cid, t=64, color="#B8975A", sw=1.15):
    r = t / 2
    k = r / 2 ** 0.5
    c = t / 2
    sq1 = f"M{c},{c - r} L{c + r},{c} L{c},{c + r} L{c - r},{c} Z"
    sq2 = f"M{c - k},{c - k} L{c + k},{c - k} L{c + k},{c + k} L{c - k},{c + k} Z"
    oct_ = "M" + " L".join(f"{c + r * 0.42 * np.cos(np.pi / 8 + i * np.pi / 4):.2f},{c + r * 0.42 * np.sin(np.pi / 8 + i * np.pi / 4):.2f}" for i in range(8)) + " Z"
    return (f'<pattern id="{cid}" width="{t}" height="{t}" patternUnits="userSpaceOnUse">'
            f'<path d="{sq1} {sq2} {oct_}" fill="none" stroke="{color}" stroke-width="{sw}"/>'
            f'<circle cx="0" cy="0" r="{t * 0.07:.1f}" fill="none" stroke="{color}" stroke-width="{sw}"/>'
            f'<circle cx="{t}" cy="0" r="{t * 0.07:.1f}" fill="none" stroke="{color}" stroke-width="{sw}"/>'
            f'<circle cx="0" cy="{t}" r="{t * 0.07:.1f}" fill="none" stroke="{color}" stroke-width="{sw}"/>'
            f'<circle cx="{t}" cy="{t}" r="{t * 0.07:.1f}" fill="none" stroke="{color}" stroke-width="{sw}"/></pattern>')


def corner_pattern():
    """Faded star lattice in the top-left corner (as in the series' original look)."""
    return f'''<svg class="cpat" width="{W}" height="760" viewBox="0 0 {W} 760">
<defs>{lattice("lp", 66, "#A88D5C", 1.1)}
<radialGradient id="fade" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(0 0) scale(700 600)">
<stop offset="0" stop-color="#fff" stop-opacity=".95"/><stop offset=".55" stop-color="#fff" stop-opacity=".45"/>
<stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>
<mask id="m"><rect width="{W}" height="760" fill="url(#fade)"/></mask></defs>
<rect width="{W}" height="760" fill="url(#lp)" mask="url(#m)" opacity=".42"/></svg>'''


# ---------------------------------------------------------------- arch with real photo
PHOTO = {   # asset, face centre x inside the asset, asset height (bottom row = original poster bottom)
    "moataz": ("assets/p_moataz.png", 262, 568),
    "hassan": ("assets/p_hassan.png", 265, 568),
}


def arch(x, y, w, h, who, scale, face_dx=0):
    src, fx, ah = PHOTO[who]
    r = w / 2
    ph = ah * scale
    left = w / 2 - fx * scale + face_dx
    top = h - ph + 3
    return f'''<div class="arch" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px;border-radius:{r}px {r}px 0 0">
  <svg class="apat" width="{w}" height="{h}"><defs>{lattice("ap" + who, 58, "#D9BC7E", 1)}</defs>
    <rect width="{w}" height="{h}" fill="url(#ap{who})"/></svg>
  <div class="glow"></div>
  <img class="person" src="{src}" style="left:{left:.1f}px;top:{top:.1f}px;height:{ph:.1f}px">
  <div class="aline" style="border-radius:{r - 14}px {r - 14}px 0 0"></div>
</div>'''


CSS = """
@font-face{font-family:Taj;src:url(fonts/Tajawal-Medium.ttf);font-weight:500}
@font-face{font-family:Taj;src:url(fonts/Tajawal-Bold.ttf);font-weight:700}
@font-face{font-family:Taj;src:url(fonts/Tajawal-ExtraBold.ttf);font-weight:800}
@font-face{font-family:Taj;src:url(fonts/Tajawal-Black.ttf);font-weight:900}
@font-face{font-family:Mont;src:url(fonts/Montserrat.ttf)}
:root{--ink:#173D2A;--green:#1F4B34;--deep:#12301F;--gold:#B8975A;--gold2:#8C6A2F;--goldl:#E2C27E;--cream:#FAF4E8}
*{box-sizing:border-box}
html,body{margin:0;width:1080px;height:1350px;overflow:hidden}
body{position:relative;background:#F3EBDE url(assets/paper.png);font-family:Taj;direction:rtl;color:var(--ink)}
.cpat{position:absolute;left:0;top:0}
.lg-h{position:absolute;left:58px;top:46px;width:150px;height:150px}
.lg-f{position:absolute;right:58px;top:50px;width:248px}
.ic{width:1em;height:1em;flex:none}
/* arch */
.arch{position:absolute;overflow:hidden;background:linear-gradient(180deg,#24563C 0%,#1C4630 55%,#143523 100%);
  box-shadow:0 18px 40px rgba(40,30,12,.22)}
.apat{position:absolute;left:0;top:0;opacity:.13}
.glow{position:absolute;inset:0;background:radial-gradient(ellipse 60% 42% at 50% 46%,rgba(226,194,126,.30),rgba(226,194,126,0) 70%)}
.person{position:absolute;max-width:none}
.aline{position:absolute;left:14px;right:14px;top:14px;bottom:-4px;border:2px solid rgba(214,180,112,.85);border-bottom:0}
/* shared bits */
.g{color:var(--gold2)}
.rule{position:absolute;height:2px;background:linear-gradient(90deg,rgba(184,151,90,0),#B8975A 18%,#B8975A 82%,rgba(184,151,90,0))}
.diamond{display:inline-block;width:11px;height:11px;background:var(--gold);transform:rotate(45deg);flex:none}
"""


def page(body, extra_css=""):
    return f"""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><style>{CSS}{extra_css}</style></head>
<body>{corner_pattern()}<img class="lg-h" src="assets/logo_harmony.png"><img class="lg-f" src="assets/logo_finjan.png">
{body}</body></html>"""


def render(name, html):
    hp = os.path.join(HERE, f"work/_{name}.html")
    # the html sits in work/, assets are one level up: rewrite relative urls
    html = html.replace("src=\"assets/", "src=\"../assets/").replace("url(assets/", "url(../assets/").replace("url(fonts/", "url(../fonts/")
    open(hp, "w", encoding="utf-8").write(html)
    big = os.path.join(HERE, f"work/_{name}@2x.png")
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files",
                    "--force-device-scale-factor=2", f"--window-size={W},{H}", f"--screenshot={big}",
                    "--virtual-time-budget=3000", "file://" + hp], capture_output=True, check=True)
    im = Image.open(big).convert("RGB")
    assert im.size == (W * 2, H * 2), im.size
    out = os.path.join(HERE, f"out/{name}.png")
    im.resize((W, H), Image.LANCZOS).save(out, optimize=True)
    print("wrote", out)


# ================================================================= 01 cover
COVER_CSS = """
.t1{position:absolute;top:262px;left:0;width:1080px;text-align:center;font:900 72px/1.1 Taj;letter-spacing:-.3px}
.t2{position:absolute;top:366px;left:0;width:1080px;display:flex;justify-content:center;align-items:center;gap:26px;
  font:700 48px/1.2 Taj;color:var(--ink)}
.t2 .ln{width:70px;height:2px;background:var(--gold)}
.info{position:absolute;top:478px;left:50%;transform:translateX(-50%);display:flex;align-items:center;gap:30px;
  background:var(--green);color:var(--cream);padding:16px 40px 14px;border-radius:60px;font:800 36px/1 Taj;white-space:nowrap;
  box-shadow:0 10px 22px rgba(30,40,20,.22)}
.info .it{display:flex;align-items:center;gap:13px}
.info .ic{color:var(--goldl);font-size:38px}
.info .sm{font-weight:700;font-size:28px;color:#EADBB8;margin-right:-4px}
.info .sep{width:7px;height:7px;background:var(--goldl);transform:rotate(45deg);opacity:.9}
.plate{position:absolute;width:384px;text-align:center;background:var(--cream);padding:16px 10px 14px;border-radius:16px;
  box-shadow:0 12px 26px rgba(20,30,15,.35);outline:1.5px solid var(--gold);outline-offset:-8px}
.plate b{display:block;font:900 41px/1.15 Taj;color:var(--ink)}
.plate span{display:flex;justify-content:center;align-items:center;gap:10px;margin-top:4px;font:800 26px/1.2 Taj;color:var(--gold2)}
.plate .ic{font-size:27px}
"""


def cover():
    body = f"""
<div class="t1">من القطاع <span class="g">العام</span> إلى <span class="g">الخاص</span>،</div>
<div class="t2"><span class="ln"></span>وما بين التنفيذ والاستشارة<span class="ln"></span></div>
<div class="info">
  <span class="it">{ic(I['cal'])}السبت</span><i class="sep"></i>
  <span class="it">{ic(I['clock'])}4:45 <span class="sm">مساءً</span></span><i class="sep"></i>
  <span class="it">{ic(I['pin'])}الناصرة</span>
</div>
{arch(560, 616, 470, 734, "hassan", 1.13)}
{arch(50, 616, 470, 734, "moataz", 1.13)}
<div class="plate" style="left:603px;top:1196px"><b>حسان طوافرة</b><span>{ic(I['cup'])}ضيف الفنجان</span></div>
<div class="plate" style="left:93px;top:1196px"><b>معتز استيتي</b><span>{ic(I['mic'])}المحاور</span></div>
"""
    render("01_cover", page(body, COVER_CSS))


# ================================================================= bio slides
BIO_CSS = """
.col{position:absolute;right:56px;width:552px;display:flex;flex-direction:column;align-items:stretch}
.col .chip{align-self:flex-start}
.col .rule{position:static;margin:30px 0 32px}
.chip{display:inline-flex;align-items:center;gap:11px;background:var(--green);color:var(--cream);font:800 29px/1 Taj;
  padding:12px 24px 10px;border-radius:40px}
.chip .ic{font-size:30px;color:var(--goldl)}
.name{font:900 94px/1.05 Taj;margin-top:20px;letter-spacing:-.5px;white-space:nowrap}
.role{font:800 35px/1.3 Taj;margin-top:16px;color:var(--ink)}
.role2{font:700 30px/1.3 Taj;margin-top:4px;color:var(--gold2)}
.rows{display:flex;flex-direction:column;gap:24px}
.boxes{margin-top:36px}
.row{display:flex;align-items:flex-start;gap:20px}
.bub{width:58px;height:58px;border-radius:50%;background:var(--green);color:var(--goldl);display:flex;align-items:center;justify-content:center;
  font-size:31px;flex:none;box-shadow:0 0 0 4px #F3EBDE,0 0 0 5.5px rgba(184,151,90,.7)}
.row p{margin:0;font:700 31px/1.38 Taj;color:var(--ink);padding-top:6px}
.row p small{display:block;font:700 25px/1.35 Taj;color:var(--gold2);margin-top:4px}
.row p em{font-style:normal;color:var(--gold2)}
.boxes{display:flex;gap:18px}
.box{flex:1;background:var(--cream);border-radius:18px;padding:20px 20px 18px;text-align:center;
  box-shadow:0 10px 24px rgba(60,45,15,.10);outline:1.5px solid rgba(184,151,90,.9);outline-offset:-7px}
.box .v{font:900 42px/1.1 Taj;color:var(--green);display:flex;align-items:center;justify-content:center;gap:10px;white-space:nowrap}
.box .v .ic{font-size:34px;color:var(--gold2)}
.box .l{font:700 24px/1.35 Taj;color:var(--gold2);margin-top:8px}
.foot{position:absolute;right:56px;width:552px;bottom:40px;height:64px;display:flex;align-items:center;justify-content:space-between}
.foot .merc{width:150px}
.foot .ev{display:flex;align-items:center;gap:14px;font:800 25px/1 Taj;color:var(--ink);border:1.5px solid rgba(184,151,90,.9);
  border-radius:40px;padding:12px 24px 10px;white-space:nowrap}
.foot .ev i{width:6px;height:6px;background:var(--gold);transform:rotate(45deg)}
"""


def bio(name, chip_icon, chip, person, role, role2, rows, boxes, who, face_dx=0):
    rows_html = "".join(f'<div class="row"><span class="bub">{ic(I[k])}</span><p>{t}</p></div>' for k, t in rows)
    boxes_html = "".join(f'<div class="box"><div class="v">{v}</div><div class="l">{l}</div></div>' for v, l in boxes)
    r2 = f'<div class="role2">{role2}</div>' if role2 else ""
    body = f"""
<div class="col" id="col" style="top:250px">
  <span class="chip">{ic(I[chip_icon])}{chip}</span>
  <div class="name">{person}</div>
  <div class="role">{role}</div>{r2}
  <div class="rule"></div>
  <div class="rows">{rows_html}</div>
  <div class="boxes">{boxes_html}</div>
</div>
{arch(44, 520, 396, 830, who, 1.2, face_dx)}
<div class="foot"><img class="merc" src="assets/logo_mercantil.png">
  <div class="ev"><span>السبت</span><i></i><span>4:45 مساءً</span><i></i><span>الناصرة</span></div></div>
"""
    render(name, page(body, BIO_CSS))


def moderator():
    bio("02_moderator", "mic", "المحاور", "معتز استيتي",
        "مستشار قانوني في شركة HAAT", None,
        [("scale", "متخصص في القانون التجاري والتكنولوجيا وحماية الخصوصية"),
         ("rocket", "مستشار قانوني سابق في شركات ناشئة، منها <em>Glassbox</em>"),
         ("users", "عضو ومدير العمليات <em>(COO)</em><br>في مجتمع هارموني")],
        [(f"{ic(I['cap'])}لقب أول", "القانون<br>جامعة تل أبيب"),
         (f"{ic(I['cap'])}لقب ثانٍ", "القانون والتكنولوجيا<br>جامعة رايخمان")],
        "moataz", face_dx=-28)


def guest():
    bio("03_guest", "cup", "ضيف الفنجان", "حسان طوافرة",
        "شريك مؤسس ومدير تنفيذي",
        "Maximize للاستشارات الاستراتيجية",
        [("landmark", "مدير عام سابق لسلطة التطوير الاقتصادي في المجتمع العربي"),
         ("chart", "قاد خططًا حكومية<br>بعشرات مليارات الشواكل<small>التعليم · البنى التحتية · التشغيل · البيئة</small>"),
         ("building", "نائب مدير سابق<br>لسلطة الشركات الحكومية")],
        [("13 عامًا", "في مناصب رفيعة<br>بالقطاع العام"),
         ("40 تحت 40", "قائمة صحيفة<br>ذا ماركر")],
        "hassan")


if __name__ == "__main__":
    make_paper()
    cover()
    moderator()
    guest()
