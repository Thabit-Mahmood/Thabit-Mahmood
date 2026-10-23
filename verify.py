"""Verify that identity/identity.json is signed by the key in this repository.

    pip install --upgrade cryptography      # or: pip install dilithium-py
    python3 verify.py

The signature is ML-DSA-65 (FIPS 204) over the canonical JSON encoding of
identity.json, bound to the context string below. Verification uses
pyca/cryptography when it supports ML-DSA, and falls back to the
pure-Python dilithium-py otherwise. Both are independent implementations.
"""
import hashlib
import importlib.metadata
import json
import pathlib
import sys

CTX = b"thabit-mahmood/profile/v1"
ID = pathlib.Path(__file__).resolve().parent / "identity"


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def load_verifier():
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric import mldsa

        def verify(pk, msg, sig):
            try:
                mldsa.MLDSA65PublicKey.from_public_bytes(pk).verify(sig, msg, CTX)
                return True
            except InvalidSignature:
                return False

        return verify, f"pyca/cryptography {importlib.metadata.version('cryptography')}"
    except (ImportError, AttributeError):
        from dilithium_py.ml_dsa import ML_DSA_65

        return (lambda pk, msg, sig: ML_DSA_65.verify(pk, msg, sig, ctx=CTX),
                f"dilithium-py {importlib.metadata.version('dilithium-py')}")


def main() -> int:
    verify, engine = load_verifier()
    record = json.loads((ID / "identity.json").read_text(encoding="utf-8"))
    pk = bytes.fromhex((ID / "ml-dsa-65.pub").read_text().strip())
    sig = bytes.fromhex((ID / "identity.sig").read_text().strip())
    ok = verify(pk, canonical(record), sig)
    print(f"key     ML-DSA-65  sha256:{hashlib.sha256(pk).hexdigest()[:16]}")
    print(f"record  {record['name']}, issued {record['issued']}")
    print(f"engine  {engine}")
    print("result  " + ("valid signature" if ok else "INVALID signature"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
