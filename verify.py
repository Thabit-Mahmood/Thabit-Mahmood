"""Verify that identity/identity.json is signed by the key in this repository.

    pip install dilithium-py
    python3 verify.py

The signature is ML-DSA-65 (FIPS 204) over the canonical JSON encoding of
identity.json, bound to the context string below.
"""
import hashlib
import json
import pathlib
import sys

from dilithium_py.ml_dsa import ML_DSA_65

CTX = b"thabit-mahmood/profile/v1"
ID = pathlib.Path(__file__).resolve().parent / "identity"


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def main() -> int:
    record = json.loads((ID / "identity.json").read_text(encoding="utf-8"))
    pk = bytes.fromhex((ID / "ml-dsa-65.pub").read_text().strip())
    sig = bytes.fromhex((ID / "identity.sig").read_text().strip())
    fp = hashlib.sha256(pk).hexdigest()
    ok = ML_DSA_65.verify(pk, canonical(record), sig, ctx=CTX)
    print(f"key     ML-DSA-65  sha256:{fp[:16]}")
    print(f"record  {record['name']}, issued {record['issued']}")
    print("result  " + ("valid signature" if ok else "INVALID signature"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
