import time
import random
import datetime
from dataclasses import dataclass
from typing import List, Tuple

from base.errors import ConfigurationError, StablecoinNotSupportedByChain
from network import EVMNetwork, Stablecoin
from stargate.bridge import BridgeHelper
from config import SUPPORTED_NETWORKS, STARGATE_SLIPPAGE, MIN_STABLECOIN_BALANCE, SleepTimings
from network.balance_helper import BalanceHelper


# State interface defining the behavior of different states
class State:
    def handle(self, thread):
        pass


# State for waiting before start to randomize start time
class SleepBeforeStart(State):
    def handle(self, thread):
        sleep_time = random.randint(SleepTimings.AFTER_START_RANGE[0], SleepTimings.AFTER_START_RANGE[1])

        thread.log_info(f"Sleeping {sleep_time} seconds before start")
        time.sleep(sleep_time)

        thread.set_state(CheckStablecoinBalanceState())


# State for waiting for the stablecoin deposit
class WaitForStablecoinDepositState(State):
    def __init__(self):
        pass

    def handle(self, thread):
        thread.log_info("Waiting for stablecoin deposit")
        time.sleep(SleepTimings.BALANCE_RECHECK_TIME)

        thread.set_state(CheckStablecoinBalanceState())


# Utility class to store the network and related stablecoin that will be used in future
@dataclass
class NetworkWithStablecoinBalance:
    network: EVMNetwork
    stablecoin: Stablecoin


# State for checking the stablecoin balance in source network
class CheckStablecoinBalanceState(State):
    def __init__(self):
        pass

    def is_enough_balance(self, thread, balance_helper: BalanceHelper, stablecoin: Stablecoin) -> bool:
        balance = balance_helper.get_stablecoin_balance(stablecoin)
        min_balance = MIN_STABLECOIN_BALANCE * 10 ** stablecoin.decimals

        thread.log_info(f'{balance_helper.network.name}. {stablecoin.symbol} '
                        f'balance - {balance / 10 ** stablecoin.decimals}')

        if balance > min_balance:
            return True
        return False

    def find_networks_with_balance(self, thread) -> List[NetworkWithStablecoinBalance]:
        """ Method that checks stablecoin balances in all networks and returns the list of networks
        and related stablecoins that satisfies the minimum balance condition """

        result = []

        for network in SUPPORTED_NETWORKS:
            for stablecoin in network.supported_stablecoins.values():
                if self.is_enough_balance(thread, BalanceHelper(network, thread.account.address),
                                          stablecoin):
                    result.append(NetworkWithStablecoinBalance(network, stablecoin))

        return result

    def handle(self, thread):
        thread.log_info("Checking stablecoin balance")

        networks = self.find_networks_with_balance(thread)
        if len(networks) == 0:
            thread.log_info("Not enough stablecoin balance. Refill one of the supported networks")
            thread.set_state(WaitForStablecoinDepositState())
        elif len(networks) == 1:
            thread.log_info(f"{networks[0].network.name} network meet the minimum stablecoin balance requirements")
            thread.set_state(ChooseDestinationNetworkState(networks[0].network, networks[0].stablecoin))
        else:
            thread.log_info(
                f"{len(networks)} networks meet the minimum stablecoin balance requirements. Randomizing choice")
            random_network = random.choice(networks)
            thread.log_info(f"{random_network.network.name} was randomized")
            thread.set_state(ChooseDestinationNetworkState(random_network.network, random_network.stablecoin))


# State for choosing a random destination network
class ChooseDestinationNetworkState(State):
    def __init__(self, src_network: EVMNetwork, src_stablecoin: Stablecoin):
        self.src_network = src_network
        self.src_stablecoin = src_stablecoin

    def handle(self, thread):
        thread.log_info("Randomizing destination network")

        networks = SUPPORTED_NETWORKS.copy()
        networks.remove(self.src_network)

        if len(networks) == 0:
            raise ConfigurationError("Unable to select destination chain. "
                                     "Revise the list of supported networks in config")

        dst_network = random.choice(networks)
        thread.log_info(f"Destination network is chosen - {dst_network.name}")
        thread.set_state(ChooseDestinationStablecoinState(self.src_network, dst_network, self.src_stablecoin))


# State for choosing a random destination stablecoin
class ChooseDestinationStablecoinState(State):
    def __init__(self, src_network: EVMNetwork, dst_network: EVMNetwork, src_stablecoin: Stablecoin):
        self.src_network = src_network
        self.dst_network = dst_network
        self.src_stablecoin = src_stablecoin

    def handle(self, thread):
        thread.log_info("Choosing destination stablecoin")

        if len(self.dst_network.supported_stablecoins) == 0:
            raise StablecoinNotSupportedByChain(f"{self.dst_network} chain doesn't support any stablecoin")

        dst_stablecoin = random.choice(list(self.dst_network.supported_stablecoins.values()))

        thread.log_info(f"Destination stablecoin is chosen - {dst_stablecoin.symbol}")
        thread.log_info(f"Path: {self.src_stablecoin.symbol}({self.src_network.name}) -> "
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
        thread.log_info("Checking possible refuel options")

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
        thread.log_info(f"{self.src_network.name}. Waiting for the native token deposit")
        time.sleep(SleepTimings.BALANCE_RECHECK_TIME)
        thread.set_state(CheckNativeTokenBalanceForGasState(self.src_network, self.dst_network,
                                                            self.src_stablecoin, self.dst_stablecoin))


# State for checking the native token balance
class CheckNativeTokenBalanceForGasState(State):
    def __init__(self, src_network: EVMNetwork, dst_network: EVMNetwork,
                 src_stablecoin: Stablecoin, dst_stablecoin: Stablecoin):
        self.src_network = src_network
        self.dst_network = dst_network
        self.src_stablecoin = src_stablecoin
        self.dst_stablecoin = dst_stablecoin

    def handle(self, thread):
        thread.log_info("Checking native token balance")
        helper = BalanceHelper(self.src_network, thread.account.address)

        if helper.is_enough_native_token_balance_for_stargate_swap_fee(self.dst_network):
            thread.log_info("Enough native token amount on source chain")
            thread.set_state(SleepBeforeBridgeState(self.src_network, self.dst_network,
                                                    self.src_stablecoin, self.dst_stablecoin))
        else:
            thread.log_info("Not enough native token amount on source chain to cover the fees")
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
        sleep_time = random.randint(SleepTimings.BETWEEN_BRIDGE_RANGE[0], SleepTimings.BETWEEN_BRIDGE_RANGE[1])

        next_swap_dt = datetime.datetime.fromtimestamp(time.time() + sleep_time)
        thread.log_info(f"Sleeping {sleep_time} seconds before bridge. Next bridge time: {next_swap_dt}")
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

        thread.log_info(f"Swapping {amount / 10 ** self.src_stablecoin.decimals} tokens through Stargate bridge. "
                        f"{self.src_stablecoin.symbol}({self.src_network.name}) -> "
                        f"{self.dst_stablecoin.symbol}({self.dst_network.name})")

        bridge_helper = BridgeHelper(thread.account, balance_helper, self.src_network, self.dst_network,
                                     self.src_stablecoin, self.dst_stablecoin, amount, STARGATE_SLIPPAGE)

        bridge_helper.make_bridge()

        thread.log_info("Bridge finished")
        thread.set_state(CheckStablecoinBalanceState())
