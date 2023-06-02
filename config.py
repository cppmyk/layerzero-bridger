import os
from typing import List
from enum import Enum

from base.errors import ConfigurationError
from network import Ethereum, Polygon, Fantom, Avalanche, Arbitrum, BSC, Optimism

SUPPORTED_NETWORKS = [
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

# Keys
OKEX_API_KEY = os.getenv("OKEX_API_KEY", "")
OKEX_SECRET_KEY = os.getenv("OKEX_SECRET_KEY", "")
OKEX_PASSWORD = os.getenv("OKEX_PASSWORD", "")

PRIVATE_KEYS_FILE_PATH = "private_keys.txt"


class RefuelMode(Enum):
    RANDOM = 0  # 50% chance of MANUAL, 50% chance of EXCHANGE
    MANUAL = 1  # Manual refuel
    EXCHANGE = 2  # Automatic native token buy and withdraw from Okex exchange


REFUEL_MODE = RefuelMode.MANUAL  # One of RefuelMode constants


# Utility class
class TimeRanges:
    MINUTE = 60
    HOUR = 3600


# Randomization ranges (seconds). The ranges shown are just examples of values that can easily be changed
class SleepTimings:
    AFTER_START_RANGE = (0, TimeRanges.MINUTE * 10)  # from 0 seconds to 10 minutes. Sleep after start
    BEFORE_BRIDGE_RANGE = (30, TimeRanges.HOUR)  # from 30 seconds to 30 minutes. Sleep before bridge
    BALANCE_RECHECK_TIME = TimeRanges.MINUTE * 2  # 2 minutes. Recheck time for stablecoin or native token deposit
    BEFORE_WITHDRAW_RANGE = (30, TimeRanges.HOUR)  # from 30 seconds to 30 minutes. Sleep before withdraw from exchange
    EXCHANGE_WITHDRAW_RECHECK_TIME = TimeRanges.MINUTE * 30  # 30 minutes. After this time soft will try to withdraw funds one more time


def load_private_keys() -> List[str]:
    with open(PRIVATE_KEYS_FILE_PATH, 'r') as file:
        return file.read().splitlines()


def check_networks_list():
    if len(SUPPORTED_NETWORKS) == 0:
        raise ConfigurationError('Supported network list is empty. Unable to run with such a configuration')
    elif len(SUPPORTED_NETWORKS) == 1:
        raise ConfigurationError('Only one supported network is provided. Unable to run with such a configuration')


def check_stagrate_slippage():
    if STARGATE_SLIPPAGE < 0.001:
        raise ConfigurationError("Slippage can't be lower than 0.01%. Check configuration settings")
    if STARGATE_SLIPPAGE > 0.2:
        raise ConfigurationError("Slippage is too high. It's more than 20%. Check configuration settings")


def check_min_stablecoin_balance():
    if MIN_STABLECOIN_BALANCE < 0:
        raise ConfigurationError("Incorrect minimum stablecoin balance. It can't be lower than zero. "
                                 "Check configuration settings")


def check_refuel_mode():
    if not isinstance(REFUEL_MODE, RefuelMode):
        raise ConfigurationError('Incorrect REFUEL_MODE value. Check possible values in the RefuelMode class')


def check_configuration():
    check_networks_list()
    check_stagrate_slippage()
    check_min_stablecoin_balance()
    check_refuel_mode()
