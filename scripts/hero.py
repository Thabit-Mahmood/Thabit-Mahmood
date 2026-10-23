"""Builds assets/hero-light.svg and assets/hero-dark.svg.

The figure is one lattice drawn with two bases. The long, nearly parallel
pair is what a public key looks like; the short, nearly orthogonal pair is
the secret trapdoor. Both span the same lattice and enclose the same area
(det = 1088 here), which is the whole point of lattice-based cryptography.

    pip install fonttools brotli
    SERIF=... MONO=... python3 scripts/hero.py

SERIF: a directory with newsreader-latin-{500-normal,400-italic}.woff2
MONO:  a directory with JetBrainsMono-Regular.ttf
Each SVG embeds only the glyphs it uses. Motion plays once, then stops,
and is skipped entirely for visitors who prefer reduced motion.
"""
from __future__ import annotations

import base64
import io
import math
import os
import pathlib
from xml.sax.saxutils import escape

from fontTools import subset

ROOT = pathlib.Path(__file__).resolve().parent.parent
SERIF = pathlib.Path(os.environ.get("SERIF", "fonts"))
MONO = pathlib.Path(os.environ.get("MONO", "fonts"))
SERIF_NAME = os.environ.get("SERIF_FAMILY", "newsreader")

W, H = 1000, 268

THEMES = {
    "light": dict(text="#1F2328", soft="#3D444D", muted="#59636E", faint="#818B98",
                  dot="#C8D0D9", pub="#9AA4B0", accent="#0E7C69", accent_fill="#0E7C69", cell=".16"),
    "dark": dict(text="#F0F3F6", soft="#C9D1D9", muted="#9198A1", faint="#6E7681",
                 dot="#30363D", pub="#6E7681", accent="#4FC8AE", accent_fill="#4FC8AE", cell=".24"),
}


def woff2(path: pathlib.Path, chars: str) -> str:
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["kern", "liga"]
    opts.hinting = False
    opts.name_IDs = [1, 2]
    font = subset.load_font(str(path), opts)
    s = subset.Subsetter(opts)
    s.populate(text=chars + " ")
    s.subset(font)
    buf = io.BytesIO()
    subset.save_font(font, buf, opts)
    return base64.b64encode(buf.getvalue()).decode()


def f(v: float) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


# ------------------------------------------------------------------ content
EYEBROW = "PHD CANDIDATE  ·  MULTIMEDIA UNIVERSITY"
NAME = "Thabit Mahmood"
TAGLINE = "Post-quantum cryptography and verifiable federated learning."
META = "Graduate Research Assistant, TM R&D  ·  Cyberjaya"
CAPTION_L = "one lattice, two bases"
CAPTION_R = "same volume"
LAB_PUB = "public"
LAB_SEC = "secret"

# lattice geometry: good (secret) basis g, bad (public) basis b = U g, det U = 1
G1, G2 = (34.0, 0.0), (10.0, -32.0)
U = ((1, 1), (2, 3))
B1 = (U[0][0] * G1[0] + U[0][1] * G2[0], U[0][0] * G1[1] + U[0][1] * G2[1])
B2 = (U[1][0] * G1[0] + U[1][1] * G2[0], U[1][0] * G1[1] + U[1][1] * G2[1])
O = (716.0, 200.0)
BOX = (622, 30, 962, 222)  # where lattice points may appear


def add(*vs):
    return (sum(v[0] for v in vs), sum(v[1] for v in vs))


def arrow(p, q, colour, cls):
    ang = math.atan2(q[1] - p[1], q[0] - p[0])
    L = math.hypot(q[0] - p[0], q[1] - p[1])
    end = (q[0] - 5.5 * math.cos(ang), q[1] - 5.5 * math.sin(ang))
    head = []
    for da in (0, 2.55, -2.55):
        r = 0 if da == 0 else 7
        head.append((q[0] + r * math.cos(ang + da), q[1] + r * math.sin(ang + da)))
    head_d = "M" + " L".join(f"{f(a)} {f(b)}" for a, b in head) + " Z"
    return (f'<path class="{cls} draw" pathLength="1" d="M{f(p[0])} {f(p[1])} L{f(end[0])} {f(end[1])}" '
            f'stroke="{colour}" stroke-width="1.6" stroke-linecap="round" fill="none"/>'
            f'<path class="{cls} late" d="{head_d}" fill="{colour}"/>'), L


def build(theme: str) -> str:
    c = THEMES[theme]
    serif_dir = SERIF
    sans_chars = NAME
    italic_chars = TAGLINE
    mono_chars = EYEBROW + META + CAPTION_L + CAPTION_R + LAB_PUB + LAB_SEC + "·"
    fonts = (
        "@font-face{font-family:S;font-weight:500;src:url(data:font/woff2;base64,"
        + woff2(serif_dir / f"{SERIF_NAME}-latin-500-normal.woff2", sans_chars) + ") format('woff2')}"
        "@font-face{font-family:S;font-style:italic;font-weight:400;src:url(data:font/woff2;base64,"
        + woff2(serif_dir / f"{SERIF_NAME}-latin-400-italic.woff2", italic_chars) + ") format('woff2')}"
        "@font-face{font-family:M;font-weight:400;src:url(data:font/woff2;base64,"
        + woff2(MONO / "JetBrainsMono-Regular.ttf", mono_chars) + ") format('woff2')}"
    )
    serif = "S, 'Newsreader', 'Iowan Old Style', Georgia, 'Times New Roman', serif"
    mono = "M, 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"

    css = f"""
{fonts}
.serif{{font-family:{serif}}}
.mono{{font-family:{mono};font-variant-ligatures:none}}
.pt{{animation:fade .5s ease-out both;animation-delay:var(--d)}}
.pub.draw{{stroke-dasharray:1;animation:draw .8s cubic-bezier(.4,0,.2,1) .75s both}}
.sec.draw{{stroke-dasharray:1;animation:draw .8s cubic-bezier(.4,0,.2,1) 1.55s both}}
.pub.late,.pub.cell{{animation:fade .45s ease-out 1.35s both}}
.sec.late,.sec.cell{{animation:fade .45s ease-out 2.15s both}}
.cap{{animation:fade .6s ease-out 2.4s both}}
@keyframes fade{{from{{opacity:0}}to{{opacity:1}}}}
@keyframes draw{{from{{stroke-dashoffset:1}}to{{stroke-dashoffset:0}}}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}
"""
    out = []
    # lattice points
    x0, y0, x1, y1 = BOX
    for a in range(-12, 16):
        for b in range(-4, 10):
            p = add(O, (a * G1[0] + b * G2[0], a * G1[1] + b * G2[1]))
            if x0 <= p[0] <= x1 and y0 <= p[1] <= y1:
                d = math.hypot(p[0] - O[0], p[1] - O[1]) / 900
                out.append(f'<circle class="pt" style="--d:{f(d)}s" cx="{f(p[0])}" cy="{f(p[1])}" r="1.9" '
                           f'fill="{c["dot"]}"/>')
    # fundamental cells: a long thin sliver and a compact cell, equal area
    sliver = [O, add(O, B1), add(O, B1, B2), add(O, B2)]
    cell = [O, add(O, G1), add(O, G1, G2), add(O, G2)]
    poly = lambda pts: " ".join(f"{f(a)},{f(b)}" for a, b in pts)
    out.append(f'<polygon class="pub cell" points="{poly(sliver)}" fill="{c["pub"]}" fill-opacity=".09" '
               f'stroke="{c["pub"]}" stroke-opacity=".55" stroke-width="1"/>')
    out.append(f'<polygon class="sec cell" points="{poly(cell)}" fill="{c["accent_fill"]}" fill-opacity="{c["cell"]}"/>')
    for v in (B1, B2):
        s, _ = arrow(O, add(O, v), c["pub"], "pub")
        out.append(s)
    for v in (G1, G2):
        s, _ = arrow(O, add(O, v), c["accent"], "sec")
        out.append(s)
    out.append(f'<circle cx="{f(O[0])}" cy="{f(O[1])}" r="2.6" fill="{c["text"]}"/>')
    tip = add(O, B2)
    out.append(f'<text class="mono pub late" x="{f(tip[0] + 10)}" y="{f(tip[1] + 5)}" font-size="13" '
               f'fill="{c["muted"]}">{LAB_PUB}</text>')
    out.append(f'<text class="mono sec late" x="{f(O[0] - 10)}" y="{f(O[1] + 5)}" font-size="13" '
               f'text-anchor="end" fill="{c["accent"]}">{LAB_SEC}</text>')
    out.append(f'<g class="cap"><text class="mono" x="{x0}" y="{H - 22}" font-size="13" fill="{c["faint"]}">'
               f'{CAPTION_L}</text><text class="mono" x="{x1}" y="{H - 22}" font-size="13" '
               f'text-anchor="end" fill="{c["faint"]}">{CAPTION_R}</text></g>')

    # text column
    out.append(f'<text class="mono" x="0" y="44" font-size="13" letter-spacing="1.8" '
               f'fill="{c["muted"]}" xml:space="preserve">{escape(EYEBROW)}</text>')
    out.append(f'<text class="serif" x="-3" y="124" font-size="70" font-weight="500" letter-spacing="-1.2" '
               f'fill="{c["text"]}">{escape(NAME)}</text>')
    out.append(f'<text class="serif" x="0" y="170" font-size="23" font-style="italic" '
               f'fill="{c["soft"]}">{escape(TAGLINE)}</text>')
    out.append(f'<text class="mono" x="0" y="{H - 22}" font-size="14" fill="{c["muted"]}" '
               f'xml:space="preserve">{escape(META)}</text>')

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d">
<title id="t">Thabit Mahmood</title>
<desc id="d">PhD candidate at Multimedia University working on post-quantum cryptography and verifiable federated learning. Graduate Research Assistant at TM R&amp;D, Cyberjaya, Malaysia. The figure shows one lattice with two bases: a long public basis and a short secret basis enclosing the same area.</desc>
<style>{css}</style>
{chr(10).join(out)}
</svg>
"""


if __name__ == "__main__":
    assert abs(B1[0] * B2[1] - B1[1] * B2[0]) == abs(G1[0] * G2[1] - G1[1] * G2[0])  # same volume
    (ROOT / "assets").mkdir(exist_ok=True)
    for t in THEMES:
        svg = build(t)
        (ROOT / "assets" / f"hero-{t}.svg").write_text(svg, encoding="utf-8")
        print(f"hero-{t}.svg {len(svg) / 1024:.1f} KB")
