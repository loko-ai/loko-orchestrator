import os
from pathlib import Path


def to_relative(path):
    path = Path(path)
    if path.is_absolute():
        return Path(*path.parts[1:])
    else:
        return path


def find_file(name, fallback=None):
    path = Path(os.getcwd())
    while True:
        if path.parent == path:
            return fallback

        if (path / name).exists():
            return path / name
        else:
            path = path.parent
