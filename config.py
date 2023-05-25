from typing import List

from base.errors import ConfigurationError
from network import Ethereum, Polygon, Fantom, Avalanche, Arbitrum, BSC, Optimism

SUPPORTED_NETWORKS = [Fantom(), Polygon(), Avalanche(), Arbitrum(), BSC(), Optimism()]  # Can be added or removed
STARGATE_SLIPPAGE = 0.01  # 0.01 - 1%
MIN_STABLECOIN_BALANCE = 1  # Minimal balance to bridge

PRIVATE_KEYS_FILE_PATH = "private_keys.txt"


# Utility class
class TimeRanges:
    MINUTE = 60
    HOUR = 3600


# Randomization ranges (seconds)
class SleepTimings:
    AFTER_START_RANGE = (0, 60)
    BETWEEN_BRIDGE_RANGE = (30, 360)
    BALANCE_RECHECK_TIME = 120


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


def check_configuration():
    check_networks_list()
    check_stagrate_slippage()
    check_min_stablecoin_balance()
