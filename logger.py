import logging
import threading


def setup_logger(level=logging.INFO):
    """Setup main console handler."""
    logging.getLogger("web3").setLevel(logging.INFO)
    logging.getLogger("urllib3").setLevel(logging.INFO)
    logging.getLogger("ccxt").setLevel(logging.INFO)

    formatter = logging.Formatter("[%(asctime)s] [%(levelname)-7s] [%(threadName)-10s] %(message)s")

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)

    return logger


class ThreadLogFilter(logging.Filter):
    """This filter only show log entries for specified thread name."""

    def __init__(self, thread_name, *args, **kwargs):
        logging.Filter.__init__(self, *args, **kwargs)
        self.thread_name = thread_name

    def filter(self, record):
        return record.threadName == self.thread_name


def setup_thread_logger(path, log_level=logging.DEBUG):
    """Add a log handler to separate file for current thread."""
    thread_name = threading.current_thread().name
    with open(f"{path}/{thread_name}.log", "w") as log_file:
        file_handler = logging.FileHandler(log_file.name)

        file_handler.setLevel(log_level)

        formatter = logging.Formatter("[%(asctime)s] [%(levelname)-7s] %(message)s")
        file_handler.setFormatter(formatter)

        log_filter = ThreadLogFilter(thread_name)
        file_handler.addFilter(log_filter)

        logger = logging.getLogger()
        logger.addHandler(file_handler)

    return file_handler
