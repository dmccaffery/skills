"""Batch export used by the nightly cron."""

from .store import get_user


def export_users(user_ids):
    """Yield export rows for each known user id."""
    for user_id in user_ids:
        user = get_user(user_id)
        if user is not None:
            yield {"id": user_id, "name": user["name"]}
