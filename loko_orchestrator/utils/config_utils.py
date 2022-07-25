import ast
import os


def guess_convert(s):
    if s is None:
        return None
    try:
        value = ast.literal_eval(s)
    except Exception:
        return s
    else:
        return value


class EnvInit:
    def __init__(self, conv=guess_convert):
        self.conv = conv

    def get(self, k, default=None):
        temp = os.environ.get(k, default)
        if self.conv:
            temp = self.conv(temp)
        return temp
