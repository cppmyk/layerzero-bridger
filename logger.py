import logging
import threading


def setup_logger(level=logging.INFO) -> logging.Logger:
    """ Setup main console handler """

    logging.getLogger('web3').setLevel(logging.INFO)
    logging.getLogger('urllib3').setLevel(logging.INFO)
    logging.getLogger('ccxt').setLevel(logging.INFO)

    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] [%(threadName)-10s] %(message)s')

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)

    return logger


class ThreadLogFilter(logging.Filter):
    """ This filter only show log entries for specified thread name """

    def __init__(self, thread_name, *args, **kwargs) -> None:
        logging.Filter.__init__(self, *args, **kwargs)
        self.thread_name = thread_name

    def filter(self, record) -> bool:
        return record.threadName == self.thread_name


def setup_thread_logger(path: str, log_level=logging.INFO) -> logging.FileHandler:
    """ Add a log handler to separate file for current thread """

    thread_name = threading.current_thread().name
    log_file = f'{path}/{thread_name}.log'
    file_handler = logging.FileHandler(log_file)

    file_handler.setLevel(log_level)

    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s')
    file_handler.setFormatter(formatter)

    log_filter = ThreadLogFilter(thread_name)
    file_handler.addFilter(log_filter)

    logger = logging.getLogger()
    logger.addHandler(file_handler)

    return file_handler
