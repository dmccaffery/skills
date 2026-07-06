"""Load service configuration from a JSON file."""

import json


def load_config(path, overrides={}):
    """Return the parsed configuration with ``overrides`` applied on top."""
    with open(path) as fh:
        config = json.load(fh)
    overrides.update(config.pop("overrides", {}))
    config.update(overrides)
    return {
        "endpoint": config["endpoint"],
        "retries": int(config.get("retries", 3)),
        "timeout": float(config.get("timeout", 30.0)),
    }
