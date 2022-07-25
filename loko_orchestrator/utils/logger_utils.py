import logging


def get_logger():
    logger = logging.getLogger()
    # fhand = logging.FileHandler(fname)
    shand = logging.StreamHandler()

    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    # fhand.setFormatter(formatter)
    shand.setFormatter(formatter)

    # logger.addHandler(fhand)
    logger.addHandler(shand)
    logger.setLevel(logging.DEBUG)

    logging.TRACE = 25
    logging.addLevelName(logging.TRACE, 'TRACE')
    setattr(logger, 'trace', lambda message, *args: logger._log(logging.TRACE, message, args))

    logging.PROCESS = 15
    logging.addLevelName(logging.PROCESS, 'PROCESS')
    setattr(logger, 'process', lambda message, *args: logger._log(logging.PROCESS, message, args))

    return logger


logger = get_logger()
