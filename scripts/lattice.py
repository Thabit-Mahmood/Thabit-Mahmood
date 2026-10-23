"""Renders assets/lattice.svg from the live contribution calendar.

Runs daily in GitHub Actions with nothing but the standard library:

    GITHUB_TOKEN=... LOGIN=Thabit-Mahmood python3 scripts/lattice.py

Each day of the last year is a point of a skewed 2-D lattice (basis b1 = one
week, b2 = one weekday). Brightness follows GitHub's own contribution
quartiles. If the API call fails, the previous SVG is left untouched.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import urllib.request

from kit import ASSETS, C, FONTS, W, card, f, font_face, spans, text, x

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount contributionLevel weekday } }
      }
    }
  }
}
"""
LEVEL = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
WEEKDAYS = ["Sundays", "Mondays", "Tuesdays", "Wednesdays", "Thursdays", "Fridays", "Saturdays"]


def fetch(login: str, token: str) -> dict:
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json",
                 "User-Agent": "profile-lattice"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    if "errors" in payload:
        raise RuntimeError(payload["errors"])
    return payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def streaks(days):
    """Current streak (today may still be empty) and longest streak, in days."""
    longest = run = 0
    for d in days:
        run = run + 1 if d["count"] > 0 else 0
        longest = max(longest, run)
    cur = 0
    seq = list(reversed(days))
    if seq and seq[0]["count"] == 0:
        seq = seq[1:]
    for d in seq:
        if d["count"] == 0:
            break
        cur += 1
    return cur, longest


def render(cal: dict, today: dt.date) -> str:
    weeks = cal["weeks"][-53:]
    flat = []
    for w_i, wk in enumerate(weeks):
        for d in wk["contributionDays"]:
            flat.append({"w": w_i, "wd": d["weekday"], "date": dt.date.fromisoformat(d["date"]),
                         "count": d["contributionCount"], "level": LEVEL.get(d["contributionLevel"], 0)})
    flat.sort(key=lambda d: d["date"])
    total = sum(d["count"] for d in flat)
    cur, longest = streaks(flat)
    by_wd = [0] * 7
    for d in flat:
        by_wd[d["wd"]] += d["count"]
    busiest = WEEKDAYS[max(range(7), key=lambda i: by_wd[i])] if total else "n/a"
    peak = max(flat, key=lambda d: d["count"]) if flat else None

    H = 300
    X0, Y0 = 58, 92
    B1, B2 = (16.1, 0.0), (5.2, 15.4)
    radius = [1.7, 2.5, 3.2, 3.9, 4.7]
    alpha = [1, .4, .6, .82, 1]

    def pos(d):
        return X0 + d["w"] * B1[0] + d["wd"] * B2[0], Y0 + d["w"] * B1[1] + d["wd"] * B2[1]

    css = ["@keyframes rise{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:none}}",
           ".p{animation:rise .55s cubic-bezier(.2,.8,.3,1) both;transform-box:fill-box}",
           "@keyframes scan{0%{transform:translateX(-80px)}55%,100%{transform:translateX(1060px)}}",
           ".scan{animation:scan 8s ease-in-out 1.6s infinite}",
           "@keyframes halo{0%,100%{opacity:.9}50%{opacity:.3}}",
           ".halo{animation:halo 2.4s ease-in-out infinite}"]
    css += [f".c{w}{{animation-delay:{w * 18}ms}}" for w in range(len(weeks))]
    defs = f"""
<filter id="hot" x="-150%" y="-150%" width="400%" height="400%">
<feGaussianBlur stdDeviation="2.4" result="b"/>
<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
</filter>
<linearGradient id="beam" x1="0" y1="0" x2="1" y2="0">
<stop offset="0" stop-color="{C['teal']}" stop-opacity="0"/>
<stop offset=".8" stop-color="{C['teal']}" stop-opacity=".14"/>
<stop offset="1" stop-color="{C['teal']}" stop-opacity="0"/>
</linearGradient>
"""
    body = []
    body.append(text(40, 46, "", size=13, raw=True).replace(
        "></text>", ">" + spans([("contribution lattice", C["teal"]), ("   L(B) = { Bz : z ∈ ℤ² }", C["faint"])], 13)
        + "</text>"))
    body.append(text(W - 40, 46, f"last 12 months · rendered {today.isoformat()}", size=11.5,
                     fill=C["faint"], anchor="end"))
    body.append(f'<line x1="40" y1="62" x2="{W - 40}" y2="62" stroke="{C["rule"]}"/>')

    # month labels on the first week of each month
    seen = set()
    for d in flat:
        if d["wd"] == 0 and d["date"].day <= 7 and (d["date"].year, d["date"].month) not in seen:
            seen.add((d["date"].year, d["date"].month))
            px, _ = pos(d)
            body.append(text(px, 80, d["date"].strftime("%b"), size=10.5, fill=C["faint"]))

    # skewed scan beam, parallel to b2
    body.append(f'<g class="scan"><g transform="skewX(18.66) translate(0 0)">'
                f'<rect x="{X0 - 40}" y="{Y0 - 12}" width="46" height="{f(6 * B2[1] + 24)}" fill="url(#beam)"/>'
                f'</g></g>')

    pts = []
    for d in flat:
        if d["date"] > today:
            continue
        px, py = pos(d)
        lv = d["level"]
        col = "#2C3B53" if lv == 0 else C["teal"]
        flt = ' filter="url(#hot)"' if lv == 4 else ""
        pts.append(f'<circle class="p c{d["w"]}" cx="{f(px)}" cy="{f(py)}" r="{radius[lv]}" fill="{col}" '
                   f'fill-opacity="{alpha[lv]}"{flt}><title>{d["date"].isoformat()}: {d["count"]}</title></circle>')
    body.append("<g>" + "".join(pts) + "</g>")

    if peak and peak["count"] > 0:
        px, py = pos(peak)
        body.append(f'<circle class="halo" cx="{f(px)}" cy="{f(py)}" r="8.5" fill="none" stroke="{C["amber"]}" '
                    f'stroke-width="1.4"/>')
        body.append(text(40, 220, "", size=11.5, raw=True).replace("></text>", ">" + spans([
            ("◆ ", C["amber"]), ("peak ", C["faint"]), (str(peak["count"]), C["amber"]),
            (" on " + peak["date"].strftime("%d %b %Y"), C["faint"])], 11.5) + "</text>"))

    # legend
    lx = W - 40
    items = list(range(4, -1, -1))
    body.append(text(lx, 220, "more", size=10.5, fill=C["faint"], anchor="end"))
    lx -= 40
    for lv in items:
        col = "#2C3B53" if lv == 0 else C["teal"]
        body.append(f'<circle cx="{f(lx)}" cy="216.5" r="{radius[lv]}" fill="{col}" fill-opacity="{alpha[lv]}"/>')
        lx -= 15
    body.append(text(lx - 2, 220, "less", size=10.5, fill=C["faint"], anchor="end"))

    body.append(f'<line x1="40" y1="236" x2="{W - 40}" y2="236" stroke="{C["rule"]}"/>')
    stats = [(f"{total:,}", "contributions"), (f"{cur}", "day current streak"),
             (f"{longest}", "day longest streak"), (busiest, "most active")]
    col_w = (W - 80) / 4
    for i, (val, lab) in enumerate(stats):
        sx = 40 + i * col_w
        body.append(text(sx, 270, val, size=21, fill=C["text"], weight=700))
        body.append(text(sx + len(val) * 21 * 0.6 + 10, 269, lab, size=11.5, fill=C["muted"]))

    fonts = font_face(FONTS / "live-400.woff2", 400) + "\n" + font_face(FONTS / "live-700.woff2", 700)
    return card(W, H, "\n".join(body), title="Contribution lattice",
                desc=f"{total} contributions in the last 12 months, current streak {cur} "
                     f"day{'s' * (cur != 1)}, longest {longest} day{'s' * (longest != 1)}, "
                     f"most active on {busiest}. Rendered {today.isoformat()}.",
                css="\n".join(css), defs=defs, fonts=fonts)


def main() -> int:
    login = os.environ.get("LOGIN", "Thabit-Mahmood")
    src = os.environ.get("CALENDAR_JSON")
    try:
        if src:
            cal = json.load(open(src))
        else:
            cal = fetch(login, os.environ["GITHUB_TOKEN"])
    except Exception as exc:  # keep yesterday's image rather than publishing a broken one
        print(f"lattice: fetch failed, keeping previous image: {exc}", file=sys.stderr)
        return 1
    svg = render(cal, dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).date())
    (ASSETS / "lattice.svg").write_text(svg, encoding="utf-8")
    print(f"lattice.svg {len(svg) / 1024:.1f} KB, {cal['totalContributions']} contributions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
