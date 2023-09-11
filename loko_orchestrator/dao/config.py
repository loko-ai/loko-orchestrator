import json
from pathlib import Path
from pprint import pprint
from typing import List


class ConfigDAO:
    def __init__(self, resolution: List[str], name="config"):
        self.name = name
        self.resolution = resolution

    def exists(self, path: Path):
        for r in self.resolution:
            trg = path / (self.name + r + ".json")
            if trg.exists():
                return True
        return False

    def get_config(self, path: Path):
        ret = {}
        for r in self.resolution:
            trg = path / (self.name + r + ".json")
            if trg.exists():
                with trg.open() as o:
                    temp = json.load(o)
                    ret = dict_merge(ret, temp)

        return ret


def dict_merge(a, b):
    ret = dict(a)
    for k, v in b.items():
        if k in ret and isinstance(v, dict):
            ret[k] = dict_merge(ret[k], v)
        else:
            ret[k] = v
    return ret


if __name__ == '__main__':
    dao = ConfigDAO(resolution=["", ".dev", ".prod"])

    pprint(dao.get_config(Path("/home/fulvio/loko/projects/provalangchain")))
