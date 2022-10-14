import json
import os
import shutil
from abc import abstractmethod
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import List
from uuid import uuid4

import aiohttp

from loko_orchestrator.business.docker_ext import LokoDockerClient, LogCollector
from loko_orchestrator.config.constants import GATEWAY, EXTERNAL_GATEWAY
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
        self.deployed = {}

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
        self.deployed = {}

    async def all(self, client: LokoDockerClient, info=None) -> List[str]:
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
                    m['deployed'] = await self.is_deployed(el.name, client)
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
                raise Exception("impossible to load %s" % str(self.path / (id + self.ext)))
        return prj

    def save(self, project: Project, new_project=False):
        # project.last_modify = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
        logger.debug(f"saving project..{project.name} -- {project.id}")
        path = self.path / project.id
        if new_project and path.exists():
            raise Exception(f"Project '{project.id}' already existing")
        if not path.exists():
            path.mkdir(exist_ok=True, parents=True)
            for p in ["extensions", "dao", "business", "services", "model", "utils", "config", "apps", "tests"]:
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

    def get_local_components(self, id, klass):
        custom = []

        conf = self.path / id / "extensions" / "components.json"
        print("Project", conf, conf.exists())
        groups = defaultdict(list)
        try:
            if conf.exists():
                with open(conf) as comp:
                    for d in json.load(comp):
                        group = d.get("group", "Custom")
                        c = klass(**d)
                        groups[group].append(c)
                        # FACTORY[c.name] = c
        except Exception as inst:
            raise Exception(f"Problems in loading local components: {inst}")
        ret = []
        for k, v in groups.items():
            ret.append(dict(group=k, components=v))
        return ret

    def get_extensions(self, id):
        if self.has_extensions(id):
            conf = self.path / id / "extensions" / "components.json"
            with open(conf) as comp:
                return json.load(comp)
        else:
            return []

    def has_extensions(self, id):
        p = self.path / id / "extensions/components.json"
        return p.exists()

    async def get_guis(self, id, client: LokoDockerClient):
        # Main gui
        ret = []

        print("Main", ret)
        # Sides guis
        p = self.path / id / "config.json"
        if not await client.is_deployed(id):
            return []
            """async with aiohttp.ClientSession() as session:
                internal_url = f"{GATEWAY}/routes/{id}/web/index.html"
                external_url = f"{EXTERNAL_GATEWAY}/routes/{id}/web/index.html"
                async with session.get(internal_url) as resp:
                    print(resp.status)
                    if resp.status == 200:
                        ret.append(dict(name="main gui", url=external_url))"""
        if p.exists():
            with p.open() as o:
                config = json.load(o)
                # Main gui
                main = config.get("main", {})
                main_gui = main.get("gui")
                if main_gui:
                    name = main_gui.get("name", "Main gui")
                    path = main_gui.get("path", "web/index.html")
                    if path.startswith("/"):
                        path = path[1:]

                    external_url = f"{EXTERNAL_GATEWAY}/routes/{id}/{path}"
                    ret.append(dict(name=name, url=external_url))

                for side, side_config in config.get("side_containers", {}).items():
                    gui = side_config.get("gui")
                    print(side, gui)
                    side_name = f"{id}_{side}"
                    if gui:
                        gw = gui.get("gw", False)
                        path = gui.get("path", "")
                        if path.startswith("/"):
                            path = path[1:]
                        name = gui.get("name")
                        if await client.exists(side_name):
                            if gw:
                                url = f"{EXTERNAL_GATEWAY}/routes/{side_name}/{path}"
                                ret.append(dict(name=name, url=url))
                            else:
                                exposed = await client.exposed(side_name)

                                ret.append(dict(name=name, url=f"http://localhost:{exposed}/{path}"))
        return ret

    def new_extension(self, id, name):
        p = self.path / id
        if p.exists():

            rp = path("loko_orchestrator", "resources")

            exts = rp / "extensions"
            for el in (exts / "code").iterdir():
                (p / "extensions").mkdir(exist_ok=True)
                np = p / "extensions" / el.name
                print("Code", el.name)

                if not np.exists():
                    if el.name == "services.py":
                        (p / "services").mkdir(exist_ok=True)
                        shutil.copy(el, p / "services/services.py")
                    elif el.name == "components.json":
                        with el.open() as ext:
                            temp = json.load(ext)
                            temp[0]['name'] = name
                            with open(np, "w") as oo:
                                json.dump(temp, oo)
                    elif el.name == "config.json":
                        shutil.copy(el, p)
                    else:
                        shutil.copy(el, np)
            print("Config")
            for el in (exts / "config").iterdir():
                print(el)
                np = p / el.name
                if not np.exists():
                    shutil.copy(el, np)


        else:
            raise Exception(f"{id} not found")

    def deploy(self, id):
        self.deployed[id] = True

    def undeploy(self, id):
        self.deployed[id] = False

    async def is_deployed(self, id, client: LokoDockerClient):
        if self.has_extensions(id):
            return id in await client.list_names()
        else:
            print(self.deployed)
            return self.deployed.get(id, False)


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
