"""Renders the profile film from identity/ and assets/status.json.

    pip install fonttools brotli cryptography
    python3 verify.py --status assets/status.json
    python3 scripts/build.py

Signing is done by scripts/sign.py; this script only draws (see scenes.py).
The guilloche seal in the last frame is generated from the signing key's
fingerprint, so a different key draws a different seal, much like SSH's
randomart, and the verification line under it comes from the nightly run.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import pathlib

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
ID = ROOT / "identity"
OUT = ROOT / "assets"
SERIF = pathlib.Path(os.environ.get("SERIF", ROOT / "fonts"))
MONO = pathlib.Path(os.environ.get("MONO", ROOT / "fonts"))

W = 840
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
    import scenes
    scenes.render_all(rec, fp, sig_hex, status, OUT)
    for p in sorted(OUT.glob("*.svg")):
        print(f"{p.name:22s} {p.stat().st_size / 1024:6.1f} KB")


if __name__ == "__main__":
    main()
