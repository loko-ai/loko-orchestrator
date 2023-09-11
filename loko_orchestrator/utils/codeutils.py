import importlib
import json
import sys


def compile_fun(s_code, g=None):
    f = "secret_function_name"
    temp = ["def %s(data):" % f] + ["\t" + x for x in s_code.split("\n")]
    try:
        code = compile("\n".join(temp), "<string>", "exec")
        g = g or {}
        exec(code, g)
        return g[f]
    except Exception as e:
        if hasattr(e, 'lineno'):
            e.lineno = e.lineno - 1
        raise e


def load_external_modules(path):
    with open(path) as imp:
        imports = json.load(imp)
        old_path = sys.path
        modules = {}
        new_path = list(old_path) + [imports['path']]
        sys.path = new_path
        for k, v in imports.get("modules", {}).items():
            modules[k] = importlib.import_module(v)
        sys.path = old_path
    return modules


def flatten(v):
    if isinstance(v, (list, tuple)):
        for value in v:
            yield from flatten(value)
    else:
        yield v
