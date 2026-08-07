"""Post-Quantum Security implementation for Craft Framework.

`WOTS` is a Lamport-style hash-based one-time signature: security rests only
on the preimage resistance of SHA-256, so it holds against quantum adversaries
(Grover only halves the effective security margin). One seed must sign only
one message — reusing it reveals both halves of the secret pairs.

Category: Core Framework (Security).
Relations:
  - `PQC` is bound as `pqc`, exposed via the `PQC` facade; a standalone
    utility, not used to sign session cookies (those use HMAC-SHA256, see
    `services/http/session.py`).
References:
  - Guide: `documentation/security.md#post-quantum-cryptography-pqc`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import hashlib
import hmac

_BITS = 256
_CHUNK = 32  # bytes per secret / hash


def _bit(digest: bytes, index: int) -> int:
    return (digest[index // 8] >> (7 - index % 8)) & 1


class WOTS:
    """Hash-based one-time signature (Lamport scheme over SHA-256).

    Key material is derived deterministically from a 32-byte seed. The public
    key is a single SHA-256 digest over the hashes of all secret halves; a
    signature reveals, per message bit, the matching secret and the hash of
    the complementary one, which is enough to rebuild and compare the public
    key without ever knowing the seed.
    """

    def __init__(self, seed: bytes):
        self.seed = seed

    def _secret(self, index: int, bit: int) -> bytes:
        return hmac.new(self.seed, f"{index}:{bit}".encode(), hashlib.sha256).digest()

    def get_public_key(self) -> bytes:
        accumulator = hashlib.sha256()
        for index in range(_BITS):
            for bit in (0, 1):
                accumulator.update(hashlib.sha256(self._secret(index, bit)).digest())
        return accumulator.digest()

    def sign(self, message: bytes) -> bytes:
        digest = hashlib.sha256(message).digest()
        parts = []
        for index in range(_BITS):
            bit = _bit(digest, index)
            # The revealed secret proves knowledge; the hash of the hidden
            # half lets the verifier rebuild the public key commitment.
            parts.append(self._secret(index, bit))
            parts.append(hashlib.sha256(self._secret(index, 1 - bit)).digest())
        return b"".join(parts)

    @staticmethod
    def verify(message: bytes, signature: bytes, public_key: bytes) -> bool:
        if len(signature) != _BITS * 2 * _CHUNK or len(public_key) != _CHUNK:
            return False

        digest = hashlib.sha256(message).digest()
        accumulator = hashlib.sha256()
        for index in range(_BITS):
            offset = index * 2 * _CHUNK
            revealed = signature[offset : offset + _CHUNK]
            hidden_hash = signature[offset + _CHUNK : offset + 2 * _CHUNK]

            pair = [b"", b""]
            bit = _bit(digest, index)
            pair[bit] = hashlib.sha256(revealed).digest()
            pair[1 - bit] = hidden_hash
            accumulator.update(pair[0])
            accumulator.update(pair[1])

        return hmac.compare_digest(accumulator.digest(), public_key)


class PQC:
    """Hybrid tokens: classical HMAC-SHA256 plus a WOTS signature."""

    @staticmethod
    def sign_token(payload: str, secret_key: str, seed: bytes) -> str:
        h = hmac.new(secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
        sig = WOTS(seed).sign(payload.encode()).hex()
        return f"{payload}.{h}.{sig}"

    @staticmethod
    def verify_token(token: str, secret_key: str, public_key: bytes) -> bool:
        # The payload may itself contain dots (e.g. JSON with floats); the two
        # signature parts never do, so split from the right.
        parts = token.rsplit(".", 2)
        if len(parts) != 3:
            return False
        payload, h, sig = parts

        expected_h = hmac.new(secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(h, expected_h):
            return False

        try:
            signature = bytes.fromhex(sig)
        except ValueError:
            return False
        return WOTS.verify(payload.encode(), signature, public_key)
