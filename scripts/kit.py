"""Shared drawing kit for the profile graphics.

Standard library only, so the daily GitHub Action can import it without
installing anything. Every graphic is a hand-written SVG: CSS keyframes for
ambient motion, SMIL timelines for choreographed sequences.
"""
from __future__ import annotations

import base64
import pathlib
from xml.sax.saxutils import escape

ROOT = pathlib.Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
FONTS = ASSETS / "fonts"

W = 1000  # every card shares one width so the stack lines up

C = {
    "bg0": "#05080E",
    "bg1": "#0A1019",
    "panel": "#0B121C",
    "edge": "#1A2433",
    "rule": "#162030",
    "dot": "#26344A",
    "text": "#E6EDF3",
    "soft": "#C3CDD8",
    "muted": "#8B98A9",
    "faint": "#5A6679",
    "teal": "#2FE6C0",
    "amber": "#FFB547",
    "violet": "#9D8CFF",
    "sky": "#5CC8FF",
    "rose": "#FF8FB1",
    "slate": "#A3B1C2",
}

MONO = "JBM, 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
ADV = 0.6  # JetBrains Mono advance width, in em


def tw(text: str, size: float, spacing: float = 0.0) -> float:
    """Rendered width of monospace text."""
    n = len(text)
    return n * size * ADV + max(n - 1, 0) * spacing


def x(s) -> str:
    """XML-escape text content."""
    return escape(str(s))


def f(v: float) -> str:
    """Compact number formatting for coordinates."""
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def font_face(path: pathlib.Path, weight: int) -> str:
    data = base64.b64encode(path.read_bytes()).decode()
    return (
        "@font-face{font-family:JBM;font-style:normal;"
        f"font-weight:{weight};src:url(data:font/woff2;base64,{data}) format('woff2');}}"
    )


def timeline(attr: str, points, dur: float, calc: str = "discrete",
             begin: str = "0s", repeat: bool = True, extra: str = "",
             tag: str = "animate") -> str:
    """A SMIL animation from (time_seconds, value) pairs inside one cycle."""
    pts = sorted(points, key=lambda p: p[0])
    if pts[0][0] > 0:
        pts.insert(0, (0.0, pts[0][1]))
    clean = []
    for t, v in pts:
        t = min(max(t, 0.0), dur)
        if clean and abs(clean[-1][0] - t) < 1e-6:
            clean[-1] = (t, v)
        else:
            clean.append((t, v))
    if calc != "discrete" and clean[-1][0] < dur:
        clean.append((dur, clean[-1][1]))
    kt = ";".join(f"{t / dur:.5f}".rstrip("0").rstrip(".") or "0" for t, _ in clean)
    vals = ";".join(str(v) for _, v in clean)
    rep = 'repeatCount="indefinite"' if repeat else 'fill="freeze"'
    return (f'<{tag} attributeName="{attr}" dur="{f(dur)}s" begin="{begin}" {rep} '
            f'calcMode="{calc}" keyTimes="{kt}" values="{vals}" {extra}/>')


def show_between(t_on: float, t_off: float, dur: float, attr: str = "opacity") -> str:
    """Discrete visibility window [t_on, t_off) inside a repeating cycle."""
    pts = [(0, 0), (t_on, 1), (t_off, 0)] if t_on > 0 else [(0, 1), (t_off, 0)]
    return timeline(attr, pts, dur)


def card(width: int, height: int, body: str, *, title: str, desc: str,
         css: str = "", defs: str = "", fonts: str = "", accent: str = C["teal"]) -> str:
    """Wrap a graphic in the shared dark card: gradient, grain, hairline edge."""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" xml:space="preserve" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="t d">
<title id="t">{x(title)}</title>
<desc id="d">{x(desc)}</desc>
<style>
{fonts}
text{{font-family:{MONO};font-variant-ligatures:none;white-space:pre;}}
{css}
</style>
<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="{C['bg1']}"/><stop offset="1" stop-color="{C['bg0']}"/>
</linearGradient>
<linearGradient id="edgeGlow" x1="0" y1="0" x2="1" y2="0">
<stop offset="0" stop-color="{accent}" stop-opacity="0"/>
<stop offset=".22" stop-color="{accent}" stop-opacity=".55"/>
<stop offset=".6" stop-color="{accent}" stop-opacity="0"/>
</linearGradient>
<filter id="grain" x="0" y="0" width="100%" height="100%">
<feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" stitchTiles="stitch"/>
<feColorMatrix values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 .05 0"/>
</filter>
<clipPath id="cardClip"><rect width="{width}" height="{height}" rx="16"/></clipPath>
{defs}
</defs>
<g clip-path="url(#cardClip)">
<rect width="{width}" height="{height}" fill="url(#bg)"/>
<rect width="{width}" height="{height}" filter="url(#grain)"/>
{body}
<rect x="0" y="0" width="{width}" height="1" fill="url(#edgeGlow)"/>
</g>
<rect x=".5" y=".5" width="{width - 1}" height="{height - 1}" rx="15.5" fill="none" stroke="{C['edge']}"/>
</svg>
"""


def text(xp: float, yp: float, content: str, *, size: float = 13, fill: str = C["text"],
         weight: int = 400, anchor: str = "start", extra: str = "", raw: bool = False,
         spacing: float = 0) -> str:
    body = content if raw else x(content)
    ls = f' letter-spacing="{f(spacing)}"' if spacing else ""
    return (f'<text x="{f(xp)}" y="{f(yp)}" font-size="{f(size)}" font-weight="{weight}" '
            f'fill="{fill}" text-anchor="{anchor}"{ls} {extra}>{body}</text>')


def spans(parts, size: float) -> str:
    """Inline coloured runs: parts = [(text, colour, weight?), ...]."""
    out = []
    for p in parts:
        t, col = p[0], p[1]
        wt = p[2] if len(p) > 2 else None
        w = f' font-weight="{wt}"' if wt else ""
        out.append(f'<tspan fill="{col}"{w}>{x(t)}</tspan>')
    return "".join(out)
