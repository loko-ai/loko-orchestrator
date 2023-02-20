import inspect
import time
from functools import wraps

from loguru import logger


class TTL:
    def __init__(self, t):
        self.last = time.time()
        self.t = t
        self.__cache = None
        self.is_async = False

    def __call__(self, f):
        self.is_async = inspect.iscoroutinefunction(f)

        @wraps(f)
        async def temp(*args, **kwargs):
            req_time = time.time()
            if (req_time - self.last) > self.t or self.__cache is None:
                self.last = req_time
                self.__cache = f(*args, **kwargs)
                if self.is_async:
                    self.__cache = await self.__cache
            else:
                logger.debug(f"Hitting cache for {args} {kwargs}")
            return self.__cache

        return temp

    def sync(self, f):

        @wraps(f)
        def temp(*args, **kwargs):
            req_time = time.time()
            if (req_time - self.last) > self.t or self.__cache is None:
                self.last = req_time
                self.__cache = f(*args, **kwargs)
            else:
                logger.debug(f"Hitting cache for {args} {kwargs}")
            return self.__cache

        return temp
