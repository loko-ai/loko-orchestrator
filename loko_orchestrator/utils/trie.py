from collections import defaultdict

from loko_orchestrator.utils.logger_utils import logger


class Value:
    def __init__(self, value):
        self.value = value


class Trie:
    def __init__(self):
        self.data = {}

    def set(self, parts, obj):
        *temp, last = parts
        dest = self.data
        for part in temp:
            if part not in dest:
                dest[part] = {}
            dest = dest[part]
        dest[last] = Value(obj)

    def get(self, parts, value=None):
        *temp, last = parts
        dest = self.data
        for part in temp:
            dest = dest.get(part, None)
            if not dest:
                return None
        return dest.get(last, value)

    def get_type(self, oname):
        if oname in self.data:
            return self.data[oname].value.type
        return None

    def find_prefix(self, parts):
        # print("PARTS",parts)
        logger.debug("PARTS {parts}".format(parts=parts))
        temp = list(parts)
        obj = None
        curr = []
        while temp:
            el = temp.pop(0)
            curr.append(el)
            obj = self.get(curr)
            if isinstance(obj, Value):
                return obj.value, curr, temp
        raise Exception("Prefix not found")


if __name__ == "__main__":
    from pathlib import Path

    t = Trie()
    p = Path("a/b")
    t.set(p.parts, "primo dao")
    p2 = Path("a/c/e")
    t.set(p2.parts, "secondo dao")
    p3 = Path("a/e/e")
    t.set(p3.parts, "terzo dao")

    test = Path("a/e/e/f/h")
    print(test.parts)
    obj, dao, rest = t.find_prefix(list(test.parts))
    print(obj, dao, Path(*rest))
