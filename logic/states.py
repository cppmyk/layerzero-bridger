import logging
import datetime
import random
import time
from dataclasses import dataclass
from typing import List

from base.errors import ConfigurationError, StablecoinNotSupportedByChain, NotWhitelistedAddress
from config import OKEX_API_KEY, OKEX_SECRET_KEY, OKEX_PASSWORD
from config import SUPPORTED_NETWORKS_STARGATE, STARGATE_SLIPPAGE, MIN_STABLECOIN_BALANCE, REFUEL_MODE, SleepTimings, RefuelMode
from network import EVMNetwork, Stablecoin
from network.balance_helper import BalanceHelper
from refuel import Okex
from stargate.bridge import BridgeHelper

logger = logging.getLogger(__name__)


# State interface defining the behavior of different states
class State:
    def handle(self, thread):
        pass


# State for waiting before start to randomize start time
class SleepBeforeStartState(State):
    def __init__(self):
        pass

    def handle(self, thread):
        sleep_time = random.randint(SleepTimings.AFTER_START_RANGE[0], SleepTimings.AFTER_START_RANGE[1])

        logger.info(f"Sleeping {sleep_time} seconds before start")
        time.sleep(sleep_time)

        thread.set_state(CheckStablecoinBalanceState())


# State for waiting for the stablecoin deposit
class WaitForStablecoinDepositState(State):
    def __init__(self):
        pass

    def handle(self, thread):
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
    def __init__(self):
        pass

    def is_enough_balance(self, balance_helper: BalanceHelper, stablecoin: Stablecoin) -> bool:
        balance = balance_helper.get_stablecoin_balance(stablecoin)
        min_balance = MIN_STABLECOIN_BALANCE * 10 ** stablecoin.decimals

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

    def handle(self, thread):
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
    def __init__(self, src_network: EVMNetwork, src_stablecoin: Stablecoin):
        self.src_network = src_network
        self.src_stablecoin = src_stablecoin

    def handle(self, thread):
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
    def __init__(self, src_network: EVMNetwork, dst_network: EVMNetwork, src_stablecoin: Stablecoin):
        self.src_network = src_network
        self.dst_network = dst_network
        self.src_stablecoin = src_stablecoin

    def handle(self, thread):
        logger.info("Choosing destination stablecoin")

        if len(self.dst_network.supported_stablecoins) == 0:
            raise StablecoinNotSupportedByChain(f"{self.dst_network} chain doesn't support any stablecoin")

        dst_stablecoin = random.choice(list(self.dst_network.supported_stablecoins.values()))

        logger.info(f"Destination stablecoin is chosen - {dst_stablecoin.symbol}")
        logger.info(f"Path: {self.src_stablecoin.symbol}({self.src_network.name}) -> "
                        f"{dst_stablecoin.symbol}({self.dst_network.name})")

        thread.set_state(CheckNativeTokenBalanceForGasState(self.src_network, self.dst_network,
                                                            self.src_stablecoin, dst_stablecoin))


# State for deciding whether gas will be refueled automatically or manually
class RefuelDecisionState(State):
    def __init__(self, src_network: EVMNetwork, dst_network: EVMNetwork,
                 src_stablecoin: Stablecoin, dst_stablecoin: Stablecoin):
        self.src_network = src_network
        self.dst_network = dst_network
        self.src_stablecoin = src_stablecoin
        self.dst_stablecoin = dst_stablecoin

    def handle(self, thread):
        logger.info("Checking possible refuel options")

        # TODO: Add auto refuel with Bungee/WooFi

        if REFUEL_MODE == RefuelMode.RANDOM:
            refuel_mode = random.choice([RefuelMode.MANUAL, RefuelMode.EXCHANGE])
        else:
            refuel_mode = REFUEL_MODE

        if refuel_mode == RefuelMode.EXCHANGE:
            thread.set_state(SleepBeforeExchangeRefuelState(self.src_network, self.dst_network,
                                                            self.src_stablecoin, self.dst_stablecoin))
        else:
            thread.set_state(WaitForManualRefuelState(self.src_network, self.dst_network,
                                                      self.src_stablecoin, self.dst_stablecoin))


# State for waiting for a manual native token deposit (in case the auto-refuel failed or disabled)
class WaitForManualRefuelState(State):
    def __init__(self, src_network: EVMNetwork, dst_network: EVMNetwork,
                 src_stablecoin: Stablecoin, dst_stablecoin: Stablecoin):
        self.src_network = src_network
        self.dst_network = dst_network
        self.src_stablecoin = src_stablecoin
        self.dst_stablecoin = dst_stablecoin

    def handle(self, thread):
        logger.info(f"{self.src_network.name}. Waiting for the native token deposit")
        time.sleep(SleepTimings.BALANCE_RECHECK_TIME)
        thread.set_state(CheckNativeTokenBalanceForGasState(self.src_network, self.dst_network,
                                                            self.src_stablecoin, self.dst_stablecoin))


# State for waiting before the exchange withdraw to make an account unique
class SleepBeforeExchangeRefuelState(State):
    def __init__(self, src_network: EVMNetwork, dst_network: EVMNetwork,
                 src_stablecoin: Stablecoin, dst_stablecoin: Stablecoin):
        self.src_network = src_network
        self.dst_network = dst_network
        self.src_stablecoin = src_stablecoin
        self.dst_stablecoin = dst_stablecoin

    def handle(self, thread):
        sleep_time = random.randint(SleepTimings.BEFORE_WITHDRAW_RANGE[0], SleepTimings.BEFORE_WITHDRAW_RANGE[1])

        withdraw_dt = datetime.datetime.fromtimestamp(time.time() + sleep_time)
        logger.info(f"Sleeping {sleep_time} seconds before withdraw from exchange. Withdraw time: {withdraw_dt}")
        time.sleep(sleep_time)

        thread.set_state(RefuelWithExchangeState(self.src_network, self.dst_network,
                                                 self.src_stablecoin, self.dst_stablecoin))


# State for refueling native token from exchange to cover gas fees
class RefuelWithExchangeState(State):
    def __init__(self, src_network: EVMNetwork, dst_network: EVMNetwork,
                 src_stablecoin: Stablecoin, dst_stablecoin: Stablecoin):
        self.src_network = src_network
        self.dst_network = dst_network
        self.src_stablecoin = src_stablecoin
        self.dst_stablecoin = dst_stablecoin

    def refuel(self, thread, amount: float) -> None:
        exchange = Okex(OKEX_API_KEY, OKEX_SECRET_KEY, OKEX_PASSWORD)
        symbol = self.src_network.native_token

        try:
            withdraw_info = exchange.get_withdraw_info(symbol, self.src_network.name)

            if withdraw_info.min_amount > amount:
                amount = withdraw_info.min_amount
            amount += withdraw_info.fee * 3

            balance = exchange.get_funding_balance(symbol)
            if balance < amount:
                # Multiplying to avoid decimals casting
                amount_to_withdraw = exchange.buy_tokens_with_usdt(symbol, amount) * 0.99
                exchange.transfer_funds(symbol, amount_to_withdraw, exchange.trading_account, exchange.funding_account)
            else:
                amount_to_withdraw = amount

            exchange.withdraw(symbol, amount_to_withdraw, self.src_network.name, thread.account.address)

        except NotWhitelistedAddress:
            logger.warning(f"WARNING! Address {thread.account.address} is not whitelisted to withdraw "
                           f"{self.src_network.native_token} in {self.src_network.name} network")

    def handle(self, thread):
        logger.info(f"Exchange refueling started")

        layer_zero_fee = self.src_network.estimate_layerzero_swap_fee(self.dst_network.stargate_chain_id,
                                                                      thread.account.address) / 10 ** 18
        swap_price = self.src_network.estimate_swap_gas_price() / 10 ** 18
        mul = 2  # Multiplier to withdraw funds with a reserve

        logger.info(f'L0 fee: {layer_zero_fee} {self.src_network.native_token}. '
                    f'Swap price: {swap_price} {self.src_network.native_token}')

        amount_to_withdraw = mul * (layer_zero_fee + swap_price)

        logger.info(f'To withdraw: {amount_to_withdraw}')
        self.refuel(thread, amount_to_withdraw)

        thread.set_state(WaitForExchangeWithdrawState(self.src_network, self.dst_network,
                                                      self.src_stablecoin, self.dst_stablecoin))


# State for waiting for exchange withdraw processing
class WaitForExchangeWithdrawState(State):
    def __init__(self, src_network: EVMNetwork, dst_network: EVMNetwork,
                 src_stablecoin: Stablecoin, dst_stablecoin: Stablecoin):
        self.src_network = src_network
        self.dst_network = dst_network
        self.src_stablecoin = src_stablecoin
        self.dst_stablecoin = dst_stablecoin

    def handle(self, thread):
        logger.info(f"Waiting for the withdraw")

        time.sleep(SleepTimings.EXCHANGE_WITHDRAW_RECHECK_TIME)

        thread.set_state(CheckNativeTokenBalanceForGasState(self.src_network, self.dst_network,
                                                            self.src_stablecoin, self.dst_stablecoin))


# TODO
class RefuelWithBungeeState(State):
    def __init__(self, src_network: EVMNetwork, dst_network: EVMNetwork,
                 src_stablecoin: Stablecoin, dst_stablecoin: Stablecoin):
        self.src_network = src_network
        self.dst_network = dst_network
        self.src_stablecoin = src_stablecoin
        self.dst_stablecoin = dst_stablecoin


# State for checking the native token balance
class CheckNativeTokenBalanceForGasState(State):
    def __init__(self, src_network: EVMNetwork, dst_network: EVMNetwork,
                 src_stablecoin: Stablecoin, dst_stablecoin: Stablecoin):
        self.src_network = src_network
        self.dst_network = dst_network
        self.src_stablecoin = src_stablecoin
        self.dst_stablecoin = dst_stablecoin

    def handle(self, thread):
        logger.info("Checking native token balance")
        helper = BalanceHelper(self.src_network, thread.account.address)

        if helper.is_enough_native_token_balance_for_stargate_swap_fee(self.dst_network):
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
                 src_stablecoin: Stablecoin, dst_stablecoin: Stablecoin):
        self.src_network = src_network
        self.dst_network = dst_network
        self.src_stablecoin = src_stablecoin
        self.dst_stablecoin = dst_stablecoin

    def handle(self, thread):
        sleep_time = random.randint(SleepTimings.BEFORE_BRIDGE_RANGE[0], SleepTimings.BEFORE_BRIDGE_RANGE[1])

        next_swap_dt = datetime.datetime.fromtimestamp(time.time() + sleep_time)
        logger.info(f"Sleeping {sleep_time} seconds before bridge. Next bridge time: {next_swap_dt}")
        time.sleep(sleep_time)

        thread.set_state(StargateSwapState(self.src_network, self.dst_network,
                                           self.src_stablecoin, self.dst_stablecoin))


# State for swapping tokens
class StargateSwapState(State):
    def __init__(self, src_network: EVMNetwork, dst_network: EVMNetwork,
                 src_stablecoin: Stablecoin, dst_stablecoin: Stablecoin):
        self.src_network = src_network
        self.dst_network = dst_network
        self.src_stablecoin = src_stablecoin
        self.dst_stablecoin = dst_stablecoin

    def handle(self, thread):
        balance_helper = BalanceHelper(self.src_network, thread.account.address)
        amount = balance_helper.get_stablecoin_balance(self.src_stablecoin)

        logger.info(f"Swapping {amount / 10 ** self.src_stablecoin.decimals} tokens through Stargate bridge. "
                    f"{self.src_stablecoin.symbol}({self.src_network.name}) -> "
                    f"{self.dst_stablecoin.symbol}({self.dst_network.name})")

        bridge_helper = BridgeHelper(thread.account, balance_helper, self.src_network, self.dst_network,
                                     self.src_stablecoin, self.dst_stablecoin, amount, STARGATE_SLIPPAGE)

        result = bridge_helper.make_bridge()

        if result:
            logger.info("Bridge finished")
        else:
            logger.error("Bridge error. Recheck config settings and balances")

        thread.set_state(CheckStablecoinBalanceState())
