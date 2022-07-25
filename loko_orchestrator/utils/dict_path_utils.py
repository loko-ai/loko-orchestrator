from dict_path import DictPath


class SafeDictPath(DictPath):
    def __contains__(self, path):
        path = self.clean_path(path)
        current = self.data.copy()
        for attr in path:
            if not isinstance(current, dict):
                # raise Exception(f"Your path is not a path of dicts (value at key {attr} is of type {type(current)})")
                return False
            if attr not in current:
                return False
            current = current[attr]
        return True
