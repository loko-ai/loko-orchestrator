import asyncio

import aiodocker


def cond(img):
    tag = img['RepoTags'][0]
    print("enel-eprocedures" in tag, tag)
    return "enel-eprocedures" in tag


async def main():
    client = aiodocker.Docker()
    for i, cont in enumerate(await client.containers.list(all=True)):
        try:
            print(i, await cont.show())

        except Exception as inst:
            print(inst)
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
