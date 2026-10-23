"""Signs identity/identity.json with the profile key when it needs it.

Run by the workflow on every push. It re-signs only if the record changed
or the published key is not the seed-derived one, so the signature file
does not churn (ML-DSA signing in pyca/cryptography is randomised).

    PROFILE_SIGNING_SEED=<64 hex> python3 scripts/sign.py
    python3 scripts/sign.py --ephemeral     # one-off key, discarded after use
"""
import json
import sys

from cryptography.hazmat.primitives.asymmetric import mldsa

from pq import CTX_IDENTITY, ID, canonical, sha256, signing_key, verify


def main() -> int:
    record = json.loads((ID / "identity.json").read_text(encoding="utf-8"))
    msg = canonical(record)
    key = signing_key()
    if key is None:
        if "--ephemeral" not in sys.argv:
            print("sign: PROFILE_SIGNING_SEED not set, leaving the existing signature in place")
            return 0
        key = mldsa.MLDSA65PrivateKey.generate()
    pk = key.public_key().public_bytes_raw()
    pub_path, sig_path = ID / "ml-dsa-65.pub", ID / "identity.sig"
    if pub_path.exists() and sig_path.exists():
        cur_pk = bytes.fromhex(pub_path.read_text().strip())
        cur_sig = bytes.fromhex(sig_path.read_text().strip())
        if cur_pk == pk and verify(cur_pk, msg, cur_sig, CTX_IDENTITY):
            print(f"sign: record already signed by key {sha256(pk)[:16]}")
            return 0
    sig = key.sign(msg, CTX_IDENTITY)
    assert verify(pk, msg, sig, CTX_IDENTITY)
    pub_path.write_text(pk.hex() + "\n")
    sig_path.write_text(sig.hex() + "\n")
    print(f"sign: signed record with key {sha256(pk)[:16]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
