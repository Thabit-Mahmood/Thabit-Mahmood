"""Builds the static profile graphics in assets/.

    JBM_TTF=/path/to/JetBrainsMono/fonts/ttf python3 scripts/build.py

Needs fontTools + brotli (pip install fonttools brotli) and the JetBrains
Mono TTFs (OFL 1.1). Each SVG embeds only the glyphs it actually uses, so
the cards render identically everywhere without loading anything remote.
The live contribution lattice is rendered separately by lattice.py.
"""
from __future__ import annotations

import base64
import io
import math
import os
import pathlib
import random
import re

from fontTools import subset

from kit import (ASSETS, C, FONTS, W, card, f, show_between, spans, text,
                 timeline, tw, x)

TTF = pathlib.Path(os.environ.get("JBM_TTF", "fonts/ttf"))
WEIGHTS = {400: "Regular", 700: "Bold", 800: "ExtraBold"}
rng = random.Random(1568)  # ML-KEM-1024 encapsulation key size, for luck


# ---------------------------------------------------------------- fonts

def subset_woff2(weight: int, chars: str) -> bytes:
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = []
    opts.hinting = False
    opts.desubroutinize = True
    opts.name_IDs = [1, 2]
    opts.notdef_outline = True
    font = subset.load_font(str(TTF / f"JetBrainsMono-{WEIGHTS[weight]}.ttf"), opts)
    s = subset.Subsetter(opts)
    s.populate(text=chars + " ")
    s.subset(font)
    buf = io.BytesIO()
    subset.save_font(font, buf, opts)
    return buf.getvalue()


def used_chars(svg: str) -> str:
    chunks = re.findall(r"<(?:text|tspan)[^>]*>([^<]*)", svg)
    raw = "".join(chunks)
    raw = (raw.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
           .replace("&quot;", '"').replace("&#x27;", "'"))
    return "".join(sorted(set(raw)))


def embed_fonts(svg: str, weights=(400, 700, 800)) -> str:
    chars = used_chars(svg)
    faces = []
    for wt in weights:
        data = base64.b64encode(subset_woff2(wt, chars)).decode()
        faces.append("@font-face{font-family:JBM;font-style:normal;"
                     f"font-weight:{wt};src:url(data:font/woff2;base64,{data}) format('woff2');}}")
    return svg.replace("/*FONTS*/", "\n".join(faces), 1)


def write(name: str, svg: str, weights=(400, 700, 800)) -> None:
    svg = embed_fonts(svg, weights)
    path = ASSETS / name
    path.write_text(svg, encoding="utf-8")
    print(f"{name:18s} {len(svg) / 1024:6.1f} KB")


def live_fonts() -> None:
    """Fixed-charset subsets for the daily lattice (no fontTools on the runner)."""
    chars = "".join(chr(c) for c in range(0x20, 0x7F)) + "·×→ℤ∈²◆●–"
    for wt in (400, 700):
        (FONTS / f"live-{wt}.woff2").write_bytes(subset_woff2(wt, chars))


def rich(xp, yp, parts, size, anchor="start", weight=400):
    return text(xp, yp, spans(parts, size), size=size, anchor=anchor, raw=True, weight=weight)


# ---------------------------------------------------------------- hero

def hero() -> str:
    H = 360
    DUR = 16.0
    body = []
    css = """
.tw{animation:tw var(--d) ease-in-out infinite;animation-delay:var(--o)}
@keyframes tw{0%,100%{opacity:.06}50%{opacity:.85}}
.pulse{animation:pulse 2.4s ease-in-out infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.25}}
.caret{animation:blink 1.05s steps(1) infinite}
@keyframes blink{0%{opacity:1}50%{opacity:0}}
"""
    defs = f"""
<radialGradient id="vign" cx=".33" cy=".52" r=".62">
<stop offset="0" stop-color="#000" stop-opacity="1"/>
<stop offset=".55" stop-color="#000" stop-opacity=".55"/>
<stop offset="1" stop-color="#000" stop-opacity="0"/>
</radialGradient>
<linearGradient id="beam" x1="0" y1="0" x2="1" y2="0">
<stop offset="0" stop-color="{C['teal']}" stop-opacity="0"/>
<stop offset=".85" stop-color="{C['teal']}" stop-opacity=".16"/>
<stop offset="1" stop-color="{C['teal']}" stop-opacity=".0"/>
</linearGradient>
<filter id="glow" x="-20%" y="-40%" width="140%" height="180%">
<feGaussianBlur in="SourceAlpha" stdDeviation="7" result="b"/>
<feFlood flood-color="{C['teal']}" flood-opacity=".33"/>
<feComposite in2="b" operator="in" result="g"/>
<feMerge><feMergeNode in="g"/><feMergeNode in="SourceGraphic"/></feMerge>
</filter>
<filter id="soft" x="-50%" y="-50%" width="200%" height="200%">
<feGaussianBlur stdDeviation="2.2"/>
</filter>
<marker id="arT" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
<path d="M0 1 L9 5 L0 9 z" fill="{C['teal']}"/></marker>
<marker id="arV" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
<path d="M0 1 L9 5 L0 9 z" fill="{C['violet']}"/></marker>
"""

    # background lattice: basis (46,0), (17,40)
    dots = []
    for j in range(-1, 10):
        for i in range(-6, 26):
            px, py = -30 + i * 46 + j * 17, 14 + j * 40
            if not (10 < px < W - 10 and 10 < py < H - 10):
                continue
            if py > 300 or (40 < py < 80 and (px < 340 or px > 720)) or (640 < px < 966 and 80 < py < 300):
                continue  # keep text rows and the panel clean
            d = math.hypot((px - 330) / 1.25, py - 190)
            op = 0.16 + 0.64 * min(1.0, d / 430)
            dots.append(f'<circle cx="{f(px)}" cy="{f(py)}" r="1.35" fill="#30425E" opacity="{f(op)}"/>')
            if rng.random() < 0.13:
                dots.append(
                    f'<circle class="tw" cx="{f(px)}" cy="{f(py)}" r="1.5" fill="{C["teal"]}" '
                    f'style="--d:{f(rng.uniform(4, 9))}s;--o:-{f(rng.uniform(0, 9))}s"/>')
    body.append("<g>" + "".join(dots) + "</g>")
    body.append(f'<rect width="{W}" height="{H}" fill="url(#vign)" opacity=".5"/>')

    # top row
    body.append(f'<circle class="pulse" cx="62" cy="62" r="3.6" fill="{C["teal"]}"/>')
    body.append(rich(74, 66, [("pq-lab://", C["faint"]), ("thabit-mahmood", C["soft"])], 12))
    body.append(rich(W - 40, 66, [("session ", C["faint"]), ("7f3a·c219", C["muted"]),
                                  ("  ·  ", C["faint"]), ("ML-KEM-1024", C["teal"])], 11.5, anchor="end"))

    # identity label: before / after decapsulation
    T_DONE = 2.05
    T_REKEY = 15.3
    lab_before = rich(56, 128, [("$ ", C["teal"]), ("decaps ", C["soft"]), ("--identity ", C["muted"]),
                                ("ct.bin", C["faint"])], 13)
    lab_after = rich(56, 128, [("✓ ", C["teal"]), ("identity verified", C["soft"]), ("  ·  ", C["faint"]),
                               ("ss = 32 B", C["muted"])], 13)
    body.append(f"<g>{timeline('opacity', [(0, 1), (T_DONE, 0), (T_REKEY, 1)], DUR)}{lab_before}</g>")
    body.append(f'<g opacity="0">{show_between(T_DONE, T_REKEY, DUR)}{lab_after}</g>')

    # the name, decrypting from ciphertext one glyph at a time
    name = "THABIT MAHMOOD"
    size, spacing = 58, 3.2
    pitch = size * 0.6 + spacing
    x0, y0 = 56, 198
    hexs = "0123456789abcdef#%$&*+=<>/"
    glyphs = []
    for i, ch in enumerate(name):
        cx = x0 + i * pitch
        t_i = 0.55 + i * 0.105
        frames = [rng.choice(hexs) for _ in range(6)]
        scram = []
        for k, g in enumerate(frames):
            slot = (k - i) % 6
            scram.append(
                f'<text x="{f(cx)}" y="{y0}" font-size="{size}" font-weight="700" fill="{C["teal"]}" '
                f'opacity="0">{x(g)}' + show_between(slot * 0.075, (slot + 1) * 0.075, 0.45) + "</text>")
        grp_s = (f'<g opacity=".78">{timeline("opacity", [(0, .78), (t_i, 0), (T_REKEY + i * 0.018, .78)], DUR)}'
                 + "".join(scram) + "</g>")
        if ch != " ":
            fin = (f'<text x="{f(cx)}" y="{y0}" font-size="{size}" font-weight="800" fill="{C["text"]}" opacity="0">'
                   + x(ch)
                   + timeline("opacity", [(0, 0), (t_i, 1), (T_REKEY + i * 0.018, 0)], DUR)
                   + timeline("fill", [(0, C["teal"]), (t_i, C["teal"]), (t_i + .55, C["text"]),
                                       (DUR, C["text"])], DUR, calc="linear")
                   + "</text>")
        else:
            fin = ""
        glyphs.append(grp_s + fin)
    jitter = timeline("transform", [(0, "0 0"), (T_REKEY, "0 0"), (T_REKEY + .06, "-4 0"),
                                    (T_REKEY + .12, "3 0"), (T_REKEY + .18, "-1 0"),
                                    (T_REKEY + .24, "0 0")], DUR, tag="animateTransform",
                      extra='type="translate"')
    body.append(f'<g filter="url(#glow)">{jitter}{"".join(glyphs)}</g>')

    # decryption beam sweeping with the glyphs
    beam_x = timeline("transform", [(0, "-120 0"), (0.29, "-120 0"), (0.3, "-10 0"), (3.25, f"{W + 60} 0"),
                                    (DUR, f"{W + 80} 0")], DUR, calc="linear",
                      tag="animateTransform", extra='type="translate"')
    body.append(f'<g>{beam_x}<rect x="-90" y="0" width="90" height="{H}" fill="url(#beam)"/>'
                f'<rect x="-1.5" y="0" width="1.5" height="{H}" fill="{C["teal"]}" opacity=".7"/></g>')

    # subtitle: typed once, then stays
    role = [("Post-quantum cryptography", C["text"]), (" × ", C["amber"]),
            ("verifiable federated learning", C["text"])]
    role_txt = "".join(p[0] for p in role)
    rs = 16.5
    rw = tw(role_txt, rs)
    T0, step = 2.25, 0.021
    widths = [(T0 + k * step, f(k * rs * 0.6)) for k in range(len(role_txt) + 1)]
    body.append(f'<clipPath id="typeRole"><rect x="54" y="220" height="26" width="0">'
                + timeline("width", [(0, 0)] + widths, 30, repeat=False) + "</rect></clipPath>")
    body.append(f'<g clip-path="url(#typeRole)">'
                + rich(56, 240, role, rs)
                + "</g>")
    t_typed = T0 + len(role_txt) * step
    body.append(f'<g opacity="0">' + timeline("opacity", [(0, 0), (t_typed, 1)], 30, repeat=False)
                + f'<rect class="caret" x="{f(56 + rw + 6)}" y="226" width="9" height="18" fill="{C["teal"]}"/></g>')
    for k, (line, yy) in enumerate([
            ([("PhD Candidate", C["soft"]), ("  ·  ", C["faint"]), ("Multimedia University", C["muted"])], 270),
            ([("Graduate Research Assistant", C["soft"]), ("  ·  ", C["faint"]), ("TM R&D", C["muted"])], 292)]):
        body.append(f'<g opacity="0">'
                    + timeline("opacity", [(0, 0), (t_typed + .15 + k * .2, 0), (t_typed + .75 + k * .2, 1)],
                               30, calc="linear", repeat=False)
                    + rich(56, yy, line, 13.5)
                    + "</g>")

    # LWE panel: lattice, basis, target t = v + e
    px0, py0, pw, ph = 648, 86, 312, 208
    body.append(f'<rect x="{px0}" y="{py0}" width="{pw}" height="{ph}" rx="12" fill="{C["panel"]}" '
                f'fill-opacity=".72" stroke="{C["edge"]}"/>')
    body.append(rich(px0 + 16, py0 + 24, [
        ("L(B)", C["soft"]), (" = { ", C["faint"]), ("Bz", C["soft"]), (" : z ∈ ", C["faint"]),
        ("ℤ²", C["soft"]), (" }", C["faint"])], 11.5))
    body.append(text(px0 + pw - 16, py0 + 24, "lattice", size=10.5, fill=C["faint"], anchor="end"))
    O = (802, 196)
    b1, b2 = (36, 7), (12, -30)
    pts = []
    for a in range(-7, 8):
        for b in range(-5, 6):
            qx, qy = O[0] + a * b1[0] + b * b2[0], O[1] + a * b1[1] + b * b2[1]
            if px0 + 14 < qx < px0 + pw - 14 and py0 + 38 < qy < py0 + ph - 44:
                delay = 0.4 + (abs(a) + abs(b)) * 0.05
                pts.append(f'<circle cx="{f(qx)}" cy="{f(qy)}" r="2.1" fill="#4A5E7D" opacity="0">'
                           + timeline("opacity", [(0, 0), (delay, 0), (delay + .4, 1)], 30,
                                      calc="linear", repeat=False) + "</circle>")
    body.append("<g>" + "".join(pts) + "</g>")

    def vec(p, q, col, marker, t0):
        grow = "".join(
            timeline(a, [(0, f(p[k])), (t0, f(p[k])), (t0 + .7, f(q[k]))], 30, calc="linear",
                     repeat=False)
            for k, a in ((0, "x2"), (1, "y2")))
        return (f'<g opacity="0">' + timeline("opacity", [(0, 0), (t0, 1)], 30, repeat=False)
                + f'<line x1="{f(p[0])}" y1="{f(p[1])}" x2="{f(p[0])}" y2="{f(p[1])}" stroke="{col}" '
                f'stroke-width="2" stroke-linecap="round" marker-end="url(#{marker})">' + grow + "</line></g>")

    tip1 = (O[0] + b1[0], O[1] + b1[1])
    tip2 = (O[0] + b2[0], O[1] + b2[1])
    body.append(vec(O, tip1, C["teal"], "arT", 1.2))
    body.append(vec(O, tip2, C["violet"], "arV", 1.45))
    body.append(f'<circle cx="{O[0]}" cy="{O[1]}" r="2.6" fill="{C["text"]}"/>')
    body.append(text(tip1[0] + 6, tip1[1] + 14, "b₁", size=11, fill=C["teal"]))
    body.append(text(tip2[0] - 4, tip2[1] - 7, "b₂", size=11, fill=C["violet"], anchor="end"))
    v = (O[0] + 2 * b1[0] + b2[0], O[1] + 2 * b1[1] + b2[1])
    t = (v[0] + 10, v[1] - 10)
    body.append(f'<g opacity="0">' + timeline("opacity", [(0, 0), (2.1, 0), (2.6, 1)], 30,
                                              calc="linear", repeat=False)
                + f'<circle cx="{f(v[0])}" cy="{f(v[1])}" r="3.2" fill="{C["soft"]}"/>'
                + f'<line x1="{f(v[0])}" y1="{f(v[1])}" x2="{f(t[0])}" y2="{f(t[1])}" stroke="{C["amber"]}" '
                  f'stroke-width="1.5" stroke-dasharray="3 3">'
                + '<animate attributeName="stroke-dashoffset" values="0;-12" dur="1.2s" repeatCount="indefinite"/>'
                + "</line>"
                + f'<circle cx="{f(t[0])}" cy="{f(t[1])}" r="4.6" fill="none" stroke="{C["amber"]}" stroke-width="1.6">'
                + '<animate attributeName="r" values="4.2;6.2;4.2" dur="2.6s" repeatCount="indefinite"/>'
                + "</circle>"
                + "".join(
                    f'<circle cx="{f(t[0])}" cy="{f(t[1])}" r="1.1" fill="{C["amber"]}" opacity=".55">'
                    f'<animateTransform attributeName="transform" type="translate" dur="{f(rng.uniform(1.8, 3.2))}s" '
                    f'repeatCount="indefinite" values="'
                    + ";".join(f"{f(rng.gauss(0, 4.5))} {f(rng.gauss(0, 4.5))}" for _ in range(5)) + ';0 0"/></circle>'
                    for _ in range(7))
                + text(t[0] + 9, t[1] - 6, "t", size=11.5, fill=C["amber"], weight=700)
                + text((v[0] + t[0]) / 2 + 7, (v[1] + t[1]) / 2 + 9, "e", size=11, fill=C["amber"])
                + "</g>")
    body.append(f'<line x1="{px0 + 14}" y1="{py0 + ph - 38}" x2="{px0 + pw - 14}" y2="{py0 + ph - 38}" stroke="{C["rule"]}"/>')
    body.append(rich(px0 + 16, py0 + ph - 16, [
        ("b", C["amber"]), (" = ", C["faint"]), ("A·s", C["soft"]), (" + ", C["faint"]), ("e", C["amber"]),
        ("  mod q", C["faint"])], 12))
    body.append(text(px0 + pw - 16, py0 + ph - 16, "hard, even quantumly", size=10.5,
                     fill=C["faint"], anchor="end"))

    # status bar
    body.append(f'<line x1="32" y1="318" x2="{W - 32}" y2="318" stroke="{C["rule"]}"/>')
    body.append(f'<circle class="pulse" cx="40" cy="338" r="3" fill="{C["teal"]}"/>')
    body.append(text(50, 342, "secure channel established", size=11.5, fill=C["muted"]))
    body.append(rich(W / 2, 342, [
        ("kem ", C["faint"]), ("ML-KEM-1024", C["soft"]), ("   sig ", C["faint"]), ("ML-DSA-87", C["soft"]),
        ("   kdf ", C["faint"]), ("HKDF-SHA-256", C["soft"])], 11.5, anchor="middle"))
    bx, bw = W - 40 - 92, 92
    body.append(text(bx - 10, 342, "rekey", size=11.5, fill=C["faint"], anchor="end"))
    body.append(f'<rect x="{bx}" y="334" width="{bw}" height="5" rx="2.5" fill="{C["rule"]}"/>')
    body.append(f'<rect x="{bx}" y="334" width="0" height="5" rx="2.5" fill="{C["teal"]}" opacity=".85">'
                + timeline("width", [(0, 0), (T_DONE, 0), (T_REKEY, bw), (DUR, bw)], DUR, calc="linear")
                + timeline("fill", [(0, C["teal"]), (T_REKEY - .01, C["teal"]), (T_REKEY, C["amber"])], DUR)
                + "</rect>")

    return card(W, H, "\n".join(body), title="Thabit Mahmood",
                desc="Animated banner: the name decrypts from ciphertext as a scan beam passes, beside a "
                     "learning-with-errors lattice panel. PhD candidate at Multimedia University working on "
                     "post-quantum cryptography and verifiable federated learning.",
                css=css, defs=defs, fonts="/*FONTS*/")



# ---------------------------------------------------------------- terminal

def terminal() -> str:
    H, DUR, RESET = 500, 22.0, 21.4
    fs, cw, lh = 14.5, 14.5 * 0.6, 23
    X0, Y0 = 32, 80
    body = []
    css = """
.caret{animation:blink 1.05s steps(1) infinite}
@keyframes blink{0%{opacity:1}50%{opacity:0}}
"""
    # window chrome
    body.append(f'<rect x="0" y="0" width="{W}" height="44" fill="{C["panel"]}" fill-opacity=".8"/>')
    body.append(f'<line x1="0" y1="44" x2="{W}" y2="44" stroke="{C["edge"]}"/>')
    for k, col in enumerate((C["teal"], C["amber"], C["violet"])):
        body.append(f'<rect x="{24 + k * 17}" y="17" width="10" height="10" rx="2.5" fill="{col}" '
                    f'fill-opacity=".18" stroke="{col}" stroke-opacity=".8"/>')
    body.append(rich(W / 2, 27, [("thabit@pq-lab", C["soft"]), (": ", C["faint"]), ("~/research", C["muted"])],
                     12.5, anchor="middle"))
    body.append(text(W - 24, 27, "pq-shell · utf-8", size=11.5, fill=C["faint"], anchor="end"))

    prompt = [("thabit", C["teal"]), ("@pq-lab", C["muted"]), (" ~/research", C["violet"]), (" $ ", C["faint"])]
    plen = sum(len(p[0]) for p in prompt)
    cmd_x = X0 + plen * cw

    def vis(t_on):
        return timeline("opacity", [(0, 0), (t_on, 1), (RESET, 0)], DUR)

    def typed(row, parts, t0, step, caret_until):
        y = Y0 + row * lh
        n = sum(len(p[0]) for p in parts)
        cid = f"ty{row}"
        widths = [(0, 0), (t0, 0)] + [(t0 + k * step, f(k * cw)) for k in range(1, n + 1)] + [(RESET, 0)]
        out = [f'<g opacity="0">{vis(t0 - 0.3)}{rich(X0, y, prompt, fs)}</g>',
               f'<clipPath id="{cid}"><rect x="{f(cmd_x)}" y="{y - 17}" height="23" width="0">'
               + timeline("width", widths, DUR) + "</rect></clipPath>",
               f'<g clip-path="url(#{cid})">{rich(cmd_x, y, parts, fs)}</g>']
        xs = [(0, f(cmd_x)), (t0, f(cmd_x))] + [(t0 + k * step, f(cmd_x + k * cw)) for k in range(1, n + 1)]
        out.append(f'<rect x="{f(cmd_x)}" y="{y - 14}" width="{f(cw)}" height="18" fill="{C["teal"]}" opacity="0">'
                   + timeline("x", xs, DUR)
                   + timeline("opacity", [(0, 0), (t0 - 0.3, .85), (caret_until, 0)], DUR) + "</rect>")
        return "".join(out)

    def line(row, parts, t_on, xpos=X0 + 24):
        return f'<g opacity="0">{vis(t_on)}{rich(xpos, Y0 + row * lh, parts, fs)}</g>'

    # 1. the handshake
    body.append(typed(0, [("./handshake", C["text"]), (" --kem ", C["muted"]), ("ML-KEM-1024", C["amber"]),
                          (" --sig ", C["muted"]), ("ML-DSA-87", C["amber"])], 0.65, 0.03, 2.25))
    steps = [
        ("keygen", [("ek ", C["faint"]), ("1568 B", C["soft"]), ("   dk ", C["faint"]), ("3168 B", C["soft"])]),
        ("encaps", [("ct ", C["faint"]), ("1568 B", C["soft"]), ("   ss ", C["faint"]), ("32 B", C["soft"])]),
        ("decaps", [("shared secret ", C["soft"]), ("matches", C["teal"])]),
        ("sign", [("ML-DSA-87", C["soft"]), ("   σ ", C["faint"]), ("4627 B", C["soft"])]),
        ("verify", [("signature ", C["soft"]), ("valid", C["teal"])]),
    ]
    for k, (lab, vals) in enumerate(steps):
        t_on = 2.3 + k * 0.32
        row = 1 + k
        y = Y0 + row * lh
        body.append(line(row, [(f"{lab:<10}", C["muted"])] + vals, t_on))
        body.append(f'<g opacity="0">{timeline("opacity", [(0, 0), (t_on, 1), (t_on + .3, 0)], DUR)}'
                    + rich(W - 40, y, [("[ ", C["faint"]), ("..", C["faint"]), (" ]", C["faint"])], fs, anchor="end")
                    + "</g>")
        body.append(f'<g opacity="0">{vis(t_on + .3)}'
                    + rich(W - 40, y, [("[ ", C["faint"]), ("ok", C["teal"], 700), (" ]", C["faint"])], fs,
                           anchor="end") + "</g>")
    body.append(line(6, [(f"{'channel':<10}", C["muted"]), ("established", C["teal"], 700), (" · ", C["faint"]),
                         ("quantum-resistant", C["soft"])], 3.95))

    # 2. about.yml
    body.append(typed(8, [("cat ", C["text"]), ("about.yml", C["amber"])], 4.8, 0.045, 5.6))
    about = [
        ("name:", "Thabit Mahmood"),
        ("role:", "PhD Candidate · Faculty of Computing & Informatics, MMU"),
        ("research:", "post-quantum verifiable federated learning"),
        ("interests:", "applied cryptography · UAV network security · AI security"),
        ("work:", "Graduate Research Assistant · TM R&D"),
        ("taught:", "Computer Science & Python · IMAS International School"),
        ("speaks:", "Arabic · English"),
    ]
    for j, (k, v) in enumerate(about):
        parts = [(f"{k:<11}", C["violet"])]
        bits = v.split(" · ")
        for b_i, b in enumerate(bits):
            if b_i:
                parts.append((" · ", C["faint"]))
            parts.append((b, C["text"] if j == 0 else C["soft"], 700 if j == 0 else None))
        body.append(line(9 + j, [p if p[2:] and p[2] else p[:2] for p in parts], 5.65 + j * 0.12))

    # 3. idle prompt
    yf = Y0 + 17 * lh
    body.append(f'<g opacity="0">{vis(6.7)}{rich(X0, yf, prompt, fs)}'
                f'<rect class="caret" x="{f(cmd_x)}" y="{yf - 14}" width="{f(cw)}" height="18" fill="{C["teal"]}"/></g>')

    return card(W, H, "\n".join(body), title="whoami",
                desc="Animated terminal: a post-quantum handshake with ML-KEM-1024 and ML-DSA-87, then an "
                     "about file: Thabit Mahmood, PhD candidate at MMU researching post-quantum verifiable "
                     "federated learning, Graduate Research Assistant at TM R&D.",
                css=css, fonts="/*FONTS*/", accent=C["amber"])


# ---------------------------------------------------------------- research flow

def research() -> str:
    H, DUR = 490, 9.0
    CX, CY, R = 500, 240, 50
    RX, RY = 338, 132
    body = []
    css = """
.led{animation:led 1.6s ease-in-out infinite}
@keyframes led{0%,100%{opacity:1}50%{opacity:.25}}
"""
    defs = f"""
<filter id="pglow" x="-100%" y="-100%" width="300%" height="300%">
<feGaussianBlur stdDeviation="3" result="b"/>
<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
</filter>
<radialGradient id="core" cx=".5" cy=".5" r=".5">
<stop offset="0" stop-color="{C['teal']}" stop-opacity=".22"/>
<stop offset="1" stop-color="{C['teal']}" stop-opacity="0"/>
</radialGradient>
"""
    body.append(rich(40, 46, [("research.flow", C["teal"]), ("  ·  ", C["faint"]),
                              ("post-quantum verifiable federated learning", C["soft"])], 13))
    rounds = ["01", "02", "03", "04", "05"]
    bounds = [0, 6.9, 15.9, 24.9, 33.9, 36.0]
    body.append(text(W - 70, 46, "round", size=12, fill=C["faint"], anchor="end"))
    for r_i, r in enumerate(rounds):
        body.append(f'<g opacity="0">{show_between(bounds[r_i], bounds[r_i + 1], 36.0)}'
                    + text(W - 40, 46, r, size=13, fill=C["amber"], weight=700, anchor="end") + "</g>")
    body.append(f'<line x1="40" y1="64" x2="{W - 40}" y2="64" stroke="{C["rule"]}"/>')

    # aggregator
    def hexpts(r):
        return " ".join(f"{f(CX + r * math.cos(math.radians(a)))},{f(CY + r * math.sin(math.radians(a)))}"
                        for a in range(-90, 270, 60))
    body.append(f'<circle cx="{CX}" cy="{CY}" r="110" fill="url(#core)" opacity="0">'
                + timeline("opacity", [(0, .25), (3.8, .25), (4.3, 1), (5.2, .25)], DUR, calc="linear") + "</circle>")
    body.append(f'<polygon points="{hexpts(R)}" fill="{C["panel"]}" stroke="{C["teal"]}" stroke-width="1.6">'
                + timeline("stroke-width", [(0, 1.6), (3.8, 1.6), (4.25, 3.2), (5.1, 1.6)], DUR, calc="linear")
                + "</polygon>")
    body.append(f'<g><animateTransform attributeName="transform" type="rotate" from="0 {CX} {CY}" '
                f'to="360 {CX} {CY}" dur="40s" repeatCount="indefinite"/>'
                f'<polygon points="{hexpts(R - 11)}" fill="none" stroke="{C["faint"]}" stroke-dasharray="2 5"/></g>')
    body.append(f'<text x="{CX}" y="{CY + 7}" font-size="28" font-weight="800" text-anchor="middle" fill="{C["teal"]}">Σ'
                + timeline("fill", [(0, C["teal"]), (3.9, C["teal"]), (4.3, C["text"]), (5.1, C["teal"])], DUR,
                           calc="linear") + "</text>")
    body.append(text(CX, CY + 27, "aggregator", size=9.5, fill=C["muted"], anchor="middle"))

    angles = [-90, -30, 30, 90, 150, 210]
    subs = "₁₂₃₄₅₆"
    for i, a in enumerate(angles):
        dx, dy = math.cos(math.radians(a)), math.sin(math.radians(a))
        px, py = CX + RX * dx, CY + RY * dy
        # edge between drone and hub
        ux, uy = CX - px, CY - py
        L = math.hypot(ux, uy)
        ux, uy = ux / L, uy / L
        s0 = (px + ux * 30, py + uy * 30)
        s1 = (CX - ux * (R + 6), CY - uy * (R + 6))
        body.append(f'<line x1="{f(s0[0])}" y1="{f(s0[1])}" x2="{f(s1[0])}" y2="{f(s1[1])}" stroke="{C["edge"]}" '
                    f'stroke-width="1.4" stroke-dasharray="4 5"/>')
        path = f"M{f(s0[0])} {f(s0[1])} L{f(s1[0])} {f(s1[1])}"
        back = f"M{f(s1[0])} {f(s1[1])} L{f(s0[0])} {f(s0[1])}"
        # uplink: signed update
        u0, u1 = 2.55 + i * 0.07, 3.65 + i * 0.05
        body.append(f'<g opacity="0" filter="url(#pglow)">'
                    + timeline("opacity", [(0, 0), (2.2 + i * 0.03, 1), (u1, 0)], DUR)
                    + f'<rect x="-7" y="-4.5" width="14" height="9" rx="2" fill="{C["amber"]}"/>'
                    + f'<animateMotion dur="{f(DUR)}s" repeatCount="indefinite" path="{path}" rotate="auto" '
                      f'calcMode="linear" keyPoints="0;0;1;1" keyTimes="0;{f(u0 / DUR)};{f(u1 / DUR)};1"/></g>')
        # verified tick near the hub
        tick = (CX - ux * (R + 20), CY - uy * (R + 20) + 4)
        body.append(f'<g opacity="0">{show_between(u1 + .12 + i * 0.05, 6.9, DUR)}'
                    + text(tick[0], tick[1], "✓", size=12.5, fill=C["teal"], weight=700, anchor="middle") + "</g>")
        # downlink: new global model
        d0, d1 = 5.15 + i * 0.05, 6.25 + i * 0.05
        body.append(f'<g opacity="0" filter="url(#pglow)">'
                    + timeline("opacity", [(0, 0), (d0, 1), (d1, 0)], DUR)
                    + f'<circle r="4.2" fill="{C["teal"]}"/>'
                    + f'<animateMotion dur="{f(DUR)}s" repeatCount="indefinite" path="{back}" '
                      f'calcMode="linear" keyPoints="0;0;1;1" keyTimes="0;{f(d0 / DUR)};{f(d1 / DUR)};1"/></g>')

        # local training progress ring
        circ = 2 * math.pi * 25
        t_end = 1.55 + (i * 37 % 6) * 0.1
        body.append(f'<circle cx="{f(px)}" cy="{f(py)}" r="25" fill="none" stroke="{C["teal"]}" stroke-width="2" '
                    f'stroke-linecap="round" stroke-dasharray="{f(circ)}" stroke-dashoffset="{f(circ)}" '
                    f'transform="rotate(-90 {f(px)} {f(py)})">'
                    + timeline("stroke-dashoffset", [(0, f(circ)), (0.3, f(circ)), (t_end, 0), (DUR, 0)], DUR,
                               calc="linear")
                    + timeline("opacity", [(0, 1), (2.25, 1), (2.6, 0), (DUR - .05, 0)], DUR, calc="linear")
                    + "</circle>")
        body.append(f'<circle cx="{f(px)}" cy="{f(py)}" r="25" fill="none" stroke="{C["rule"]}" stroke-width="2"/>')

        # the drone itself, hovering
        bob = (f'<animateTransform attributeName="transform" type="translate" values="0 0;0 -2.5;0 0" '
               f'dur="{f(2.6 + i * 0.23)}s" begin="-{f(i * 0.4)}s" repeatCount="indefinite"/>')
        parts = [bob]
        for sx in (-1, 1):
            for sy in (-1, 1):
                rx_, ry_ = px + sx * 12.5, py + sy * 12.5
                parts.append(f'<line x1="{f(px + sx * 5)}" y1="{f(py + sy * 5)}" x2="{f(rx_)}" y2="{f(ry_)}" '
                             f'stroke="#4A5E7D" stroke-width="2"/>')
                parts.append(f'<circle cx="{f(rx_)}" cy="{f(ry_)}" r="6.3" fill="{C["bg0"]}" fill-opacity=".6" '
                             f'stroke="{C["faint"]}" stroke-width="1.1"/>')
                spin = "360" if sx * sy > 0 else "-360"
                parts.append(f'<line x1="{f(rx_ - 5)}" y1="{f(ry_)}" x2="{f(rx_ + 5)}" y2="{f(ry_)}" '
                             f'stroke="{C["soft"]}" stroke-width="1.4" stroke-linecap="round">'
                             f'<animateTransform attributeName="transform" type="rotate" from="0 {f(rx_)} {f(ry_)}" '
                             f'to="{spin} {f(rx_)} {f(ry_)}" dur=".28s" repeatCount="indefinite"/></line>')
        parts.append(f'<rect x="{f(px - 7)}" y="{f(py - 7)}" width="14" height="14" rx="3.5" fill="{C["panel"]}" '
                     f'stroke="{C["soft"]}" stroke-width="1.4">'
                     + timeline("stroke", [(0, C["soft"]), (6.25 + i * .05, C["teal"]), (7.1 + i * .05, C["soft"])],
                                DUR) + "</rect>")
        parts.append(f'<circle class="led" cx="{f(px)}" cy="{f(py)}" r="2" fill="{C["teal"]}"/>')
        body.append("<g>" + "".join(parts) + "</g>")
        side = 1 if dx > -.2 else -1
        lx, ly = px + 42 * side, py + 4
        anchor = "start" if side > 0 else "end"
        body.append(rich(lx, ly, [("uav", C["muted"]), (subs[i], C["muted"])], 11.5, anchor=anchor))

    # stage strip
    stages = ["local training", "sign · ML-DSA", "upload · ML-KEM", "verify + aggregate", "broadcast"]
    spans_t = [(0, 2.2), (2.2, 2.6), (2.6, 3.8), (3.8, 5.0), (5.0, DUR)]
    gap = 22
    widths = [tw(s, 11.5) + 26 for s in stages]
    total = sum(widths) + gap * (len(stages) - 1)
    sx = (W - total) / 2
    xs = []
    for wdt in widths:
        xs.append(sx)
        sx += wdt + gap
    SY = 442
    body.append(f'<line x1="40" y1="410" x2="{W - 40}" y2="410" stroke="{C["rule"]}"/>')
    pill_x = [(0, f(xs[0]))]
    pill_w = [(0, f(widths[0]))]
    for k in range(1, len(stages)):
        t = spans_t[k][0]
        pill_x += [(t - 0.001, f(xs[k - 1])), (t + 0.22, f(xs[k]))]
        pill_w += [(t - 0.001, f(widths[k - 1])), (t + 0.22, f(widths[k]))]
    body.append(f'<rect x="{f(xs[0])}" y="{SY - 17}" width="{f(widths[0])}" height="25" rx="12.5" '
                f'fill="{C["teal"]}" fill-opacity=".09" stroke="{C["teal"]}" stroke-opacity=".55">'
                + timeline("x", pill_x, DUR, calc="linear") + timeline("width", pill_w, DUR, calc="linear")
                + "</rect>")
    for k, st in enumerate(stages):
        t0, t1 = spans_t[k]
        pts = [(0, C["faint"]), (t0, C["text"]), (t1, C["faint"])] if t0 > 0 else [(0, C["text"]), (t1, C["faint"])]
        body.append(f'<text x="{f(xs[k] + widths[k] / 2)}" y="{SY}" font-size="11.5" text-anchor="middle" '
                    f'fill="{C["faint"]}">{x(st)}' + timeline("fill", pts, DUR) + "</text>")
    body.append(text(40, H - 14, "schematic only · protocol specifics withheld until publication", size=10.5,
                     fill=C["faint"]))
    body.append(text(W - 40, H - 14, "each drone is a federated client", size=10.5, fill=C["faint"], anchor="end"))

    return card(W, H, "\n".join(body), title="Research flow",
                desc="Animated schematic of a federated learning round: six drones train locally, sign updates "
                     "with ML-DSA, upload over ML-KEM channels, the aggregator verifies and aggregates, then "
                     "broadcasts the new global model.",
                css=css, defs=defs, fonts="/*FONTS*/", accent=C["violet"])


# ---------------------------------------------------------------- capabilities

def stack() -> str:
    rows = [
        ("crypto", C["teal"], ["ML-KEM", "ML-DSA", "lattice cryptography", "HKDF", "Ed25519", "protocol design"]),
        ("learning", C["violet"], ["federated learning", "PyTorch", "deep learning", "medical imaging"]),
        ("security", C["amber"], ["threat modelling", "intrusion detection", "UAV networks", "secure systems"]),
        ("languages", C["sky"], ["Python", "Rust", "Go", "TypeScript", "Kotlin", "Bash"]),
        ("systems", C["slate"], ["Linux", "Docker", "Git", "GitHub Actions", "CI/CD", "Cypress"]),
        ("research", C["rose"], ["systematic reviews", "academic writing", "conference organising", "teaching"]),
    ]
    top, rh = 92, 42
    H = top + len(rows) * rh + 22
    n_items = sum(len(r[2]) for r in rows)
    body = []
    css = """
@keyframes sweep{0%{transform:translateX(-420px)}60%,100%{transform:translateX(1400px)}}
.glare{animation:sweep 9s ease-in-out 3s infinite}
"""
    defs = """
<linearGradient id="gl" x1="0" y1="0" x2="1" y2="0">
<stop offset="0" stop-color="#fff" stop-opacity="0"/>
<stop offset=".5" stop-color="#fff" stop-opacity=".055"/>
<stop offset="1" stop-color="#fff" stop-opacity="0"/>
</linearGradient>
"""
    body.append(rich(40, 46, [("capabilities", C["teal"]), (".negotiate", C["soft"]), ("()", C["faint"])], 13))
    body.append(rich(W - 40, 46, [(f"{len(rows)}", C["amber"], 700), (" groups  ·  ", C["faint"]),
                                  (f"{n_items}", C["amber"], 700), (" suites accepted", C["faint"])], 12,
                     anchor="end"))
    body.append(f'<line x1="40" y1="64" x2="{W - 40}" y2="64" stroke="{C["rule"]}"/>')
    body.append(f'<line x1="48" y1="{top - 4}" x2="48" y2="{top + (len(rows) - 1) * rh}" stroke="{C["edge"]}"/>')
    fs = 12.5
    for r_i, (cat, col, items) in enumerate(rows):
        cy = top + r_i * rh
        t_row = 0.25 + r_i * 0.22
        body.append(f'<line x1="48" y1="{cy}" x2="62" y2="{cy}" stroke="{C["edge"]}"/>')
        body.append(f'<circle cx="48" cy="{cy}" r="2.6" fill="{col}"/>')
        body.append(f'<g opacity="0">' + timeline("opacity", [(0, 0), (t_row, 0), (t_row + .4, 1)], 30,
                                                  calc="linear", repeat=False)
                    + text(72, cy + 4.5, cat, size=13, fill=C["muted"]) + "</g>")
        px = 192
        for k, it in enumerate(items):
            wdt = tw(it, fs) + 24
            t_in = t_row + 0.12 + k * 0.06
            body.append(
                f'<g opacity="0">'
                + timeline("opacity", [(0, 0), (t_in, 0), (t_in + .35, 1)], 30, calc="linear", repeat=False)
                + f'<animateTransform attributeName="transform" type="translate" values="0 7;0 7;0 0" '
                  f'keyTimes="0;{f(t_in / 30)};{f((t_in + .35) / 30)}" dur="30s" fill="freeze" calcMode="spline" '
                  f'keySplines="0 0 1 1;.2 .8 .3 1"/>'
                + f'<rect x="{f(px)}" y="{cy - 13}" width="{f(wdt)}" height="26" rx="7" fill="{col}" '
                  f'fill-opacity=".07" stroke="{col}" stroke-opacity=".45"/>'
                + text(px + 12, cy + 4.5, it, size=fs, fill=C["soft"])
                + "</g>")
            px += wdt + 9
    body.append(f'<rect class="glare" x="0" y="0" width="320" height="{H}" fill="url(#gl)" '
                f'transform="skewX(-18)"/>')
    return card(W, H, "\n".join(body), title="Capabilities",
                desc="Skills grouped as a negotiation transcript: post-quantum crypto (ML-KEM, ML-DSA, lattices), "
                     "federated and deep learning, security, languages (Python, Rust, Go, TypeScript, Kotlin, Bash), "
                     "systems and research.",
                css=css, defs=defs, fonts="/*FONTS*/", accent=C["sky"])


# ---------------------------------------------------------------- footer

def footer() -> str:
    H = 116
    body = []
    css = """
.mq{animation:mq 38s linear infinite}
@keyframes mq{from{transform:translateX(0)}to{transform:translateX(var(--p))}}
.caret{animation:blink 1.05s steps(1) infinite}
@keyframes blink{0%{opacity:1}50%{opacity:0}}
"""
    cw = 13 * 0.6
    body.append(rich(40, 48, [("$ ", C["teal"])], 13))
    widths = [(0, 0), (0.5, 0)] + [(0.5 + k * 0.09, f(k * cw)) for k in range(1, 5)]
    body.append(f'<clipPath id="ex"><rect x="{f(40 + 2 * cw)}" y="30" height="24" width="0">'
                + timeline("width", widths, 30, repeat=False) + "</rect></clipPath>")
    body.append(f'<g clip-path="url(#ex)">{text(40 + 2 * cw, 48, "exit", size=13, fill=C["text"])}</g>')
    body.append(f'<g opacity="0">' + timeline("opacity", [(0, 0), (1.1, 0), (1.5, 1)], 30, calc="linear",
                                              repeat=False)
                + rich(40 + 8 * cw, 48, [("session closed", C["soft"]), ("  ·  ", C["faint"]),
                                         ("transcript signed", C["muted"])], 13) + "</g>")
    hexrun = "".join(rng.choice("0123456789abcdef") for _ in range(132))
    period = len(hexrun) * 12 * 0.6
    body.append(f'<clipPath id="mqc"><rect x="66" y="64" width="640" height="26"/></clipPath>')
    body.append(text(40, 82, "σ", size=13, fill=C["amber"], weight=700))
    body.append(f'<g clip-path="url(#mqc)"><g class="mq" style="--p:-{f(period)}px">'
                + text(66, 82, hexrun + hexrun, size=12, fill=C["teal"], extra='opacity=".55"') + "</g></g>")
    body.append(f'<g opacity="0">' + timeline("opacity", [(0, 0), (1.9, 0), (2.3, 1)], 30, calc="linear",
                                              repeat=False)
                + rich(W - 40, 82, [("ML-DSA-87 ", C["muted"]), ("✓ verified", C["teal"], 700)], 13, anchor="end")
                + "</g>")
    body.append(rich(W - 40, 48, [("thanks for visiting", C["faint"])], 12, anchor="end"))
    return card(W, H, "\n".join(body), title="Session closed",
                desc="Closing terminal line: exit, session closed, transcript signed with ML-DSA-87 and verified.",
                css=css, fonts="/*FONTS*/")


def orcid_button() -> str:
    label = [("ORCID", C["text"], 700), ("  0009-0003-3909-3427", C["muted"])]
    n = sum(len(p[0]) for p in label)
    w = int(52 + n * 13 * 0.6 + 22)
    h = 46
    body = (f'<circle cx="27" cy="23" r="12" fill="#A6CE39"/>'
            + text(27, 27.5, "iD", size=11, weight=800, fill="#FFFFFF", anchor="middle")
            + rich(50, 27.5, label, 13))
    return (card(w, h, body, title="ORCID 0009-0003-3909-3427",
                 desc="Link to Thabit Mahmood's ORCID record", fonts="/*FONTS*/", accent="#A6CE39")
            .replace('rx="16"', 'rx="23"').replace('rx="15.5"', 'rx="22.5"'))


if __name__ == "__main__":
    ASSETS.mkdir(exist_ok=True)
    FONTS.mkdir(exist_ok=True)
    write("hero.svg", hero())
    write("terminal.svg", terminal())
    write("research.svg", research())
    write("stack.svg", stack())
    write("footer.svg", footer())
    write("btn-orcid.svg", orcid_button(), weights=(400, 700, 800))
    live_fonts()
