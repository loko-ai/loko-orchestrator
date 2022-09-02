import asyncio


class Throttle:
    def __init__(self, f, t=0.1):
        self.f = f
        self.task = None
        self.t = t

    async def __call__(self, *args, **kwargs):
        if self.task:
            self.task.cancel()
            self.task = None

        async def temp():
            await asyncio.sleep(self.t)
            return self.f(*args, **kwargs)

        self.task = asyncio.create_task(temp())


async def main():
    t = Throttle(lambda a, b: print(a + b))
    for i in range(100):
        await t(i, i)
    await asyncio.sleep(.5)
    await t(2, 3)
    await asyncio.sleep(20)


asyncio.run(main())
