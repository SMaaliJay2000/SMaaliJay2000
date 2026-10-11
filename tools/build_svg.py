"""Render dark_mode.svg and light_mode.svg from config.json, stats.json and assets/ascii.txt."""
import json
from datetime import date
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
cfg = json.loads((ROOT / "config.json").read_text())
stats_path = ROOT / "stats.json"
stats = json.loads(stats_path.read_text()) if stats_path.exists() else {}
ARTS = {
    "dark": (ROOT / "assets" / "ascii.txt").read_text().splitlines(),
    "light": (ROOT / "assets" / "ascii_light.txt").read_text().splitlines(),
}

# ---------- layout ----------
W, H = 1000, 590
ART_X, ART_Y = 22, 34
ART_FS, ART_CW, ART_LH = 10.0, 6.0, 11.6          # font size, char width, line height
INFO_X, INFO_R = 470, 975                          # left / right edge of info panel
INFO_FS, INFO_LH = 14, 21.5

THEMES = {
    "dark": dict(bg="#0d1117", art="#c9d1d9", key="#ffa657", val="#79c0ff",
                 head="#c9d1d9", rule="#30363d", add="#3fb950", dele="#f85149", border="#30363d"),
    "light": dict(bg="#ffffff", art="#24292f", key="#953800", val="#0550ae",
                  head="#24292f", rule="#d0d7de", add="#1a7f37", dele="#cf222e", border="#d0d7de"),
}


def age(born: date, today: date) -> str:
    y, m, d = today.year - born.year, today.month - born.month, today.day - born.day
    if d < 0:
        m -= 1
        prev_month_end = date(today.year, today.month, 1).toordinal() - 1
        d += date.fromordinal(prev_month_end).day
    if m < 0:
        y, m = y - 1, m + 12
    s = lambda n, w: f"{n} {w}{'' if n == 1 else 's'}"
    return f"{s(y, 'year')}, {s(m, 'month')}, {s(d, 'day')}"


def fmt(n):
    return "—" if n is None else f"{n:,}"


born = date.fromisoformat(cfg["birthday"])
uptime = age(born, date.today())


def build(theme: str) -> str:
    t = THEMES[theme]
    art = ARTS[theme]
    COLS = max(len(l) for l in art)
    out = []
    a = out.append
    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
      f'font-family="Consolas,\'DejaVu Sans Mono\',\'Courier New\',monospace">')
    a(f'<title>{escape(cfg["handle"])} — Maalitha Jayawardhana</title>')
    a(f'<rect width="{W}" height="{H}" rx="12" fill="{t["bg"]}" stroke="{t["border"]}"/>')

    # ASCII portrait: every line padded to COLS and locked to a fixed width
    # (spaces become NBSP so no renderer collapses the leading/inner whitespace)
    a(f'<g fill="{t["art"]}" font-size="{ART_FS}">')
    for i, line in enumerate(art):
        y = ART_Y + i * ART_LH
        a(f'<text x="{ART_X}" y="{y:.1f}" textLength="{COLS * ART_CW:.1f}" '
          f'lengthAdjust="spacing">{escape(line.ljust(COLS)).replace(" ", chr(160))}</text>')
    a('</g>')

    y = ART_Y
    a(f'<g font-size="{INFO_FS}">')

    def header(text):
        nonlocal y
        a(f'<text x="{INFO_X}" y="{y:.1f}" fill="{t["head"]}" font-weight="bold">{escape(text)}</text>')
        a(f'<line x1="{INFO_X + len(text) * 8.6 + 8:.1f}" x2="{INFO_R}" y1="{y - 4:.1f}" y2="{y - 4:.1f}" '
          f'stroke="{t["rule"]}" stroke-width="1.5"/>')
        y += INFO_LH

    def row(key, val, vcolor=None):
        nonlocal y
        a(f'<text x="{INFO_X}" y="{y:.1f}" fill="{t["key"]}">{escape(key)}:</text>')
        a(f'<text x="{INFO_R}" y="{y:.1f}" fill="{vcolor or t["val"]}" text-anchor="end">{escape(val)}</text>')
        y += INFO_LH

    header(cfg["handle"])
    for k, v in cfg["info"]:
        row(k, uptime if v == "@AGE@" else v)
    y += INFO_LH * 0.5
    for k, v in cfg["languages"]:
        row(k, v)
    y += INFO_LH * 0.5
    for k, v in cfg["hobbies"]:
        row(k, v)
    y += INFO_LH * 0.5
    header("Contact")
    for k, v in cfg["contact"]:
        row(k, v)
    y += INFO_LH * 0.5
    header("GitHub Stats")

    # two-column stat rows
    def pair(k1, v1, k2, v2):
        nonlocal y
        a(f'<text x="{INFO_X}" y="{y:.1f}" fill="{t["key"]}">{k1}:</text>')
        a(f'<text x="{INFO_X + 240}" y="{y:.1f}" fill="{t["val"]}" text-anchor="end">{escape(v1)}</text>')
        a(f'<text x="{INFO_X + 290}" y="{y:.1f}" fill="{t["key"]}">{k2}:</text>')
        a(f'<text x="{INFO_R}" y="{y:.1f}" fill="{t["val"]}" text-anchor="end">{escape(v2)}</text>')
        y += INFO_LH

    pair("Repos", f'{fmt(stats.get("repos"))} (Contributed: {fmt(stats.get("contributed"))})',
         "Stars", fmt(stats.get("stars")))
    pair("Commits", fmt(stats.get("commits")), "Followers", fmt(stats.get("followers")))

    a(f'<text x="{INFO_X}" y="{y:.1f}" fill="{t["key"]}">Lines of Code on GitHub:</text>')
    x = INFO_R
    # multi-colour value: each piece is right-anchored with a locked width (monospace cell = 0.6em)
    cw = INFO_FS * 0.6
    pieces = [
        (f'{fmt(stats.get("loc_total"))} (', t["val"]),
        (f'{fmt(stats.get("loc_added"))}++', t["add"]),
        (', ', t["val"]),
        (f'{fmt(stats.get("loc_deleted"))}--', t["dele"]),
        (')', t["val"]),
    ]
    for text, color in reversed(pieces):
        width = len(text) * cw
        a(f'<text x="{x:.1f}" y="{y:.1f}" fill="{color}" text-anchor="end" textLength="{width:.1f}" '
          f'lengthAdjust="spacing">{escape(text).replace(" ", chr(160))}</text>')
        x -= width
    y += INFO_LH
    a('</g>')
    a('</svg>')
    return "\n".join(out) + "\n"


for theme in THEMES:
    (ROOT / f"{theme}_mode.svg").write_text(build(theme))
print("built dark_mode.svg and light_mode.svg; uptime:", uptime)
