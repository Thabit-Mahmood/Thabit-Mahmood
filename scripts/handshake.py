"""Runs a post-quantum handshake with whoever opened a "handshake" issue.

Triggered by the workflow on issues titled "handshake". For the issue's
author it:

  1. takes their ML-KEM-768 encapsulation key from the issue body if they
     pasted one (2368 hex characters), or generates an ephemeral key pair
     for them otherwise,
  2. encapsulates a fresh 32-byte shared secret to that key (FIPS 203),
  3. signs the transcript with the profile's ML-DSA-65 key (FIPS 204),
  4. appends it to identity/handshakes.json, replies on the issue, closes it.

Inputs come from the environment only (never interpolated into a shell):
LOGIN, USER_TYPE, ISSUE_NUMBER, ISSUE_BODY, REPO, GITHUB_TOKEN,
PROFILE_SIGNING_SEED.
"""
import datetime as dt
import json
import os
import re
import sys
import urllib.request

from cryptography.hazmat.primitives.asymmetric import mlkem

from pq import CTX_HANDSHAKE, ID, b64, canonical, sha256, signing_key, verify

LEDGER = ID / "handshakes.json"
EK_HEX = 1184 * 2


def api(method, path, payload):
    req = urllib.request.Request(
        f"https://api.github.com/repos/{os.environ['REPO']}{path}", method=method,
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
                 "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
                 "User-Agent": "profile-handshake"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status


def reply_and_close(n_issue, body, close=True):
    api("POST", f"/issues/{n_issue}/comments", {"body": body})
    if close:
        api("PATCH", f"/issues/{n_issue}", {"state": "closed", "state_reason": "completed"})


def main() -> int:
    login = os.environ.get("LOGIN", "")
    issue = int(os.environ["ISSUE_NUMBER"])
    if os.environ.get("USER_TYPE") == "Bot" or not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})", login):
        print("handshake: ignoring this author")
        return 0
    key = signing_key()
    if key is None:
        reply_and_close(issue, "Handshakes are not switched on yet. This issue will stay open until they are.",
                        close=False)
        return 0
    ledger = json.loads(LEDGER.read_text()) if LEDGER.exists() else []
    for e in ledger:
        if e["visitor"].lower() == login.lower():
            reply_and_close(issue, f"You're already in the ledger as handshake #{e['n']}, signed {e['at']}. "
                                   "One per account keeps the record meaningful.")
            return 0

    body = re.sub(r"\s+", "", os.environ.get("ISSUE_BODY", ""))
    runs = [r for r in re.findall(r"[0-9a-fA-F]+", body) if len(r) == EK_HEX]
    visitor_sk, mode, ek = None, "ephemeral", None
    if runs:
        try:
            pub = mlkem.MLKEM768PublicKey.from_public_bytes(bytes.fromhex(runs[0]))
            mode = "visitor-key"
        except Exception:
            runs = []
    if not runs:
        visitor_sk = mlkem.MLKEM768PrivateKey.generate()
        pub = visitor_sk.public_key()
    ek = pub.public_bytes_raw()
    ss, ct = pub.encapsulate()
    if visitor_sk is not None:
        assert visitor_sk.decapsulate(ct) == ss  # both sides hold the same secret

    profile_pk = key.public_key().public_bytes_raw()
    transcript = {
        "n": len(ledger) + 1,
        "visitor": login,
        "at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "kem": "ML-KEM-768",
        "mode": mode,
        "ek_sha256": sha256(ek),
        "ct_sha256": sha256(ct),
        "ss_sha256": sha256(ss),
        "profile_key_sha256": sha256(profile_pk),
    }
    sig = key.sign(canonical(transcript), CTX_HANDSHAKE)
    assert verify(profile_pk, canonical(transcript), sig, CTX_HANDSHAKE)
    ledger.append(dict(transcript, sig=b64(sig)))
    LEDGER.write_text(json.dumps(ledger, indent=1, ensure_ascii=False) + "\n")

    n = transcript["n"]
    if mode == "visitor-key":
        ek_line = "your key, from the issue"
        ss_line = (f"32 bytes. Decapsulate the ciphertext below with your decapsulation key; its SHA-256 "
                   f"should be `{transcript['ss_sha256']}`")
        extra = f"\n\n<details><summary>Ciphertext (1088 bytes, hex)</summary>\n\n```\n{ct.hex()}\n```\n\n</details>"
    else:
        ek_line = "ephemeral, generated for you and then destroyed"
        ss_line = f"32 bytes, derived on both sides and equal, commitment `sha256:{transcript['ss_sha256'][:16]}`"
        extra = ""
    reply_and_close(issue, f"""**Handshake #{n} complete.** Thanks for stopping by, {login}.

| step | result |
|---|---|
| ML-KEM-768 encapsulation key | `sha256:{transcript['ek_sha256'][:16]}`, {ek_line} |
| ciphertext | 1088 bytes, `sha256:{transcript['ct_sha256'][:16]}` |
| shared secret | {ss_line} |
| ML-DSA-65 transcript signature | 3309 bytes, profile key `sha256:{transcript['profile_key_sha256'][:16]}` |

It's recorded in [`identity/handshakes.json`](https://github.com/{os.environ['REPO']}/blob/main/identity/handshakes.json). Check every entry yourself with `python3 verify.py --handshakes`.{extra}""")
    print(f"handshake: #{n} with {login} ({mode})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
