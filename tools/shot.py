"""Capture headless (Edge) d'une URL et découpage en tranches lisibles.

Usage : python shot.py <url> <nom> [largeur=1366] [hauteur=4000] [tranche=1100]
Les images sont écrites dans le dossier SHOTS (variable d'env) ou ./shots.
"""
import os, subprocess, sys
from PIL import Image

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
url, name = sys.argv[1], sys.argv[2]
w, h, step = (int(x) for x in (sys.argv[3:] + ["1366", "4000", "1100"][len(sys.argv[3:]):]))
out = os.environ.get("SHOTS", "shots"); os.makedirs(out, exist_ok=True)
full = os.path.join(out, f"{name}.png")
subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--window-size={w},{h}",
                f"--screenshot={full}", url], capture_output=True, timeout=90)
img = Image.open(full)
# rogne le blanc sous le contenu
px = img.convert("RGB"); bottom = img.height
while bottom > 200 and px.getpixel((w // 2, bottom - 1)) == (255, 255, 255) and px.getpixel((10, bottom - 1)) == (255, 255, 255):
    bottom -= 20
for i, top in enumerate(range(0, bottom, step)):
    img.crop((0, top, w, min(top + step, bottom))).save(os.path.join(out, f"{name}-{i}.png"))
    print(os.path.join(out, f"{name}-{i}.png"))
