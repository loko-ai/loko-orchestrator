import asyncio
import json
from pathlib import Path
from pprint import pprint

import aiodocker
import json

from aiodocker import DockerError

from loko_orchestrator.business.builder.aio_docker_builder import build_extension_image, run_extension_image, \
    run_sides
from loko_orchestrator.utils.dict_utils import search_key


async def main():
    id = "ciccio"
    path = f"/home/fulvio/loko/projects/{id}"
    # await build_extension_image(path)
    client = aiodocker.Docker()
    insp = await client.images.inspect(id)
    pprint(search_key(insp, "ExposedPorts"))
    insp2 = await client.containers.get(id)
    print(search_key(insp2._container, "Ports"))
    # await run_extension_image(id)
    # await run_sides(path)
    await client.close()


asyncio.run(main())
