import logging
import threading
import time

import requests
from ccxt.base.errors import RateLimitExceeded, InsufficientFunds
from eth_account import Account

from base.errors import BaseError
from config import TimeRanges
from logger import setup_thread_logger
from logic.states import SleepBeforeStartState, CheckStablecoinBalanceState

logger = logging.getLogger(__name__)


class AccountThread(threading.Thread):
    def __init__(self, account_id: int, private_key: str):
        super().__init__(name=f"Account-{account_id}")
        self.account_id = account_id
        self.account = Account.from_key(private_key)
        self.state = SleepBeforeStartState()

    def run(self):
        setup_thread_logger("logs")
        logger.info(f'Account address: {self.account.address}')
        while True:
            try:
                self.state.handle(self)
            except BaseError as ex:
                logger.error(f'Exception: {ex}')
                self.set_state(CheckStablecoinBalanceState())
            except requests.exceptions.HTTPError:
                logger.error(f'Too many request to HTTP Provider!')
                self.set_state(CheckStablecoinBalanceState())
                time.sleep(TimeRanges.MINUTE)
            except RateLimitExceeded:
                logger.error(f'Too many request to Okex exchange!')
                self.set_state(CheckStablecoinBalanceState())
                time.sleep(TimeRanges.MINUTE)
            except InsufficientFunds:
                logger.error(f'Not enough USDT balance on Okex trading account!')
                self.set_state(CheckStablecoinBalanceState())
                time.sleep(10 * TimeRanges.MINUTE)

    def set_state(self, state):
        self.state = state
