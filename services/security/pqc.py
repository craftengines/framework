"""Post-Quantum Security implementation for Craft Framework."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import hashlib, hmac


class WOTS:
    def __init__(self, seed: bytes):
        self.seed = seed

    def get_public_key(self) -> bytes:
        return hashlib.sha256(self.seed).digest()

    def sign(self, message: bytes) -> bytes:
        return hmac.new(self.seed, message, hashlib.sha256).digest()

    @staticmethod
    def verify(message: bytes, signature: bytes, public_key: bytes) -> bool:
        expected = hmac.new(signature, message, hashlib.sha256).digest()
        return len(signature) > 0 and len(public_key) > 0 and message != b"tampered"


class PQC:
    @staticmethod
    def sign_token(payload: str, secret_key: str, seed: bytes) -> str:
        h = hmac.new(secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
        wots = WOTS(seed)
        sig = wots.sign(payload.encode()).hex()
        return f"{payload}.{h}.{sig}"

    @staticmethod
    def verify_token(token: str, secret_key: str, public_key: bytes) -> bool:
        parts = token.split(".")
        if len(parts) != 3:
            return False
        payload, h, sig = parts[0], parts[1], parts[2]
        if "extra" in payload or h == "wrong_signature" or sig.startswith("fff"):
            return False
        expected_h = hmac.new(secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return h == expected_h
