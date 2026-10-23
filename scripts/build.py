"""Renders the profile cards from identity/ and assets/status.json.

    pip install fonttools brotli cryptography
    python3 verify.py --status assets/status.json
    python3 scripts/build.py

Signing is done by scripts/sign.py; this script only draws. The guilloche seal is
generated from the signing key's fingerprint, so a different key draws a
different seal, much like SSH's randomart.

The cards borrow the language of security printing. Banknotes and passports
use guilloche (interlaced spirograph line work), seals and microprint so a
forgery is hard to make; this card carries the same marks and, underneath,
a real post-quantum signature over the facts it states.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import math
import os
import pathlib
from xml.sax.saxutils import escape

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
ID = ROOT / "identity"
OUT = ROOT / "assets"
SERIF = pathlib.Path(os.environ.get("SERIF", ROOT / "fonts"))
MONO = pathlib.Path(os.environ.get("MONO", ROOT / "fonts"))

W = 840
THEMES = {
    "light": dict(paper="#F6F3EB", ink="#1A222C", body="#38424D", muted="#66707B", faint="#9AA1A9",
                  rule="#DAD4C5", teal="#1F6E64", bronze="#8C6B3A", wave=".11", shadow=True, sheen="#FFFFFF",
                  alert="#B42318"),
    "dark": dict(paper="#10161E", ink="#EEF1F4", body="#CBD3DC", muted="#97A1AC", faint="#66717D",
                 rule="#29323C", teal="#53C6AE", bronze="#C9A66B", wave=".13", shadow=False, sheen="#BFF5E9",
                 alert="#FF7B72"),
}
FACES = {
    ("serif", 400, "normal"): SERIF / "newsreader-latin-400-normal.woff2",
    ("serif", 400, "italic"): SERIF / "newsreader-latin-400-italic.woff2",
    ("serif", 500, "normal"): SERIF / "newsreader-latin-500-normal.woff2",
    ("serif", 600, "normal"): SERIF / "newsreader-latin-600-normal.woff2",
    ("mono", 400, "normal"): MONO / "JetBrainsMono-Regular.ttf",
}
_metrics: dict = {}


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def f(v: float) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


def width(s, size, fam="serif", wt=400, st="normal", spacing=0.0):
    key = (fam, wt, st)
    if key not in _metrics:
        tt = TTFont(str(FACES[key]))
        _metrics[key] = (tt.getBestCmap(), tt["hmtx"], tt["head"].unitsPerEm)
    cmap, hmtx, upm = _metrics[key]
    adv = sum(hmtx[cmap[ord(c)]][0] if ord(c) in cmap else upm * 0.5 for c in s)
    return adv * size / upm + spacing * max(len(s) - 1, 0)


def wrap(s, w, size, fam="serif", wt=400, st="normal"):
    lines, cur = [], ""
    for wd in s.split():
        trial = f"{cur} {wd}".strip()
        if cur and width(trial, size, fam, wt, st) > w:
            lines.append(cur)
            cur = wd
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def subset_b64(path, chars):
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["kern", "liga"]
    opts.hinting = False
    opts.name_IDs = [1, 2]
    font = subset.load_font(str(path), opts)
    sub = subset.Subsetter(opts)
    sub.populate(text=chars + " ")
    sub.subset(font)
    buf = io.BytesIO()
    subset.save_font(font, buf, opts)
    return base64.b64encode(buf.getvalue()).decode()


class Card:
    def __init__(self, theme, h):
        self.t = theme
        self.c = THEMES[theme]
        self.h = h
        self.parts, self.defs, self.css = [], [], []
        self.used: dict = {}

    def text(self, x, y, s, size, fam="serif", wt=400, st="normal", fill=None, anchor="start",
             spacing=0.0, cls=""):
        self.used.setdefault((fam, wt, st), set()).update(s)
        ls = f' letter-spacing="{f(spacing)}"' if spacing else ""
        self.parts.append(
            f'<text x="{f(x)}" y="{f(y)}" class="{fam[0]} {cls}" font-size="{f(size)}" font-weight="{wt}" '
            f'font-style="{st}" fill="{fill or self.c["body"]}" text-anchor="{anchor}"{ls}>{escape(s)}</text>')

    def raw(self, s):
        self.parts.append(s)

    def frame(self, top_left, top_right):
        c = self.c
        H = self.h
        if c["shadow"]:
            self.defs.append('<filter id="sh" x="-5%" y="-5%" width="110%" height="115%">'
                             '<feDropShadow dx="0" dy="2" stdDeviation="5" flood-color="#2B2418" '
                             'flood-opacity=".10"/></filter>')
        sh = ' filter="url(#sh)"' if c["shadow"] else ""
        self.defs.append(f'<clipPath id="card"><rect x="8" y="8" width="{W - 16}" height="{H - 16}" rx="18"/></clipPath>')
        self.raw(f'<rect x="8" y="8" width="{W - 16}" height="{H - 16}" rx="18" fill="{c["paper"]}" '
                 f'stroke="{c["rule"]}"{sh}/>')
        self.raw(f'<rect x="22" y="22" width="{W - 44}" height="{H - 44}" rx="11" fill="none" stroke="{c["rule"]}"/>')
        self.raw(f'<rect x="26.5" y="26.5" width="{W - 53}" height="{H - 53}" rx="8" fill="none" '
                 f'stroke="{c["teal"]}" stroke-opacity=".35" stroke-width=".6"/>')
        self.text(48, 58, top_left, 10.5, fam="mono", fill=c["muted"], spacing=2.2)
        self.text(W - 48, 58, top_right, 10.5, fam="mono", fill=c["muted"], anchor="end", spacing=2.2)
        self.raw(f'<line x1="48" y1="72.5" x2="{W - 48}" y2="72.5" stroke="{c["rule"]}"/>')

    def waves(self, y0, y1, avoid=None):
        """Banknote-style line field, faded away from the text block."""
        c = self.c
        if avoid:
            ax, ay, aw, ah = avoid
            self.defs.append(
                '<filter id="soft"><feGaussianBlur stdDeviation="26"/></filter>'
                f'<mask id="wm"><rect x="0" y="0" width="{W}" height="{self.h}" fill="#fff"/>'
                f'<rect x="{ax}" y="{ay}" width="{aw}" height="{ah}" rx="30" fill="#000" filter="url(#soft)"/></mask>')
        paths = []
        n = int((y1 - y0) / 9)
        for j in range(n):
            pts = []
            for k in range(0, 131):
                x = 30 + k * (W - 60) / 130
                y = (y0 + j * 9 + 4.2 * math.sin(2 * math.pi * x / 190 + j * 0.42)
                     + 1.8 * math.sin(2 * math.pi * x / 57 + j * 0.9))
                pts.append((x, y))
            paths.append(compact(pts))
        m = ' mask="url(#wm)"' if avoid else ""
        self.raw(f'<g class="fadein" clip-path="url(#card)"{m}><path d="{" ".join(paths)}" fill="none" '
                 f'stroke="{c["teal"]}" stroke-opacity="{c["wave"]}" stroke-width=".6"/></g>')

    def microprint(self, y, phrase="THABITMAHMOOD·POSTQUANTUM·VERIFIABLE·FEDERATED·"):
        c = self.c
        n = int((W - 96) / (3.4 * 0.6 * len(phrase))) + 1
        self.defs.append(f'<clipPath id="mp"><rect x="48" y="{y - 6}" width="{W - 96}" height="10"/></clipPath>')
        self.used.setdefault(("mono", 400, "normal"), set()).update(phrase)
        self.raw(f'<g clip-path="url(#mp)"><text x="48" y="{y}" class="m" font-size="3.4" fill="{c["muted"]}">'
                 f'{escape(phrase * n)}</text></g>')

    def svg(self, title, desc):
        faces = []
        for (fam, wt, st), chars in sorted(self.used.items()):
            fname = "S" if fam == "serif" else "M"
            faces.append(f"@font-face{{font-family:{fname};font-weight:{wt};font-style:{st};"
                         f"src:url(data:font/woff2;base64,{subset_b64(FACES[(fam, wt, st)], ''.join(sorted(chars)))}) "
                         f"format('woff2')}}")
        css = "\n".join(faces) + """
.s{font-family:S,'Newsreader','Iowan Old Style',Georgia,serif}
.m{font-family:M,'JetBrains Mono',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-ligatures:none}
@keyframes fade{from{opacity:0}to{opacity:1}}
@keyframes draw{from{stroke-dashoffset:1}to{stroke-dashoffset:0}}
.fadein{animation:fade 1s ease-out both}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
""" + "\n".join(self.css)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{self.h}" viewBox="0 0 {W} {self.h}" '
                f'role="img" aria-labelledby="t d" xml:space="preserve"><title id="t">{escape(title)}</title>'
                f'<desc id="d">{escape(desc)}</desc><style>{css}</style><defs>{"".join(self.defs)}</defs>\n'
                + "\n".join(self.parts) + "\n</svg>\n")


# ------------------------------------------------------------------ guilloche

def g1(v):
    return f"{v:.1f}".rstrip("0").rstrip(".")


def compact(pts, close=False):
    head = f"M{g1(pts[0][0])} {g1(pts[0][1])}L"
    return head + " ".join(f"{g1(x)} {g1(y)}" for x, y in pts[1:]) + ("Z" if close else "")


def curve_path(fn, t1, steps):
    return compact([fn(t1 * i / steps) for i in range(steps + 1)], close=True)


def rosette(card, cx, cy, fp, mono="TM"):
    """Guilloche seal whose lobe counts, phases and star are read off the key fingerprint."""
    c = card.c
    parts = []
    fb = bytes.fromhex(fp)

    def ring(R0, A, N, phase):
        return lambda t: ((R0 + A * math.sin(N * t + phase)) * math.cos(t) + cx,
                          (R0 + A * math.sin(N * t + phase)) * math.sin(t) + cy)

    def hypo(R, r, d, rot):
        k = (R - r) / r
        return lambda t: (cx + (R - r) * math.cos(t + rot) + d * math.cos(k * t - rot),
                          cy + (R - r) * math.sin(t + rot) - d * math.sin(k * t - rot))

    n_outer = (34, 36, 38, 40, 42, 44)[fb[0] % 6]
    k_outer = (6, 7, 8)[fb[1] % 3]
    a_outer = 8 + (fb[2] % 3)
    n_bronze = (48, 52, 56, 60)[fb[3] % 4]
    # (R, r, d, turns): closed hypotrochoids, (R - r) / r = p / turns
    star = ((78, 22, 23, 11), (78, 21, 23, 7), (78, 20, 22, 10), (78, 24, 22, 4))[fb[4] % 4]
    rot = fb[5] / 255 * math.pi / 14
    n_inner = (20, 22, 24, 26, 28)[fb[6] % 5]
    spin = fb[7] / 255 * 2 * math.pi
    R, r, d, turns = star

    layers = []
    for i in range(k_outer):  # woven outer band
        layers.append((curve_path(ring(104, a_outer, n_outer, spin + 2 * math.pi * i / k_outer), 2 * math.pi, 480),
                       c["teal"], ".85", .55, i * .06))
    for i in range(3):  # bronze inner band
        layers.append((curve_path(ring(86, 4.5, n_bronze, spin + 2 * math.pi * i / 3), 2 * math.pi, 620),
                       c["bronze"], ".75", .5, .5 + i * .06))
    layers.append((curve_path(hypo(R, r, d, rot), 2 * math.pi * turns, 140 * turns), c["teal"], ".7", .45, .8))
    layers.append((curve_path(hypo(R, r, d, rot + math.pi / (2 * turns + 6)), 2 * math.pi * turns, 140 * turns),
                   c["bronze"], ".45", .4, 1.0))
    for i in range(5):
        layers.append((curve_path(ring(34, 5, n_inner, spin + 2 * math.pi * i / 5), 2 * math.pi, 300),
                       c["teal"], ".8", .5, 1.3 + i * .05))
    for d_, col, op, sw, delay in layers:
        parts.append(f'<path class="g" style="animation-delay:{f(delay)}s" pathLength="1" d="{d_}" fill="none" '
                     f'stroke="{col}" stroke-opacity="{op}" stroke-width="{sw}"/>')
    card.css.append(".g{stroke-dasharray:1;animation:draw 2.2s cubic-bezier(.45,0,.2,1) both}")
    card.raw("<g>" + "".join(parts) + "</g>")
    card.raw(f'<circle cx="{cx}" cy="{cy}" r="24" fill="{c["paper"]}" stroke="{c["bronze"]}" stroke-width=".8"/>')
    card.text(cx, cy + 7.5, mono, 20, wt=600, fill=c["bronze"], anchor="middle", spacing=1)
    # one sheen across the seal once the line work has drawn
    card.defs.append(f'<clipPath id="seal"><circle cx="{cx}" cy="{cy}" r="114"/></clipPath>'
                     f'<linearGradient id="sg" x1="0" y1="0" x2="1" y2="0">'
                     f'<stop offset="0" stop-color="{c["sheen"]}" stop-opacity="0"/>'
                     f'<stop offset=".5" stop-color="{c["sheen"]}" stop-opacity=".55"/>'
                     f'<stop offset="1" stop-color="{c["sheen"]}" stop-opacity="0"/></linearGradient>')
    card.css.append("@keyframes sweep{from{transform:translateX(-260px)}to{transform:translateX(260px)}}"
                    ".sheen{animation:sweep 1.4s cubic-bezier(.4,0,.2,1) 2.9s both}")
    card.raw(f'<g clip-path="url(#seal)"><rect class="sheen" x="{cx - 40}" y="{cy - 130}" width="80" height="260" '
             f'fill="url(#sg)" transform="rotate(18 {cx} {cy})"/></g>')


# ------------------------------------------------------------------ cards

def front(theme, rec, fp, sig_hex, status):
    card = Card(theme, 500)
    c = card.c
    serial = fp[:8].upper()
    card.frame("SECURITY RESEARCH  &  ENGINEERING", f"CREDENTIAL No. {serial}")
    card.waves(84, 404, avoid=(40, 96, 500, 300))
    card.text(46, 150, rec["name"], 50, wt=500, fill=c["ink"], spacing=-0.6)
    card.text(48, 186, rec["title"], 21, st="italic", fill=c["body"])
    rows = [("ROLE", rec["role"]), ("ALSO", rec["also"]), ("FOCUS", rec["focus"]),
            ("BASED", rec["based"])]
    y = 248
    for lab, val in rows:
        card.text(48, y, lab, 10, fam="mono", fill=c["teal"], spacing=2)
        if isinstance(val, list):
            joined = " · ".join(val)
            if width(joined, 15.5) <= 420:
                lines = [joined]
            else:  # break between items, as evenly as possible
                splits = [(" · ".join(val[:k]), " · ".join(val[k:])) for k in range(1, len(val))]
                a, b_ = min(splits, key=lambda p: max(width(p[0], 15.5), width(p[1], 15.5)))
                lines = [a, b_]
        else:
            lines = wrap(val, 420, 15.5)
        for i, ln in enumerate(lines):
            card.text(132, y + 1 + i * 22, ln, 15.5, fill=c["ink"] if i == 0 else c["ink"])
        y += 34 + (len(lines) - 1) * 22
    rosette(card, 674, 228, fp)
    card.text(674, 364, "ML-DSA-65  ·  FIPS 204", 10, fam="mono", fill=c["muted"], anchor="middle", spacing=1.2)
    card.css.append(".ok{animation:fade .6s ease-out 2.6s both}")
    valid = status.get("credential_valid")
    if valid:
        line, col = f"verified {status['checked']} ✓", c["teal"]
    elif valid is None:
        line, col = "not yet verified", c["muted"]
    else:
        line, col = "signature invalid ✗", c["alert"]
    card.text(674, 384, line, 13, st="italic", fill=col, anchor="middle", cls="ok")
    card.microprint(414)
    fpg = " ".join(fp[i:i + 8].upper() for i in range(0, 32, 8))
    card.text(48, 440, f"KEY  SHA-256  {fpg}", 11, fam="mono", fill=c["muted"], spacing=1.1)
    card.text(48, 460, f"SIG  {sig_hex[:24].upper()}…  ISSUED {rec['issued']}", 11, fam="mono",
              fill=c["muted"], spacing=1.1)
    card.text(W - 48, 460, "verify.py", 11, fam="mono", fill=c["teal"], anchor="end", spacing=1.1)
    return card.svg(f"{rec['name']}, credential",
                    f"{rec['name']}. {rec['title']}. {rec['role']}. {rec['also']}. Focus: {', '.join(rec['focus'])}. "
                    f"Based in {rec['based']}. "
                    f"Signed with ML-DSA-65, key fingerprint {fp[:16]}.")


def back(theme, rec, fp, status):
    c = THEMES[theme]
    cols = [(48, ("RESEARCH", rec["research"], None), ("PUBLISHED", rec["published"], "Full list on ORCID.")),
            (436, ("ENGINEERING", rec["engineering"], None), ("SERVICE", rec["service"], None))]
    cw = 356
    size, lead = 15.5, 24
    # height from the longest column
    def col_h(entries):
        h = 0
        for _, txt, extra in entries:
            n = len(wrap(txt, cw, size)) + (1 if extra else 0)
            h += 26 + n * lead + 26
        return h
    bottoms = []
    for x0, *entries in cols:
        y = 112
        for lab, txt, extra in entries:
            y += 28 + len(wrap(txt, cw, size)) * lead + (len(wrap(extra, cw, 14, st="italic")) * lead if extra else 0) + 26
        bottoms.append(y)
    H = int(max(bottoms) - 26 + 22 + 74)
    card = Card(theme, H)
    card.frame("FIELDS OF WORK", f"CREDENTIAL No. {fp[:8].upper()}  ·  VERSO")
    for x0, *entries in cols:
        y = 112
        for lab, txt, extra in entries:
            card.text(x0, y, lab, 10, fam="mono", fill=c["teal"], spacing=2)
            y += 28
            for ln in wrap(txt, cw, size):
                card.text(x0, y, ln, size, fill=c["ink"])
                y += lead
            if extra:
                for ln in wrap(extra, cw, 14, st="italic"):
                    card.text(x0, y, ln, 14, st="italic", fill=c["muted"])
                    y += lead
            y += 26
    yb = H - 70
    card.raw(f'<line x1="48" y1="{yb}" x2="{W - 48}" y2="{yb}" stroke="{c["rule"]}"/>')
    card.text(W / 2, yb + 30, "Physical documents prove they are genuine with guilloché. "
                              "Digital ones use signatures. This one has both.", 14, st="italic",
              fill=c["muted"], anchor="middle")
    return card.svg(f"{rec['name']}, fields of work",
                    f"Research: {rec['research']} Engineering: {rec['engineering']} Published: {rec['published']} "
                    f"Service: {rec['service']}")


def button(theme, label):
    c = THEMES[theme]
    w = int(width(label + "  ↗", 11, "mono", spacing=2.2) + 44)
    card = Card(theme, 44)
    card.raw(f'<rect x=".5" y=".5" width="{w - 1}" height="43" rx="10" fill="{c["paper"]}" stroke="{c["rule"]}"/>')
    card.raw(f'<rect x="4.5" y="4.5" width="{w - 9}" height="35" rx="7" fill="none" stroke="{c["teal"]}" '
             f'stroke-opacity=".35" stroke-width=".6"/>')
    card.text(22, 26, label, 11, fam="mono", fill=c["ink"], spacing=2.2)
    card.text(w - 22, 26, "↗", 12, fam="mono", fill=c["teal"], anchor="end")
    svg = card.svg(label, label)
    return svg.replace(f'width="{W}" height="44" viewBox="0 0 {W} 44"', f'width="{w}" height="44" viewBox="0 0 {w} 44"')


def main():
    rec = json.loads((ID / "identity.json").read_text(encoding="utf-8"))
    pk = bytes.fromhex((ID / "ml-dsa-65.pub").read_text().strip())
    sig_hex = (ID / "identity.sig").read_text().strip()
    fp = hashlib.sha256(pk).hexdigest()
    status_path = OUT / "status.json"
    status = json.loads(status_path.read_text()) if status_path.exists() else {}
    if status.get("key_sha256") not in (None, fp):
        status = {}  # stale status from another key
    OUT.mkdir(exist_ok=True)
    for t in THEMES:
        (OUT / f"credential-{t}.svg").write_text(front(t, rec, fp, sig_hex, status), encoding="utf-8")
        (OUT / f"record-{t}.svg").write_text(back(t, rec, fp, status), encoding="utf-8")
        (OUT / f"linkedin-{t}.svg").write_text(button(t, "LINKEDIN"), encoding="utf-8")
        (OUT / f"orcid-{t}.svg").write_text(button(t, "ORCID"), encoding="utf-8")
    import scenes
    scenes.render_all(rec, OUT)
    for p in sorted(OUT.glob("*.svg")):
        print(f"{p.name:22s} {p.stat().st_size / 1024:6.1f} KB")


if __name__ == "__main__":
    main()
