import json

from loko_orchestrator.apps.conv import ChainTransform, Move, DictTransform


def ports_transform(d):
    ret = {}
    for k, v in d.items():
        ret[f'{k}/tcp'] = [dict(HostPort=str(v))]
    return ret


def env_transform(d):
    ret = []
    for k, v in d.items():
        ret.append(f"{k}={v}")
    return ret


def enrich(d):
    ret = dict(d)
    temp = d.get("HostConfig") or {}
    temp.update({"AutoRemove": True,
                 "NetworkMode": 'loko'})
    ret['HostConfig'] = temp
    return ret


cc = ChainTransform(ports_transform, Move(("HostConfig", "PortBindings")))

mm = DictTransform(ports=cc, image=Move("Image"), environment=ChainTransform(env_transform, Move("Env")))

config2docker = ChainTransform(mm, enrich)
if __name__ == "__main__":

    p = "/home/fulvio/loko/projects/mongo_extension_example/config.json"
    with open(p) as o:
        content = json.load(o)
        for name, el in content.get("side_containers", {}).items():
            print("Side", el)
            print(config2docker(el))
