import logging
import datetime
import random
import time
import os
from dataclasses import dataclass
from dotenv import load_dotenv
from typing import List

from base.errors import ConfigurationError, StablecoinNotSupportedByChain, NotWhitelistedAddress
from config import SUPPORTED_NETWORKS_STARGATE, SleepTimings, \
    RefuelMode
from logic.state import State
from network import EVMNetwork
from utility import Stablecoin
from network.balance_helper import BalanceHelper
from exchange import ExchangeFactory
from stargate import StargateBridgeHelper, StargateUtils

logger = logging.getLogger(__name__)
load_dotenv()


# State for waiting before start to randomize start time
class SleepBeforeStartStargateBridgerState(State):
    def __init__(self) -> None:
        pass

    def handle(self, thread) -> None:
        sleep_time = random.randint(SleepTimings.AFTER_START_RANGE[0], SleepTimings.AFTER_START_RANGE[1])

        logger.info(f"Sleeping {sleep_time} seconds before start")
        time.sleep(sleep_time)

        thread.set_state(CheckStablecoinBalanceState())


# State for waiting for the stablecoin deposit
class WaitForStablecoinDepositState(State):
    def __init__(self) -> None:
        pass

    def handle(self, thread) -> None:
        logger.info("Waiting for stablecoin deposit")
        time.sleep(SleepTimings.BALANCE_RECHECK_TIME)

        thread.set_state(CheckStablecoinBalanceState())


# Utility class to store the network and related stablecoin that will be used in future
@dataclass
class NetworkWithStablecoinBalance:
    network: EVMNetwork
    stablecoin: Stablecoin


# State for checking the stablecoin balance
class CheckStablecoinBalanceState(State):
    def __init__(self) -> None:
        pass

    def is_enough_balance(self, balance_helper: BalanceHelper, stablecoin: Stablecoin) -> bool:
        balance = balance_helper.get_stablecoin_balance(stablecoin)
        min_balance = float(os.getenv('STARGATE_MIN_STABLECOIN_BALANCE')) * 10 ** stablecoin.decimals
        min_balance = int(min_balance)

        logger.info(f'{balance_helper.network.name}. {stablecoin.symbol} '
                    f'balance - {balance / 10 ** stablecoin.decimals}')

        if balance > min_balance:
            return True
        return False

    def find_networks_with_balance(self, thread) -> List[NetworkWithStablecoinBalance]:
        """ Method that checks stablecoin balances in all networks and returns the list of networks
        and related stablecoins that satisfies the minimum balance condition """

        result = []

        for network in SUPPORTED_NETWORKS_STARGATE:
            for stablecoin in network.supported_stablecoins.values():
                if self.is_enough_balance(BalanceHelper(network, thread.account.address),
                                          stablecoin):
                    result.append(NetworkWithStablecoinBalance(network, stablecoin))

        return result

    def handle(self, thread) -> None:
        logger.info("Checking stablecoin balance")

        networks = self.find_networks_with_balance(thread)
        if len(networks) == 0:
            logger.info("Not enough stablecoin balance. Refill one of the supported networks")
            thread.set_state(WaitForStablecoinDepositState())
        elif len(networks) == 1:
            logger.info(f"{networks[0].network.name} network meet the minimum stablecoin balance requirements")
            thread.set_state(ChooseDestinationNetworkState(networks[0].network, networks[0].stablecoin))
        else:
            logger.info(
                f"{len(networks)} networks meet the minimum stablecoin balance requirements. Randomizing choice")
            random_network = random.choice(networks)
            logger.info(f"{random_network.network.name} was randomized")
            thread.set_state(ChooseDestinationNetworkState(random_network.network, random_network.stablecoin))


# State for choosing a random destination network
class ChooseDestinationNetworkState(State):
    def __init__(self, src_network: EVMNetwork, src_stablecoin: Stablecoin) -> None:
        self.src_network = src_network
        self.src_stablecoin = src_stablecoin

    def handle(self, thread) -> None:
        logger.info("Randomizing destination network")

        networks = SUPPORTED_NETWORKS_STARGATE.copy()
        networks.remove(self.src_network)

        if len(networks) == 0:
            raise ConfigurationError("Unable to select destination chain. "
                                     "Revise the list of supported networks in config")

        dst_network = random.choice(networks)
        logger.info(f"Destination network is chosen - {dst_network.name}")
        thread.set_state(ChooseDestinationStablecoinState(self.src_network, dst_network, self.src_stablecoin))


# State for choosing a random destination stablecoin
class ChooseDestinationStablecoinState(State):
    def __init__(self, src_network: EVMNetwork, dst_network: EVMNetwork, src_stablecoin: Stablecoin) -> None:
        self.src_network = src_network
        self.dst_network = dst_network
        self.src_stablecoin = src_stablecoin

    def handle(self, thread) -> None:
        logger.info("Choosing destination stablecoin")

        if len(self.dst_network.supported_stablecoins) == 0:
            raise StablecoinNotSupportedByChain(f"{self.dst_network} chain doesn't support any stablecoin")

        dst_stablecoin = random.choice(list(self.dst_network.supported_stablecoins.values()))

        logger.info(f"Destination stablecoin is chosen - {dst_stablecoin.symbol}")
        logger.info(f"Path: {self.src_stablecoin.symbol} ({self.src_network.name}) -> "
                    f"{dst_stablecoin.symbol} ({self.dst_network.name})")

        thread.set_state(CheckNativeTokenBalanceForGasState(self.src_network, self.dst_network,
                                                            self.src_stablecoin, dst_stablecoin))


# State for deciding whether gas will be refueled automatically or manually
class RefuelDecisionState(State):
    def __init__(self, src_network: EVMNetwork, dst_network: EVMNetwork,
                 src_stablecoin: Stablecoin, dst_stablecoin: Stablecoin) -> None:
        self.src_network = src_network
        self.dst_network = dst_network
        self.src_stablecoin = src_stablecoin
        self.dst_stablecoin = dst_stablecoin

    def handle(self, thread) -> None:
        logger.info("Checking possible refuel options")

        # TODO: Add auto refuel with Bungee/WooFi

        if thread.refuel_mode == RefuelMode.OKEX or thread.refuel_mode == RefuelMode.BINANCE:
            thread.set_state(SleepBeforeExchangeRefuelState(self.src_network, self.dst_network,
                                                            self.src_stablecoin, self.dst_stablecoin))
        else:
            thread.set_state(WaitForManualRefuelState(self.src_network, self.dst_network,
                                                      self.src_stablecoin, self.dst_stablecoin))


# State for waiting for a manual native token deposit (in case the auto-refuel failed or disabled)
class WaitForManualRefuelState(State):
    def __init__(self, src_network: EVMNetwork, dst_network: EVMNetwork,
                 src_stablecoin: Stablecoin, dst_stablecoin: Stablecoin) -> None:
        self.src_network = src_network
        self.dst_network = dst_network
        self.src_stablecoin = src_stablecoin
        self.dst_stablecoin = dst_stablecoin

    def handle(self, thread) -> None:
        logger.info(f"{self.src_network.name}. Manual refuel chosen. Waiting for the native token deposit")
        time.sleep(SleepTimings.BALANCE_RECHECK_TIME)
        thread.set_state(CheckNativeTokenBalanceForGasState(self.src_network, self.dst_network,
                                                            self.src_stablecoin, self.dst_stablecoin))


# State for waiting before the exchange withdraw to make an account unique
class SleepBeforeExchangeRefuelState(State):
    def __init__(self, src_network: EVMNetwork, dst_network: EVMNetwork,
                 src_stablecoin: Stablecoin, dst_stablecoin: Stablecoin) -> None:
        self.src_network = src_network
        self.dst_network = dst_network
        self.src_stablecoin = src_stablecoin
        self.dst_stablecoin = dst_stablecoin

    def handle(self, thread) -> None:
        sleep_time = random.randint(SleepTimings.BEFORE_WITHDRAW_RANGE[0], SleepTimings.BEFORE_WITHDRAW_RANGE[1])

        withdraw_dt = datetime.datetime.fromtimestamp(time.time() + sleep_time)
        logger.info(f"Sleeping {sleep_time} seconds before withdraw from exchange. Withdraw time: {withdraw_dt}")
        time.sleep(sleep_time)

        thread.set_state(RefuelWithExchangeState(self.src_network, self.dst_network,
                                                 self.src_stablecoin, self.dst_stablecoin))


# State for refueling native token from exchange to cover gas fees
class RefuelWithExchangeState(State):
    def __init__(self, src_network: EVMNetwork, dst_network: EVMNetwork,
                 src_stablecoin: Stablecoin, dst_stablecoin: Stablecoin) -> None:
        self.src_network = src_network
        self.dst_network = dst_network
        self.src_stablecoin = src_stablecoin
        self.dst_stablecoin = dst_stablecoin

    def refuel(self, thread, amount: float) -> None:
        factory = ExchangeFactory()

        if thread.refuel_mode == RefuelMode.OKEX:
            exchange = factory.create("okex")
        else:
            exchange = factory.create("binance")

        symbol = self.src_network.native_token

        try:
            exchange.buy_token_and_withdraw(symbol, amount, self.src_network.name, thread.account.address)
        except NotWhitelistedAddress:
            logger.warning(f"WARNING! Address {thread.account.address} is not whitelisted to withdraw "
                           f"{self.src_network.native_token} in {self.src_network.name} network")

    def handle(self, thread) -> None:
        logger.info(f"Exchange refueling started")

        layer_zero_fee = StargateUtils.estimate_layerzero_swap_fee(self.src_network, self.dst_network,
                                                                   thread.account.address) / 10 ** 18
        swap_price = StargateUtils.estimate_swap_gas_price(self.src_network, self.dst_network,
                                                           thread.account.address) / 10 ** 18
        mul = 2  # Multiplier to withdraw funds with a reserve

        logger.info(f'L0 fee: {layer_zero_fee} {self.src_network.native_token}. '
                    f'Swap price: {swap_price} {self.src_network.native_token}')

        amount_to_withdraw = mul * (layer_zero_fee + swap_price)

        # Multiplier to randomize withdraw amount
        multiplier = random.uniform(1, 1.5)
        amount_to_withdraw *= multiplier
        decimals = random.randint(4, 7)
        amount_to_withdraw = round(amount_to_withdraw, decimals)

        logger.info(f'To withdraw: {amount_to_withdraw}')
        self.refuel(thread, amount_to_withdraw)

        thread.set_state(CheckNativeTokenBalanceForGasState(self.src_network, self.dst_network,
                                                            self.src_stablecoin, self.dst_stablecoin))


# TODO
class RefuelWithBungeeState(State):
    def __init__(self, src_network: EVMNetwork, dst_network: EVMNetwork,
                 src_stablecoin: Stablecoin, dst_stablecoin: Stablecoin) -> None:
        self.src_network = src_network
        self.dst_network = dst_network
        self.src_stablecoin = src_stablecoin
        self.dst_stablecoin = dst_stablecoin


# State for checking the native token balance
class CheckNativeTokenBalanceForGasState(State):
    def __init__(self, src_network: EVMNetwork, dst_network: EVMNetwork,
                 src_stablecoin: Stablecoin, dst_stablecoin: Stablecoin) -> None:
        self.src_network = src_network
        self.dst_network = dst_network
        self.src_stablecoin = src_stablecoin
        self.dst_stablecoin = dst_stablecoin

    def handle(self, thread) -> None:
        logger.info("Checking native token balance")

        if StargateUtils.is_enough_native_balance_for_swap_fee(self.src_network, self.dst_network,
                                                               thread.account.address):
            logger.info("Enough native token amount on source chain. Moving to the swap")
            thread.set_state(SleepBeforeBridgeState(self.src_network, self.dst_network,
                                                    self.src_stablecoin, self.dst_stablecoin))
        else:
            logger.info("Not enough native token amount on source chain to cover the fees")
            thread.set_state(RefuelDecisionState(self.src_network, self.dst_network,
                                                 self.src_stablecoin, self.dst_stablecoin))


# State for waiting before every bridge to make an account unique
class SleepBeforeBridgeState(State):
    def __init__(self, src_network: EVMNetwork, dst_network: EVMNetwork,
                 src_stablecoin: Stablecoin, dst_stablecoin: Stablecoin) -> None:
        self.src_network = src_network
        self.dst_network = dst_network
        self.src_stablecoin = src_stablecoin
        self.dst_stablecoin = dst_stablecoin

    def handle(self, thread) -> None:
        sleep_time = random.randint(SleepTimings.BEFORE_BRIDGE_RANGE[0], SleepTimings.BEFORE_BRIDGE_RANGE[1])

        next_swap_dt = datetime.datetime.fromtimestamp(time.time() + sleep_time)
        logger.info(f"Sleeping {sleep_time} seconds before bridge. Next bridge time: {next_swap_dt}")
        time.sleep(sleep_time)

        thread.set_state(StargateSwapState(self.src_network, self.dst_network,
                                           self.src_stablecoin, self.dst_stablecoin))


# State for swapping tokens
class StargateSwapState(State):
    def __init__(self, src_network: EVMNetwork, dst_network: EVMNetwork,
                 src_stablecoin: Stablecoin, dst_stablecoin: Stablecoin) -> None:
        self.src_network = src_network
        self.dst_network = dst_network
        self.src_stablecoin = src_stablecoin
        self.dst_stablecoin = dst_stablecoin

    def handle(self, thread) -> None:
        balance_helper = BalanceHelper(self.src_network, thread.account.address)
        amount = balance_helper.get_stablecoin_balance(self.src_stablecoin)

        logger.info(f"Swapping {amount / 10 ** self.src_stablecoin.decimals} tokens through Stargate bridge. "
                    f"{self.src_stablecoin.symbol}({self.src_network.name}) -> "
                    f"{self.dst_stablecoin.symbol}({self.dst_network.name})")

        bridge_helper = StargateBridgeHelper(thread.account, self.src_network, self.dst_network,
                                             self.src_stablecoin, self.dst_stablecoin, amount,
                                             float(os.getenv('STARGATE_SLIPPAGE', 0.01)))
        bridge_result = bridge_helper.make_bridge()

        if bridge_result:
            thread.remaining_bridges -= 1
            logger.info(f"Stargate bridge finished successfully. "
                        f"Remaining bridges: {thread.remaining_bridges}/{thread.bridges_limit}")
        else:
            logger.info(f"Stargate bridge finished with error. "
                        f"Remaining bridges: {thread.remaining_bridges}/{thread.bridges_limit}")

        thread.set_state(CheckStablecoinBalanceState())
