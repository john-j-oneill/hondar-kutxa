#!/usr/bin/env python3
"""Generate name buttons for a robotics team.

Reads a CSV of names, pronouns and roles, writes one SVG per button and lays
them all out on printable pages in a single PDF.

    python make_buttons.py people.csv --logo logo.png --team "Team 1234"

All text is converted to vector outlines (no fonts needed to view or print the
SVGs), and the logo is embedded, so every SVG is self-contained.
"""

import argparse
import base64
import csv
import io
import math
import re
from pathlib import Path

import cairosvg
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from pypdf import PdfWriter

HERE = Path(__file__).resolve().parent
PT = 72  # SVG user units are points; 72 per inch

PAPER = {"letter": (8.5, 11.0), "a4": (8.27, 11.69)}

STUDENT_ROLES = {"", "student", "kid", "member"}


# --- text -> outlines --------------------------------------------------------

class Font:
    def __init__(self, path):
        self.tt = TTFont(path)
        self.glyphs = self.tt.getGlyphSet()
        self.cmap = self.tt.getBestCmap()
        self.upm = self.tt["head"].unitsPerEm
        self.hmtx = self.tt["hmtx"]
        os2 = self.tt["OS/2"]
        self.cap = getattr(os2, "sCapHeight", 0) or 0.7 * self.upm

    def _gname(self, ch):
        return self.cmap.get(ord(ch)) or self.cmap.get(ord("?"))

    def advance(self, ch, size):
        return self.hmtx[self._gname(ch)][0] * size / self.upm

    def width(self, text, size):
        return sum(self.advance(c, size) for c in text)

    def cap_height(self, size):
        return self.cap * size / self.upm

    def glyph_path(self, ch, size, x=0.0, y=0.0):
        """SVG path data for one glyph with its origin (baseline-left) at x, y."""
        pen = SVGPathPen(self.glyphs)
        s = size / self.upm
        self.glyphs[self._gname(ch)].draw(TransformPen(pen, (s, 0, 0, -s, x, y)))
        return pen.getCommands()

    def line(self, text, size, cx, baseline):
        """Path data for a horizontally centred line of text."""
        x = cx - self.width(text, size) / 2
        parts = []
        for ch in text:
            parts.append(self.glyph_path(ch, size, x, baseline))
            x += self.advance(ch, size)
        return " ".join(p for p in parts if p)

    def arc(self, text, size, radius, top, spacing=0.0):
        """<path> elements for text on a circle centred at the origin.

        top=True: along the top, letters stand outward from `radius`.
        top=False: along the bottom, letters stand inward from `radius`.
        Both read left to right with letters upright.
        """
        advs = [self.advance(c, size) + spacing * size for c in text]
        total = sum(advs) - spacing * size
        out, s = [], -total / 2
        for ch, adv in zip(text, advs):
            mid = s + (adv - spacing * size) / 2
            if top:
                theta = -90 + math.degrees(mid / radius)
                rot = theta + 90
            else:
                theta = 90 - math.degrees(mid / radius)
                rot = theta - 90
            d = self.glyph_path(ch, size, -(adv - spacing * size) / 2, 0)
            s += adv
            if not d:
                continue
            t = math.radians(theta)
            x, y = radius * math.cos(t), radius * math.sin(t)
            out.append(f'<path transform="translate({x:.2f} {y:.2f}) '
                       f'rotate({rot:.2f})" d="{d}"/>')
        return "\n".join(out)


# --- colours -------------------------------------------------------------------

def hex_rgb(c):
    c = c.lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    return tuple(int(c[i:i + 2], 16) / 255 for i in (0, 2, 4))


def luminance(c):
    def lin(v):
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(v) for v in hex_rgb(c))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ink_on(bg):
    """Black or white, whichever reads better on bg."""
    return "#1a1a1a" if luminance(bg) > 0.4 else "#ffffff"


def shade(c, f):
    """Darken (f<0) or lighten (f>0) a colour."""
    rgb = hex_rgb(c)
    rgb = [v + (1 - v) * f if f > 0 else v * (1 + f) for v in rgb]
    return "#" + "".join(f"{round(v * 255):02x}" for v in rgb)


# --- the button ---------------------------------------------------------------

def gear(radius, teeth=10, fill="#fff"):
    """Placeholder logo: a simple gear, centred on the origin."""
    pts, inner, outer = [], radius * 0.78, radius
    for i in range(teeth * 4):
        a = 2 * math.pi * i / (teeth * 4) - math.pi / 2
        r = outer if i % 4 in (1, 2) else inner
        pts.append(f"{r * math.cos(a):.2f},{r * math.sin(a):.2f}")
    hole = radius * 0.35
    return (f'<path fill="{fill}" fill-rule="evenodd" d="M{" L".join(pts)} Z '
            f'M{hole},0 A{hole},{hole} 0 1 0 {-hole},0 A{hole},{hole} 0 1 0 {hole},0 Z"/>')


def fit_name(font, name, max_w, max_size, min_two_line):
    """Pick a size (and maybe a two-line split) so the name fits max_w."""
    size = min(max_size, max_size * max_w / font.width(name, max_size))
    words = name.split()
    if size >= min_two_line or len(words) < 2:
        return [name], size
    # try every split point, keep the one that allows the biggest text
    best = ([name], size)
    for i in range(1, len(words)):
        lines = [" ".join(words[:i]), " ".join(words[i:])]
        w = max(font.width(l, max_size) for l in lines)
        s = min(max_size * 0.8, max_size * (max_w * 0.92) / w)
        if s > best[1]:
            best = (lines, s)
    return best


def button_svg(person, cfg, fonts):
    bold, medium = fonts
    coach = person["role"].lower() not in STUDENT_ROLES
    bg = cfg.coach_color if coach else cfg.color
    accent = cfg.coach_accent if coach else cfg.accent
    ink = ink_on(bg)
    accent_ink = ink_on(accent)

    cut_r = cfg.cut * PT / 2
    face_r = cfg.face * PT / 2
    safe_r = cfg.safe * PT / 2
    u = safe_r / 97.2  # layout below was tuned for a 2.7in safe area

    el = []
    # background bleeds all the way to the cut line
    el.append(f'<circle r="{cut_r:.2f}" fill="{bg}"/>')
    # the wrap-around edge: a ring in the accent colour, starting just inside
    # the visible face so a slightly off-centre press still looks deliberate
    ring_in = safe_r + (face_r - safe_r) * 0.35
    el.append(f'<circle r="{(cut_r + ring_in) / 2:.2f}" fill="none" stroke="{accent}" '
              f'stroke-width="{cut_r - ring_in:.2f}"/>')
    el.append(f'<circle r="{ring_in - 1.2 * u:.2f}" fill="none" stroke="{ink}" '
              f'stroke-opacity="0.35" stroke-width="{0.8 * u:.2f}"/>')

    # top arc: team name
    arc_size = 11.5 * u
    arc_r = safe_r - 13 * u
    if cfg.team:
        el.append(f'<g fill="{ink}">{medium.arc(cfg.team.upper(), arc_size, arc_r, True, 0.08)}</g>')

    # bottom arc: role for coaches, optional tagline for students
    bottom = person["role"].upper() if coach else (cfg.tagline or "").upper()
    if bottom:
        if coach:
            size, sp = 15 * u, 0.18
            el.append(f'<g fill="{accent}">{bold.arc(bottom, size, safe_r - 4 * u, False, sp)}</g>')
            # stars either side of the label
            span = (bold.width(bottom, size) + sp * size * (len(bottom) - 1)) / (safe_r - 4 * u)
            for sgn in (-1, 1):
                a = math.pi / 2 + sgn * (span / 2 + 0.17)
                r = safe_r - 4 * u - bold.cap_height(size) / 2
                el.append(star(r * math.cos(a), r * math.sin(a), 6.5 * u, accent))
        else:
            el.append(f'<g fill="{ink}">{medium.arc(bottom, arc_size, safe_r - 5 * u, False, 0.08)}</g>')

    # logo
    lw, lh, ly = 74 * u, 40 * u, -36 * u
    if cfg.logo_data:
        el.append(f'<image x="{-lw / 2:.2f}" y="{ly - lh / 2:.2f}" width="{lw:.2f}" '
                  f'height="{lh:.2f}" preserveAspectRatio="xMidYMid meet" '
                  f'href="{cfg.logo_data}"/>')
    else:
        el.append(f'<g transform="translate(0 {ly:.2f})">{gear(lh / 2, fill=ink)}</g>')

    # name
    name_y = 14 * u
    max_w = 2 * math.sqrt(safe_r ** 2 - (name_y + 4 * u) ** 2) * 0.86
    lines, size = fit_name(bold, person["name"], max_w, 40 * u, 26 * u)
    cap = bold.cap_height(size)
    if len(lines) == 1:
        baseline = name_y + cap / 2
        el.append(f'<path fill="{ink}" d="{bold.line(lines[0], size, 0, baseline)}"/>')
    else:
        gap = cap * 0.45
        name_y -= 5 * u  # two lines: nudge the block up to leave room below
        el.append(f'<path fill="{ink}" d="{bold.line(lines[0], size, 0, name_y - gap / 2)}"/>')
        baseline = name_y + cap + gap / 2
        el.append(f'<path fill="{ink}" d="{bold.line(lines[1], size, 0, baseline)}"/>')
    text_bottom = baseline + 0.2 * size  # allow for descenders

    # pronouns, in a pill just under the name
    if person["pronouns"]:
        text = person["pronouns"]
        psize = 15 * u
        ph = medium.cap_height(psize) + 13 * u
        py = text_bottom + 4 * u + ph / 2
        pmax = 2 * math.sqrt(max(safe_r ** 2 - (py + 12 * u) ** 2, 0)) * 0.78
        psize = min(psize, psize * pmax / medium.width(text, psize))
        pw = medium.width(text, psize) + 18 * u
        el.append(f'<rect x="{-pw / 2:.2f}" y="{py - ph / 2:.2f}" width="{pw:.2f}" '
                  f'height="{ph:.2f}" rx="{ph / 2:.2f}" fill="{accent}"/>')
        el.append(f'<path fill="{accent_ink}" '
                  f'd="{medium.line(text, psize, 0, py + medium.cap_height(psize) / 2)}"/>')

    if cfg.guides:
        for r, colour in ((face_r, "#e0218a"), (safe_r, "#1e90ff")):
            el.append(f'<circle r="{r:.2f}" fill="none" stroke="{colour}" '
                      f'stroke-width="0.6" stroke-dasharray="3 2"/>')

    return el


def star(x, y, r, fill):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append(f"{x + rr * math.cos(a):.2f},{y + rr * math.sin(a):.2f}")
    return f'<polygon fill="{fill}" points="{" ".join(pts)}"/>'


def wrap_svg(elements, size_in, x=None, y=None):
    """Standalone SVG (x, y None) or a nested <svg> placed on a page."""
    half = size_in * PT / 2
    pos = "" if x is None else f'x="{x:.2f}" y="{y:.2f}" '
    head = ('<svg xmlns="http://www.w3.org/2000/svg" '
            'xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{size_in}in" height="{size_in}in" ') if x is None else '<svg '
    if x is not None:
        head += f'width="{2 * half:.2f}" height="{2 * half:.2f}" '
    return (f'{head}{pos}viewBox="{-half:.2f} {-half:.2f} {2 * half:.2f} {2 * half:.2f}">\n'
            + "\n".join(elements) + "\n</svg>\n")


# --- page layout ------------------------------------------------------------

def layout(paper, cut, margin, gap):
    pw, ph = paper
    cols = int((pw - 2 * margin + gap) // (cut + gap))
    rows = int((ph - 2 * margin + gap) // (cut + gap))
    if cols < 1 or rows < 1:
        raise SystemExit("A button doesn't fit on the page with those margins.")
    # centre the grid on the page
    x0 = (pw - (cols * cut + (cols - 1) * gap)) / 2
    y0 = (ph - (rows * cut + (rows - 1) * gap)) / 2
    return [(x0 + c * (cut + gap), y0 + r * (cut + gap))
            for r in range(rows) for c in range(cols)]


def page_svg(buttons, paper, cut, slots):
    pw, ph = paper
    body = []
    for els, (x, y) in zip(buttons, slots):
        body.append(wrap_svg(els, cut, x * PT, y * PT))
        # hairline cut guide in case the background is white
        body.append(f'<circle cx="{(x + cut / 2) * PT:.2f}" cy="{(y + cut / 2) * PT:.2f}" '
                    f'r="{cut * PT / 2:.2f}" fill="none" stroke="#999" stroke-width="0.3"/>')
    return ('<svg xmlns="http://www.w3.org/2000/svg" '
            'xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{pw}in" height="{ph}in" viewBox="0 0 {pw * PT} {ph * PT}">\n'
            + "\n".join(body) + "\n</svg>\n")


# --- main --------------------------------------------------------------------

def read_people(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    people = []
    for row in rows:
        row = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
        if not row.get("name"):
            continue
        copies = int(row.get("copies") or 1)
        people += [{"name": row["name"], "pronouns": row.get("pronouns", ""),
                    "role": row.get("role", "")}] * copies
    return people


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "button"


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("csv", help="CSV with columns name, pronouns, role (optional: copies)")
    p.add_argument("--logo", help="PNG (or JPG/SVG) logo; a gear is drawn if omitted")
    p.add_argument("--team", default="", help="text arced along the top, e.g. 'Team 1234 RoboRaiders'")
    p.add_argument("--tagline", default="", help="text arced along the bottom of student buttons, e.g. '2026 Season'")
    p.add_argument("--color", default="#1f4e9c", help="student background colour")
    p.add_argument("--accent", default="#ffc72c", help="student ring and pronoun pill colour")
    p.add_argument("--coach-color", default="#1a1a1a", help="coach background colour")
    p.add_argument("--coach-accent", default="#ffc72c", help="coach ring, label and pill colour")
    p.add_argument("--cut", type=float, default=3.5, help="cut circle diameter, inches (default 3.5)")
    p.add_argument("--face", type=float, default=3.0, help="visible button face diameter, inches (default 3.0)")
    p.add_argument("--safe", type=float, default=2.7, help="keep text and logo inside this diameter (default 2.7)")
    p.add_argument("--paper", choices=PAPER, default="letter")
    p.add_argument("--margin", type=float, default=0.25, help="page margin, inches")
    p.add_argument("--gap", type=float, default=0.0, help="space between buttons, inches")
    p.add_argument("--blanks", type=int, default=0, help="extra name-less spares to add (student style)")
    p.add_argument("--guides", action="store_true", help="draw face (pink) and safe-area (blue) circles for proofing")
    p.add_argument("--out", default="out", help="output folder (default ./out)")
    cfg = p.parse_args()

    if cfg.logo:
        logo = Path(cfg.logo)
        mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".svg": "image/svg+xml"}.get(logo.suffix.lower(), "image/png")
        cfg.logo_data = f"data:{mime};base64," + base64.b64encode(logo.read_bytes()).decode()
    else:
        cfg.logo_data = None

    fonts = (Font(HERE / "fonts" / "Fredoka-700.ttf"), Font(HERE / "fonts" / "Fredoka-500.ttf"))
    people = read_people(cfg.csv)
    people += [{"name": "", "pronouns": "", "role": ""}] * cfg.blanks
    if not people:
        raise SystemExit("No names found in the CSV (it needs a 'name' column).")

    out = Path(cfg.out)
    (out / "svg").mkdir(parents=True, exist_ok=True)
    buttons, used = [], {}
    for person in people:
        # a blank spare is the student design with an invisible name
        els = button_svg(person if person["name"] else {**person, "name": " "}, cfg, fonts)
        buttons.append(els)
        base = slug(person["name"] or "blank")
        used[base] = used.get(base, 0) + 1
        name = base if used[base] == 1 else f"{base}-{used[base]}"
        (out / "svg" / f"{name}.svg").write_text(wrap_svg(els, cfg.cut), encoding="utf-8")

    paper = PAPER[cfg.paper]
    slots = layout(paper, cfg.cut, cfg.margin, cfg.gap)
    writer = PdfWriter()
    pages = [buttons[i:i + len(slots)] for i in range(0, len(buttons), len(slots))]
    for n, chunk in enumerate(pages, 1):
        svg = page_svg(chunk, paper, cfg.cut, slots)
        (out / f"page-{n}.svg").write_text(svg, encoding="utf-8")
        writer.append(io.BytesIO(cairosvg.svg2pdf(bytestring=svg.encode())))
    with open(out / "buttons.pdf", "wb") as f:
        writer.write(f)

    print(f"{len(buttons)} buttons, {len(slots)} per page, {len(pages)} page(s) -> {out / 'buttons.pdf'}")
    print("Print at 100% / 'Actual size' (not 'Fit to page') so the circles stay "
          f"{cfg.cut} in across.")


if __name__ == "__main__":
    main()
