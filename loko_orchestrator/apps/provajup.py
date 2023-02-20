import asyncio

from loko_orchestrator.business.docker_ext import LokoDockerClient

side_config = {
    "image": "jupyter/datascience-notebook",
    "ports": {"8888": None},
    "expose": [
        8888
    ],
    "gui": {
        "name": "notebook",
        "path": "/"
    },
    "cmd": "jupyter notebook --ip='*' --NotebookApp.token='' --NotebookApp.password=''".split(" ")
}


async def main():
    client = LokoDockerClient()

    image = side_config.get('image')
    if ":" not in image:
        image = f"{image}:latest"
    if image:
        if not await client.image_exists(image):
            print("Doesn't exist" * 20, image)
            await client.pull(image)
    else:
        raise Exception(f"Specify an image for 'notebook'")
    cont = await client.run("notebook", **side_config, network="loko",
                            labels=dict(type="loko_side_container"))

    await client.close()


asyncio.run(main())
