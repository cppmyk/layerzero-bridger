import threading
import time
import requests

from config import TimeRanges
from logic.states import SleepBeforeStart, CheckStablecoinBalanceState
from eth_account import Account
from base.errors import BaseError
from logger import setup_logger


class AccountThread(threading.Thread):
    def __init__(self, account_id: int, private_key: str):
        super().__init__()
        self.logger = setup_logger(f"account_{account_id}_logger", f"logs/account_{account_id}.log")
        self.account_id = account_id
        self.account = Account.from_key(private_key)
        self.state = SleepBeforeStart()

        self.log_info('-' * 60)
        self.log_info(f'Account address: {self.account.address}')

    def run(self):
        while True:
            try:
                self.state.handle(self)
            except BaseError as ex:
                self.log_error(f'Exception: {ex}')
                self.set_state(CheckStablecoinBalanceState())
            except requests.exceptions.HTTPError:
                self.log_error(f'Too many request to HTTP Provider!')
                self.set_state(CheckStablecoinBalanceState())
                time.sleep(TimeRanges.MINUTE)

    def set_state(self, state):
        self.state = state

    def log_info(self, msg: str):
        print(f"Account {self.account_id} - {msg}")
        self.logger.info(msg)

    def log_error(self, msg):
        print(f"Account {self.account_id} - ERROR! {msg}")
        self.logger.error(msg)
