import json
from abc import abstractmethod
from builtins import callable

from loko_orchestrator.utils.validators import DictVal


class KeyValue:
    def __init__(self, key, value):
        self.key = key
        self.value = value


class ObjectT:
    @abstractmethod
    def __call__(self, o):
        pass


class Move(ObjectT):
    def __init__(self, new_key):
        self.new_key = new_key

    def __call__(self, o):
        return KeyValue(self.new_key, o)


class DictTransform(dict):
    def __call__(self, o, keep=None):
        ret = {}
        keep = keep or set()
        for k, t in self.items():
            if callable(k):
                for k2, v2 in o.items():
                    if k(k2, v2):
                        print("YES", k2, t(v2))
                        self._update_ret(k2, t(v2), ret)
            else:
                if k in o:
                    temp = t(o[k])
                    self._update_ret(k, temp, ret)
        keys = set(self.keys())
        for k in o:
            if k not in keys:
                ret[k] = o[k]
        return ret

    def _update_ret(self, k, value, ret):
        if isinstance(value, KeyValue):
            if isinstance(value.key, tuple):
                temp = ret
                for k in value.key[:-1]:
                    ret[k] = ret.get(k) or {}
                    temp = ret[k]
                temp[value.key[-1]] = value.value
            else:
                ret[value.key] = value.value
        else:
            ret[k] = value


class ChainTransform:
    def __init__(self, *ts):
        self.ts = ts

    def __call__(self, o):
        ret = o
        for t in self.ts:
            ret = t(ret)
        return ret


def portst(d):
    ret = {}
    for k, v in d.items():
        ret[f'{k}/tcp'] = [dict(HostPort=str(v))]
    return ret


if __name__ == "__main__":
    m = DictTransform(name=Move(("contact", "nome")))
    m[lambda k, v: isinstance(v, int)] = lambda x: x * 100

    # print(m(dict(name="Fulvio", age=1)))

    c = ChainTransform(portst, Move(("HostConfig", "PortBindings")))

    m = DictTransform(ports=c)

    p = "/home/fulvio/loko/projects/mongo_extension_example/config.json"
    with open(p) as o:
        content = json.load(o)
        for name, el in content.get("side_containers", {}).items():
            print("Side", el)
            print(m(el, keep={"image", "environment"}))
