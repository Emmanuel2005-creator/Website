"""Compatibility with the original Werkzeug salted SHA-256 accounts."""
import hashlib
import hmac

from werkzeug.security import check_password_hash


def verify_password(stored_hash, password):
    if not stored_hash:
        return False
    try:
        method, salt, digest = stored_hash.split('$', 2)
        if method == 'sha256':
            # Werkzeug < 3 used HMAC-SHA256 with the salt as its key.
            # Constant-time verification leaves existing account records intact.
            if not salt or len(digest) != 64:
                return False
            candidate = hmac.new(salt.encode(), password.encode(), hashlib.sha256).hexdigest()
            return hmac.compare_digest(digest, candidate)
        return check_password_hash(stored_hash, password)
    except (ValueError, TypeError):
        return False
