import os
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

SUPPORTED_NETWORKS_BTCB = [
    # Ethereum(),  # High gas price
    Polygon(),
    Avalanche(),
    Arbitrum(),
    BSC(),
    Optimism()
]

DEFAULT_PRIVATE_KEYS_FILE_PATH = os.getenv("DEFAULT_PRIVATE_KEYS_FILE_PATH")


class BridgerMode(Enum):
    STARGATE = "stargate"
    BTCB = "btcb"
    TESTNET = "testnet"


class RefuelMode(Enum):
    MANUAL = "manual"  # Manual refuel
    OKEX = "okex"  # Automatic refuel from the Okex exchange
    BINANCE = "binance"  # Automatic refuel from the Binance exchange


# Utility class
class TimeRanges:
    MINUTE = 60
    HOUR = 3600


# Randomization ranges (seconds). The ranges shown are just examples of values that can easily be changed
class SleepTimings:
    AFTER_START_RANGE = (0, TimeRanges.MINUTE * 10)  # from 0 seconds to 10 minutes. Sleep after start
    BEFORE_BRIDGE_RANGE = (30, TimeRanges.HOUR)  # from 30 seconds to 1 hour. Sleep before bridge
    BALANCE_RECHECK_TIME = TimeRanges.MINUTE * 2  # 2 minutes. Recheck time for stablecoin or native token deposit
    BEFORE_WITHDRAW_RANGE = (30, TimeRanges.HOUR)  # from 30 seconds to 30 minutes. Sleep before withdraw from exchange


# -------- Utility class --------
class ConfigurationHelper:
    @staticmethod
    def check_networks_list() -> None:
        if len(SUPPORTED_NETWORKS_STARGATE) == 0:
            raise ConfigurationError('Supported network list is empty. Unable to run with such a configuration')
        elif len(SUPPORTED_NETWORKS_STARGATE) == 1:
            raise ConfigurationError('Only one supported network is provided. Unable to run with such a configuration')

    @staticmethod
    def check_stargate_slippage() -> None:
        if float(os.getenv('STARGATE_SLIPPAGE')) < 0.001:
            raise ConfigurationError("Slippage can't be lower than 0.01%. Check configuration settings")
        if float(os.getenv('STARGATE_SLIPPAGE')) > 0.2:
            raise ConfigurationError("Slippage is too high. It's more than 20%. Check configuration settings")

    @staticmethod
    def check_min_stablecoin_balance() -> None:
        if float(os.getenv('STARGATE_MIN_STABLECOIN_BALANCE')) < 0:
            raise ConfigurationError("Incorrect minimum stablecoin balance. It can't be lower than zero. "
                                     "Check configuration settings")

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

        ConfigurationHelper.create_logging_directory()
