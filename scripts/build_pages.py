"""
Builds the publishable pages:
  dashboards/students/index.src.html  (body-only, for preview)
  dashboards/<name>/index.html        (full documents for GitHub Pages)
  index.html                          (landing page linking both dashboards)
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
gtm_src = (ROOT / "dashboards/gtm/index.src.html").read_text()
style = gtm_src[gtm_src.index("<style>"): gtm_src.index("</style>") + len("</style>")]
part = (ROOT / "dashboards/students/page.part.html").read_text()
(ROOT / "dashboards/students/index.src.html").write_text(part.replace("<!--GTM_STYLE-->", style, 1))


def full(src):
    head_end = src.index('\n<div class="wrap">')
    return ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            + src[:head_end].replace("<style>", "<style>\nbody{margin:0}", 1)
            + "\n</head>\n<body>" + src[head_end:] + "\n</body>\n</html>\n")


for name in ("gtm", "students"):
    src = (ROOT / f"dashboards/{name}/index.src.html").read_text()
    (ROOT / f"dashboards/{name}/index.html").write_text(full(src))
print("built dashboards/gtm/index.html and dashboards/students/index.html")
