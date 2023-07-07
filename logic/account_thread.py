import logging
import threading
import time
from typing import Optional

import requests
from ccxt.base.errors import RateLimitExceeded, InsufficientFunds
from eth_account import Account

from base.errors import BaseError
from config import TimeRanges, BridgerMode, RefuelMode
from logger import setup_thread_logger
from logic.stargate_states import SleepBeforeStartStargateBridgerState, CheckStablecoinBalanceState
from logic.btcb_states import SleepBeforeStartBTCBridgerState, CheckBTCbBalanceState
from logic.state import InitialState

logger = logging.getLogger(__name__)


class AccountThread(threading.Thread):
    def __init__(self, account_id: int, private_key: str, bridger_mode: BridgerMode, refuel_mode: RefuelMode,
                 bridges_limit: Optional[int]) -> None:
        self.account = Account.from_key(private_key)
        super().__init__(name=f"Account-{account_id}-{self.account.address}")
        self.account_id = account_id
        self.bridger_mode = bridger_mode
        self.refuel_mode = refuel_mode
        self.bridges_limit = bridges_limit
        self.remaining_bridges = bridges_limit
        self.state = InitialState()

    def run(self) -> None:
        setup_thread_logger("logs")
        logger.info(f"Account address: {self.account.address}")

        if self.bridger_mode == BridgerMode.STARGATE:
            self._run_stargate_mode()
        elif self.bridger_mode == BridgerMode.BTCB:
            self._run_btcb_mode()
        elif self.bridger_mode == BridgerMode.TESTNET:
            pass
        else:
            raise ValueError("Unknown BridgeMode")

    def set_state(self, state) -> None:
        self.state = state

    def are_bridges_left(self) -> bool:
        if self.remaining_bridges is None:
            return True

        bridges_left = self.remaining_bridges > 0
        if not bridges_left:
            logger.info('The bridge limit has been reached. The work is over')
        return bridges_left

    def _run_stargate_mode(self) -> None:
        logger.info("Running Stargate bridger")

        self.set_state(SleepBeforeStartStargateBridgerState())
        while self.are_bridges_left():
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

    def _run_btcb_mode(self) -> None:
        logger.info("Running BTC.b bridger")

        self.set_state(SleepBeforeStartBTCBridgerState())
        while self.are_bridges_left():
            try:
                self.state.handle(self)
            except BaseError as ex:
                logger.error(f'Exception: {ex}')
                self.set_state(CheckBTCbBalanceState())
            except requests.exceptions.HTTPError:
                logger.error(f'Too many request to HTTP Provider!')
                self.set_state(CheckBTCbBalanceState())
                time.sleep(TimeRanges.MINUTE)
            except RateLimitExceeded:
                logger.error(f'Too many request to exchange!')
                self.set_state(CheckBTCbBalanceState())
                time.sleep(TimeRanges.MINUTE)
            except InsufficientFunds:
                logger.error(f'Not enough balance on exchange!')
                self.set_state(CheckBTCbBalanceState())
                time.sleep(10 * TimeRanges.MINUTE)
