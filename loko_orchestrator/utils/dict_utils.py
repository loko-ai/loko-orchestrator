from _collections import defaultdict


class ObjectDict(defaultdict):

    def __init__(self, mapping=None):
        if mapping:
            defaultdict.__init__(self, ObjectDict, ObjectDict.convert(mapping))
        else:
            defaultdict.__init__(self, ObjectDict)

    def __setattr__(self, k, v):
        self[k] = ObjectDict.convert(v)

    def __getattr__(self, k):
        return self[k]

    @classmethod
    def convert(cls, obj):
        if type(obj) is dict:
            ret = ObjectDict()
            for k, v in obj.items():
                ret[k] = ObjectDict.convert(v)
            return ret
        elif type(obj) is list:
            return [ObjectDict.convert(x) for x in obj]
        else:
            return obj

    def to_dict(self):
        ret = {}
        for k, v in self.items():
            if isinstance(v, ObjectDict):
                ret[k] = v.to_dict()
            else:
                ret[k] = v
        return ret


def multiple_keys(d, keys):
    ret = d
    for k in keys:
        ret = ret[k]
    return ret


def kdict(klass, **kwargs):
    kwargs["__klass__"] = klass
    return dict(**kwargs)


def search_key(d, k):
    if isinstance(d, dict):
        if k in d:
            return d[k]
        else:
            for k1, v in d.items():
                ret = search_key(v, k)
                if ret:
                    return ret
            return None
    else:
        return None
