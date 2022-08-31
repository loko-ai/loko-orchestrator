import asyncio
import os

from pathlib import Path

import aiodocker
import aiohttp
import requests
from docker.api.build import process_dockerfile
from docker.utils import tar


def prepare_docker_ignore(path):
    dockerignore = os.path.join(path, '.dockerignore')
    exclude = None
    if os.path.exists(dockerignore):
        with open(dockerignore) as f:
            exclude = list(filter(
                lambda x: x != '' and x[0] != '#',
                [l.strip() for l in f.read().splitlines()]
            ))
    return exclude


async def build_extension_image(path):
    async with aiohttp.ClientSession(timeout=300 * 1000) as session:
        client = aiodocker.Docker()
        client.session = aiohttp.ClientSession(connector=client.connector, read_timeout=200 * 1000,
                                               conn_timeout=200 * 1000)

        path = Path(path)
        print("Tarring the file")
        exclude = prepare_docker_ignore(path)
        print("Excludes", exclude)
        context = tar(
            path, exclude=exclude, dockerfile=process_dockerfile("Dockerfile", path), gzip=True
        )
        print("File tarred")

        async for line in client.images.build(fileobj=context,
                                              encoding="gzip",
                                              tag=f"{path.name}",
                                              buildargs=dict(GATEWAY="http://localhost:8080"), stream=True):
            if "stream" in line:
                msg = line['stream'].strip()
            if msg:
                print(msg)
        await client.close()


async def download(name):
    docker = aiodocker.Docker()
    async for el in docker.pull(name, tag="latest", stream=True):
        print(el)
        """if el.get("status") == "Pull complete":
            break"""
    await docker.close()


async def run_extension_image(id, gw, dev=False):
    client = aiodocker.Docker()
    print("Trying to get", id)

    try:
        container = await client.containers.get(id)
        await container.kill()
        while await get_status(id, client):
            await asyncio.sleep(0.5)


    except Exception as inst:
        print("kkk", inst)
    config = dict(Image=id, ExposedPorts={
        '8080/tcp': {},
    }, HostConfig={
        "AutoRemove": True,
        "NetworkMode": 'loko',
    })
    if dev:
        config['HostConfig']["PortBindings"] = {'8080/tcp': [{"HostPort": '8083'}]}

    try:
        cont = await client.containers.run(name=id, config=config)
        print("Ora loggo")
        # async for msg in cont.log(stdout=True, stderr=True, follow=True):
        #    print("Log", msg)
        # print("Deployed", id)
        resp = requests.post(gw + "/rules", json={
            "name": id,
            "host": id,
            "port": 8080,
            "type": "custom",
            "scan": False
        })
        print("Response: GW routing", id, resp.status_code)
    except Exception as inst:
        print(inst)
    print("Routed", id)
    await client.close()


async def get_status(id, client):
    try:
        cont = await client.containers.get(id)
        return cont._container["State"]["Status"]
    except:
        return None


async def main():
    id = "nn-simple-img-clf"
    path = f"/home/fulvio/loko/projects/{id}"
    await build_extension_image(path)
    await run_extension_image(id, None)


if __name__ == "__main__":
    # asyncio.run(build_extension_image(path))
    # asyncio.run(test_build_from_tar())
    asyncio.run(main())
