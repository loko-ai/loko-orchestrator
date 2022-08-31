import asyncio

import aiodocker
from aiodocker.events import DockerEvents


async def main():
    client = aiodocker.Docker()
    cont = await client.containers.run(name="sss", config={"Image": "sss", "HostConfig": {"AutoRemove": True}})
    cont = await client.containers.get("sss")
    async for el in cont.log(stdout=True, stderr=True, follow=True):
        print(el)
    await client.close()


async def listen():
    client = aiodocker.Docker()
    sub = client.events.subscribe()
    while True:
        res = await sub.get()
        print(res)


asyncio.run(listen())
