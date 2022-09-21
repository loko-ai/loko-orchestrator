import asyncio
import os

from pathlib import Path
from pprint import pprint

import aiodocker
import aiohttp
import requests
from aiodocker import DockerError
from docker.api.build import process_dockerfile
from docker.utils import tar
import json

from loko_orchestrator.apps.conv import Move, DictTransform, ChainTransform
from loko_orchestrator.business.builder.config2docker import config2docker


def ports_transform(d):
    ret = {}
    for k, v in d.items():
        ret[f'{k}/tcp'] = [dict(HostPort=str(v))]
    return ret


def env_transform(d):
    ret = []
    for k, v in d.items():
        ret.append(f"{k}:{v}")
    return ret


async def kill_if_exists(name, client):
    try:
        container = await client.containers.get(name)
        await container.kill()
        while await get_status(id, client):
            await asyncio.sleep(0.5)


    except DockerError as inst:
        if inst.status == 404:
            return


async def run_container(name, labels, config, path):
    client = aiodocker.Docker()
    await kill_if_exists(name, client)
    """hc = config.get("HostConfig") or {}

    hc.update({
        "AutoRemove": True,
        "NetworkMode": 'loko',
    })
    if config.get("volumes"):
        binds = []
        for el in config['volumes']:
            local, rm = el.split(":", maxsplit=1)
            local = Path(local)
            if not local.is_absolute():
                local = path / local
            local = str(local.resolve())
            print(local, rm)
            binds.append(f"{local}:{rm}")
        if binds:
            hc['Binds'] = binds

    _config = dict(Image=config['image'], labels=labels, ExposedPorts={
        '8080/tcp': {},
    })
    if 'Env' in config:
        _config["Env"] = config["Env"]
    pprint(_config)"""
    config['labels'] = labels
    print(config)
    await client.containers.run(name=name, config=config)
    await client.close()


async def run_sides(path, gateway=None):
    path = Path(path)
    config_path = path / "config.json"
    if config_path.exists():
        with config_path.open() as o:
            config = json.load(o)
            web = config.get('web')
            expose_to_gateway = config.get('expose_to_gateway', [])
            ports = config.get("ports", [])
            for name, side_config in config.get("side_containers", {}).items():
                print(name, side_config)
                tconfig = config2docker(side_config)

                await run_container(name, labels=dict(type=f"{path.name}_side"), config=tconfig, path=path)
                port = side_config.get("exposed")
                if gateway and name in expose_to_gateway and port:
                    resp = requests.post(gateway + "/rules", json={
                        "name": name,
                        "host": name,
                        "port": port,
                        "type": "custom",
                        "scan": False
                    })


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


async def run_extension_image(id, gw=None, dev=False):
    client = aiodocker.Docker()
    print("Trying to get", id)
    await kill_if_exists(id, client)
    config = dict(Image=id, labels=dict(type="loko_project"), ExposedPorts={
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
        #     print("Log", msg)
        # print("Deployed", id)
        if gw:
            resp = requests.post(gw + "/rules", json={
                "name": id,
                "host": id,
                "port": 8080,
                "type": "custom",
                "scan": False
            })
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
