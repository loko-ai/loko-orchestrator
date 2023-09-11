import asyncio
import json
import shutil
from pathlib import Path

import aiodocker
from loguru import logger

from loko_orchestrator.business.builder.aio_docker_builder import build_extension_image, run_extension_image
from loko_orchestrator.business.docker_ext import LokoDockerClient
from loko_orchestrator.config.constants import EXTERNAL_GATEWAY
from loko_orchestrator.utils.cache_utils import TTL


class SharedExtensionsDAO:
    def __init__(self, path: Path, gw):
        self.path = path
        self.gw = gw
        self.deployed = {}

    def all(self):
        for el in self.path.iterdir():
            if el.is_dir():
                temp = list(el.glob("**/components.json"))
                if len(temp) == 1:
                    yield el.name

    async def status(self, id):
        return self.deployed.get(id)

    async def deploy(self, id):
        self.deployed[id] = "running"

    async def undeploy(self, id):
        if id in self.deployed:
            del self.deployed[id]

    def delete(self, id):
        ext = self.path / id
        shutil.rmtree(ext)

    def has_icon(self, id):
        return (self.path / id / "icon.png").exists()

    async def get_guis(self, id, client: LokoDockerClient):
        # Main gui
        ret = []
        # Sides guis
        p = self.path / id / "config.json"
        if not await client.is_deployed(id):
            return []
        if p.exists():
            with p.open() as o:
                config = json.load(o)
                # Main gui
                print(config)
                main = config.get("main", {})
                main_gui = main.get("gui")
                if main_gui:
                    name = main_gui.get("name", f"{id} gui")
                    path = main_gui.get("path", "web/index.html")
                    if path.startswith("/"):
                        path = path[1:]

                    external_url = f"{EXTERNAL_GATEWAY}/routes/{id}/{path}"
                    ret.append(dict(name=name, url=external_url))
                for side, side_config in config.get("side_containers", {}).items():
                    gui = side_config.get("gui")
                    print("Side", side, gui)
                    side_name = f"{id}_{side}"
                    logger.debug(f"{side_name}:{gui}")

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


if __name__ == "__main__":
    from loko_orchestrator.config.app_config import PUBLIC_FOLDER, GATEWAY


    async def main():
        dao = SharedExtensionsDAO(PUBLIC_FOLDER / "shared/extensions")
        id = 'tesseract-base-api'
        await dao.deploy(id)
        # await dao.undeploy('tesseract-base-api')

        for el in dao.all():
            print(el, await dao.status(el))


    asyncio.run(main())
