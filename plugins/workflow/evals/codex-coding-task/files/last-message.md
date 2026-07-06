# Codex task result

Task: rename `get_user` to `fetch_user` across `src/`, updating the definition and every import and call site.

All occurrences of `get_user` have been renamed to `fetch_user`. The definition in `src/store.py` was renamed, and the
call sites in `src/api.py` were updated to import and use the new name. The rename is complete and every module imports
cleanly.
