import os
from typing import List
from enum import Enum

from base.errors import ConfigurationError
from network import Ethereum, Polygon, Fantom, Avalanche, Arbitrum, BSC, Optimism

SUPPORTED_NETWORKS_STARGATE = [
    # Ethereum(),  # High gas price
    Polygon(),
    # Fantom(),  # Liquidity problems
    Avalanche(),
    Arbitrum(),
    BSC(),
    Optimism()
]

STARGATE_SLIPPAGE = 0.01  # 0.01 - 1%
MIN_STABLECOIN_BALANCE = 1  # Minimal balance to bridge

DEFAULT_PRIVATE_KEYS_FILE_PATH = os.getenv("DEFAULT_PRIVATE_KEYS_FILE_PATH")


class RefuelMode(Enum):
    MANUAL = 1  # Manual refuel
    OKEX = 2  # Automatic refuel from the Okex exchange
    BINANCE = 3  # Automatic refuel from the Binance exchange


REFUEL_MODE = RefuelMode.BINANCE  # One of RefuelMode constants


# Utility class
class TimeRanges:
    MINUTE = 60
    HOUR = 3600


# Randomization ranges (seconds). The ranges shown are just examples of values that can easily be changed
class SleepTimings:
    AFTER_START_RANGE = (0, TimeRanges.MINUTE)  # from 0 seconds to 10 minutes. Sleep after start
    BEFORE_BRIDGE_RANGE = (30, TimeRanges.HOUR)  # from 30 seconds to 1 hour. Sleep before bridge
    BALANCE_RECHECK_TIME = TimeRanges.MINUTE * 2  # 2 minutes. Recheck time for stablecoin or native token deposit
    BEFORE_WITHDRAW_RANGE = (30, TimeRanges.HOUR)  # from 30 seconds to 30 minutes. Sleep before withdraw from exchange


# -------- Utility class --------
class ConfigurationHelper:

    @staticmethod
    def load_default_keys() -> List[str]:
        keys = ConfigurationHelper.load_private_keys(DEFAULT_PRIVATE_KEYS_FILE_PATH)
        if not keys:
            raise ConfigurationError(
                f'No private keys were found. Check the contents of the {DEFAULT_PRIVATE_KEYS_FILE_PATH}')

        return keys

    @staticmethod
    def load_private_keys(file_path: str) -> List[str]:
        with open(file_path, 'r') as file:
            return file.read().splitlines()

    @staticmethod
    def check_networks_list() -> None:
        if len(SUPPORTED_NETWORKS_STARGATE) == 0:
            raise ConfigurationError('Supported network list is empty. Unable to run with such a configuration')
        elif len(SUPPORTED_NETWORKS_STARGATE) == 1:
            raise ConfigurationError('Only one supported network is provided. Unable to run with such a configuration')

    @staticmethod
    def check_stargate_slippage() -> None:
        if STARGATE_SLIPPAGE < 0.001:
            raise ConfigurationError("Slippage can't be lower than 0.01%. Check configuration settings")
        if STARGATE_SLIPPAGE > 0.2:
            raise ConfigurationError("Slippage is too high. It's more than 20%. Check configuration settings")

    @staticmethod
    def check_min_stablecoin_balance() -> None:
        if MIN_STABLECOIN_BALANCE < 0:
            raise ConfigurationError("Incorrect minimum stablecoin balance. It can't be lower than zero. "
                                     "Check configuration settings")

    @staticmethod
    def check_refuel_mode() -> None:
        if not isinstance(REFUEL_MODE, RefuelMode):
            raise ConfigurationError('Incorrect REFUEL_MODE value. Check possible values in the RefuelMode class')

    @staticmethod
    def create_logging_directory() -> None:
        log_dir = 'logs'

        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

    @staticmethod
    def check_configuration() -> None:
        ConfigurationHelper.check_networks_list()
        ConfigurationHelper.check_stargate_slippage()
        ConfigurationHelper.check_min_stablecoin_balance()
        ConfigurationHelper.check_refuel_mode()

        ConfigurationHelper.create_logging_directory()
