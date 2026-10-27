import time
import threading
from typing import Dict, Optional
from docuquery.services.auth_service import decode_token

_lock = threading.Lock()
# Maps token (or token jti/sub+exp) to expiration timestamp
_revoked_tokens: Dict[str, float] = {}


def revoke_token(token: str) -> None:
    """
    Mark a token as revoked until its original expiration time.
    """
    if not token:
        return

    payload = decode_token(token)
    now = time.time()
    # If payload cannot be decoded or lacks exp, default to 2 hours
    exp = payload.get("exp", now + 7200) if payload else (now + 7200)

    with _lock:
        _cleanup_expired(now)
        _revoked_tokens[token] = float(exp)


def is_token_revoked(token: str) -> bool:
    """
    Check if a token has been revoked.
    """
    if not token:
        return False

    now = time.time()
    with _lock:
        if token in _revoked_tokens:
            if _revoked_tokens[token] > now:
                return True
            else:
                # Expired naturally
                del _revoked_tokens[token]
                return False
    return False


def _cleanup_expired(now: float) -> None:
    """Internal helper to sweep expired entries."""
    to_delete = [tok for tok, exp in _revoked_tokens.items() if exp <= now]
    for tok in to_delete:
        del _revoked_tokens[tok]


def clear_blacklist() -> None:
    """Reset blacklist (useful for test isolation)."""
    with _lock:
        _revoked_tokens.clear()
