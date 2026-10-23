"""The opening film: a title card and five chapters that lead to the credential.

Story: a single point of light opens the page and becomes the protagonist.
It travels down one spine through every chapter: messages are being
recorded (01), a quantum computer could one day read them (02), so the work
is cryptography built from lattices (03) and learning that can prove itself
(04), and this profile is signed with the same mathematics (05). The light
is amber while it is exposed and turns teal once it enters the lattice.

Motion plays once and settles; a few elements keep breathing. Visitors who
prefer reduced motion see the final frame. Everything is plain SVG with
CSS and SMIL, rendered by scripts/build.py.
"""
from __future__ import annotations

import math
import random
from xml.sax.saxutils import escape

from build import FACES, f, subset_b64, width, wrap

W = 840
SPINE = 40
C = dict(bg="#07090D", panel="#0B0F15", line="#1C232D", spine="#28313D", ink="#E9EDF1", body="#C4CCD5",
         muted="#8B95A1", faint="#566170", amber="#F2A541", teal="#4FC8AE")
EASE = ".45 0 .2 1"
rng = random.Random(203204)


class Path:
    """A motion path with measured segment lengths, so timing can be set per segment."""

    def __init__(self, x, y):
        self.d = [f"M{f(x)} {f(y)}"]
        self.cur = (x, y)
        self.lengths = []

    def line(self, x, y):
        self.lengths.append(math.hypot(x - self.cur[0], y - self.cur[1]))
        self.d.append(f"L{f(x)} {f(y)}")
        self.cur = (x, y)
        return self

    def curve(self, c1, c2, p):
        pts = [self.cur, c1, c2, p]
        n, L, prev = 40, 0.0, self.cur
        for i in range(1, n + 1):
            t = i / n
            q = tuple((1 - t) ** 3 * pts[0][k] + 3 * (1 - t) ** 2 * t * pts[1][k]
                      + 3 * (1 - t) * t * t * pts[2][k] + t ** 3 * pts[3][k] for k in (0, 1))
            L += math.hypot(q[0] - prev[0], q[1] - prev[1])
            prev = q
        self.lengths.append(L)
        self.d.append(f"C{f(c1[0])} {f(c1[1])} {f(c2[0])} {f(c2[1])} {f(p[0])} {f(p[1])}")
        self.cur = p
        return self

    def motion(self, times):
        """times: [t0, t1, ...] seconds at each segment boundary (len = segments + 1)."""
        total = sum(self.lengths)
        cum = [0.0]
        for L in self.lengths:
            cum.append(cum[-1] + L)
        dur = times[-1]
        kp = ";".join(f(c / total) for c in cum)
        kt = ";".join(f(t / dur) for t in times)
        if times[0] > 0:  # hold at the start until t0
            kp = "0;" + kp
            kt = "0;" + kt
        n = kt.count(";")
        splines = ";".join([EASE] * n)
        return (f'<animateMotion dur="{f(dur)}s" fill="freeze" calcMode="spline" keyTimes="{kt}" '
                f'keyPoints="{kp}" keySplines="{splines}" path="{" ".join(self.d)}"/>')

    def svg_d(self):
        return " ".join(self.d)


class Scene:
    def __init__(self, h, chapter=None, label=None, hud=None):
        self.h = h
        self.parts, self.defs, self.css = [], [], []
        self.used: dict = {}
        self._frame(chapter, label, hud)

    # -------------------------------------------------------------- text
    def text(self, x, y, s, size, fam="serif", wt=400, st="normal", fill=None, anchor="start", spacing=0.0,
             cls="", style=""):
        self.used.setdefault((fam, wt, st), set()).update(s)
        ls = f' letter-spacing="{f(spacing)}"' if spacing else ""
        sty = f' style="{style}"' if style else ""
        self.parts.append(
            f'<text x="{f(x)}" y="{f(y)}" class="{fam[0]} {cls}" font-size="{f(size)}" font-weight="{wt}" '
            f'font-style="{st}" fill="{fill or C["body"]}" text-anchor="{anchor}"{ls}{sty}>{escape(s)}</text>')

    def words(self, x, y, items, size, start, step=0.09, wt=500, st="normal"):
        """Kinetic line: items = [(word, colour or None)], revealed one by one."""
        space = width(" ", size, "serif", wt, st)
        px, t = x, start
        for w_, col in items:
            self.text(px, y, w_, size, wt=wt, st=st, fill=col or C["ink"], cls="w", style=f"--d:{f(t)}s")
            px += width(w_, size, "serif", wt, st) + space
            t += step
        return t

    def para(self, x, y, s, size, w, lead, start, fill=None, st="italic", wt=400):
        for i, ln in enumerate(wrap(s, w, size, "serif", wt, st)):
            self.text(x, y + i * lead, ln, size, wt=wt, st=st, fill=fill or C["muted"], cls="w",
                      style=f"--d:{f(start + i * .12)}s")
        return y + (len(wrap(s, w, size, "serif", wt, st)) - 1) * lead

    def raw(self, s):
        self.parts.append(s)

    # -------------------------------------------------------------- frame
    def _frame(self, chapter, label, hud):
        h = self.h
        self.defs.append(
            '<pattern id="grid" width="28" height="28" patternUnits="userSpaceOnUse">'
            '<path d="M28 0H0V28" fill="none" stroke="#FFFFFF" stroke-opacity=".035"/></pattern>'
            '<radialGradient id="vig" cx=".55" cy=".45" r=".75"><stop offset=".55" stop-color="#000" stop-opacity="0"/>'
            '<stop offset="1" stop-color="#000" stop-opacity=".6"/></radialGradient>'
            f'<radialGradient id="ga"><stop offset="0" stop-color="{C["amber"]}" stop-opacity=".75"/>'
            f'<stop offset=".35" stop-color="{C["amber"]}" stop-opacity=".22"/>'
            f'<stop offset="1" stop-color="{C["amber"]}" stop-opacity="0"/></radialGradient>'
            f'<radialGradient id="gt"><stop offset="0" stop-color="{C["teal"]}" stop-opacity=".75"/>'
            f'<stop offset=".35" stop-color="{C["teal"]}" stop-opacity=".22"/>'
            f'<stop offset="1" stop-color="{C["teal"]}" stop-opacity="0"/></radialGradient>'
            '<radialGradient id="gw"><stop offset="0" stop-color="#FFFFFF" stop-opacity=".7"/>'
            '<stop offset=".35" stop-color="#FFFFFF" stop-opacity=".16"/>'
            '<stop offset="1" stop-color="#FFFFFF" stop-opacity="0"/></radialGradient>'
            f'<clipPath id="clip"><rect width="{W}" height="{h}" rx="14"/></clipPath>')
        self.raw(f'<g clip-path="url(#clip)"><rect width="{W}" height="{h}" fill="{C["bg"]}"/>'
                 f'<rect width="{W}" height="{h}" fill="url(#grid)"/>')
        for (x, y, dx, dy) in ((14, 14, 1, 1), (W - 14, 14, -1, 1), (14, h - 14, 1, -1), (W - 14, h - 14, -1, -1)):
            self.raw(f'<path d="M{x} {y + 10 * dy}V{y}H{x + 10 * dx}" fill="none" stroke="#FFFFFF" '
                     f'stroke-opacity=".22"/>')
        if chapter:
            self.raw(f'<line x1="{SPINE}" y1="0" x2="{SPINE}" y2="{h}" stroke="{C["spine"]}"/>')
            self.raw(f'<circle cx="{SPINE}" cy="48" r="3.5" fill="{C["bg"]}" stroke="{C["muted"]}"/>')
            self.text(56, 52, chapter, 10, fam="mono", fill=C["teal"], spacing=2)
            self.text(80, 52, label, 10, fam="mono", fill=C["muted"], spacing=2.4)
        if hud:
            self.text(W - 30, 52, hud, 10, fam="mono", fill=C["faint"], anchor="end", spacing=1.6)

    def light(self, path, times, colour="amber", turn=None, breathe=True, idle_until=None):
        """The protagonist. turn=(t0, t1) cross-fades amber to teal during the journey."""
        arrive = times[-1]
        glow_a = f'<circle r="11" fill="url(#ga)" opacity="{1 if colour == "amber" else 0}">'
        glow_t = f'<circle r="11" fill="url(#gt)" opacity="{1 if colour == "teal" else 0}">'
        if turn:
            t0, t1 = turn
            glow_a += (f'<animate attributeName="opacity" values="1;1;0" keyTimes="0;{f(t0 / t1)};1" '
                       f'dur="{f(t1)}s" fill="freeze"/>')
            glow_t += (f'<animate attributeName="opacity" values="0;0;1" keyTimes="0;{f(t0 / t1)};1" '
                       f'dur="{f(t1)}s" fill="freeze"/>')
        if idle_until:  # waiting in place before it sets off
            idle = (f'<animate attributeName="r" values="9;16;9" dur="1.15s" begin="0s" end="{f(idle_until)}s" '
                    f'repeatCount="indefinite"/>')
            glow_a += idle
            glow_t += idle
        if breathe:
            pulse = (f'<animate attributeName="r" values="11;15;11" dur="2.8s" begin="{f(arrive)}s" '
                     f'repeatCount="indefinite"/>')
            glow_a += pulse
            glow_t += pulse
        glow_a += "</circle>"
        glow_t += "</circle>"
        self.raw(f'<g opacity="0"><animate attributeName="opacity" values="0;1" dur=".35s" fill="freeze"/>'
                 f'{glow_a}{glow_t}<circle r="2.6" fill="#FFFFFF"/>{path.motion(times)}</g>')

    def trail(self, path, t0, t1, colour=None, op=".55"):
        """The route the light took, drawn behind it."""
        self.raw(f'<path class="trail" d="{path.svg_d()}" fill="none" stroke="{colour or C["spine"]}" '
                 f'stroke-opacity="{op}" pathLength="1" style="--d:{f(t0)}s;--l:{f(t1 - t0)}s"/>')

    # -------------------------------------------------------------- output
    def svg(self, title, desc):
        self.raw(f'<rect width="{W}" height="{self.h}" fill="url(#vig)" pointer-events="none"/></g>')
        self.raw(f'<rect x=".5" y=".5" width="{W - 1}" height="{self.h - 1}" rx="13.5" fill="none" '
                 f'stroke="{C["line"]}"/>')
        faces = []
        for (fam, wt, st), chars in sorted(self.used.items()):
            name = "S" if fam == "serif" else "M"
            faces.append(f"@font-face{{font-family:{name};font-weight:{wt};font-style:{st};src:url(data:font/woff2;"
                         f"base64,{subset_b64(FACES[(fam, wt, st)], ''.join(sorted(chars)))}) format('woff2')}}")
        css = "\n".join(faces) + """
.s{font-family:S,'Newsreader',Georgia,serif}
.m{font-family:M,'JetBrains Mono',ui-monospace,Menlo,Consolas,monospace;font-variant-ligatures:none}
@keyframes up{from{opacity:0;transform:translateY(7px)}to{opacity:1;transform:none}}
@keyframes fade{from{opacity:0}to{opacity:1}}
@keyframes draw{from{stroke-dashoffset:1}to{stroke-dashoffset:0}}
.w{animation:up .7s cubic-bezier(.2,.7,.2,1) both;animation-delay:var(--d)}
.fd{animation:fade .8s ease-out both;animation-delay:var(--d)}
.dr{stroke-dasharray:1;animation:draw var(--l,.8s) cubic-bezier(.45,0,.2,1) both;animation-delay:var(--d)}
.trail{stroke-dasharray:1;animation:draw var(--l) cubic-bezier(.45,0,.2,1) both;animation-delay:var(--d)}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
""" + "\n".join(self.css)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{self.h}" viewBox="0 0 {W} {self.h}" '
                f'role="img" aria-labelledby="t d" xml:space="preserve"><title id="t">{escape(title)}</title>'
                f'<desc id="d">{escape(desc)}</desc><style>{css}</style><defs>{"".join(self.defs)}</defs>\n'
                + "\n".join(self.parts) + "\n</svg>\n")


RAIL = 76


def route(x_drop, dest):
    """Spine, then the rail above the text, then down to the destination."""
    p = Path(SPINE, -14).line(SPINE, 48).curve((SPINE, 64), (SPINE + 8, RAIL), (SPINE + 26, RAIL))
    p.line(x_drop - 30, RAIL)
    p.curve((x_drop, RAIL), (dest[0] - (dest[0] - x_drop) * .2, dest[1] - 18), dest)
    return p


def hexrow(n):
    return "".join(rng.choice("0123456789abcdef") for _ in range(n))


# ====================================================================== title

def title(rec):
    s = Scene(300)
    cx, cy = 420, 84
    s.text(32, 40, "README", 10, fam="mono", fill=C["faint"], spacing=2.4)
    s.text(W - 30, 40, "CYBERJAYA, MY", 10, fam="mono", fill=C["faint"], anchor="end", spacing=2.4)
    # a faint lattice revealed by the ring as it passes
    pts = []
    for a in range(-14, 15):
        for b in range(-4, 6):
            x, y = cx + a * 34 + b * 10, 132 + b * -30
            if 20 < x < W - 20 and 20 < y < 290:
                d = math.hypot(x - cx, y - cy - 40)
                op = max(0.0, .5 - d / 900)
                pts.append(f'<circle class="fd" style="--d:{f(1.05 + d / 520)}s" cx="{f(x)}" cy="{f(y)}" r="1.1" '
                           f'fill="#FFFFFF" fill-opacity="{f(op)}"/>')
    s.raw("<g>" + "".join(pts) + "</g>")
    # the ring pulse that opens the page
    s.raw(f'<circle cx="{cx}" cy="{cy}" r="0" fill="none" stroke="#FFFFFF" stroke-width="1.2" opacity="0">'
          f'<animate attributeName="r" values="0;520" begin="1s" dur="1.6s" fill="freeze" calcMode="spline" '
          f'keyTimes="0;1" keySplines=".2 .6 .2 1"/>'
          f'<animate attributeName="opacity" values="0;.55;0" keyTimes="0;.15;1" begin="1s" dur="1.6s" fill="freeze"/>'
          f'</circle>')
    s.text(cx, 160, rec["name"], 60, wt=500, fill=C["ink"], anchor="middle", cls="w", style="--d:1.35s",
           spacing=-.6)
    s.text(cx, 198, rec["title"], 21, st="italic", fill=C["muted"], anchor="middle", cls="w", style="--d:1.7s")
    s.raw(f'<g class="fd" style="--d:2.05s">')
    s.text(cx, 236, "POST-QUANTUM CRYPTOGRAPHY   ·   VERIFIABLE FEDERATED LEARNING", 10.5, fam="mono",
           fill=C["muted"], anchor="middle", spacing=2.4)
    s.raw("</g>")
    # the light: it appears, pulses, then leaves for the spine and the first chapter
    p = Path(cx, cy).curve((cx - 160, cy), (SPINE + 30, cy + 6), (SPINE, cy + 60)).line(SPINE, 312)
    s.raw(f'<line class="dr" x1="{SPINE}" y1="{cy + 60}" x2="{SPINE}" y2="300" stroke="{C["spine"]}" pathLength="1" '
          f'style="--d:3.1s;--l:.9s"/>')
    s.light(p, [2.35, 3.15, 4.0], colour="amber", breathe=False, idle_until=2.35)
    return s.svg(rec["name"], f"{rec['name']}. {rec['title']}. Post-quantum cryptography and verifiable federated "
                              "learning. A point of light opens the page and sets off down the spine.")


# ====================================================================== 01 harvest

def harvest():
    s = Scene(330, "01", "HARVEST", "RSA-2048  ·  X25519  ·  AES-256-GCM")
    t = s.words(72, 128, [("Every", None), ("message", None), ("sent", None), ("today", None)], 30, .5)
    t = s.words(72, 166, [("can", None), ("be", None), ("recorded.", C["amber"])], 30, t)
    s.para(72, 210, "Encrypted traffic is cheap to store. An adversary can keep it until the day it can be "
                    "broken.", 15.5, 360, 23, t + .2)
    s.raw(f'<g class="fd" style="--d:{f(t + .6)}s">')
    s.text(72, 290, "HARVEST NOW  ·  DECRYPT LATER", 10, fam="mono", fill=C["amber"], spacing=2.4)
    s.raw("</g>")
    lanes = [110, 136, 162, 188, 214, 240]
    x0, x1, ax = 470, 704, 716
    s.defs.append(f'<clipPath id="lanes"><rect x="{x0}" y="90" width="{x1 - x0}" height="170"/></clipPath>')
    s.css.append("@keyframes flow{from{transform:translateX(-120px)}to{transform:translateX(250px)}}"
                 ".flow{animation:flow var(--s) linear infinite;animation-delay:var(--o)}")
    for i, y in enumerate(lanes):
        s.raw(f'<line class="dr" x1="{x0}" y1="{y}" x2="{ax}" y2="{y}" stroke="{C["line"]}" pathLength="1" '
              f'style="--d:{f(.4 + i * .06)}s;--l:.9s"/>')
        grp = []
        for k in range(3):
            hx = hexrow(8)
            s.used.setdefault(("mono", 400, "normal"), set()).update(hx)
            grp.append(f'<text x="{f(x0 + k * 96)}" y="{y - 4}" class="m" font-size="9" fill="{C["faint"]}">{hx}</text>')
        s.raw(f'<g clip-path="url(#lanes)"><g class="flow" style="--s:{f(7 + i * 1.3)}s;--o:-{f(i * 1.7)}s">'
              + "".join(grp) + "</g></g>")
    s.css.append("@keyframes led{0%,100%{opacity:.25}50%{opacity:.9}}"
                 ".led{animation:led var(--s) ease-in-out infinite;animation-delay:var(--o)}")
    for i, y in enumerate(lanes):
        s.raw(f'<rect class="fd" style="--d:{f(.7 + i * .07)}s" x="{ax}" y="{y - 9}" width="86" height="18" rx="3" '
              f'fill="{C["panel"]}" stroke="{C["line"]}"/>')
        s.raw(f'<circle class="led" style="--s:{f(2.2 + rng.random() * 2)}s;--o:-{f(rng.random() * 3)}s" '
              f'cx="{ax + 10}" cy="{y}" r="1.7" fill="{C["muted"]}"/>')
        s.raw(f'<line x1="{ax + 20}" y1="{y}" x2="{ax + 74}" y2="{y}" stroke="{C["line"]}" stroke-dasharray="2 3"/>')
    s.raw(f'<g class="fd" style="--d:1.2s">')
    s.text(ax + 43, 274, "STORED FOR LATER", 9, fam="mono", fill=C["faint"], anchor="middle", spacing=1.6)
    s.raw("</g>")
    # the light is one of those messages; it is filed away in slot three
    y3 = lanes[0]
    p = route(x0 - 20, (x0, y3)).line(ax + 10, y3)
    s.trail(p, .8, 3.0, op=".9")
    s.light(p, [0, .8, 1.0, 1.9, 2.3, 3.2], colour="amber")
    s.raw(f'<rect x="{ax}" y="{y3 - 9}" width="86" height="18" rx="3" fill="none" stroke="{C["amber"]}" '
          f'stroke-opacity="0"><animate attributeName="stroke-opacity" values="0;.8" begin="3.2s" dur=".4s" '
          f'fill="freeze"/></rect>')
    return s.svg("01 Harvest", "Chapter 1. Every message sent today can be recorded. Encrypted traffic is cheap to "
                               "store; an adversary can keep it until the day it can be broken. Harvest now, decrypt "
                               "later.")


# ====================================================================== 02 q-day

def qday():
    s = Scene(330, "02", "Q-DAY", "")
    # the date nobody knows: digits keep searching
    n_dates, cyc = 6, 2.4
    s.css.append("@keyframes cyc{0%{opacity:1}" + f(100 / n_dates) + "%,100%{opacity:0}}"
                 f".cy{{opacity:0;animation:cyc {f(cyc)}s steps(1) infinite;animation-delay:var(--o)}}")
    s.text(W - 30 - 10 * (.6 * 10 + 1.6) - 14, 52, "Q-DAY", 10, fam="mono", fill=C["faint"], anchor="end",
           spacing=1.6)
    dates = ["????-??-??"] + [f"20{rng.randint(30, 49)}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}"
                              for _ in range(n_dates - 1)]
    for k, date in enumerate(dates):
        s.text(W - 30, 52, date, 10, fam="mono", fill=C["amber"] if k else C["muted"], anchor="end", spacing=1.6,
               cls="cy", style=f"--o:-{f((n_dates - k) % n_dates * cyc / n_dates)}s")
    t = s.words(72, 128, [("A", None), ("large", None), ("enough", None), ("quantum", None), ("computer", None)],
                30, .5)
    t = s.words(72, 166, [("could", None), ("one", None), ("day", None), ("read", C["amber"]), ("it.", C["amber"])],
                30, t)
    s.para(72, 210, "Shor's algorithm factors RSA moduli and solves the discrete logarithms behind elliptic "
                    "curves in polynomial time.", 15.5, 360, 23, t + .2)
    bx, by, bw, bh = 570, 100, 230, 112
    rows = [hexrow(32) for _ in range(7)]
    for r_ in rows:
        s.used.setdefault(("mono", 400, "normal"), set()).update(r_)
    half = 16
    s.css.append("@keyframes splitL{to{transform:translateX(-6px)}}@keyframes splitR{to{transform:translateX(36px)}}"
                 ".sl{animation:splitL .9s cubic-bezier(.6,0,.2,1) 2.5s both}"
                 ".sr{animation:splitR .9s cubic-bezier(.6,0,.2,1) 2.5s both}")
    cw = 9 * 0.6
    left = "".join(f'<text x="{bx + 10}" y="{by + 20 + i * 14}" class="m" font-size="9" fill="{C["faint"]}">'
                   f'{r_[:half]}</text>' for i, r_ in enumerate(rows))
    right = "".join(f'<text x="{f(bx + 10 + half * cw + 6)}" y="{by + 20 + i * 14}" class="m" font-size="9" '
                    f'fill="{C["faint"]}">{r_[half:]}</text>' for i, r_ in enumerate(rows))
    s.raw(f'<g class="fd" style="--d:.6s"><g class="sl">{left}</g><g class="sr">{right}</g></g>')
    s.raw(f'<g class="fd" style="--d:.6s"><text x="{bx}" y="{by - 8}" class="m" font-size="9" fill="{C["muted"]}" '
          f'letter-spacing="1.4">N  ·  2048-BIT RSA MODULUS</text></g>')
    s.used.setdefault(("mono", 400, "normal"), set()).update("N  ·  2048-BIT RSA MODULUS")
    # scan line driven by the light
    s.raw(f'<rect x="{bx - 8}" y="{by}" width="{bw - 40}" height="1.6" fill="{C["amber"]}" opacity="0">'
          f'<animate attributeName="opacity" values="0;.8;.8;0" keyTimes="0;.05;.9;1" begin="1.4s" dur="1.1s" '
          f'fill="freeze"/><animate attributeName="y" values="{by};{by + bh - 8}" begin="1.4s" dur="1.1s" '
          f'fill="freeze"/></rect>')
    # p x q
    s.raw('<g class="fd" style="--d:3.1s">')
    pc, qc = bx + 10 - 6 + half * cw / 2, bx + 10 + half * cw + 6 + 36 + half * cw / 2
    s.text(pc, by + bh + 22, "p", 20, st="italic", fill=C["amber"], anchor="middle")
    s.text((pc + qc) / 2, by + bh + 20, "×", 18, fill=C["muted"], anchor="middle")
    s.text(qc, by + bh + 22, "q", 20, st="italic", fill=C["amber"], anchor="middle")
    s.raw("</g>")
    # a lock, drawn in line, that opens
    lx, ly = round((pc + qc) / 2), 278
    s.raw(f'<g class="fd" style="--d:.9s"><rect x="{lx - 13}" y="{ly - 10}" width="26" height="20" rx="3" fill="none" '
          f'stroke="{C["muted"]}" stroke-width="1.3"/>'
          f'<g><path d="M{lx - 8} {ly - 10}V{ly - 17}a8 8 0 0 1 16 0V{ly - 10}" fill="none" stroke="{C["muted"]}" '
          f'stroke-width="1.3"><animate attributeName="stroke" values="{C["muted"]};{C["amber"]}" begin="3.4s" '
          f'dur=".3s" fill="freeze"/></path>'
          f'<animateTransform attributeName="transform" type="translate" values="0 0;0 -7" begin="3.4s" dur=".45s" '
          f'fill="freeze" calcMode="spline" keyTimes="0;1" keySplines=".3 1.6 .4 1"/></g>'
          f'<circle cx="{lx}" cy="{ly}" r="1.8" fill="{C["muted"]}"/></g>')
    p = route(bx - 22, (bx - 8, by)).line(bx - 8, by + bh - 8).curve((bx - 8, by + bh + 40), (lx - 60, ly), (lx, ly))
    s.trail(p, .8, 3.3, op=".9")
    s.light(p, [0, .8, 1.0, 1.2, 1.45, 2.5, 3.3], colour="amber")
    return s.svg("02 Q-Day", "Chapter 2. A large enough quantum computer could one day read it. Shor's algorithm "
                             "factors RSA moduli and solves the discrete logarithms behind elliptic curves in "
                             "polynomial time. The 2048-bit modulus splits into its factors p and q, and the lock opens.")


# ====================================================================== 03 lattices

def lattices():
    s = Scene(330, "03", "LATTICES", "FIPS 203  ·  FIPS 204  ·  NIST 2024")
    t = s.words(72, 128, [("So", None), ("I", None), ("work", None), ("on", None), ("cryptography", None)], 30, .5)
    t = s.words(72, 166, [("built", None), ("from", None), ("lattices.", C["teal"])], 30, t)
    s.para(72, 210, "ML-KEM and ML-DSA, standardised by NIST in 2024, rest on lattice problems with no known "
                    "efficient quantum attack.", 15.5, 360, 23, t + .2)
    g1, g2 = (30.0, 0.0), (9.0, -28.0)
    b1 = (g1[0] + g2[0], g1[1] + g2[1])                    # U = [[1,1],[2,3]], det 1
    b2 = (2 * g1[0] + 3 * g2[0], 2 * g1[1] + 3 * g2[1])
    O = (590.0, 250.0)
    add = lambda *v: (sum(a[0] for a in v), sum(a[1] for a in v))
    box = (530, 92, 808, 282)
    tip2 = add(O, b2)
    target = add(O, (4 * g1[0] + 3 * g2[0], 4 * g1[1] + 3 * g2[1]), (7, -6))
    clear = [(tip2[0] - 98, tip2[1] - 8, tip2[0] - 4, tip2[1] + 8), (O[0] - 56, O[1] - 10, O[0] - 4, O[1] + 10),
             (box[2] - 150, box[3] + 2, box[2], box[3] + 20)]
    s.defs.append(f'<radialGradient id="lit" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="{C["teal"]}" '
                  f'stop-opacity=".16"/><stop offset="1" stop-color="{C["teal"]}" stop-opacity="0"/></radialGradient>')
    s.raw(f'<ellipse class="fd" style="--d:3.4s" cx="{f(O[0] + 70)}" cy="{f(O[1] - 70)}" rx="230" ry="150" fill="url(#lit)"/>')
    pts = []
    for a in range(-10, 14):
        for b in range(-3, 9):
            p = add(O, (a * g1[0] + b * g2[0], a * g1[1] + b * g2[1]))
            hidden = any(x0_ <= p[0] <= x1_ and y0_ <= p[1] <= y1_ for x0_, y0_, x1_, y1_ in clear)
            if box[0] <= p[0] <= box[2] and box[1] <= p[1] <= box[3] and not hidden:
                d = math.hypot(p[0] - O[0], p[1] - O[1])
                pts.append(f'<circle class="fd" style="--d:{f(.6 + d / 400)}s" cx="{f(p[0])}" cy="{f(p[1])}" '
                           f'r="1.7" fill="#3A4554"/>')
    s.raw("<g>" + "".join(pts) + "</g>")
    poly = lambda q: " ".join(f"{f(x)},{f(y)}" for x, y in q)
    sliver = [O, add(O, b1), add(O, b1, b2), add(O, b2)]
    cell = [O, add(O, g1), add(O, g1, g2), add(O, g2)]
    # the public sliver morphs into the secret cell: same lattice, same area
    s.raw(f'<polygon points="{poly(sliver)}" fill="{C["muted"]}" fill-opacity="0" stroke="{C["muted"]}" '
          f'stroke-opacity="0" stroke-width="1">'
          f'<animate attributeName="fill-opacity" values="0;.1" begin="1.7s" dur=".5s" fill="freeze"/>'
          f'<animate attributeName="stroke-opacity" values="0;.6" begin="1.7s" dur=".5s" fill="freeze"/>'
          f'<animate attributeName="points" values="{poly(sliver)};{poly(cell)}" begin="2.9s" dur="1.1s" '
          f'fill="freeze" calcMode="spline" keyTimes="0;1" keySplines=".6 0 .2 1"/>'
          f'<animate attributeName="fill" values="{C["muted"]};{C["teal"]}" begin="2.9s" dur="1.1s" fill="freeze"/>'
          f'<animate attributeName="stroke" values="{C["muted"]};{C["teal"]}" begin="2.9s" dur="1.1s" fill="freeze"/>'
          f'<animate attributeName="fill-opacity" values=".1;.22" begin="2.9s" dur="1.1s" fill="freeze"/>'
          f'</polygon>')

    def vec(v, col, d0, cls):
        q = add(O, v)
        ang = math.atan2(v[1], v[0])
        tip = [q] + [(q[0] + 7 * math.cos(ang + dd), q[1] + 7 * math.sin(ang + dd)) for dd in (2.6, -2.6)]
        end = (q[0] - 5 * math.cos(ang), q[1] - 5 * math.sin(ang))
        return (f'<g class="{cls}"><path class="dr" pathLength="1" style="--d:{f(d0)}s;--l:.6s" '
                f'd="M{f(O[0])} {f(O[1])}L{f(end[0])} {f(end[1])}" stroke="{col}" stroke-width="1.6" '
                f'stroke-linecap="round" fill="none"/><path class="fd" style="--d:{f(d0 + .5)}s" '
                f'd="M{" L".join(f"{f(a)} {f(b)}" for a, b in tip)}Z" fill="{col}"/></g>')
    s.css.append("@keyframes out{to{opacity:0}}.pubv{animation:out .6s ease-in 2.9s both}")
    s.raw(vec(b1, C["muted"], 1.5, "pubv") + vec(b2, C["muted"], 1.6, "pubv"))
    s.raw(vec(g1, C["teal"], 3.5, "secv") + vec(g2, C["teal"], 3.6, "secv"))
    s.raw(f'<circle cx="{f(O[0])}" cy="{f(O[1])}" r="2.4" fill="{C["ink"]}"/>')
    s.raw(f'<g class="fd" style="--d:1.9s"><g class="pubv">')
    s.text(tip2[0] - 12, tip2[1] + 4, "public basis", 10, fam="mono", fill=C["muted"], anchor="end", spacing=1)
    s.raw("</g></g>")
    s.raw(f'<g class="fd" style="--d:4.1s">')
    s.text(O[0] - 10, O[1] + 4, "secret", 10, fam="mono", fill=C["teal"], anchor="end", spacing=1)
    s.text(box[2] - 4, box[3] + 14, "b = A·s + e  (mod q)", 10.5, fam="mono", fill=C["muted"], anchor="end",
           spacing=.6)
    s.raw("</g>")
    # the light enters the lattice and is no longer exposed: amber becomes teal
    s.css.append("@keyframes jit{0%,100%{transform:translate(0,0)}25%{transform:translate(3px,-2px)}"
                 "50%{transform:translate(-2px,3px)}75%{transform:translate(2px,2px)}}"
                 ".jit{animation:jit var(--s) ease-in-out infinite}")
    noise = "".join(f'<circle class="jit" style="--s:{f(1.6 + rng.random() * 1.6)}s" cx="{f(target[0] + rng.gauss(0, 6))}" '
                    f'cy="{f(target[1] + rng.gauss(0, 6))}" r="1" fill="{C["teal"]}" fill-opacity=".6"/>'
                    for _ in range(9))
    s.raw(f'<g class="fd" style="--d:2.5s">{noise}</g>')
    p = route(target[0] - 40, target)
    s.trail(p, .8, 2.6, op=".9")
    s.light(p, [0, .8, 1.0, 2.0, 2.6], colour="amber", turn=(1.9, 2.6))
    return s.svg("03 Lattices", "Chapter 3. So I work on cryptography built from lattices. ML-KEM and ML-DSA, "
                                "standardised by NIST in 2024, rest on lattice problems with no known efficient "
                                "quantum attack. A long public basis morphs into a short secret one of the same area.")


# ====================================================================== 04 learning

def learning(rec):
    s = Scene(340, "04", "VERIFIABLE LEARNING", "FEDERATED  ·  VERIFIABLE  ·  POST-QUANTUM")
    t = s.words(72, 128, [("And", None), ("on", None), ("learning", None), ("that", None)], 30, .5)
    t = s.words(72, 166, [("can", None), ("prove", C["teal"]), ("itself.", None)], 30, t)
    s.para(72, 210, rec["research"], 15.5, 360, 23, t + .2)
    agg = (642, 104)
    nodes = [(506 + i * 68, 252) for i in range(5)]
    for i, (x, y) in enumerate(nodes):
        s.raw(f'<line class="dr" x1="{x}" y1="{y - 10}" x2="{agg[0]}" y2="{agg[1] + 16}" stroke="{C["line"]}" '
              f'pathLength="1" style="--d:{f(.7 + i * .06)}s;--l:.7s"/>')
    s.raw(f'<rect class="fd" style="--d:.6s" x="{agg[0] - 56}" y="{agg[1] - 16}" width="112" height="32" rx="7" '
          f'fill="{C["panel"]}" stroke="{C["teal"]}" stroke-opacity=".7"/>')
    s.raw(f'<g class="fd" style="--d:.7s">')
    s.text(agg[0], agg[1] + 4, "aggregate", 10.5, fam="mono", fill=C["body"], anchor="middle", spacing=1)
    s.raw("</g>")
    # ring pulse from the aggregator once updates arrive
    s.raw(f'<circle cx="{agg[0]}" cy="{agg[1]}" r="20" fill="none" stroke="{C["teal"]}" opacity="0">'
          f'<animate attributeName="r" values="20;90" begin="3s" dur="1.2s" fill="freeze"/>'
          f'<animate attributeName="opacity" values="0;.7;0" keyTimes="0;.15;1" begin="3s" dur="1.2s" fill="freeze"/>'
          f'</circle>')
    for i, (x, y) in enumerate(nodes):
        up = Path(x, y - 10).line(agg[0], agg[1] + 16)
        dn = Path(agg[0], agg[1] + 16).line(x, y - 10)
        t_up = 1.9 + i * .1
        s.raw(f'<circle r="2.2" fill="{C["muted"]}" opacity="0"><animate attributeName="opacity" values="0;1;1;0" '
              f'keyTimes="0;.1;.9;1" begin="{f(t_up)}s" dur=".9s" fill="freeze"/>'
              f'<animateMotion begin="{f(t_up)}s" dur=".9s" fill="freeze" path="{up.svg_d()}" calcMode="spline" '
              f'keyTimes="0;1" keyPoints="0;1" keySplines="{EASE}"/></circle>')
        t_dn = 3.4 + i * .1
        s.raw(f'<circle r="2.4" fill="{C["teal"]}" opacity="0"><animate attributeName="opacity" values="0;1;1;0" '
              f'keyTimes="0;.1;.85;1" begin="{f(t_dn)}s" dur=".8s" fill="freeze"/>'
              f'<animateMotion begin="{f(t_dn)}s" dur=".8s" fill="freeze" path="{dn.svg_d()}" calcMode="spline" '
              f'keyTimes="0;1" keyPoints="0;1" keySplines="{EASE}"/></circle>')
        s.raw(f'<rect class="fd" style="--d:{f(.8 + i * .07)}s" x="{x - 10}" y="{y - 10}" width="20" height="20" '
              f'rx="4" fill="{C["panel"]}" stroke="{C["muted"]}" stroke-width="1.2">'
              f'<animate attributeName="stroke" values="{C["muted"]};{C["teal"]}" begin="{f(t_dn + .8)}s" dur=".3s" '
              f'fill="freeze"/></rect>')
        s.raw(f'<g class="fd" style="--d:{f(t_dn + .85)}s">')
        s.text(x, y + 32, "✓", 13, fam="mono", fill=C["teal"], anchor="middle")
        s.raw("</g>")
    s.raw(f'<g class="fd" style="--d:1s">')
    s.text(agg[0], 312, "EVERY PARTICIPANT CHECKS THE RESULT", 9, fam="mono", fill=C["faint"], anchor="middle",
           spacing=1.6)
    s.raw("</g>")
    p = route(agg[0] - 80, (agg[0] - 56, agg[1]))
    s.trail(p, .8, 1.9, op=".9")
    s.light(p, [0, .8, .95, 1.6, 1.9], colour="teal")
    return s.svg("04 Verifiable learning", "Chapter 4. And on learning that can prove itself. " + rec["research"]
                 + " Participants send updates to an aggregator; the result is checked by every participant.")


# ====================================================================== 05 signed

def signed():
    s = Scene(150, "05", "SIGNED", "ML-DSA-65  ·  FIPS 204")
    t = s.words(72, 98, [("This", None), ("profile", None), ("is", None), ("signed", C["teal"]), ("with", None),
                         ("the", None), ("same", None), ("mathematics.", None)], 26, .4, step=.07)
    s.raw(f'<g class="fd" style="--d:{f(t + .2)}s">')
    s.text(72, 126, "RE-VERIFIED EVERY NIGHT  ·  SEE verify.py BELOW", 9.5, fam="mono", fill=C["muted"],
           spacing=1.8)
    s.raw("</g>")
    p = Path(SPINE, -14).line(SPINE, 48).line(SPINE, 164)
    s.light(p, [0, .8, 2.6], colour="teal", breathe=False)
    return s.svg("05 Signed", "Chapter 5. This profile is signed with the same mathematics, and re-verified every "
                              "night.")


def render_all(rec, out):
    files = {"film-0-title.svg": title(rec), "film-1-harvest.svg": harvest(), "film-2-qday.svg": qday(),
             "film-3-lattices.svg": lattices(), "film-4-learning.svg": learning(rec), "film-5-signed.svg": signed()}
    for name, svg in files.items():
        (out / name).write_text(svg, encoding="utf-8")
    return list(files)
