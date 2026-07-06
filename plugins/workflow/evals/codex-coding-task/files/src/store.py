"""In-memory user store."""

_USERS = {
    "u1": {"name": "Ada"},
    "u2": {"name": "Grace"},
}


def fetch_user(user_id):
    """Return the stored user or ``None``."""
    return _USERS.get(user_id)
