import asyncio

import aiodocker

from loko_orchestrator.utils.dict_utils import search_key


async def main():
    client = aiodocker.Docker()
    for c in await client.containers.list(filters={"label": ["type=complex_extension_side"]}):
        print(c)
        sh = await c.show()
        print(search_key(sh, "Labels"))

    await client.close()


asyncio.run(main())
