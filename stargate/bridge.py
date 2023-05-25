import time

from config import TimeRanges
from network import EVMNetwork, Stablecoin
from eth_account.signers.local import LocalAccount
from base.errors import NotEnoughNativeTokenBalance, NotEnoughStablecoinBalance
from network.balance_helper import BalanceHelper


class BridgeHelper:

    def __init__(self, account: LocalAccount, balance_helper: BalanceHelper,
                 src_network: EVMNetwork, dst_network: EVMNetwork,
                 src_stablecoin: Stablecoin, dst_stablecoin: Stablecoin, amount: int, slippage: int):
        self.account = account
        self.balance_helper = balance_helper
        self.src_network = src_network
        self.dst_network = dst_network
        self.src_stablecoin = src_stablecoin
        self.dst_stablecoin = dst_stablecoin
        self.amount = amount
        self.slippage = slippage

    def _is_bridge_possible(self) -> bool:
        """ Method that checks account balance on the source chain and decides if it is possible to make bridge """

        if not self.balance_helper.is_enough_native_token_balance_for_stargate_swap_fee(self.dst_network):
            return False
            # raise NotEnoughNativeTokenBalance(f"{self.src_network.name} - not enough native token balance")

        stablecoin_balance = self.src_network.get_token_balance(self.src_stablecoin.contract_address,
                                                                self.account.address)
        if stablecoin_balance < self.amount:
            return False
            # raise NotEnoughStablecoinBalance(f"{self.src_network.name} - not enough stablecoin balance")

        return True

    def approve_stablecoin_usage(self, amount: int) -> None:
        allowance = self.src_network.get_token_allowance(self.src_stablecoin.contract_address, self.account.address,
                                                         self.src_network.stargate_router_address)
        # print(f'Allowance: {allowance}. Amount: {amount}')
        if allowance < amount:
            self.src_network.approve_token_usage(self.account.key, self.src_stablecoin.contract_address,
                                                 self.src_network.stargate_router_address, amount)

    def make_bridge(self):
        """ Method that performs bridge from src_network to dst_network """

        if not self._is_bridge_possible():
            return

        self.approve_stablecoin_usage(self.amount)
        amount_with_slippage = self.amount - int(self.amount * self.slippage)

        time.sleep(TimeRanges.MINUTE)

        return self.src_network.make_stargate_swap(self.account.key, self.dst_network.stargate_chain_id,
                                                   self.src_stablecoin.stargate_pool_id,
                                                   self.dst_stablecoin.stargate_pool_id,
                                                   self.amount, amount_with_slippage)
