def ellipsis(obj, n=50, lsize=10):
    if isinstance(obj, dict):
        return {k: ellipsis(v, n, lsize) for (k, v) in obj.items()}
    if isinstance(obj, (list, tuple)):
        if len(obj) > lsize:
            return [ellipsis(x, n, lsize) for x in obj[:5]] + ["..."] + [ellipsis(x, n, lsize) for x in
                                                                         obj[-5:]] + [f"{len(obj)} elements"]

        else:
            return [ellipsis(x, n, lsize) for x in obj]

    if isinstance(obj, str):
        if len(obj) <= n:
            return obj
        else:
            return obj[:n] + "...(%d more chars)" % (len(obj) - n)
    return obj
