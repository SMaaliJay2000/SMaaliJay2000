"""Convert a portrait + subject mask into ASCII art (light-on-dark)."""
import sys
import numpy as np
from PIL import Image, ImageFilter, ImageOps

photo_path, mask_path, out_path = sys.argv[1:4]
COLS = int(sys.argv[4]) if len(sys.argv) > 4 else 54
INVERT = len(sys.argv) > 5 and sys.argv[5] == "invert"  # dark ink on light background
CHAR_ASPECT = 0.52  # char width / line height used by the SVG

RAMP = " .,:;i1tfLCG08@"  # sparse -> dense

im = Image.open(photo_path).convert("L")
mask = Image.open(mask_path).convert("L")

# crop to head + shoulders
w, h = im.size
box = (int(w * 0.10), int(h * 0.03), int(w * 0.92), int(h * 0.88))
im, mask = im.crop(box), mask.crop(box)

rows = int(COLS * (im.size[1] / im.size[0]) * CHAR_ASPECT)
im = im.filter(ImageFilter.UnsharpMask(radius=6, percent=180, threshold=2))
im = im.resize((COLS, rows), Image.LANCZOS)
mask = mask.filter(ImageFilter.GaussianBlur(1.5)).resize((COLS, rows), Image.LANCZOS)

a = np.asarray(im, dtype=float) / 255.0
m = np.asarray(mask, dtype=float) / 255.0

# stretch contrast inside the subject only
inside = a[m > 0.5]
lo, hi = np.percentile(inside, 3), np.percentile(inside, 99)
a = np.clip((a - lo) / (hi - lo), 0, 1) ** 0.75
a = 0.22 + 0.78 * a  # keep dark hair visible
if INVERT:
    a = 1.22 - a

lines = []
for y in range(rows):
    row = ""
    for x in range(COLS):
        if m[y, x] < 0.45:
            row += " "
        else:
            row += RAMP[int(a[y, x] * (len(RAMP) - 1))]
    lines.append(row.rstrip())

open(out_path, "w").write("\n".join(lines) + "\n")
print(f"{COLS}x{rows}")
