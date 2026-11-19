"""Wrap app.html (the page body published as the Claude artifact) into a
standalone index.html that any static host can serve (GitHub Pages, Netlify).

    python build.py
"""
from pathlib import Path

HERE = Path(__file__).parent
body = (HERE / "app.html").read_text(encoding="utf-8")

head = (
    "<!doctype html>\n"
    '<html lang="ar" dir="rtl">\n<head>\n'
    '<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
    "<style>:root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);"
    "padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0;font-size:14px;"
    "font-family:system-ui,sans-serif}img{max-width:100%}"
    "[hidden]{display:none!important}</style>\n"
    "</head>\n<body>\n"
)
(HERE / "index.html").write_text(head + body + "\n</body>\n</html>\n", encoding="utf-8")
print("wrote index.html")
