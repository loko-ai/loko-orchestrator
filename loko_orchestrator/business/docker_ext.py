import asyncio
import json
import logging
import os
from collections import defaultdict
from datetime import timezone
from pathlib import Path
from pprint import pprint
from typing import Union, Any, Optional, Mapping

import aiodocker
import aiohttp
import requests
from aiodocker.containers import DockerContainer
from aiohttp import ClientTimeout
from docker.api.build import process_dockerfile
from docker.utils import tar
from loguru import logger

from loko_orchestrator.business.log_collector import LogCollector
from loko_orchestrator.config.constants import GATEWAY, DEVELOPMENT, config_dao
from loko_orchestrator.utils.dict_utils import search_key
from loko_orchestrator.utils.user_utils import get_docker_group


def gateway_route(id, host=None, port=8080):
    resp = requests.post(GATEWAY + "/rules", json={
        "name": id,
        "host": host or id,
        "port": port,
        "type": "custom",
        "scan": False
    })


from yarl import URL


class MyDocker(aiodocker.Docker):
    def _query(
            self,
            path: Union[str, URL],
            method: str = "GET",
            *,
            params: Optional[Mapping[str, Any]] = None,
            data: Any = None,
            headers=None,
            timeout=None,
            chunked=None,
            read_until_eof: bool = True,
            versioned_api: bool = True,
    ):
        return super()._query(path, method, params=params, data=data, headers=headers, timeout=100_000, chunked=chunked,
                              read_until_eof=read_until_eof,
                              versioned_api=versioned_api)


class LokoDockerClient:
    def __init__(self):
        self.client: aiodocker.Docker = MyDocker()
        # self.client.session = aiohttp.ClientSession(connector=self.client.connector, timeout=ClientTimeout(total=10))
        self.sub = self.client.events.subscribe()
        self.observers = []

    def add_observer(self, observer):
        self.observers.append(observer)

    async def listen(self):
        while True:
            try:
                value = await self.sub.get()
                if not value.get("status", "").startswith("exec"):  # filter healtcheck
                    logger.debug(f"Docker event {value}")
                    await asyncio.gather(*(o(value) for o in self.observers))
            except Exception as inst:
                logging.exception(inst)

    async def close(self):
        await self.client.session.close()
        await self.client.close()

    async def exists(self, id):
        temp = await self.client.containers.list(filters={"name": [f"^{id}$"]})
        return bool(temp)

    async def is_deployed(self, id):
        temp = await self.list_names()
        return id in temp

    async def get_status(self, id):
        if await self.exists(id):
            cont = await self.client.containers.get(id)
            return cont._container["State"]["Status"]
        else:
            return None

    async def get(self, name) -> DockerContainer:
        if await self.exists(name):
            return await self.client.containers.get(name)
        else:
            return None

    async def get_name(self, container):
        return (await container.show())['Name'].replace("/", "")

    async def exposed_image(self, id):
        try:
            insp = await self.client.images.inspect(id)
            temp = search_key(insp, "ExposedPorts")
            ret = []
            for k, v in temp.items():

                if k.endswith("/tcp"):
                    ret.append(int(k[:-4]))
            return ret
        except Exception as inst:
            logging.error(inst)
            return []

    async def exposed(self, id):
        try:
            cont = await self.get(id)
            temp = search_key(cont._container, "Ports")
            ret = None
            for k, v in temp.items():
                if k.endswith("/tcp"):
                    ret = int(v[0].get("HostPort"))
            return ret
        except Exception as inst:
            logging.error(inst)
            return None

    async def pull(self, id, final_name=None, log_collector: LogCollector = None):
        if ":" not in id:
            id = f"{id}:latest"
        logger.debug(("Pulling", id))
        async for line in self.client.images.pull(from_image=id, stream=True):
            if log_collector and final_name:
                await log_collector(dict(type="log", name=final_name, msg=json.dumps(line)))

    async def build(self, path, log_collector: LogCollector = None):
        client = self.client

        path = Path(path)
        logger.debug("Tarring the file")
        exclude = self.prepare_docker_ignore(path)
        logger.debug(("Excludes", exclude))
        context = tar(
            path, exclude=exclude, dockerfile=process_dockerfile("Dockerfile", path), gzip=True
        )
        # bname = f"{path.name}:builder"
        # self.collector.logs[bname] = []
        # await self.collector.emit_now(bname, f"Building {path.name} image...")
        # self.collector.labels[bname] = "loko_project"
        last_msg = None

        async for line in client.images.build(fileobj=context,
                                              encoding="gzip",
                                              rm=True,
                                              tag=f"{path.name}",
                                              buildargs=dict(GATEWAY=GATEWAY), stream=True):
            if "stream" in line:
                msg = line['stream'].strip()

            if msg:
                last_msg = msg
                if log_collector:
                    await log_collector(dict(type="log", name=f"{path.name}:builder", msg=msg))
                # await self.collector.emit_now(bname, msg)
        return last_msg.startswith("Successfully tagged")

    async def run(self, name, image, replace=True, autoremove=True, network=None, environment=None, ports=None,
                  volumes=None, labels=None, expose=None, gw=False, path=None, log_task=None, **kwargs):
        if replace and await self.exists(name):
            container = await self.get(name)
            # await container.stop()
            await container.kill()
        config = dict(Image=image, Hostname=name)
        hc = {}
        while await self.exists(name):
            asyncio.sleep(0.5)

        if autoremove:
            hc["AutoRemove"] = True
        if expose:
            temp = {}
            for el in expose:
                temp[f"{el}/tcp"] = {}
            config['ExposedPorts'] = temp

        if ports:
            temp = {}
            exposed = {}
            for k, v in ports.items():
                if v:
                    temp[f"{k}/tcp"] = [{"HostPort": str(v)}]
                else:
                    temp[f"{k}/tcp"] = [{"HostPort": ""}]
                exposed[f"{k}/tcp"] = {}
            hc['PortBindings'] = temp
            config['ExposedPorts'] = exposed

        if volumes and path:
            binds = []
            for el in volumes:
                binds.append(el)
            if binds:
                hc['Binds'] = binds
        if network:
            hc['NetworkMode'] = network

        if hc:
            config["HostConfig"] = hc
        if labels:
            config['labels'] = labels
        if environment:
            temp = []
            for k, v in environment.items():
                temp.append(f"{k}={v}")
            config["Env"] = temp

        logger.debug(f"ENV {config} {environment}")

        cont = await self.client.containers.run(name=name, config=config)

        if gw:
            status = self.get_status(name)

            # gateway_route(id)
        return cont

    async def get_labels(self, id):
        container = await self.get(id)
        temp = await container.show()
        return search_key(temp, "Labels")

    async def add_log_task(self, name, container, stdout=True, stderr=True, observers=None):
        # container = await self.get(name)
        observers = observers or []
        if container:
            async for ev in container.log(stdout=stdout, stderr=stderr, follow=True):
                for o in observers:
                    channel = "DEBUG"
                    if stderr:
                        channel = "ERROR"
                    await o(dict(type="log", name=name, msg=ev, channel=channel))

    def prepare_docker_ignore(self, path):
        path = Path(path)
        dockerignore = path / '.dockerignore'
        exclude = None
        if dockerignore.exists():
            with open(dockerignore) as f:
                exclude = list(filter(
                    lambda x: x != '' and x[0] != '#',
                    [l.strip() for l in f.read().splitlines()]
                ))
        return exclude

    async def image_exists(self, id):
        try:
            await self.client.images.inspect(name=id)
            return True
        except:
            return False

    async def get_image(self, id):
        if await self.image_exists(id):
            return await self.client.images.inspect(id)
        else:
            return None

    async def list_names(self, **kwargs):
        return {await self.get_name(x) for x in await self.client.containers.list(**kwargs)}


async def log(v):
    print("LOOOOOG", v)


async def deploy(p: Path, client: LokoDockerClient, lc: LogCollector):
    try:
        # task = asyncio.create_task(client._listen())

        # Building phase
        lc.remove_log(p.name)

        lc.add_log(f"{p.name}:builder")
        success = await client.build(p, lc)

        # Running main project
        # config_path = p / "config.json"
        # config = {}

        config = config_dao.get_config(p)

        # if config_path.exists():
        #    with config_path.open() as inp:
        #        config = json.load(inp)

        if success:
            lc.remove_log(f"{p.name}:builder")
            lc.add_log(p.name)

            exposed = await client.exposed_image(p.name)
            if len(exposed) == 0:
                raise Exception("No ports exposed")
            if len(exposed) != 1:
                raise Exception("Too many ports exposed")
            port = exposed[0]
            main = config.get("main", {})
            if "environment" not in main:
                main['environment'] = {}
            main['environment']['USER_UID'] = os.getuid()
            main['environment']['USER_GID'] = get_docker_group()

            if DEVELOPMENT:
                cont = await client.run(p.name, p.name, network="loko", ports={port: None},
                                        labels=dict(type="loko_project", parent=p.name), path=p, **main)
                exposed_cont = await client.exposed(p.name)
                logger.debug(exposed_cont)
                if exposed_cont:
                    gateway_route(p.name, "localhost", exposed_cont)
            else:
                cont = await client.run(p.name, p.name, network="loko",
                                        labels=dict(type="loko_project", parent=p.name), path=p, **main)
                gateway_route(p.name, port=port)
            asyncio.create_task(client.add_log_task(p.name, cont, stdout=False, stderr=True, observers=[lc]))
            asyncio.create_task(client.add_log_task(p.name, cont, stdout=True, stderr=False, observers=[lc]))

            # Running side containers
            if config:
                for side_name, side_config in config.get("side_containers", {}).items():
                    logger.debug((side_name, side_config))
                    final_name = f"{p.name}_{side_name}"
                    lc.add_log(final_name)

                    logger.debug(final_name)
                    image = side_config.get('image')
                    if ":" not in image:
                        image = f"{image}:latest"
                    if image:
                        if not await client.image_exists(image):
                            await client.pull(image, final_name, lc)
                    else:
                        raise Exception(f"Specify an image for '{side_name}'")
                    cont = await client.run(final_name, **side_config, network="loko",
                                            labels=dict(type="loko_side_container", parent=p.name), path=p)
                    if side_config.get("gw"):
                        exposed_cont = await client.exposed(final_name) or 8080
                        logger.debug((final_name, "Routing to gw"))
                        gateway_route(final_name, exposed_cont)
                    asyncio.create_task(
                        client.add_log_task(final_name, cont, stdout=False, stderr=True, observers=[lc]))
                    asyncio.create_task(
                        client.add_log_task(final_name, cont, stdout=True, stderr=False, observers=[lc]))



        else:
            await lc(dict(type="log", name=f"{p.name}:builder", msg="Build failed"))

    except Exception as inst:
        raise inst


async def undeploy(p: Path, client: LokoDockerClient, lc: LogCollector):
    name = p.name
    main = await client.get(name)
    if main:
        lc.remove_log(name)
        lc.statuses[name] = None
        await main.kill()
    config_path = p / "config.json"
    while await client.exists(name):
        await asyncio.sleep(.1)
    config = config_dao.get_config(p)
    for side_name, side_config in config.get("side_containers", {}).items():
        final_name = f"{p.name}_{side_name}"
        side = await client.get(final_name)
        if side:
            lc.remove_log(final_name)
            lc.statuses[final_name] = None

            await side.kill()
