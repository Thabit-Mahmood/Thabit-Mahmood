"""The profile, told as a short film in five frames.

A point of light opens the page and travels one spine through four
first-person chapters: I research (01), I build (02), I publish (03) and I
sign my work (04). In each chapter it docks into the thing the line is
about: the aggregator of a federated network, the cursor of a terminal
running this repository's verify.py, a bank of detection instruments, and
the centre of a guilloche seal drawn from the signing key.

Text plays once. Each chapter's main beat then repeats on a slow loop, and
a signal runs down the spine through every frame, so whichever frame a
visitor scrolls to is moving. (GitHub plays README images from page load
and strips lazy loading, so motion cannot wait for the scroll.) Everything
is plain SVG with CSS and SMIL, rendered by scripts/build.py.
"""
from __future__ import annotations

import math
import random
from xml.sax.saxutils import escape

from build import FACES, f, subset_b64, width, wrap

W = 840
SPINE = 40
C = dict(bg="#07090D", panel="#0B0F15", line="#1C232D", spine="#28313D", ink="#E9EDF1", body="#C4CCD5",
         muted="#8B95A1", faint="#566170", dot="#3A4554", amber="#F2A541", teal="#4FC8AE", sheen="#BFF5E9")
EASE = ".45 0 .2 1"
rng = random.Random(203204)

# The spine signal: one pulse every P seconds that flows down through all frames
# in turn, timed from each frame's position on the page.
V, P, PULSE_L, GAP = 200.0, 10.0, 70, 5
HEIGHTS = {"title": 300, "research": 330, "build": 330, "published": 384, "signed": 400}
ORDER = ["title", "research", "build", "published", "signed"]
TITLE_SPINE = 144                      # where the spine starts in the title frame
T0 = 3.15 - TITLE_SPINE / V            # the title's light passes y=144 at 3.15 s; the signal follows it


def kt(x: float) -> str:
    return f"{x:.4f}".rstrip("0").rstrip(".") or "0"


def windows(attr, wins, total, on, off, ramp=.2, begin=0.0, mode="linear"):
    """A looping SMIL animation that holds `on` inside each (t0, t1) window and `off` elsewhere."""
    times, vals = [0.0], [off]
    for t0, t1 in wins:
        if mode == "discrete":
            if t0 <= 0:
                vals[0] = on
                times.append(t1)
                vals.append(off)
                continue
            times += [t0, t1]
            vals += [on, off]
        else:
            times += [t0, t0 + ramp, t1 - ramp, t1]
            vals += [off, on, on, off]
    if mode != "discrete":
        times.append(total)
        vals.append(off)
    return (f'<animate attributeName="{attr}" values="{";".join(map(str, vals))}" '
            f'keyTimes="{";".join(kt(t / total) for t in times)}" dur="{f(total)}s" begin="{f(begin)}s" '
            f'repeatCount="indefinite" calcMode="{mode}"/>')


def motion_loop(d, t0, t1, total, begin=0.0, ease=EASE):
    """Move along `d` between t0 and t1 of every `total`-second loop."""
    return (f'<animateMotion path="{d}" dur="{f(total)}s" begin="{f(begin)}s" repeatCount="indefinite" '
            f'calcMode="spline" keyTimes="0;{kt(t0 / total)};{kt(t1 / total)};1" keyPoints="0;0;1;1" '
            f'keySplines="0 0 1 1;{ease};0 0 1 1"/>')


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
        assert len(times) == len(self.lengths) + 1, "one time per segment boundary"
        dur = times[-1]
        kp = ";".join(kt(c / total) for c in cum)
        kts = ";".join(kt(t / dur) for t in times)
        if times[0] > 0:  # hold at the start until t0
            kp = "0;" + kp
            kts = "0;" + kts
        n = kts.count(";")
        splines = ";".join([EASE] * n)
        return (f'<animateMotion dur="{f(dur)}s" fill="freeze" calcMode="spline" keyTimes="{kts}" '
                f'keyPoints="{kp}" keySplines="{splines}" path="{" ".join(self.d)}"/>')

    def svg_d(self):
        return " ".join(self.d)


class Scene:
    def __init__(self, h, chapter=None, label=None, hud=None, Y=None, hud_spacing=1.6):
        self.h = h
        self.parts, self.defs, self.css = [], [], []
        self.used: dict = {}
        self._css_once: set = set()
        self._frame(chapter, label, hud, Y, hud_spacing)

    def once(self, key, css):
        if key not in self._css_once:
            self._css_once.add(key)
            self.css.append(css)

    # -------------------------------------------------------------- text
    def text(self, x, y, s, size, fam="serif", wt=400, st="normal", fill=None, anchor="start", spacing=0.0,
             cls="", style="", extra=""):
        self.used.setdefault((fam, wt, st), set()).update(s)
        ls = f' letter-spacing="{f(spacing)}"' if spacing else ""
        sty = f' style="{style}"' if style else ""
        self.parts.append(
            f'<text x="{f(x)}" y="{f(y)}" class="{fam[0]} {cls}" font-size="{f(size)}" font-weight="{wt}" '
            f'font-style="{st}" fill="{fill or C["body"]}" text-anchor="{anchor}"{ls}{sty}{extra}>{escape(s)}</text>')

    def mono(self, s):
        self.used.setdefault(("mono", 400, "normal"), set()).update(s)

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
        lines = wrap(s, w, size, "serif", wt, st)
        for i, ln in enumerate(lines):
            self.text(x, y + i * lead, ln, size, wt=wt, st=st, fill=fill or C["muted"], cls="w",
                      style=f"--d:{f(start + i * .12)}s")
        return y + (len(lines) - 1) * lead, start + len(lines) * .12

    def raw(self, s):
        self.parts.append(s)

    # -------------------------------------------------------------- ambient
    def field(self, pts, origin, d0=.6, r=1.5, fill=None, op=.6, wave_from=2.6):
        """A point field that fades in from `origin`, then a slow band of light washes across it."""
        self.once("wave", "@keyframes wv{0%,100%{opacity:.4}9%{opacity:1}22%{opacity:.4}}"
                          ".wv{animation:wv 9s ease-in-out infinite both;animation-delay:var(--w)}")
        out = []
        for x, y in pts:
            d = math.hypot(x - origin[0], y - origin[1])
            w_ = wave_from + (x + (self.h - y) * .45) / W * 3.4
            out.append(f'<g class="fd" style="--d:{f(d0 + d / 420)}s"><circle class="wv" style="--w:{f(w_)}s" '
                       f'cx="{f(x)}" cy="{f(y)}" r="{f(r)}" fill="{fill or C["muted"]}" fill-opacity="{f(op)}"/></g>')
        self.raw("<g>" + "".join(out) + "</g>")

    def _pulse(self, Y, y_from=0.0):
        h, L = self.h, PULSE_L
        t_s = T0 + (Y + y_from) / V
        q = (h + L - y_from) / V / P * 100
        self.defs.append(
            f'<linearGradient id="pg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{C["teal"]}" '
            f'stop-opacity="0"/><stop offset=".75" stop-color="{C["teal"]}" stop-opacity=".6"/>'
            f'<stop offset="1" stop-color="#FFFFFF" stop-opacity=".95"/></linearGradient>'
            f'<linearGradient id="pw" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{C["teal"]}" '
            f'stop-opacity="0"/><stop offset="1" stop-color="{C["teal"]}" stop-opacity=".25"/></linearGradient>'
            f'<clipPath id="pc"><rect x="{SPINE - 10}" y="{f(y_from)}" width="20" height="{f(h - y_from)}"/></clipPath>')
        self.css.append(f"@keyframes pl{{0%{{transform:translateY({f(y_from)}px)}}{f(q)}%,100%{{transform:"
                        f"translateY({f(h + L)}px)}}}}.pl{{animation:pl {f(P)}s linear {f(t_s)}s infinite both}}")
        self.raw(f'<g clip-path="url(#pc)"><g class="pl"><rect x="{SPINE - 5}" y="-{L}" width="10" height="{L}" '
                 f'rx="5" fill="url(#pw)"/><rect x="{SPINE - .9}" y="-{L}" width="1.8" height="{L}" '
                 f'fill="url(#pg)"/></g></g>')
        return t_s

    # -------------------------------------------------------------- frame
    def _frame(self, chapter, label, hud, Y, hud_spacing):
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
            f'<clipPath id="clip"><rect width="{W}" height="{h}" rx="14"/></clipPath>')
        self.raw(f'<g clip-path="url(#clip)"><rect width="{W}" height="{h}" fill="{C["bg"]}"/>'
                 f'<rect width="{W}" height="{h}" fill="url(#grid)"/>')
        for (x, y, dx, dy) in ((14, 14, 1, 1), (W - 14, 14, -1, 1), (14, h - 14, 1, -1), (W - 14, h - 14, -1, -1)):
            self.raw(f'<path d="M{x} {y + 10 * dy}V{y}H{x + 10 * dx}" fill="none" stroke="#FFFFFF" '
                     f'stroke-opacity=".22"/>')
        if chapter:
            self.raw(f'<line x1="{SPINE}" y1="0" x2="{SPINE}" y2="{h}" stroke="{C["spine"]}"/>')
            mk = ""
            if Y is not None:
                t_s = self._pulse(Y)
                a = 48 / V / P * 100
                self.css.append(
                    f"@keyframes mk{{0%,{f(a - .5)}%{{stroke:{C['muted']}}}{f(a + .3)}%{{stroke:{C['teal']}}}"
                    f"{f(a + 8)}%,100%{{stroke:{C['muted']}}}}}"
                    f"@keyframes mkh{{0%,{f(a - .5)}%{{opacity:0}}{f(a + .3)}%{{opacity:.9}}{f(a + 8)}%,100%"
                    f"{{opacity:0}}}}.mk{{animation:mk {f(P)}s linear {f(t_s)}s infinite both}}"
                    f".mkh{{opacity:0;animation:mkh {f(P)}s linear {f(t_s)}s infinite both}}")
                self.raw(f'<circle class="mkh" cx="{SPINE}" cy="48" r="11" fill="url(#gt)"/>')
                mk = ' class="mk"'
            self.raw(f'<circle{mk} cx="{SPINE}" cy="48" r="3.5" fill="{C["bg"]}" stroke="{C["muted"]}"/>')
            self.text(56, 52, chapter, 10, fam="mono", fill=C["teal"], spacing=2)
            self.text(80, 52, label, 10, fam="mono", fill=C["muted"], spacing=2.4)
        if hud:
            self.text(W - 30, 52, hud, 10, fam="mono", fill=C["faint"], anchor="end", spacing=hud_spacing)

    # -------------------------------------------------------------- the protagonist
    def light(self, path, times, colour="amber", turn=None, breathe=True, idle_until=None, vanish=False):
        """turn=(t0, t1) cross-fades amber to teal; vanish hands the light over to whatever it docks into."""
        arrive = times[-1]
        glow_a = f'<circle r="11" fill="url(#ga)" opacity="{1 if colour == "amber" else 0}">'
        glow_t = f'<circle r="11" fill="url(#gt)" opacity="{1 if colour == "teal" else 0}">'
        if turn:
            t0, t1 = turn
            glow_a += (f'<animate attributeName="opacity" values="1;1;0" keyTimes="0;{kt(t0 / t1)};1" '
                       f'dur="{f(t1)}s" fill="freeze"/>')
            glow_t += (f'<animate attributeName="opacity" values="0;0;1" keyTimes="0;{kt(t0 / t1)};1" '
                       f'dur="{f(t1)}s" fill="freeze"/>')
        if idle_until:  # waiting in place before it sets off
            idle = (f'<animate attributeName="r" values="9;16;9" dur="1.15s" begin="0s" end="{f(idle_until)}s" '
                    f'repeatCount="indefinite"/>')
            glow_a += idle
            glow_t += idle
        if breathe and not vanish:
            pulse = (f'<animate attributeName="r" values="11;15;11" dur="2.8s" begin="{f(arrive)}s" '
                     f'repeatCount="indefinite"/>')
            glow_a += pulse
            glow_t += pulse
        glow_a += "</circle>"
        glow_t += "</circle>"
        out = (f'<animate attributeName="opacity" values="1;0" begin="{f(arrive)}s" dur=".35s" fill="freeze"/>'
               if vanish else "")
        self.raw(f'<g opacity="0"><animate attributeName="opacity" values="0;1" dur=".35s" fill="freeze"/>{out}'
                 f'{glow_a}{glow_t}<circle r="2.6" fill="#FFFFFF"/>{path.motion(times)}</g>')

    def trail(self, path, t0, t1, colour=None, op=".55"):
        """The route the light took, drawn behind it."""
        self.raw(f'<path class="trail" d="{path.svg_d()}" fill="none" stroke="{colour or C["spine"]}" '
                 f'stroke-opacity="{op}" pathLength="1" style="--d:{f(t0)}s;--l:{f(t1 - t0)}s"/>')

    # -------------------------------------------------------------- output
    def svg(self, title, desc, w=W):
        h = self.h
        if w == W:
            self.raw(f'<rect width="{W}" height="{h}" fill="url(#vig)" pointer-events="none"/></g>')
            self.raw(f'<rect x=".5" y=".5" width="{W - 1}" height="{h - 1}" rx="13.5" fill="none" '
                     f'stroke="{C["line"]}"/>')
        faces = []
        for (fam, wt, st), chars in sorted(self.used.items()):
            name = "S" if fam == "serif" else "M"
            faces.append(f"@font-face{{font-family:{name};font-weight:{wt};font-style:{st};src:url(data:font/woff2;"
                         f"base64,{subset_b64(FACES[(fam, wt, st)], ''.join(sorted(chars)))}) format('woff2')}}")
        css = "\n".join(faces) + """
text{white-space:pre}
.s{font-family:S,'Newsreader',Georgia,serif}
.m{font-family:M,'JetBrains Mono',ui-monospace,Menlo,Consolas,monospace;font-variant-ligatures:none}
@keyframes up{from{opacity:0;transform:translateY(7px)}to{opacity:1;transform:none}}
@keyframes fade{from{opacity:0}to{opacity:1}}
@keyframes draw{from{stroke-dashoffset:1}to{stroke-dashoffset:0}}
@keyframes spin{to{transform:rotate(360deg)}}
.w{animation:up .7s cubic-bezier(.2,.7,.2,1) both;animation-delay:var(--d)}
.fd{animation:fade .8s ease-out both;animation-delay:var(--d)}
.dr{stroke-dasharray:1;animation:draw var(--l,.8s) cubic-bezier(.45,0,.2,1) both;animation-delay:var(--d)}
.trail{stroke-dasharray:1;animation:draw var(--l) cubic-bezier(.45,0,.2,1) both;animation-delay:var(--d)}
.spin{transform-origin:var(--o);animation:spin var(--r) linear infinite}
.ccw{animation-direction:reverse}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
""" + "\n".join(self.css)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
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


def headline(s, l1, l2, start=.5):
    t = s.words(72, 128, l1, 30, start)
    return s.words(72, 166, l2, 30, t)


# ====================================================================== title

def title(rec, Y):
    s = Scene(HEIGHTS["title"])
    cx, cy = 420, 84
    s.text(32, 40, "README", 10, fam="mono", fill=C["faint"], spacing=2.4)
    s.text(W - 30, 40, rec["based"].split(",")[0].upper() + ", MY", 10, fam="mono", fill=C["faint"], anchor="end",
           spacing=2.4)
    # a faint lattice revealed by the opening ring; afterwards a slow band of light keeps washing over it
    pts = []
    for a in range(-14, 15):
        for b in range(-4, 6):
            x, y = cx + a * 34 + b * 10, 132 + b * -30
            if 20 < x < W - 20 and 20 < y < 290:
                pts.append((x, y))
    s.once("wave", "@keyframes wv{0%,100%{opacity:.4}9%{opacity:1}22%{opacity:.4}}"
                   ".wv{animation:wv 9s ease-in-out infinite both;animation-delay:var(--w)}")
    out = []
    for x, y in pts:
        d = math.hypot(x - cx, y - cy - 40)
        op = max(0.0, .9 - d / 520)
        if op <= .02:
            continue
        w_ = 4.2 + (x + (300 - y) * .45) / W * 3.4
        out.append(f'<g class="fd" style="--d:{f(1.05 + d / 520)}s"><circle class="wv" style="--w:{f(w_)}s" '
                   f'cx="{f(x)}" cy="{f(y)}" r="1.1" fill="#FFFFFF" fill-opacity="{f(op)}"/></g>')
    s.raw("<g>" + "".join(out) + "</g>")
    # the ring pulse that opens the page
    s.raw(f'<circle cx="{cx}" cy="{cy}" r="0" fill="none" stroke="#FFFFFF" stroke-width="1.2" opacity="0">'
          f'<animate attributeName="r" values="0;520" begin="1s" dur="1.6s" fill="freeze" calcMode="spline" '
          f'keyTimes="0;1" keySplines=".2 .6 .2 1"/>'
          f'<animate attributeName="opacity" values="0;.55;0" keyTimes="0;.15;1" begin="1s" dur="1.6s" fill="freeze"/>'
          f'</circle>')
    s.text(cx, 160, rec["name"], 60, wt=500, fill=C["ink"], anchor="middle", cls="w", style="--d:1.35s",
           spacing=-.6)
    s.text(cx, 198, rec["title"], 21, st="italic", fill=C["muted"], anchor="middle", cls="w", style="--d:1.7s")
    roles = f"{rec['role'].upper()}   ·   {rec['also'].upper()}"
    sp = 2.0
    while width(roles, 10, "mono", spacing=sp) > 690 and sp > .8:
        sp -= .2
    s.raw(f'<g class="fd" style="--d:2.05s">')
    s.text(cx, 236, roles, 10, fam="mono", fill=C["muted"], anchor="middle", spacing=sp)
    s.raw("</g>")
    # the light: it appears, pulses, then leaves for the spine and the first chapter
    p = Path(cx, cy).curve((cx - 160, cy), (SPINE + 30, cy + 6), (SPINE, cy + 60)).line(SPINE, 312)
    s.raw(f'<line class="dr" x1="{SPINE}" y1="{cy + 60}" x2="{SPINE}" y2="{HEIGHTS["title"]}" '
          f'stroke="{C["spine"]}" pathLength="1" style="--d:3.1s;--l:.9s"/>')
    s._pulse(Y, y_from=TITLE_SPINE)
    s.light(p, [2.35, 3.15, 4.0], colour="amber", breathe=False, idle_until=2.35)
    return s.svg(rec["name"], f"{rec['name']}. {rec['title']}. {rec['role']}. {rec['also']}. "
                              f"Based in {rec['based']}.")


# ====================================================================== 01 research

def research(rec, Y):
    h = HEIGHTS["research"]
    s = Scene(h, "01", "RESEARCH", "  ·  ".join(x.upper() for x in rec["focus"]), Y=Y, hud_spacing=1.2)
    t = headline(s, [("I", None), ("research", C["teal"]), ("security", None)],
                 [("for", None), ("the", None), ("post-quantum", None), ("era.", None)])
    s.para(72, 210, rec["research"], 15.5, 360, 23, t + .2)

    hx, hy = 652, 126
    nodes = [(512 + i * 70, 252 + 10 * ((i - 2) / 2) ** 2) for i in range(5)]
    # the network sits on a lattice: the post-quantum ground it is built on
    g1, g2 = (30.0, 0.0), (9.0, -28.0)
    pts = []
    for a in range(-14, 14):
        for b in range(-5, 8):
            x, y = hx + a * g1[0] + b * g2[0], hy + a * g1[1] + b * g2[1]
            if not (480 <= x <= 812 and 84 <= y <= 296):
                continue
            if math.hypot(x - hx, y - hy) < 40 or any(abs(x - nx) < 18 and abs(y - ny) < 18 for nx, ny in nodes):
                continue
            if hx + 36 <= x <= hx + 110 and hy - 10 <= y <= hy + 12:   # the label
                continue
            pts.append((x, y))
    s.field(pts, origin=(hx, hy), d0=.5)

    B, CY, NC = 2.4, 8.0, 3
    SUP = CY * NC
    culprits = [3, 0, 4]

    geo = []
    for nx, ny in nodes:
        top = (nx, ny - 10)
        dx, dy = top[0] - hx, top[1] - hy
        n = math.hypot(dx, dy)
        ux, uy = dx / n, dy / n
        geo.append((top, (hx + ux * 31, hy + uy * 31), (hx + ux * 15, hy + uy * 15)))
    for i, (top, ck, hub) in enumerate(geo):
        s.raw(f'<line class="dr" x1="{f(top[0])}" y1="{f(top[1])}" x2="{f(hub[0])}" y2="{f(hub[1])}" '
              f'stroke="{C["line"]}" stroke-width="1.1" pathLength="1" style="--d:{f(.7 + i * .06)}s;--l:.7s"/>')
    # checkpoint ring: every update is checked here before it reaches the aggregate
    ck_flash = windows("stroke", [(c * CY + 1.0, c * CY + 1.8) for c in range(NC)], SUP, C["amber"], C["teal"],
                       ramp=.15, begin=B)
    s.raw(f'<g class="fd" style="--d:.9s"><g class="spin" style="--o:{hx}px {hy}px;--r:48s">'
          f'<circle cx="{hx}" cy="{hy}" r="31" fill="none" stroke="{C["teal"]}" stroke-opacity=".45" '
          f'stroke-dasharray="2 4.5">{ck_flash}</circle></g></g>')
    s.raw(f'<g class="fd" style="--d:.6s"><circle cx="{hx}" cy="{hy}" r="15" fill="{C["panel"]}" stroke="{C["teal"]}" '
          f'stroke-opacity=".8"/><circle cx="{hx}" cy="{hy}" r="3" fill="{C["teal"]}"/></g>')
    s.raw('<g class="fd" style="--d:1s">')
    s.text(hx + 40, hy + 4, "aggregate", 9.5, fam="mono", fill=C["faint"], spacing=1)
    s.raw("</g>")
    # hub pulse when the honest updates are in
    s.raw(f'<circle cx="{hx}" cy="{hy}" r="15" fill="none" stroke="{C["teal"]}" opacity="0">'
          f'<animate attributeName="r" values="15;15;64;64" keyTimes="0;{kt(1.5 / CY)};{kt(2.6 / CY)};1" dur="{f(CY)}s" '
          f'begin="{f(B)}s" repeatCount="indefinite"/>'
          f'<animate attributeName="opacity" values="0;0;.6;0;0" keyTimes="0;{kt(1.5 / CY)};{kt(1.6 / CY)};'
          f'{kt(2.6 / CY)};1" dur="{f(CY)}s" begin="{f(B)}s" repeatCount="indefinite"/></circle>')
    for c in range(NC):
        o, cul = c * CY, culprits[c]
        for i, (top, ck, hub) in enumerate(geo):
            a = o + .15 + .1 * i
            if i == cul:   # an intruding update, stopped at the checkpoint
                d = f"M{f(top[0])} {f(top[1])}L{f(ck[0])} {f(ck[1])}"
                s.raw(f'<circle r="2.6" fill="{C["amber"]}" opacity="0">'
                      f'{windows("opacity", [(a, a + .85)], SUP, 1, 0, .05, B)}'
                      f'{motion_loop(d, a, a + .8, SUP, B)}</circle>')
                s.raw(f'<circle cx="{f(ck[0])}" cy="{f(ck[1])}" r="3" fill="none" stroke="{C["amber"]}" opacity="0">'
                      f'<animate attributeName="r" values="3;3;16;16" keyTimes="0;{kt((a + .8) / SUP)};'
                      f'{kt((a + 1.6) / SUP)};1" dur="{f(SUP)}s" begin="{f(B)}s" repeatCount="indefinite"/>'
                      f'{windows("opacity", [(a + .8, a + 1.6)], SUP, .9, 0, .08, B)}</circle>')
            else:
                d = f"M{f(top[0])} {f(top[1])}L{f(hub[0])} {f(hub[1])}"
                s.raw(f'<circle r="2.2" fill="{C["body"]}" opacity="0">'
                      f'{windows("opacity", [(a, a + .95)], SUP, 1, 0, .05, B)}'
                      f'{motion_loop(d, a, a + .9, SUP, B)}</circle>')
                dn = o + 2.0 + .06 * i
                d = f"M{f(hub[0])} {f(hub[1])}L{f(top[0])} {f(top[1])}"
                s.raw(f'<circle r="2.4" fill="{C["teal"]}" opacity="0">'
                      f'{windows("opacity", [(dn, dn + .8)], SUP, 1, 0, .05, B)}'
                      f'{motion_loop(d, dn, dn + .75, SUP, B)}</circle>')
    for i, (nx, ny) in enumerate(nodes):
        ok = [(c * CY + 2.85 + .06 * i, c * CY + 7.3) for c in range(NC) if culprits[c] != i]
        bad = [(c * CY + 1.0, c * CY + 7.3) for c in range(NC) if culprits[c] == i]
        stroke_t = windows("stroke-opacity", ok, SUP, 1, 0, .2, B)
        stroke_a = windows("stroke-opacity", bad, SUP, 1, 0, .2, B) if bad else ""
        s.raw(f'<g class="fd" style="--d:{f(.8 + i * .07)}s">'
              f'<rect x="{f(nx - 10)}" y="{f(ny - 10)}" width="20" height="20" rx="4" fill="{C["panel"]}" '
              f'stroke="{C["muted"]}" stroke-width="1.2"/>'
              f'<rect x="{f(nx - 10)}" y="{f(ny - 10)}" width="20" height="20" rx="4" fill="none" '
              f'stroke="{C["teal"]}" stroke-width="1.2" stroke-opacity="0">{stroke_t}</rect>'
              + (f'<rect x="{f(nx - 10)}" y="{f(ny - 10)}" width="20" height="20" rx="4" fill="none" '
                 f'stroke="{C["amber"]}" stroke-width="1.2" stroke-opacity="0">{stroke_a}</rect>' if bad else "")
              + f'<circle cx="{f(nx)}" cy="{f(ny)}" r="1.8" fill="{C["muted"]}"/></g>')
        s.raw(f'<text x="{f(nx)}" y="{f(ny + 30)}" class="m" font-size="12" fill="{C["teal"]}" text-anchor="middle" '
              f'opacity="0">✓{windows("opacity", ok, SUP, 1, 0, .2, B)}</text>')
        s.mono("✓✗")
        if bad:
            s.raw(f'<text x="{f(nx)}" y="{f(ny + 30)}" class="m" font-size="12" fill="{C["amber"]}" '
                  f'text-anchor="middle" opacity="0">✗{windows("opacity", bad, SUP, 1, 0, .2, B)}</text>')
    s.raw('<g class="fd" style="--d:1.1s">')
    s.text(hx, 314, "INTRUSIONS CAUGHT  ·  RESULTS VERIFIED BY ALL", 8.5, fam="mono",
           fill=C["faint"], anchor="middle", spacing=1.4)
    s.raw("</g>")
    p = route(hx - 76, (hx - 21, hy))
    s.trail(p, .8, 2.2, op=".9")
    s.light(p, [0, .8, 1.0, 1.8, 2.25], colour="amber", turn=(1.7, 2.25))
    return s.svg("01 Research", f"Chapter 1. I research security for the post-quantum era. {rec['research']} "
                                "A federated network on a lattice: participants send updates, an intrusion is "
                                "caught at the checkpoint, and every honest participant verifies the result.")


# ====================================================================== 02 engineering

def build(rec, fp, status, Y):
    h = HEIGHTS["build"]
    checked = status.get("checked")
    s = Scene(h, "02", "ENGINEERING", f"verify.py  ·  LAST RUN {checked}" if checked else "verify.py", Y=Y)
    t = headline(s, [("I", None), ("build", C["teal"]), ("what", None)], [("I", None), ("research.", None)])
    eng = rec["engineering"]
    lead = "I build what I research, "
    body = eng[len(lead)].upper() + eng[len(lead) + 1:] if eng.startswith(lead) else eng
    _, t2 = s.para(72, 210, body, 15.5, 360, 23, t + .2)
    # languages, each lit in turn
    langs = ["Python", "Rust", "Go", "TypeScript"]
    s.once("chip", "@keyframes chip{0%,100%{opacity:0}6%{opacity:1}22%{opacity:0}}"
                   ".chip{opacity:0;animation:chip 7s ease-in-out infinite both;animation-delay:var(--c)}")
    x = 72
    for i, lg in enumerate(langs):
        wd = width(lg, 10, "mono", spacing=1) + 20
        s.raw(f'<g class="fd" style="--d:{f(t2 + .15 + i * .08)}s">'
              f'<rect x="{f(x)}" y="264" width="{f(wd)}" height="22" rx="5" fill="{C["panel"]}" stroke="{C["line"]}"/>'
              f'<rect class="chip" style="--c:{f(3.4 + i * .45)}s" x="{f(x)}" y="264" width="{f(wd)}" height="22" '
              f'rx="5" fill="{C["teal"]}" fill-opacity=".06" stroke="{C["teal"]}" stroke-opacity=".8"/>')
        s.text(x + 10, 279, lg, 10, fam="mono", fill=C["body"], spacing=1)
        s.raw("</g>")
        x += wd + 8

    # a terminal running this repository's verifier, with the output of the last nightly run
    X0, Y0, TW, TH = 478, 92, 332, 206
    cw = 10.5 * .6
    s.raw(f'<g class="fd" style="--d:.6s"><rect x="{X0}" y="{Y0}" width="{TW}" height="{TH}" rx="8" '
          f'fill="{C["panel"]}" stroke="{C["line"]}"/><line x1="{X0}" y1="{Y0 + 24}" x2="{X0 + TW}" y2="{Y0 + 24}" '
          f'stroke="{C["line"]}"/>')
    for k in range(3):
        s.raw(f'<circle cx="{X0 + 14 + k * 11}" cy="{Y0 + 12}" r="2.6" fill="none" stroke="{C["faint"]}"/>')
    s.text(X0 + TW - 14, Y0 + 16, "~/Thabit-Mahmood", 9, fam="mono", fill=C["faint"], anchor="end", spacing=.6)
    s.raw("</g>")
    xl, ys = X0 + 16, [Y0 + 50, Y0 + 72, Y0 + 92, Y0 + 112, Y0 + 132, Y0 + 162]
    valid = status.get("credential_valid")
    engine = status.get("engine") or "pyca/cryptography"
    result, rcol = (("valid signature ✓", C["teal"]) if valid else
                    ("not yet verified", C["muted"]) if valid is None else ("INVALID signature ✗", C["amber"]))
    out = [(f"key     ML-DSA-65  sha256:{fp[:16]}", C["muted"]),
           (f"record  {rec['name']}, issued {rec['issued']}", C["muted"]),
           (f"engine  {engine}", C["muted"]),
           (f"result  {result}", rcol)]
    cmd = "python3 verify.py"
    TL, B = 12.0, 2.2
    t_type0, dt = .35, .055
    t_enter = t_type0 + len(cmd) * dt + .2
    t_out = [t_enter + .25 + k * .28 for k in range(len(out))]
    t_prompt = t_out[-1] + .35
    t_clear = 11.3
    # line 1: prompt, then the command typed under a clip
    s.raw(f'<g class="fd" style="--d:1.2s">')
    s.text(xl, ys[0], "$", 10.5, fam="mono", fill=C["teal"])
    s.raw("</g>")
    widths = ";".join(f(k * cw) for k in range(len(cmd) + 1)) + ";0"
    kts = ";".join(["0"] + [kt((t_type0 + k * dt) / TL) for k in range(len(cmd))] + [kt(t_clear / TL)])
    s.defs.append(f'<clipPath id="ty"><rect x="{f(xl + 2 * cw - 1)}" y="{ys[0] - 12}" width="0" height="16">'
                  f'<animate attributeName="width" values="{widths}" keyTimes="{kts}" dur="{f(TL)}s" begin="{f(B)}s" '
                  f'repeatCount="indefinite" calcMode="discrete"/></rect></clipPath>')
    s.raw('<g clip-path="url(#ty)">')
    s.text(xl + 2 * cw, ys[0], cmd, 10.5, fam="mono", fill=C["ink"])
    s.raw("</g>")
    for k, (ln, col) in enumerate(out):
        s.text(xl, ys[k + 1], ln, 10.5, fam="mono", fill=col,
               extra=f' opacity="0"')
        s.parts[-1] = s.parts[-1].replace("</text>", windows("opacity", [(t_out[k], t_clear)], TL, 1, 0, .05, B)
                                          + "</text>")
    s.text(xl, ys[5], "$", 10.5, fam="mono", fill=C["teal"], extra=' opacity="0"')
    s.parts[-1] = s.parts[-1].replace("</text>", windows("opacity", [(t_prompt, t_clear)], TL, 1, 0, .05, B)
                                      + "</text>")
    # the cursor is the light, arrived
    cx_vals = ";".join([f(xl + 2 * cw)] + [f(xl + (2 + k + 1) * cw) for k in range(len(cmd))] + [f(xl + 2 * cw)])
    cx_kts = ";".join(["0"] + [kt((t_type0 + k * dt) / TL) for k in range(len(cmd))] + [kt(t_prompt / TL)])
    s.once("blink", "@keyframes bl{0%,55%{opacity:1}56%,100%{opacity:0}}.bl{animation:bl 1.06s steps(1) infinite}")
    s.raw(f'<g class="bl"><rect x="{f(xl + 2 * cw)}" y="{ys[0] - 10}" width="{f(cw)}" height="13" fill="{C["teal"]}" '
          f'opacity="0"><animate attributeName="x" values="{cx_vals}" keyTimes="{cx_kts}" dur="{f(TL)}s" '
          f'begin="{f(B)}s" repeatCount="indefinite" calcMode="discrete"/>'
          f'<animate attributeName="y" values="{ys[0] - 10};{ys[5] - 10}" keyTimes="0;{kt(t_prompt / TL)}" '
          f'dur="{f(TL)}s" begin="{f(B)}s" repeatCount="indefinite" calcMode="discrete"/>'
          f'{windows("opacity", [(0.0, t_enter), (t_prompt, TL - .05)], TL, 1, 0, mode="discrete", begin=B)}'
          f'</rect></g>')
    p = route(xl - 26, (xl + 2 * cw + 3, ys[0] - 4))
    s.trail(p, .8, 2.1, op=".9")
    s.light(p, [0, .8, 1.0, 1.75, 2.15], colour="teal", vanish=True)
    return s.svg("02 Engineering", f"Chapter 2. I build what I research. {body} A terminal runs this repository's "
                                   f"verify.py: key ML-DSA-65, record {rec['name']}, result {result}.")


# ====================================================================== 03 published

def published(rec, Y):
    h = HEIGHTS["published"]
    orcid = rec["links"]["orcid"].rstrip("/").rsplit("/", 1)[-1]
    s = Scene(h, "03", "PUBLISHED", f"ORCID  {orcid}", Y=Y)
    t = headline(s, [("I", None), ("publish", C["teal"]), ("what", None)], [("I", None), ("find.", None)])
    pub = rec["published"]
    body = "Research" + pub[len("Published research"):] if pub.startswith("Published research") else pub
    y_end, t2 = s.para(72, 210, body + " Full list on ORCID.", 15.5, 360, 23, t + .2)
    ys = y_end + 34
    s.raw(f'<g class="fd" style="--d:{f(t2 + .2)}s">')
    s.text(72, ys, "SERVICE", 10, fam="mono", fill=C["teal"], spacing=2.2)
    s.raw("</g>")
    s.para(72, ys + 24, rec["service"], 15.5, 380, 23, t2 + .3, fill=C["body"], st="normal")

    X0, PW, PH = 478, 332, 72
    py = [92, 176, 260]
    labels = ["DRONE NETWORKS", "ZERO-DAY THREATS", "HEALTHCARE"]
    pass_t = [1.85, 2.2, 2.6]
    for k, y0 in enumerate(py):
        s.raw(f'<g class="fd" style="--d:{f(.6 + k * .12)}s"><rect x="{X0}" y="{y0}" width="{PW}" height="{PH}" '
              f'rx="7" fill="{C["panel"]}" stroke="{C["line"]}"/>'
              f'<rect x="{X0}" y="{y0}" width="{PW}" height="{PH}" rx="7" fill="none" stroke="{C["teal"]}" '
              f'stroke-opacity="0"><animate attributeName="stroke-opacity" values="0;.8;.18" keyTimes="0;.25;1" '
              f'begin="{f(pass_t[k])}s" dur="1.2s" fill="freeze"/></rect>')
        s.text(X0 + 14, y0 + 20, labels[k], 9, fam="mono", fill=C["muted"], spacing=1.4)
        s.raw("</g>")
    gx0, gx1 = 604, 798

    # --- drone network: nodes hover, traffic moves, an intrusion is caught every few seconds
    y0 = py[0]
    nd = [(618, y0 + 46), (662, y0 + 24), (708, y0 + 48), (752, y0 + 26), (788, y0 + 46)]
    edges = [(0, 1), (1, 2), (2, 3), (3, 4), (1, 3)]
    bob = [2.9 + rng.random() * 1.2 for _ in nd]
    sp = "; ".join([".45 0 .55 1"] * 2)
    s.raw(f'<g class="fd" style="--d:1s">')
    for a, b in edges:
        (xa, ya), (xb, yb) = nd[a], nd[b]
        s.raw(f'<line x1="{xa}" y1="{ya}" x2="{xb}" y2="{yb}" stroke="{C["spine"]}">'
              f'<animate attributeName="y1" values="{ya};{ya - 2.4};{ya}" dur="{f(bob[a])}s" repeatCount="indefinite" '
              f'calcMode="spline" keySplines="{sp}"/>'
              f'<animate attributeName="y2" values="{yb};{yb - 2.4};{yb}" dur="{f(bob[b])}s" repeatCount="indefinite" '
              f'calcMode="spline" keySplines="{sp}"/></line>')
    for i, (x, y) in enumerate(nd):
        s.raw(f'<g><animateTransform attributeName="transform" type="translate" values="0 0;0 -2.4;0 0" '
              f'dur="{f(bob[i])}s" repeatCount="indefinite" calcMode="spline" keySplines="{sp}"/>'
              f'<circle cx="{x}" cy="{y}" r="6.5" fill="{C["bg"]}" stroke="{C["muted"]}" stroke-opacity=".6"/>'
              f'<path d="M{x - 3} {y}H{x + 3}M{x} {y - 3}V{y + 3}" stroke="{C["body"]}" stroke-width="1.1"/></g>')
    for j, (a, b) in enumerate([(0, 1), (2, 3), (3, 4)]):
        (xa, ya), (xb, yb) = nd[a], nd[b]
        d = f"M{xa} {ya}L{xb} {yb}"
        T = 2.6 + j * .7
        s.raw(f'<circle r="1.6" fill="{C["body"]}" opacity="0">'
              f'{windows("opacity", [(.2, 1.2)], T, .9, 0, .1, j * .5)}{motion_loop(d, .2, 1.2, T, j * .5, "0 0 1 1")}'
              f'</circle>')
    s.raw("</g>")
    TI, BI = 7.0, 3.2
    (xa, ya), (xb, yb) = nd[3], nd[1]
    mx, my = (xa + xb) / 2, (ya + yb) / 2 - 1
    d = f"M{xa} {ya}L{f(mx)} {f(my)}"
    s.raw(f'<circle r="2.4" fill="{C["amber"]}" opacity="0">{windows("opacity", [(0.0, .95)], TI, 1, 0, .05, BI)}'
          f'{motion_loop(d, 0, .9, TI, BI, "0 0 1 1")}</circle>')
    s.raw(f'<circle cx="{f(mx)}" cy="{f(my)}" r="3" fill="none" stroke="{C["amber"]}" opacity="0">'
          f'<animate attributeName="r" values="3;3;15;15" keyTimes="0;{kt(.9 / TI)};{kt(1.7 / TI)};1" dur="{f(TI)}s" '
          f'begin="{f(BI)}s" repeatCount="indefinite"/>{windows("opacity", [(.9, 1.7)], TI, .9, 0, .08, BI)}</circle>')
    s.text(X0 + 14, y0 + 40, "INTRUSION FLAGGED", 8.5, fam="mono", fill=C["amber"], spacing=1.2,
           extra=' opacity="0"')
    s.parts[-1] = s.parts[-1].replace("</text>", windows("opacity", [(.95, 3.2)], TI, 1, 0, .2, BI) + "</text>")

    # --- zero-day: a live signal scrolls past a detector; an unseen pattern is caught each time it passes
    y0 = py[1]
    base = y0 + 46
    Wp = gx1 - gx0
    tr, SX = [], 166
    for xi in range(0, int(Wp) + 1, 2):
        v = 3.0 * math.sin(xi * .23) + 2.0 * math.sin(xi * .61 + 1.3) + 1.2 * math.sin(xi * 1.37)
        v += -17 * math.exp(-((xi - SX) / 2.6) ** 2) + 8 * math.exp(-((xi - SX - 6) / 2.4) ** 2)
        tr.append((xi, base + v))
    dtr = "M" + " L".join(f"{f(x)} {f(y)}" for x, y in tr)
    TS = 4.8
    xd = 712
    phi = ((gx0 + SX - xd) / Wp) % 1
    s.defs.append(f'<clipPath id="zd"><rect x="{gx0}" y="{y0 + 8}" width="{Wp}" height="{PH - 14}"/></clipPath>')
    s.once("scroll", f"@keyframes sc{{from{{transform:translateX(0)}}to{{transform:translateX(-{f(Wp)}px)}}}}"
                     f".sc{{animation:sc {f(TS)}s linear infinite}}")
    a_ = phi * 100
    s.css.append(f"@keyframes det{{0%,{f(a_ - 1.5)}%{{stroke:{C['faint']};fill-opacity:0}}{f(a_ + .5)}%"
                 f"{{stroke:{C['amber']};fill-opacity:.12}}{f(a_ + 22)}%,100%{{stroke:{C['faint']};fill-opacity:0}}}}"
                 f".det{{animation:det {f(TS)}s linear infinite}}"
                 f"@keyframes anm{{0%,{f(a_ - 1)}%{{opacity:0}}{f(a_ + 1)}%{{opacity:1}}{f(a_ + 30)}%{{opacity:1}}"
                 f"{f(a_ + 38)}%,100%{{opacity:0}}}}.anm{{opacity:0;animation:anm {f(TS)}s linear infinite}}")
    s.raw(f'<g class="fd" style="--d:1.1s"><g clip-path="url(#zd)"><g class="sc">'
          f'<path d="{dtr}" transform="translate({gx0} 0)" fill="none" stroke="{C["muted"]}" stroke-width="1.1"/>'
          f'<path d="{dtr}" transform="translate({gx0 + Wp} 0)" fill="none" stroke="{C["muted"]}" stroke-width="1.1"/>'
          f'</g></g>'
          f'<rect class="det" x="{xd - 12}" y="{y0 + 12}" width="24" height="{PH - 20}" rx="3" fill="{C["amber"]}" '
          f'fill-opacity="0" stroke="{C["faint"]}" stroke-dasharray="2 3"/></g>')
    s.text(X0 + 14, y0 + 40, "UNSEEN PATTERN", 8.5, fam="mono", fill=C["amber"], spacing=1.2, cls="anm")

    # --- healthcare: a heartbeat trace, swept like a monitor
    y0 = py[2]
    base = y0 + 46
    beat = [(0, 0), (8, 0), (11, -3), (14, 0), (18, 0), (20, 3), (23, -20), (26, 8), (29, 0), (36, 0), (41, -5),
            (46, 0), (64, 0)]
    pts = []
    x = gx0
    while x + 64 <= gx1 + 1:
        pts += [(x + bx, base + by) for bx, by in beat]
        x += 64
    pts.append((gx1, base))
    decg = "M" + " L".join(f"{f(x)} {f(y)}" for x, y in pts)
    s.once("ecg", "@keyframes ecg{from{stroke-dashoffset:.24}to{stroke-dashoffset:-1.02}}"
                  ".ecg{stroke-dasharray:.24 1.3;animation:ecg 2.7s linear infinite}")
    s.raw(f'<g class="fd" style="--d:1.2s"><path d="{decg}" fill="none" stroke="{C["spine"]}" stroke-width="1.1"/>'
          f'<path class="ecg" d="{decg}" pathLength="1" fill="none" stroke="{C["teal"]}" stroke-width="1.5" '
          f'stroke-linejoin="round"/></g>')

    # the light runs the instrument bank, lighting each panel as it passes
    xb = X0 - 9
    p = route(xb - 6, (xb, py[0] + PH / 2)).line(xb, py[2] + PH / 2)
    s.trail(p, .8, 2.6, op=".9")
    s.light(p, [0, .8, 1.0, 1.6, 1.85, 2.6], colour="teal")
    return s.svg("03 Published", f"Chapter 3. I publish what I find. {body} Full list on ORCID. "
                                 f"Service: {rec['service']}")


# ====================================================================== 04 signed

def seal_layers(cx, cy, fp):
    """Guilloche seal whose lobe counts, phases and star are read off the key fingerprint."""
    fb = bytes.fromhex(fp)

    def ring(R0, A, N, phase):
        return lambda t: ((R0 + A * math.sin(N * t + phase)) * math.cos(t) + cx,
                          (R0 + A * math.sin(N * t + phase)) * math.sin(t) + cy)

    def hypo(R, r, d, rot):
        k = (R - r) / r
        return lambda t: (cx + (R - r) * math.cos(t + rot) + d * math.cos(k * t - rot),
                          cy + (R - r) * math.sin(t + rot) - d * math.sin(k * t - rot))

    def path(fn, t1, steps):
        pts = [fn(t1 * i / steps) for i in range(steps + 1)]
        return "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + "Z"

    n_outer = (34, 36, 38, 40, 42, 44)[fb[0] % 6]
    k_outer = (6, 7, 8)[fb[1] % 3]
    a_outer = 8 + (fb[2] % 3)
    n_bronze = (48, 52, 56, 60)[fb[3] % 4]
    star = ((78, 22, 23, 11), (78, 21, 23, 7), (78, 20, 22, 10), (78, 24, 22, 4))[fb[4] % 4]
    rot = fb[5] / 255 * math.pi / 14
    n_inner = (20, 22, 24, 26, 28)[fb[6] % 5]
    spin = fb[7] / 255 * 2 * math.pi
    R, r, d, turns = star
    outer = [path(ring(104, a_outer, n_outer, spin + 2 * math.pi * i / k_outer), 2 * math.pi, 420)
             for i in range(k_outer)]
    bronze = [path(ring(86, 4.5, n_bronze, spin + 2 * math.pi * i / 3), 2 * math.pi, 520) for i in range(3)]
    stars = [path(hypo(R, r, d, rot), 2 * math.pi * turns, 120 * turns),
             path(hypo(R, r, d, rot + math.pi / (2 * turns + 6)), 2 * math.pi * turns, 120 * turns)]
    inner = [path(ring(34, 5, n_inner, spin + 2 * math.pi * i / 5), 2 * math.pi, 260) for i in range(5)]
    return outer, bronze, stars, inner


def signed(rec, fp, sig_hex, status, Y):
    h = HEIGHTS["signed"]
    s = Scene(h, "04", "SIGNED", "ML-DSA-65  ·  FIPS 204", Y=Y)
    t = headline(s, [("And", None), ("I", None), ("sign", C["teal"])], [("my", None), ("work.", None)])
    _, t2 = s.para(72, 210, "This page is signed with ML-DSA-65, NIST's post-quantum signature standard. A GitHub "
                            "Action checks it every night and redraws this frame from the result.", 15.5, 360, 23,
                   t + .2)
    cx, cy, k = 660, 178, .92
    outer, bronze, stars, inner = seal_layers(cx, cy, fp)
    s.css.append(".g{stroke-dasharray:1;animation:draw 2.4s cubic-bezier(.45,0,.2,1) both;animation-delay:var(--d)}")

    def layer(paths, col, op, sw, d0, rot_s=None, ccw=False):
        body = "".join(f'<path class="g" style="--d:{f(d0 + i * .06)}s" pathLength="1" d="{d_}" fill="none" '
                       f'stroke="{col}" stroke-opacity="{op}" stroke-width="{sw}"/>' for i, d_ in enumerate(paths))
        if rot_s:
            return (f'<g class="spin{" ccw" if ccw else ""}" style="--o:{cx}px {cy}px;--r:{rot_s}s">{body}</g>')
        return f"<g>{body}</g>"

    s.raw(f'<g transform="translate({cx} {cy}) scale({k}) translate({-cx} {-cy})">')
    s.raw(layer(outer, C["teal"], ".55", .6, .7, 150))
    s.raw(layer(bronze, C["amber"], ".5", .55, 1.1, 190, ccw=True))
    s.raw(layer(stars[:1], C["teal"], ".42", .5, 1.4))
    s.raw(layer(stars[1:], C["amber"], ".3", .45, 1.55))
    s.raw(layer(inner, C["teal"], ".55", .55, 1.8, 110))
    # monogram: the light hands itself over to the ring and keeps breathing there
    s.raw(f'<circle cx="{cx}" cy="{cy}" r="34" fill="url(#gt)" opacity="0">'
          f'<animate attributeName="opacity" values="0;.9" begin="2.8s" dur=".5s" fill="freeze"/>'
          f'<animate attributeName="r" values="30;40;30" begin="3.3s" dur="3.4s" repeatCount="indefinite"/></circle>')
    s.raw(f'<circle cx="{cx}" cy="{cy}" r="24" fill="{C["bg"]}" stroke="{C["amber"]}" stroke-opacity=".8" '
          f'stroke-width=".9"><animate attributeName="stroke" values="{C["amber"]};{C["teal"]}" begin="2.8s" '
          f'dur=".5s" fill="freeze"/></circle>')
    s.raw('<g class="fd" style="--d:1.9s">')
    s.text(cx, cy + 7.5, "TM", 20, wt=600, fill=C["amber"], anchor="middle", spacing=1)
    s.raw("</g>")
    # a sheen that crosses the seal every few seconds
    s.defs.append(f'<clipPath id="seal"><circle cx="{cx}" cy="{cy}" r="116"/></clipPath>'
                  f'<linearGradient id="sg" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{C["sheen"]}" '
                  f'stop-opacity="0"/><stop offset=".5" stop-color="{C["sheen"]}" stop-opacity=".28"/>'
                  f'<stop offset="1" stop-color="{C["sheen"]}" stop-opacity="0"/></linearGradient>')
    s.css.append("@keyframes sweep{0%{transform:translateX(-270px)}18%,100%{transform:translateX(270px)}}"
                 ".sheen{animation:sweep 9s cubic-bezier(.4,0,.2,1) 3.6s infinite both}")
    s.raw(f'<g clip-path="url(#seal)"><g transform="rotate(18 {cx} {cy})"><rect class="sheen" x="{cx - 40}" '
          f'y="{cy - 140}" width="80" height="280" fill="url(#sg)"/></g></g>')
    s.raw("</g>")
    valid = status.get("credential_valid")
    if valid:
        line, col = f"verified {status['checked']} ✓", C["teal"]
    elif valid is None:
        line, col = "not yet verified", C["muted"]
    else:
        line, col = "signature invalid ✗", C["amber"]
    s.raw('<g class="fd" style="--d:3.1s">')
    s.text(cx, 318, line, 13.5, st="italic", fill=col, anchor="middle")
    s.raw("</g>")
    s.raw(f'<g class="fd" style="--d:{f(t2 + .2)}s">')
    s.text(72, 310, "HOW TO CHECK IT YOURSELF  ·  BELOW", 9.5, fam="mono", fill=C["muted"], spacing=1.6)
    s.raw("</g>")
    # instrument footer: microprint, key and signature
    phrase = "THABITMAHMOOD·POSTQUANTUM·VERIFIABLE·FEDERATED·"
    n = int((W - 128) / (3.4 * .6 * len(phrase))) + 1
    s.mono(phrase)
    s.defs.append(f'<clipPath id="mp"><rect x="56" y="332" width="{W - 86}" height="8"/></clipPath>')
    fpg = " ".join(fp[i:i + 8].upper() for i in range(0, 32, 8))
    s.raw(f'<g class="fd" style="--d:1.4s"><g clip-path="url(#mp)"><text x="56" y="338" class="m" font-size="3.4" '
          f'fill="{C["faint"]}">{escape(phrase * n)}</text></g>')
    s.text(56, 362, f"KEY  SHA-256  {fpg}", 10.5, fam="mono", fill=C["muted"], spacing=1)
    s.text(56, 382, f"SIG  {sig_hex[:24].upper()}…  ISSUED {rec['issued']}", 10.5, fam="mono", fill=C["muted"],
           spacing=1)
    s.text(W - 30, 382, "verify.py", 10.5, fam="mono", fill=C["teal"], anchor="end", spacing=1)
    s.raw("</g>")
    p = route(cx - 70, (cx - 25, cy))
    s.trail(p, .8, 2.7, op=".9")
    s.light(p, [0, .8, 1.0, 2.0, 2.8], colour="teal", vanish=True)
    return s.svg("04 Signed", f"Chapter 4. And I sign my work. This page is signed with ML-DSA-65, NIST's post-quantum "
                              f"signature standard, and checked every night: {line}. Key fingerprint {fp[:16]}.")


# ====================================================================== links

def button(label, phase):
    w = int(width(label + "  ↗", 11, "mono", spacing=2.2) + 48)
    hgt = 46
    s = Scene.__new__(Scene)
    s.h, s.parts, s.defs, s.css, s.used, s._css_once = hgt, [], [], [], {}, set()
    s.raw(f'<rect x=".5" y=".5" width="{w - 1}" height="{hgt - 1}" rx="10" fill="{C["bg"]}" stroke="{C["line"]}"/>')
    s.raw(f'<rect x="4.5" y="4.5" width="{w - 9}" height="{hgt - 9}" rx="7" fill="none" stroke="{C["teal"]}" '
          f'stroke-opacity=".28" stroke-width=".7"/>')
    s.text(24, 28, label, 11, fam="mono", fill=C["ink"], spacing=2.2)
    s.text(w - 22, 28, "↗", 12, fam="mono", fill=C["teal"], anchor="end")
    # a point of light that circles the button now and then
    r_, x0, y0, x1, y1 = 7, 4.5, 4.5, w - 4.5, hgt - 4.5
    d = (f"M{x0 + r_} {y0}H{x1 - r_}A{r_} {r_} 0 0 1 {x1} {y0 + r_}V{y1 - r_}A{r_} {r_} 0 0 1 {x1 - r_} {y1}"
         f"H{x0 + r_}A{r_} {r_} 0 0 1 {x0} {y1 - r_}V{y0 + r_}A{r_} {r_} 0 0 1 {x0 + r_} {y0}Z")
    TB = 10.0
    s.raw(f'<g opacity="0">{windows("opacity", [(0.0, 3.4)], TB, 1, 0, .5, phase)}'
          f'<circle r="7" fill="url(#gtb)"/><circle r="1.6" fill="#FFFFFF"/>'
          f'{motion_loop(d, 0, 3.4, TB, phase, "0 0 1 1")}</g>')
    s.defs.append(f'<radialGradient id="gtb"><stop offset="0" stop-color="{C["teal"]}" stop-opacity=".8"/>'
                  f'<stop offset="1" stop-color="{C["teal"]}" stop-opacity="0"/></radialGradient>')
    return s.svg(label, label, w=w)


def render_all(rec, fp, sig_hex, status, out):
    Y, offs = 0.0, {}
    for k in ORDER:
        offs[k] = Y
        Y += HEIGHTS[k] + GAP
    files = {
        "film-0-title.svg": title(rec, offs["title"]),
        "film-1-research.svg": research(rec, offs["research"]),
        "film-2-build.svg": build(rec, fp, status, offs["build"]),
        "film-3-published.svg": published(rec, offs["published"]),
        "film-4-signed.svg": signed(rec, fp, sig_hex, status, offs["signed"]),
        "link-linkedin.svg": button("LINKEDIN", 2.0),
        "link-orcid.svg": button("ORCID", 7.0),
    }
    for name, svg in files.items():
        (out / name).write_text(svg, encoding="utf-8")
    return list(files)
