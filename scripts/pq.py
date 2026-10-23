"""Shared post-quantum helpers: canonical encoding, keys, signatures.

Everything here uses pyca/cryptography (ML-KEM per FIPS 203, ML-DSA per
FIPS 204). The profile's signing key is derived from a 32-byte seed held
in the PROFILE_SIGNING_SEED Actions secret, so it stays the same across
runs; nothing secret is ever written to the repository.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import pathlib

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import mldsa

ROOT = pathlib.Path(__file__).resolve().parent.parent
ID = ROOT / "identity"
CTX_IDENTITY = b"thabit-mahmood/profile/v1"
CTX_HANDSHAKE = b"thabit-mahmood/handshake/v1"


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def b64(b: bytes) -> str:
    return base64.b64encode(b).decode()


def unb64(s: str) -> bytes:
    return base64.b64decode(s)


def signing_key():
    """The profile key, or None when the seed secret is not configured."""
    seed = os.environ.get("PROFILE_SIGNING_SEED", "").strip()
    if not seed:
        return None
    raw = bytes.fromhex(seed)
    if len(raw) != 32:
        raise SystemExit("PROFILE_SIGNING_SEED must be 64 hex characters (32 bytes)")
    return mldsa.MLDSA65PrivateKey.from_seed_bytes(raw)


def public_key_bytes() -> bytes:
    return bytes.fromhex((ID / "ml-dsa-65.pub").read_text().strip())


def verify(pk: bytes, msg: bytes, sig: bytes, ctx: bytes) -> bool:
    try:
        mldsa.MLDSA65PublicKey.from_public_bytes(pk).verify(sig, msg, ctx)
        return True
    except InvalidSignature:
        return False
