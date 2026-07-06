"""HTTP handlers for the user service."""

from .store import fetch_user


def handle_user_lookup(request):
    """Return the user identified by the request's ``user_id``."""
    user = fetch_user(request["user_id"])
    if user is None:
        return {"status": 404}
    return {"status": 200, "body": user}
