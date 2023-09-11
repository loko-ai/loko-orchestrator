import copy
import json
from pathlib import Path
from pprint import pprint

from loko_orchestrator.business.groups import get_components
from loko_orchestrator.dao.projects import FSProjectDAO
from loko_orchestrator.model.projects import Project
from loko_orchestrator.utils.jsonutils import GenericJsonEncoder

# pdao: FSProjectDAO = FSProjectDAO("/home/fulvio/loko/projects", ".project")

# p = pdao.get("sempl")

components = {}
for g in get_components():
    for c in g['components']:
        components[c.name] = c
        # print(c.__dict__)

"""for node, g in p.nodes():
    name = node.data['name']
    print(node.id)
    values = node.data['options']['values']
    values['id'] = node.id
    print(json.dumps(values, indent=2))
    pprint(components[name].__dict__)"""


# print(json.dumps(p, default=GenericJsonEncoder().default))

class OtherProjectDAO(FSProjectDAO):
    def __init__(self, base, components):
        self.base = Path(base)
        self.components = components

    def get(self, id: str):
        proj_file = self.base / id / "loko.project"
        if proj_file.exists():
            with proj_file.open() as o:
                temp = json.load(o)
                p = Project(name=id, **temp)
                for g, comps in list(p.graphs.items()):
                    nn = []
                    for n in comps:
                        c = self.components[n['name']]
                        cc = copy.deepcopy(c)
                        cc.id = n['id']
                        cc.options['values'] = n
                        nn.append(cc)
                    p.graphs[g] = nn
                return p

    def save(self):
        pass


o = FSProjectDAO("/home/fulvio/loko/projects", ext=".project", components=get_components())
p = o.get("ndao")

print(json.dumps(p, indent=2, default=GenericJsonEncoder().default))
