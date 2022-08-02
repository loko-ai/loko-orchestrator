import json
import os
import shutil
from abc import abstractmethod
from datetime import datetime
from pathlib import Path
from typing import List
from uuid import uuid4

from loko_orchestrator.business.components.commons import Custom
from loko_orchestrator.business.groups import get_components, FACTORY
from loko_orchestrator.utils.dict_utils import ObjectDict

from loko_orchestrator.model.projects import Project, Endpoint, Edge, Node, Graph, Comment, Template
from loko_orchestrator.utils.jsonutils import GenericJsonEncoder, GenericJsonDecoder
from loko_orchestrator.utils.logger_utils import logger
from importlib.resources import path


# from loko_orchestrator.utils.projects_utils import check_prj_duplicate, check_prj_id_duplicate
# from loko_orchestrator.utils.update_version_prj_utils import get_updated_prj_structure


class ProjectDAO:
    @abstractmethod
    def all(self, info=None) -> List[str]:
        pass

    @abstractmethod
    def get(self, id) -> Project:
        pass

    @abstractmethod
    def save(self, project: Project):
        pass

    @abstractmethod
    def delete(self, id):
        pass

    def save_json(self, id=None, o=None, f_name=None, update=True):
        if update:
            p = self.get(id)
        else:
            p = Project(name=o["name"], id=id, description=o["description"], created_on=o["created_on"],
                        last_modify=o["last_modify"])
            if (f_name is not None) and (f_name != p.name):
                logger.debug(f"updating imported project name from {p.name} to {f_name}..")
                p.name = f_name
        p.last_modify = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
        p.open = o.get("open", [])
        p.active = o.get("active", "main")
        p.graphs = {}

        m = set()
        for name, g in o.get("graphs", {}).items():
            gr = Graph([], [])
            for n in g.get("nodes", []):
                if "__class__" in n:
                    del n["__class__"]
                try:
                    node = Node(**n)
                except Exception as e:
                    print("eeee", e)
                    raise e
                gr.nodes.append(node)
                m.add(node.id)
                del node
            for e in g.get("edges", []):
                if "__class__" in e:
                    del e["__class__"]
                try:
                    ee = Edge(**e)
                except Exception as e:
                    raise e
                if ee.source in m and ee.target in m:
                    gr.edges.append(ee)
                del ee

            p.graphs[name] = gr
        return self.save(p)


class InMemoryProjectDAO(ProjectDAO):
    def __init__(self):
        self.projects = {}

    def all(self) -> List[str]:
        return list(self.projects.keys())

    def get(self, id) -> Project:
        return self.projects[id]

    def save(self, project: Project):
        self.projects[project.id] = project

    def delete(self, id):
        del self.projects[id]


class FSProjectDAO(ProjectDAO):
    def __init__(self, path, ext=".studio"):
        self.path = Path(path)
        self._enc = GenericJsonEncoder(include_class=True)
        self._dec = GenericJsonDecoder([Project, Template, Edge, Node, Endpoint, Graph], )
        self.ext = ext

    def all(self, info=None) -> List[str]:
        ret = []
        if not self.path.exists():
            return ret
        for el in self.path.iterdir():
            if el.is_dir() and (el / "loko.project").exists():

                p = self.get(el.name)
                # with open(str(x)) as f:
                #     p = ObjectDict(json.load(f))
                if info:
                    m = dict()
                    m["id"] = el.name
                    m["name"] = el.name
                    m["created_on"] = p.created_on
                    m["last_modify"] = p.last_modify
                    m["description"] = p.description
                    m["version"] = p.version
                    ret.append(m)
                else:
                    ret.append(p.name)
                # print(ret)
        return ret

    def get(self, id, info=None) -> Project:
        try:
            path = self.path / id / ("loko" + self.ext)
            logger.debug("opening project: %s" % path)
            with open(path, "r") as o:
                prj = json.load(o, object_hook=self._dec.object_hook)
                prj.id = id
                prj.name = id
        except Exception as e:
            try:
                logger.debug("first attempt project opening failed")
                logger.debug("opening project file with old structure version: %s" % str(self.path / (id + self.ext)))
                with open(path, "r") as o:
                    prj = json.load(o)
                prj = self.update_structure(prj)
                prj.id = id
                prj.name = id
            except Exception as e:
                logger.exception("impossible to load %s" % str(self.path / (id + self.ext)))
                raise e
        return prj

    def save(self, project: Project):
        # project.last_modify = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
        logger.debug(f"saving project..{project.name} -- {project.id}")
        path = self.path / project.id
        if not path.exists():
            path.mkdir(exist_ok=True, parents=True)
            for p in ["extensions", "dao", "business", "services", "model", "utils"]:
                np = path / p
                np.mkdir(exist_ok=True, parents=True)
                (np / "__init__.py").touch()

        with open(path / ("loko" + self.ext), "w") as o:
            json.dump(project, o, default=self._enc.default, indent=2)

    def update(self, id, updated_info):
        logger.debug(f"updating info project..{id}")

        new_name = updated_info["new_name"]
        new_description = updated_info["new_description"]
        project = self.get(id)
        logger.debug(f"project name {project.name}")
        project.name = new_name
        project.description = new_description
        project.version = updated_info.get("new version", project.version)
        project.last_modify = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
        logger.debug(f"new info to update: {updated_info}")

        self.save(project)

    def delete(self, id):
        p = self.path / (id)
        shutil.rmtree(p)

    def rename(self, id, new_id):
        p = self.path / id
        np = self.path / new_id
        if not p.exists():
            raise Exception(f"{id} doesn't exist")
        if np.exists():
            raise Exception(f"{new_id} doesn't exist")
        p.rename(np)

    """def update_structure(self, prj):
        if isinstance(prj, dict):
            prj_name = prj["id"]
            prj = get_updated_prj_structure(prj)
            prj_id = prj["id"]
            # check_prj_duplicate(prj_name)
            # try:
            #     check_prj_id_duplicate(prj_id)
            # except:
            #     prj_id = uuid4()
            try:
                logger.debug(f"deleting prj: {prj_name}")
                self.delete(prj_name)
            except Exception as e:
                print(e)
                pass
            logger.debug(f"saving new project file {prj_id}")
            self.save_json(id=prj_id, o=prj, f_name=prj_name, update=False)
        return self.get(prj_id)"""

    def get_components(self, id):
        components = get_components()
        custom = []

        conf = self.path / id / "extensions" / "components.json"
        print("Project", conf, conf.exists())
        if conf.exists():
            with open(conf) as comp:
                for d in json.load(comp):
                    c = Custom(**d)
                    custom.append(c)
                    print(c)
                    FACTORY[c.name] = c
        return components + [dict(group="Custom", components=custom)]

    def new_extension(self, id):
        p = self.path / id
        if p.exists():

            rp = path("loko_orchestrator", "resources")

            exts = rp / "extensions"
            for el in (exts / "code").iterdir():
                shutil.copy(el, p / "extensions" / el.name)
            for el in (exts / "config").iterdir():
                shutil.copy(el, p / el.name)


        else:
            raise Exception(f"{id} not found")


class TemplateDAO(FSProjectDAO):

    def __init__(self, path):
        super().__init__(path, ext=".template")

    def all(self, info=None) -> List[str]:
        ret = []
        for x in self.path.glob("*" + self.ext):
            with open(str(x)) as f:
                p = ObjectDict(json.load(f))
            if info:
                m = dict()
                m["id"] = p.id
                m["created_on"] = p.created_on
                m["last_modify"] = p.last_modify
                ret.append(m)
            else:
                ret.append(p.id)
            # print(ret)
        return ret

    def save(self, template: Template):
        self.path.mkdir(exist_ok=True, parents=True)
        with open(self.path / (template.id + self.ext), "w") as o:
            json.dump(template, o, default=self._enc.default, indent=2)

    def get(self, id) -> Template:
        with open(self.path / (id + self.ext)) as o:
            return json.load(o, object_hook=self._dec.object_hook)

    def save_json(self, id, o):
        p = Template(id)
        m = set()
        gr = Graph([], [])
        for n in o.get("nodes", []):
            node = Node(**n)
            gr.nodes.append(node)
            m.add(node.id)
        for e in o.get("edges", []):
            ee = Edge(**e)
            if ee.source in m and ee.target in m:
                gr.edges.append(ee)

        p.graph = gr
        logger.debug("saving projects %s" % p.__dict__)
        return self.save(p)

    def delete(self, id):
        p = self.path / id
        if p.exists():
            p.unlink()


if __name__ == '__main__':
    dao = FSProjectDAO("/home/fulvio/loko/.studio/projects")
    for el in dao.path.iterdir():
        print(el, el.is_dir() and (el / "loko.project").exists())
