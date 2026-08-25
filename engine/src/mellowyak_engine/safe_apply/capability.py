from __future__ import annotations

import hashlib
import hmac
import secrets


def issue_confirmation(
    transaction_id: str,
    project_id: str,
    candidate_id: str,
    source_manifest_digest: str,
) -> tuple[str, str]:
    nonce = secrets.token_urlsafe(32)
    return nonce, confirmation_digest(
        nonce, transaction_id, project_id, candidate_id, source_manifest_digest
    )


def confirmation_digest(
    nonce: str,
    transaction_id: str,
    project_id: str,
    candidate_id: str,
    source_manifest_digest: str,
) -> str:
    payload = "\0".join(
        [nonce, transaction_id, project_id, candidate_id, source_manifest_digest]
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def verify_confirmation(provided: str, expected: str) -> bool:
    return hmac.compare_digest(provided, expected)
