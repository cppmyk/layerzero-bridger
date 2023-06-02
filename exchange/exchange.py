import logging
import time
from dataclasses import dataclass
from enum import Enum

from base.errors import NotSupported, WithdrawCanceled, WithdrawTimeout

logger = logging.getLogger(__name__)


class WithdrawStatus(Enum):
    INITIATED = 0
    PENDING = 1
    FINISHED = 2
    CANCELED = 3


@dataclass
class WithdrawInfo:
    symbol: str
    chain: str
    fee: float
    min_amount: float


# Base exchange class
class Exchange:

    def __init__(self, name: str) -> None:
        self.name = name

    def withdraw(self, symbol: str, amount: float, network: str, address: str) -> WithdrawStatus:
        """ Method that initiates withdraw funds from the exchange """
        raise NotSupported(f"{self.name} withdraw() is not implemented")

    def wait_for_withdraw_to_finish(self, withdraw_id: str, timeout: int = 1800):
        start_time = time.time()

        logger.info(f'Waiting for {withdraw_id} withdraw to be sent')
        while True:
            status = self.get_withdraw_status(withdraw_id)

            if status == WithdrawStatus.FINISHED:
                logger.info(f"Withdraw {withdraw_id} finished")
                return

            if status == WithdrawStatus.CANCELED:
                raise WithdrawCanceled(f'Withdraw {withdraw_id} canceled')

            if time.time() - start_time >= timeout:
                raise WithdrawTimeout(f"Withdraw timeout reached. Id: {withdraw_id}")

            time.sleep(10)  # Wait for 10 seconds before checking again

    def get_withdraw_info(self, symbol: str, network: str) -> WithdrawInfo:
        """ Method that fetches symbol withdraw information"""
        raise NotSupported(f"{self.name} get_withdraw_info() is not implemented")

    def get_funding_balance(self, symbol: str) -> float:
        """ Method that fetches non-trading balance from which we can initiate withdraw (can be named differently) """
        raise NotSupported(f"{self.name} get_withdraw_info() is not implemented")

    def get_withdraw_status(self, withdraw_id: str) -> WithdrawStatus:
        """ Method that fetches withdraw status """
        raise NotSupported(f"{self.name} get_withdraw_info() is not implemented")

    def buy_token_and_withdraw(self, symbol: str, amount: float, network: str, address: str) -> None:
        """ Method that checks balance of symbol token, buys it if it's not enough and withdraws this token """
        raise NotSupported(f"{self.name} get_withdraw_info() is not implemented")

    @staticmethod
    def _parse_withdraw_status(withdraw_info: dict) -> WithdrawStatus:
        if 'status' not in withdraw_info:
            raise ValueError(f"Incorrect withdraw_info: {withdraw_info}")

        if withdraw_info['status'] == 'ok':
            return WithdrawStatus.FINISHED
        if withdraw_info['status'] == 'pending':
            return WithdrawStatus.PENDING
        if withdraw_info['status'] == 'canceled':
            return WithdrawStatus.CANCELED

        raise ValueError(f'Unknown withdraw status: {withdraw_info}')
