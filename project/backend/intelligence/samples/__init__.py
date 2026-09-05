"""Access to the bundled demo spreadsheets."""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(HERE, "manifest.json")


def list_samples():
    """The catalogue the import screen offers, or an empty list if absent."""
    try:
        with open(MANIFEST, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return []


def load_sample(name):
    """Return (bytes, label) for a bundled file, or None. Name is not a path."""
    if not name or os.path.basename(name) != name:
        return None
    for entry in list_samples():
        if entry.get("file") == name:
            path = os.path.join(HERE, name)
            if not os.path.exists(path):
                return None
            with open(path, "rb") as fh:
                return fh.read(), entry.get("label", name)
    return None
