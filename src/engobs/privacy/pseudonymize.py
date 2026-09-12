from __future__ import annotations

import hashlib


def stable_hash(value: str, salt: str, *, namespace: str) -> str:
    digest = hashlib.sha256(f"{namespace}:{salt}:{value}".encode()).hexdigest()
    return digest[:16]


def opaque_session_id(session_id: str) -> str:
    digest = hashlib.sha256(f"engobs-session:{session_id}".encode()).hexdigest()
    return digest[:24]
