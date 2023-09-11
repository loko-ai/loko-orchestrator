import git
import json

repo = git.Repo("/home/fulvio/loko/projects/problemanuovo")

conflicted_files = repo.index.unmerged_blobs()

working_tree_path = repo.working_tree_dir


def merge_conflicts(o1, o2):
    if isinstance(o1, dict):
        if not isinstance(o2, dict):
            raise Exception("Not a dict")

        ret = {}
        for k, v in o1.items():
            if k in o2:
                ret[k] = merge_conflicts(v, o2[k])
        return ret
    else:
        if o1 == o2:
            return o1
        else:
            raise Exception("No so farlo!")


o1 = dict(a=1, b=2)
o2 = dict(a=1)

print(merge_conflicts(o1, o2))

print(merge_conflicts(2, 3))
"""
print(working_tree_path)
for path, v in conflicted_files.items():
    remote = json.loads(repo.git.show(f":2:{path}"))
    local = json.loads(repo.git.show(f":3:{path}"))
    custom_merge(remote, local)
"""
