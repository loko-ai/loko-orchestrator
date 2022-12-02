import asyncio
from functools import lru_cache

from loko_orchestrator.business.docker_ext import LokoDockerClient
from loko_orchestrator.dao.projects import FSProjectDAO


class MyCache:
    def __init__(self, pdao, client):
        self.client = client
        self.pdao = pdao
        self.cache = None

    async def __call__(self):
        if self.cache is None:
            self.cache = await self.pdao.all(client=self.client, info=True)
        return self.cache


async def main():
    pdao: FSProjectDAO = FSProjectDAO("/home/fulvio/loko/projects", ".project")
    client = LokoDockerClient()
    mc = MyCache(pdao, client)

    for i in range(100):
        alls = await mc()
        print(len(alls))

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
