import logging
import threading
import time

import requests
from ccxt.base.errors import RateLimitExceeded, InsufficientFunds
from eth_account import Account

from base.errors import BaseError
from config import TimeRanges, BridgerMode, RefuelMode
from logger import setup_thread_logger
from logic.stargate_states import SleepBeforeStartStargateBridgerState, CheckStablecoinBalanceState
from logic.state import InitialState

logger = logging.getLogger(__name__)


class AccountThread(threading.Thread):
    def __init__(self, account_id: int, private_key: str, bridger_mode: BridgerMode, refuel_mode: RefuelMode):
        super().__init__(name=f"Account-{account_id}")
        self.account_id = account_id
        self.account = Account.from_key(private_key)
        self.bridger_mode = bridger_mode
        self.refuel_mode = refuel_mode
        self.state = InitialState()

    def run(self):
        setup_thread_logger("logs")
        logger.info(f"Account address: {self.account.address}")

        if self.bridger_mode == BridgerMode.STARGATE:
            self._run_stargate_mode()
        elif self.bridger_mode == BridgerMode.BTCB:
            pass
        elif self.bridger_mode == BridgerMode.TESTNET:
            pass
        else:
            raise ValueError("Unknown BridgeMode")

    def _run_stargate_mode(self):
        logger.info("Running Stargate bridger")

        self.set_state(SleepBeforeStartStargateBridgerState())
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
                logger.error(f'Too many request to exchange!')
                self.set_state(CheckStablecoinBalanceState())
                time.sleep(TimeRanges.MINUTE)
            except InsufficientFunds:
                logger.error(f'Not enough balance on exchange!')
                self.set_state(CheckStablecoinBalanceState())
                time.sleep(10 * TimeRanges.MINUTE)

    def set_state(self, state):
        self.state = state
