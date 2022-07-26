import asyncio
from pathlib import Path

import aiodocker

from loko_orchestrator.business.builder.aio_docker_builder import build_extension_image, run_extension_image


class SharedExtensionsDAO:
    def __init__(self, path: Path, gw):
        self.path = path
        self.gw = gw

    def all(self):
        for el in self.path.iterdir():
            if el.is_dir():
                temp = list(el.glob("**/components.json"))
                if len(temp) == 1:
                    yield el.name

    async def status(self, id):
        client = aiodocker.Docker()
        try:
            await client.containers.get(id)
            return "running"
        except Exception as inst:
            print(inst)
            return "not running"
        finally:
            await client.close()

    async def deploy(self, id):

        await build_extension_image(self.path / id)
        await run_extension_image(id, self.gw)

    async def undeploy(self, id):
        if await self.status(id) == "running":
            client = aiodocker.Docker()
            container = await client.containers.get(id)
            await container.kill()


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
