class DictVal(dict):
    def __call__(self, obj):
        if not isinstance(obj, dict):
            return False
        for k in self:
            if not self[k](obj.get(k)):
                return False
        return True


class TypeValidator:
    def __init__(self, _type):
        self._type = _type

    def __call__(self, obj):
        return isinstance(obj, self._type)
