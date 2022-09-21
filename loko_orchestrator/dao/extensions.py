import asyncio
import shutil
from pathlib import Path

import aiodocker

from loko_orchestrator.business.builder.aio_docker_builder import build_extension_image, run_extension_image


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
        """client = aiodocker.Docker()
        try:
            await client.containers.get(id)
            return "running"
        except Exception as inst:
            print(inst)
            return "not running"
        finally:
            await client.close()"""
        print(id, self.deployed.get(id))
        return self.deployed.get(id)

    async def deploy(self, id):
        self.deployed[id] = "running"

    # await build_extension_image(self.path / id)
    # await run_extension_image(id, self.gw)

    async def undeploy(self, id):
        if id in self.deployed:
            del self.deployed[id]
        """if await self.status(id) == "running":
            client = aiodocker.Docker()
            container = await client.containers.get(id)
            await container.kill()
            for el in await client.containers.list(filters={"label": [f"type={id}_side"]}):
                print(el)
                try:
                    await el.kill()
                except Exception as inst:
                    print(id, inst)"""

    def delete(self, id):
        ext = self.path / id
        shutil.rmtree(ext)


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
