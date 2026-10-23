"""Verify this profile's signatures.

    pip install --upgrade cryptography      # or: pip install dilithium-py
    python3 verify.py                       # the credential
    python3 verify.py --handshakes          # plus every visitor handshake

identity/identity.json is signed with ML-DSA-65 (FIPS 204) under the
context "thabit-mahmood/profile/v1"; each entry of identity/handshakes.json
is signed by the same key under "thabit-mahmood/handshake/v1". Verification
uses pyca/cryptography when it supports ML-DSA and falls back to the
independent pure-Python dilithium-py otherwise.
"""
import base64
import datetime as dt
import hashlib
import importlib.metadata
import json
import pathlib
import sys

ID = pathlib.Path(__file__).resolve().parent / "identity"
CTX_IDENTITY = b"thabit-mahmood/profile/v1"
CTX_HANDSHAKE = b"thabit-mahmood/handshake/v1"


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def load_verifier():
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric import mldsa

        def verify(pk, msg, sig, ctx):
            try:
                mldsa.MLDSA65PublicKey.from_public_bytes(pk).verify(sig, msg, ctx)
                return True
            except InvalidSignature:
                return False

        return verify, f"pyca/cryptography {importlib.metadata.version('cryptography')}"
    except (ImportError, AttributeError):
        from dilithium_py.ml_dsa import ML_DSA_65

        return (lambda pk, msg, sig, ctx: ML_DSA_65.verify(pk, msg, sig, ctx=ctx),
                f"dilithium-py {importlib.metadata.version('dilithium-py')}")


def main() -> int:
    verify, engine = load_verifier()
    record = json.loads((ID / "identity.json").read_text(encoding="utf-8"))
    pk = bytes.fromhex((ID / "ml-dsa-65.pub").read_text().strip())
    sig = bytes.fromhex((ID / "identity.sig").read_text().strip())
    fp = hashlib.sha256(pk).hexdigest()
    ok = verify(pk, canonical(record), sig, CTX_IDENTITY)
    print(f"key         ML-DSA-65  sha256:{fp[:16]}")
    print(f"record      {record['name']}, issued {record['issued']}")
    print(f"engine      {engine}")
    print("credential  " + ("valid signature" if ok else "INVALID signature"))

    good, total = 0, 0
    ledger_path = ID / "handshakes.json"
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else []
    if "--handshakes" in sys.argv or "--status" in sys.argv:
        for e in ledger:
            total += 1
            body = {k: v for k, v in e.items() if k != "sig"}
            if body.get("profile_key_sha256") == fp and verify(pk, canonical(body), base64.b64decode(e["sig"]),
                                                              CTX_HANDSHAKE):
                good += 1
            else:
                print(f"handshake   #{e['n']} {e['visitor']}: INVALID")
        print(f"handshakes  {good}/{total} valid")

    if "--status" in sys.argv:
        out = pathlib.Path(sys.argv[sys.argv.index("--status") + 1])
        out.write_text(json.dumps({
            "credential_valid": ok, "engine": engine, "key_sha256": fp,
            "checked": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d"),
            "handshakes_valid": good, "handshakes_total": total,
            "recent": [e["visitor"] for e in ledger[-4:]][::-1],
        }, indent=1) + "\n")
    return 0 if ok and good == total else 1


if __name__ == "__main__":
    sys.exit(main())
