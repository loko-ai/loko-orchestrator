import asyncio
import traceback

from loko_orchestrator.config.app_config import GATEWAY
from loko_orchestrator.utils.logger_utils import logger

sio_lock = False


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
