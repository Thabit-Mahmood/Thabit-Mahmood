"""Typesets the profile README as a short research paper.

Every block (title, sections, references) is an SVG built on one grid:
an 840-unit page, a 500-unit main column and a 280-unit margin for figures
and side notes. Text is measured with the real font metrics and justified,
so the blocks read like a typeset page rather than a web widget.

    pip install fonttools brotli
    SERIF=... MONO=... python3 scripts/paper.py

SERIF: fontsource Newsreader files (newsreader-latin-<w>-<style>.woff2)
MONO:  JetBrains Mono TTFs
Each block is written twice, assets/<name>-light.svg and -dark.svg.
"""
from __future__ import annotations

import base64
import io
import math
import os
import pathlib
from xml.sax.saxutils import escape

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
SERIF = pathlib.Path(os.environ.get("SERIF", "fonts"))
MONO = pathlib.Path(os.environ.get("MONO", "fonts"))

W = 840
MAIN = 520          # main column width
MX = 556            # margin column x
MW = W - MX         # margin column width

THEMES = {
    "light": dict(ink="#1F2328", body="#2F353D", muted="#59636E", faint="#8C959F", rule="#D0D7DE",
                  dot="#C3CBD4", pub="#8C959F", acc="#0D7A66", cell=".15", fig="#57606A"),
    "dark": dict(ink="#F0F3F6", body="#D1D7E0", muted="#9198A1", faint="#6E7681", rule="#30363D",
                 dot="#3A424C", pub="#7D8590", acc="#4FC8AE", cell=".22", fig="#9198A1"),
}

FACES = {
    ("serif", 400, "normal"): SERIF / "newsreader-latin-400-normal.woff2",
    ("serif", 400, "italic"): SERIF / "newsreader-latin-400-italic.woff2",
    ("serif", 500, "normal"): SERIF / "newsreader-latin-500-normal.woff2",
    ("serif", 600, "normal"): SERIF / "newsreader-latin-600-normal.woff2",
    ("mono", 400, "normal"): MONO / "JetBrainsMono-Regular.ttf",
}
_metrics = {}


def face(fam, wt, st):
    key = (fam, wt, st)
    if key not in _metrics:
        tt = TTFont(str(FACES[key]))
        _metrics[key] = (tt.getBestCmap(), tt["hmtx"], tt["head"].unitsPerEm)
    return _metrics[key]


def width(s, size, fam="serif", wt=400, st="normal", spacing=0.0):
    cmap, hmtx, upm = face(fam, wt, st)
    adv = 0
    for ch in s:
        g = cmap.get(ord(ch))
        adv += hmtx[g][0] if g else upm * 0.5
    return adv * size / upm + spacing * max(len(s) - 1, 0)


def f(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


class Block:
    """One SVG block. Collects text per face so fonts can be subset exactly."""

    def __init__(self, theme):
        self.c = THEMES[theme]
        self.parts = []
        self.used = {}
        self.css = []

    def use(self, fam, wt, st, s):
        self.used.setdefault((fam, wt, st), set()).update(s)

    def text(self, x, y, s, size, fam="serif", wt=400, st="normal", fill=None, anchor="start",
             spacing=0.0, extra="", cls=""):
        self.use(fam, wt, st, s)
        fill = fill or self.c["body"]
        ls = f' letter-spacing="{f(spacing)}"' if spacing else ""
        self.parts.append(
            f'<text x="{f(x)}" y="{f(y)}" class="{fam[0]} {cls}" font-size="{f(size)}" font-weight="{wt}" '
            f'font-style="{st}" fill="{fill}" text-anchor="{anchor}"{ls} {extra}>{escape(s)}</text>')

    def runs(self, x, y, runs, size, anchor="start", extra=""):
        """runs: [(text, fam, wt, st, fill), ...] on one baseline."""
        spans = []
        for t, fam, wt, st, fill in runs:
            self.use(fam, wt, st, t)
            spans.append(f'<tspan class="{fam[0]}" font-weight="{wt}" font-style="{st}" '
                         f'fill="{fill}">{escape(t)}</tspan>')
        self.parts.append(f'<text x="{f(x)}" y="{f(y)}" font-size="{f(size)}" text-anchor="{anchor}" '
                          f'{extra}>{"".join(spans)}</text>')

    def para(self, x, y, w, s, size=16.0, lead=25.0, st="normal", wt=400, fill=None,
             justify=True, indent=0.0, bold=()):
        """Greedy line breaking with measured widths; justified except the last line.
        Words listed in `bold` (ignoring trailing punctuation) are set in semibold ink."""
        fill = fill or self.c["body"]

        def style(wd):
            core = wd.rstrip(".,;:")
            if core in bold:
                return 600, "normal", self.c["ink"]
            return wt, st, fill

        def wlen(wd):
            w_, s_, _ = style(wd)
            return width(wd, size, "serif", w_, s_)

        words = s.split()
        space = width(" ", size, "serif", wt, st)
        lines, cur, cur_w = [], [], 0.0
        for wd in words:
            ww = wlen(wd)
            avail = w - (indent if not lines else 0)
            if cur and cur_w + space + ww > avail:
                lines.append(cur)
                cur, cur_w = [wd], ww
            else:
                cur_w = cur_w + (space if cur else 0) + ww
                cur.append(wd)
        if cur:
            lines.append(cur)
        for i, ln in enumerate(lines):
            lx = x + (indent if i == 0 else 0)
            lw = w - (indent if i == 0 else 0)
            yy = y + i * lead
            widths = [wlen(wd) for wd in ln]
            gap = (lw - sum(widths)) / (len(ln) - 1) if len(ln) > 1 else 0
            just = justify and i < len(lines) - 1 and gap <= space * 2.4
            if not just:
                gap = space
            px = lx
            for j, wd in enumerate(ln):
                w_, s_, col = style(wd)
                if just and j == len(ln) - 1:
                    self.text(lx + lw, yy, wd, size, wt=w_, st=s_, fill=col, anchor="end")
                else:
                    self.text(px, yy, wd, size, wt=w_, st=s_, fill=col)
                px += widths[j] + gap
        return y + (len(lines) - 1) * lead

    def raw(self, s):
        self.parts.append(s)

    def svg(self, h, title, desc):
        faces = []
        for (fam, wt, st), chars in sorted(self.used.items()):
            data = subset_b64(FACES[(fam, wt, st)], "".join(sorted(chars)))
            fname = "S" if fam == "serif" else "M"
            faces.append(f"@font-face{{font-family:{fname};font-weight:{wt};font-style:{st};"
                         f"src:url(data:font/woff2;base64,{data}) format('woff2')}}")
        css = "\n".join(faces) + """
.s{font-family:S,'Newsreader','Iowan Old Style',Georgia,serif}
.m{font-family:M,'JetBrains Mono',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-ligatures:none}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
""" + "\n".join(self.css)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{f(h)}" viewBox="0 0 {W} {f(h)}" '
                f'role="img" aria-labelledby="t d" xml:space="preserve"><title id="t">{escape(title)}</title>'
                f'<desc id="d">{escape(desc)}</desc><style>{css}</style>\n' + "\n".join(self.parts) + "\n</svg>\n")


def subset_b64(path, chars):
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


# ------------------------------------------------------------------ pieces

def section_head(b, num, title, y=34):
    c = b.c
    b.raw(f'<line x1="0" y1="0.5" x2="{W}" y2="0.5" stroke="{c["rule"]}"/>')
    if num:
        b.text(0, y, num, 15, fam="mono", fill=c["acc"])
        b.text(24, y, title, 22, wt=600, fill=c["ink"])
    else:
        b.text(0, y, title, 22, wt=600, fill=c["ink"])


def caption(b, x, y, w, label, s, size=13.0, lead=19.0):
    c = b.c
    lab_w = width(label + " ", size, "serif", 600, "normal")
    b.text(x, y, label, size, wt=600, fill=c["muted"])
    # first line after the label, the rest wraps under it
    return b.para(x, y, w, s, size=size, lead=lead, st="italic", fill=c["muted"], justify=False, indent=lab_w)


def arrow(b, p, q, colour, cls, sw=1.6):
    ang = math.atan2(q[1] - p[1], q[0] - p[0])
    end = (q[0] - 5.5 * math.cos(ang), q[1] - 5.5 * math.sin(ang))
    pts = [q] + [(q[0] + 7 * math.cos(ang + d), q[1] + 7 * math.sin(ang + d)) for d in (2.6, -2.6)]
    d = "M" + " L".join(f"{f(a)} {f(c_)}" for a, c_ in pts) + " Z"
    b.raw(f'<path class="{cls} draw" pathLength="1" d="M{f(p[0])} {f(p[1])} L{f(end[0])} {f(end[1])}" '
          f'stroke="{colour}" stroke-width="{sw}" stroke-linecap="round" fill="none"/>'
          f'<path class="{cls} late" d="{d}" fill="{colour}"/>')


# ------------------------------------------------------------------ blocks

ABSTRACT = ("I study how to keep federated learning trustworthy once quantum computers arrive. In federated "
            "learning many parties train one model without pooling their data. My PhD at Multimedia University "
            "asks how every participant can check that the shared model was computed honestly, and how to keep "
            "that guarantee against an adversary with a quantum computer.")
KEYWORDS = "post-quantum cryptography, federated learning, lattice-based cryptography, verifiable computation"


def title_block(theme):
    b = Block(theme)
    c = b.c
    b.text(0, 16, "MULTIMEDIA UNIVERSITY  ·  FACULTY OF COMPUTING AND INFORMATICS", 11, fam="mono",
           fill=c["faint"], spacing=1.4)
    b.text(W, 16, "CYBERJAYA, MALAYSIA", 11, fam="mono", fill=c["faint"], anchor="end", spacing=1.4)
    b.raw(f'<line x1="0" y1="30.5" x2="{W}" y2="30.5" stroke="{c["rule"]}"/>')
    b.text(-2, 96, "Thabit Mahmood", 54, wt=500, fill=c["ink"], spacing=-0.8)
    b.text(0, 134, "Post-quantum cryptography for verifiable federated learning", 22, st="italic", fill=c["body"])
    b.runs(0, 170, [("PhD Candidate", "serif", 500, "normal", c["ink"]),
                    (", Multimedia University", "serif", 400, "normal", c["muted"]),
                    ("     ·     ", "serif", 400, "normal", c["faint"]),
                    ("Graduate Research Assistant", "serif", 500, "normal", c["ink"]),
                    (", TM R&D", "serif", 400, "normal", c["muted"])], 15.5)
    y = 222
    b.text(56, y, "ABSTRACT", 11, fam="mono", fill=c["acc"], spacing=1.6)
    y = b.para(56, y + 28, W - 112, ABSTRACT, size=16, lead=25)
    y += 34
    kw_lab = "Keywords: "
    b.runs(56, y, [(kw_lab, "serif", 600, "normal", c["muted"]),
                   (KEYWORDS, "serif", 400, "italic", c["muted"])], 14.5)
    h = y + 26
    return b.svg(h, "Thabit Mahmood",
                 "Title block. Thabit Mahmood. Post-quantum cryptography for verifiable federated learning. "
                 "PhD Candidate, Multimedia University. Graduate Research Assistant, TM R&D. Abstract: " + ABSTRACT)


S1 = ("Federated learning trains a shared model while the data stays where it was produced. In each round, "
      "participants send model updates to an aggregator and receive the combined model back. Two guarantees "
      "are usually missing. Participants have no way to confirm that the aggregate they receive is correct, and "
      "the public-key cryptography that protects the exchange, RSA and elliptic curves, falls to a large "
      "quantum computer running Shor's algorithm.")
CAP1 = "One round of federated learning. Updates flow in and the new model flows out, yet nothing in the round proves the aggregate is honest."


def section1(theme):
    b = Block(theme)
    c = b.c
    section_head(b, "1", "The problem")
    end = b.para(0, 72, MAIN, S1)

    # Figure 1: an aggregator and five clients, one slow repeating round
    fx, fy, fw = MX, 52, MW
    srv = (fx + fw / 2, fy + 34)
    xs = [fx + 26 + k * (fw - 52) / 4 for k in range(5)]
    cy = fy + 150
    DUR = 7.0
    b.css.append("""
@keyframes up{0%,4%{offset-distance:0%;opacity:0}8%{opacity:1}30%{offset-distance:100%;opacity:1}33%,100%{offset-distance:100%;opacity:0}}
@keyframes down{0%,44%{offset-distance:0%;opacity:0}48%{opacity:1}70%{offset-distance:100%;opacity:1}73%,100%{offset-distance:100%;opacity:0}}
@keyframes hub{0%,30%,48%,100%{stroke-width:1.4}36%{stroke-width:3}}
@keyframes q{0%,100%{opacity:.55}50%{opacity:1}}
.up{animation:up 7s cubic-bezier(.45,0,.55,1) infinite}
.down{animation:down 7s cubic-bezier(.45,0,.55,1) infinite}
.hub{animation:hub 7s ease-in-out infinite}
.qm{animation:q 3.5s ease-in-out infinite}
""")
    for k, xk in enumerate(xs):
        b.raw(f'<line x1="{f(xk)}" y1="{f(cy - 9)}" x2="{f(srv[0])}" y2="{f(srv[1] + 14)}" stroke="{c["rule"]}" '
              f'stroke-width="1.2"/>')
    for k, xk in enumerate(xs):
        path_up = f"M{f(xk)} {f(cy - 9)} L{f(srv[0])} {f(srv[1] + 14)}"
        path_dn = f"M{f(srv[0])} {f(srv[1] + 14)} L{f(xk)} {f(cy - 9)}"
        d = k * 0.08
        b.raw(f'<circle class="up" r="2.6" fill="{c["fig"]}" style="offset-path:path(\'{path_up}\');'
              f'animation-delay:{f(d)}s"/>')
        b.raw(f'<circle class="down" r="2.6" fill="{c["acc"]}" style="offset-path:path(\'{path_dn}\');'
              f'animation-delay:{f(d)}s"/>')
        b.raw(f'<rect x="{f(xk - 9)}" y="{f(cy - 9)}" width="18" height="18" rx="4" fill="none" '
              f'stroke="{c["fig"]}" stroke-width="1.4"/>')
    b.raw(f'<rect class="hub" x="{f(srv[0] - 44)}" y="{f(srv[1] - 14)}" width="88" height="28" rx="6" '
          f'fill="none" stroke="{c["acc"]}" stroke-width="1.4"/>')
    b.text(srv[0], srv[1] + 4.5, "aggregator", 11.5, fam="mono", fill=c["ink"], anchor="middle")
    b.text(srv[0] + 54, srv[1] + 6, "verified?", 15, st="italic", fill=c["acc"], cls="qm")
    b.text(srv[0], cy + 28, "participants", 11.5, fam="mono", fill=c["muted"], anchor="middle")
    cap_end = caption(b, fx, cy + 62, fw, "Figure 1.", CAP1)
    h = max(end, cap_end) + 22
    return b.svg(h, "1 The problem", "Section 1, The problem. " + S1 + " Figure 1. " + CAP1)


S2a = ("My work builds federated learning on lattice-based cryptography, the family NIST standardised in 2024 as "
       "ML-KEM (FIPS 203) and ML-DSA (FIPS 204). Its security rests on the learning with errors problem.")
S2b = ("Given A and b, recovering the secret s is believed to be hard even for a quantum computer. The aim is a "
       "protocol in which updates stay protected and every participant can verify the aggregate. Details will "
       "follow with publication.")
CAP2 = "One lattice, two bases. The short basis is the secret trapdoor and the long, skewed one is public. Both enclose the same area."


def section2(theme):
    b = Block(theme)
    c = b.c
    section_head(b, "2", "The approach")
    y = b.para(0, 72, MAIN, S2a)
    # displayed equation (1)
    ey = y + 52
    b.runs(MAIN / 2, ey, [("b", "serif", 600, "normal", c["ink"]), ("  =  ", "serif", 400, "normal", c["body"]),
                          ("A", "serif", 600, "normal", c["ink"]), ("s", "serif", 600, "normal", c["ink"]),
                          ("  +  ", "serif", 400, "normal", c["body"]), ("e", "serif", 600, "normal", c["ink"]),
                          ("    (mod ", "serif", 400, "normal", c["body"]), ("q", "serif", 400, "italic", c["ink"]),
                          (")", "serif", 400, "normal", c["body"])], 22, anchor="middle")
    b.text(MAIN, ey, "(1)", 15, fill=c["muted"], anchor="end")
    end = b.para(0, ey + 50, MAIN, S2b, bold={"A", "b", "s"})

    # Figure 2: one lattice, a short secret basis and a long public basis of equal volume
    g1, g2 = (30.0, 0.0), (9.0, -28.0)
    U = ((1, 1), (2, 3))
    b1 = (U[0][0] * g1[0] + U[0][1] * g2[0], U[0][0] * g1[1] + U[0][1] * g2[1])
    b2 = (U[1][0] * g1[0] + U[1][1] * g2[0], U[1][0] * g1[1] + U[1][1] * g2[1])
    assert abs(b1[0] * b2[1] - b1[1] * b2[0]) == abs(g1[0] * g2[1] - g1[1] * g2[0])
    box = (MX + 4, 56, W - 4, 214)
    O = (MX + 92, 196)
    add = lambda *v: (sum(a[0] for a in v), sum(a[1] for a in v))
    b.css.append("""
@keyframes fade{from{opacity:0}to{opacity:1}}
@keyframes draw{from{stroke-dashoffset:1}to{stroke-dashoffset:0}}
.pt{animation:fade .5s ease-out both;animation-delay:var(--d)}
.pub.draw{stroke-dasharray:1;animation:draw .8s cubic-bezier(.4,0,.2,1) .7s both}
.sec.draw{stroke-dasharray:1;animation:draw .8s cubic-bezier(.4,0,.2,1) 1.5s both}
.pub.late,.pub.cell{animation:fade .45s ease-out 1.3s both}
.sec.late,.sec.cell{animation:fade .45s ease-out 2.1s both}
""")
    for a in range(-10, 14):
        for k in range(-3, 9):
            p = add(O, (a * g1[0] + k * g2[0], a * g1[1] + k * g2[1]))
            tipx, tipy = O[0] + b2[0], O[1] + b2[1]
            under_pub = tipx + 2 <= p[0] <= tipx + 58 and tipy - 12 <= p[1] <= tipy + 10
            under_sec = O[0] - 64 <= p[0] <= O[0] - 4 and O[1] - 12 <= p[1] <= O[1] + 10
            if box[0] <= p[0] <= box[2] and box[1] <= p[1] <= box[3] and not (under_pub or under_sec):
                d = math.hypot(p[0] - O[0], p[1] - O[1]) / 900
                b.raw(f'<circle class="pt" style="--d:{f(d)}s" cx="{f(p[0])}" cy="{f(p[1])}" r="1.8" fill="{c["dot"]}"/>')
    poly = lambda pts: " ".join(f"{f(x_)},{f(y_)}" for x_, y_ in pts)
    b.raw(f'<polygon class="pub cell" points="{poly([O, add(O, b1), add(O, b1, b2), add(O, b2)])}" fill="{c["pub"]}" '
          f'fill-opacity=".09" stroke="{c["pub"]}" stroke-opacity=".55"/>')
    b.raw(f'<polygon class="sec cell" points="{poly([O, add(O, g1), add(O, g1, g2), add(O, g2)])}" '
          f'fill="{c["acc"]}" fill-opacity="{c["cell"]}"/>')
    for v in (b1, b2):
        arrow(b, O, add(O, v), c["pub"], "pub")
    for v in (g1, g2):
        arrow(b, O, add(O, v), c["acc"], "sec")
    b.raw(f'<circle cx="{f(O[0])}" cy="{f(O[1])}" r="2.5" fill="{c["ink"]}"/>')
    tip = add(O, b2)
    b.text(tip[0] + 9, tip[1] + 5, "public", 11.5, fam="mono", fill=c["muted"], cls="pub late")
    b.text(O[0] - 9, O[1] + 5, "secret", 11.5, fam="mono", fill=c["acc"], anchor="end", cls="sec late")
    cap_end = caption(b, MX, 246, MW, "Figure 2.", CAP2)
    h = max(end, cap_end) + 22
    return b.svg(h, "2 The approach", "Section 2, The approach. " + S2a + " Equation 1: b = A s + e mod q. " + S2b
                 + " Figure 2. " + CAP2)


TABLE = [
    ("Post-quantum", "ML-KEM, ML-DSA, lattice-based cryptography"),
    ("Languages", "Python, Rust, Go, TypeScript"),
    ("Tooling", "Linux, Git, GitHub Actions"),
]
NOTE = "Code and papers will appear on this profile once they are published."


def section3(theme):
    b = Block(theme)
    c = b.c
    section_head(b, "3", "Tools")
    caption(b, 0, 72, MAIN, "Table 1.", "What I work with.")
    top = 92
    col2 = 150
    b.raw(f'<line x1="0" y1="{top}" x2="{MAIN}" y2="{top}" stroke="{c["ink"]}" stroke-width="1.3"/>')
    b.text(0, top + 24, "Area", 14.5, wt=600, fill=c["ink"])
    b.text(col2, top + 24, "Tools", 14.5, wt=600, fill=c["ink"])
    b.raw(f'<line x1="0" y1="{top + 36}" x2="{MAIN}" y2="{top + 36}" stroke="{c["ink"]}" stroke-width=".7"/>')
    y = top + 62
    for area, tools in TABLE:
        b.text(0, y, area, 15.5, st="italic", fill=c["body"])
        b.text(col2, y, tools, 15.5, fill=c["body"])
        y += 30
    bottom = y - 14
    b.raw(f'<line x1="0" y1="{bottom}" x2="{MAIN}" y2="{bottom}" stroke="{c["ink"]}" stroke-width="1.3"/>')
    # side note in the margin
    b.raw(f'<line x1="{MX}" y1="{top}" x2="{MX}" y2="{top + 64}" stroke="{c["acc"]}" stroke-width="2"/>')
    note_end = b.para(MX + 16, top + 20, MW - 16, NOTE, size=14, lead=21, st="italic", fill=c["muted"],
                      justify=False)
    h = max(bottom, note_end) + 26
    return b.svg(h, "3 Tools", "Section 3, Tools. Table 1: " +
                 "; ".join(f"{a}: {t}" for a, t in TABLE) + ". " + NOTE)


def refs_head(theme):
    b = Block(theme)
    section_head(b, "", "References")
    return b.svg(46, "References", "References")


REFS = [
    ("1", "LinkedIn", "linkedin.com/in/thabit-mahmood"),
    ("2", "ORCID iD 0009-0003-3909-3427", "orcid.org/0009-0003-3909-3427"),
]


def ref_row(theme, num, what, url):
    b = Block(theme)
    c = b.c
    b.text(0, 22, f"[{num}]", 15.5, fill=c["muted"])
    b.runs(44, 22, [("Thabit Mahmood. ", "serif", 400, "normal", c["body"]),
                    (what + ". ", "serif", 400, "italic", c["body"]),
                    (url, "mono", 400, "normal", c["acc"])], 15.5)
    return b.svg(32, f"[{num}] {what}", f"Reference {num}: Thabit Mahmood, {what}, {url}")


def colophon(theme):
    b = Block(theme)
    c = b.c
    b.raw(f'<line x1="0" y1="0.5" x2="{W}" y2="0.5" stroke="{c["rule"]}"/>')
    b.text(0, 30, "Set in Newsreader and JetBrains Mono. Figures drawn by hand in SVG.", 12.5, st="italic",
           fill=c["faint"])
    b.raw(f'<rect x="{W - 9}" y="20" width="9" height="11" fill="{c["ink"]}"/>')  # end of proof
    return b.svg(42, "Colophon", "Set in Newsreader and JetBrains Mono. Figures drawn by hand in SVG.")


if __name__ == "__main__":
    out = ROOT / "assets"
    out.mkdir(exist_ok=True)
    blocks = {"title": title_block, "s1": section1, "s2": section2, "s3": section3,
              "refs": refs_head, "colophon": colophon}
    for theme in THEMES:
        for name, fn in blocks.items():
            (out / f"{name}-{theme}.svg").write_text(fn(theme), encoding="utf-8")
        for num, what, url in REFS:
            (out / f"ref{num}-{theme}.svg").write_text(ref_row(theme, num, what, url), encoding="utf-8")
    for p in sorted(out.glob("*.svg")):
        print(f"{p.name:22s} {p.stat().st_size / 1024:5.1f} KB")
