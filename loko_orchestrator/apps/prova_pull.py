import asyncio

import aiodocker

from loko_orchestrator.business.docker_ext import LokoDockerClient


async def main():
    client = aiodocker.Docker()
    async for ev in client.pull("neo4j:latest", stream=True):
        print(ev)
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
