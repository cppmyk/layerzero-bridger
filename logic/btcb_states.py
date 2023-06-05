import logging
import datetime
import random
import time
import os
from dataclasses import dataclass
from dotenv import load_dotenv
from typing import List

from base.errors import ConfigurationError, NotWhitelistedAddress
from config import SUPPORTED_NETWORKS_BTCB, SleepTimings, RefuelMode
from logic.state import State
from network import EVMNetwork
from utility import Stablecoin
from exchange import ExchangeFactory
from btcb import BTCbBridgeHelper, BTCbUtils, BTCbConstants

logger = logging.getLogger(__name__)
load_dotenv()


# State for waiting before start to randomize start time
class SleepBeforeStartBTCBridgerState(State):
    def __init__(self) -> None:
        pass

    def handle(self, thread) -> None:
        sleep_time = random.randint(SleepTimings.AFTER_START_RANGE[0], SleepTimings.AFTER_START_RANGE[1])

        logger.info(f"Sleeping {sleep_time} seconds before start")
        time.sleep(sleep_time)

        thread.set_state(CheckBTCbBalanceState())


# State for waiting for the BTC.b deposit
class WaitForBTCbDeposit(State):
    def __init__(self) -> None:
        pass

    def handle(self, thread) -> None:
        logger.info("Waiting for BTC.b deposit")
        time.sleep(SleepTimings.BALANCE_RECHECK_TIME)

        thread.set_state(CheckBTCbBalanceState())


# State for checking the BTC.b balance
class CheckBTCbBalanceState(State):
    def __init__(self) -> None:
        pass

    def is_enough_balance(self, network: EVMNetwork, address: str) -> bool:
        balance = BTCbUtils.get_btcb_balance(network, address)
        min_balance = float(os.getenv('BTCB_MIN_BALANCE')) * 10 ** BTCbConstants.BTCB_DECIMALS
        min_balance = int(min_balance)

        logger.info(f'{network.name}. BTC.b balance - {balance / 10 ** BTCbConstants.BTCB_DECIMALS}')

        if balance > min_balance:
            return True
        return False

    def find_networks_with_balance(self, thread) -> List[EVMNetwork]:
        """ Method that checks BTC.b balances in all networks and returns the list of networks
        that satisfies the minimum balance condition """

        result = []

        for network in SUPPORTED_NETWORKS_BTCB:
            if self.is_enough_balance(network, thread.account.address):
                result.append(network)

        return result

    def handle(self, thread) -> None:
        logger.info("Checking BTC.b balance")

        networks = self.find_networks_with_balance(thread)
        if len(networks) == 0:
            logger.info("Not enough BTC.b balance. Refill one of the supported networks")
            thread.set_state(WaitForBTCbDeposit())
        elif len(networks) == 1:
            logger.info(f"{networks[0].name} network meet the minimum BTC.b balance requirements")
            thread.set_state(ChooseDestinationNetworkState(networks[0]))
        else:
            logger.info(
                f"{len(networks)} networks meet the minimum BTC.b balance requirements. Randomizing choice")
            random_network = random.choice(networks)
            logger.info(f"{random_network.name} was randomized")
            thread.set_state(ChooseDestinationNetworkState(random_network))


# State for choosing a random destination network
class ChooseDestinationNetworkState(State):
    def __init__(self, src_network: EVMNetwork) -> None:
        self.src_network = src_network

    def handle(self, thread) -> None:
        logger.info("Randomizing destination network")

        networks = SUPPORTED_NETWORKS_BTCB.copy()
        networks.remove(self.src_network)

        if len(networks) == 0:
            raise ConfigurationError("Unable to select destination chain. "
                                     "Revise the list of supported networks in config")

        dst_network = random.choice(networks)
        logger.info(f"Destination network is chosen - {dst_network.name}")
        thread.set_state(CheckNativeTokenBalanceForGasState(self.src_network, dst_network))


# State for deciding whether gas will be refueled automatically or manually
class RefuelDecisionState(State):
    def __init__(self, src_network: EVMNetwork, dst_network: EVMNetwork) -> None:
        self.src_network = src_network
        self.dst_network = dst_network

    def handle(self, thread) -> None:
        logger.info("Checking possible refuel options")

        if thread.refuel_mode in [RefuelMode.OKEX, RefuelMode.BINANCE]:
            thread.set_state(SleepBeforeExchangeRefuelState(self.src_network, self.dst_network))
        else:
            thread.set_state(WaitForManualRefuelState(self.src_network, self.dst_network))


# State for waiting for a manual native token deposit (in case the auto-refuel failed or disabled)
class WaitForManualRefuelState(State):
    def __init__(self, src_network: EVMNetwork, dst_network: EVMNetwork) -> None:
        self.src_network = src_network
        self.dst_network = dst_network

    def handle(self, thread) -> None:
        logger.info(f"{self.src_network.name}. Manual refuel chosen. Waiting for the native token deposit")
        time.sleep(SleepTimings.BALANCE_RECHECK_TIME)
        thread.set_state(CheckNativeTokenBalanceForGasState(self.src_network, self.dst_network))


# State for waiting before the exchange withdraw to make an account unique
class SleepBeforeExchangeRefuelState(State):
    def __init__(self, src_network: EVMNetwork, dst_network: EVMNetwork) -> None:
        self.src_network = src_network
        self.dst_network = dst_network

    def handle(self, thread) -> None:
        sleep_time = random.randint(SleepTimings.BEFORE_WITHDRAW_RANGE[0], SleepTimings.BEFORE_WITHDRAW_RANGE[1])

        withdraw_dt = datetime.datetime.fromtimestamp(time.time() + sleep_time)
        logger.info(f"Sleeping {sleep_time} seconds before withdraw from exchange. Withdraw time: {withdraw_dt}")
        time.sleep(sleep_time)

        thread.set_state(RefuelWithExchangeState(self.src_network, self.dst_network))


# State for refueling native token from exchange to cover gas fees
class RefuelWithExchangeState(State):
    def __init__(self, src_network: EVMNetwork, dst_network: EVMNetwork) -> None:
        self.src_network = src_network
        self.dst_network = dst_network

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
            logger.warning(f"Address {thread.account.address} is not whitelisted to withdraw "
                           f"{self.src_network.native_token} in {self.src_network.name} network")

    def handle(self, thread) -> None:
        logger.info(f"Exchange refueling started")

        layer_zero_fee = BTCbUtils.estimate_layerzero_bridge_fee(self.src_network, self.dst_network,
                                                                 thread.account.address) / 10 ** 18
        bridge_price = BTCbUtils.estimate_bridge_gas_price(self.src_network, self.dst_network,
                                                           thread.account.address) / 10 ** 18
        mul = 1.5  # Multiplier to withdraw funds with a reserve

        logger.info(f'L0 fee: {layer_zero_fee} {self.src_network.native_token}. '
                    f'BTC bridge price: {bridge_price} {self.src_network.native_token}')

        amount_to_withdraw = mul * (layer_zero_fee + bridge_price)

        # Multiplier to randomize withdraw amount
        multiplier = random.uniform(1, 1.5)
        amount_to_withdraw *= multiplier
        decimals = random.randint(4, 7)
        amount_to_withdraw = round(amount_to_withdraw, decimals)

        logger.info(f'To withdraw: {amount_to_withdraw}')
        self.refuel(thread, amount_to_withdraw)

        thread.set_state(CheckNativeTokenBalanceForGasState(self.src_network, self.dst_network))


# State for checking the native token balance
class CheckNativeTokenBalanceForGasState(State):
    def __init__(self, src_network: EVMNetwork, dst_network: EVMNetwork) -> None:
        self.src_network = src_network
        self.dst_network = dst_network

    def handle(self, thread) -> None:
        logger.info("Checking native token balance")

        if BTCbUtils.is_enough_native_balance_for_bridge_fee(self.src_network, self.dst_network,
                                                             thread.account.address):
            logger.info("Enough native token amount on source chain. Moving to the bridge")
            thread.set_state(SleepBeforeBridgeState(self.src_network, self.dst_network))
        else:
            logger.info("Not enough native token amount on source chain to cover the fees")
            thread.set_state(RefuelDecisionState(self.src_network, self.dst_network))


# State for waiting before every bridge to make an account unique
class SleepBeforeBridgeState(State):
    def __init__(self, src_network: EVMNetwork, dst_network: EVMNetwork) -> None:
        self.src_network = src_network
        self.dst_network = dst_network

    def handle(self, thread) -> None:
        sleep_time = random.randint(SleepTimings.BEFORE_BRIDGE_RANGE[0], SleepTimings.BEFORE_BRIDGE_RANGE[1])

        next_swap_dt = datetime.datetime.fromtimestamp(time.time() + sleep_time)
        logger.info(f"Sleeping {sleep_time} seconds before bridge. Next bridge time: {next_swap_dt}")
        time.sleep(sleep_time)

        thread.set_state(BTCBridgeState(self.src_network, self.dst_network))


# State for swapping tokens
class BTCBridgeState(State):
    def __init__(self, src_network: EVMNetwork, dst_network: EVMNetwork) -> None:
        self.src_network = src_network
        self.dst_network = dst_network

    def handle(self, thread) -> None:
        amount = BTCbUtils.get_btcb_balance(self.src_network, thread.account.address)

        logger.info(f"Bridging {amount / 10 ** BTCbConstants.BTCB_DECIMALS} BTC.b through BTC bridge. "
                    f"{self.src_network.name} -> {self.dst_network.name}")

        bh = BTCbBridgeHelper(thread.account, self.src_network, self.dst_network, amount)
        bridge_result = bh.make_bridge()

        if bridge_result:
            logger.info("BTC bridge finished successfully")
        else:
            logger.info("BTC bridge finished with error")

        thread.set_state(CheckBTCbBalanceState())
