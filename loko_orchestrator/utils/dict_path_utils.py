
from dict_path import DictPath

class SafeDictPath(DictPath):

    def clean_path(self, path):
        if isinstance(path, tuple):
            return list(path)
        return super().clean_path(path)
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

    def __delitem__(self, path):
        orig_path = self.clean_path(path)
        path = orig_path[:-1]
        args = orig_path[-1]
        current = self.data
        for attr in path:
            current = current[attr]

        del current[args]




if __name__ == '__main__':



    # test_dict = {'foo1': {'foo2': {'foo3': ["1", "2"]}}}
    test_dict = {'foo1': {'foo2': {'foo3': {'foo4': 'bar'}}, "mila":[1, 2, 3]}, "cua":1, "clua":"pp", "ccc":2}

    data = SafeDictPath(test_dict)
    print(data.clean_path('foo1/foo2/foo3/foo4'))
    print(data.get('foo1/foo2/foo3/foo4'))  # result: bar
    # set value with easy
    data.set('foo1/foo2/foo3/foo5', 'bar1')
    data.get('foo1/foo2/foo3/foo5')  # result: bar1
    # print(data)
    del data["foo1/foo2/foo4"]

    # data.__delitem__()
    print(data)
    # data.__delitem__()
    #


    # f(test_dict, ['foo1'])
    # print(test_dict)
    #
    ## test  __contains__ function
    # print("foo" in data)
    # print("foo1/foo3" in data)
    # print("foo1/foo2/foo5" in data)
    # print("foo1/foo2" in data)
    # print("foo1/foo2/foo3" in data)

