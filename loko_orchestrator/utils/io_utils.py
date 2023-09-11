import json
from pathlib import Path


def content_reader(path, fsdao, output_type="text"):
    match output_type:
        case "text":
            with fsdao.get(Path(path), "r") as f:
                return f.read()
        case "binary":
            with fsdao.get(Path(path), "rb") as f:
                return f.read()
        case "json":
            with fsdao.get(Path(path)) as f:
                return json.load(f)
    raise Exception(f"Can't read file: output_type {output_type}")
