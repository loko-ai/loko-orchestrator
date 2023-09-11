import asyncio
import json
import logging
import traceback

from loko_orchestrator.config.constants import GATEWAY
from loko_orchestrator.utils.logger_utils import logger

sio_lock = False


class Throttle:
    def __init__(self, f, t=0.1):
        self.f = f
        self.task = None
        self.t = t
        self.tasks = {}

    async def __call__(self, *args, **kwargs):
        _hash = json.dumps((args, kwargs))
        task = self.tasks.get(_hash)
        # print(_hash, args, kwargs)
        if task:
            return

        async def temp(tasks, _hash):
            try:
                await asyncio.sleep(self.t)
                await self.f(*args, **kwargs)
            except Exception as inst:
                logging.exception(inst)
            finally:
                del tasks[_hash]
                # print(tasks,_hash)

        self.tasks[_hash] = asyncio.create_task(temp(self.tasks, _hash))


async def emit(sio, event, data):
    # if event == 'animation':
    #     return None
    # if event == 'messages':
    #     logger.debug(f'EMIT: {event} - {data}')
    global sio_lock
    while sio_lock:
        logger.debug(f'LOCKED!! {sio.connected}')
        await asyncio.sleep(.05)

    sio_lock = True

    try:
        while not sio.connected:
            if event == 'messages':
                logger.debug('Reconnect.')
            await sio.connect(GATEWAY, wait=True)
            await asyncio.sleep(2)

        await sio.call(event, data)
        logger.debug(f'END EMIT  -  EVENT: {event} - MSG: {data}')
    except Exception as inst:
        logger.debug(f'EXCEPTION: {inst} - CONNECTED: {sio.connected} -  EVENT: {event} - MSG: {data}')
        logger.debug(sio.__dict__)
        logger.debug(traceback.format_exc())
    finally:
        sio_lock = False
