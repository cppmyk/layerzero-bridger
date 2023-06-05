import logging
import random

from hexbytes import HexBytes
from web3 import Web3
from web3.types import TxParams

from abi import STARGATE_ROUTER_ABI
from network.network import EVMNetwork
from network.optimism.optimism import Optimism
from utility import Stablecoin

from stargate.constants import StargateConstants
from eth_account.signers.local import LocalAccount

logger = logging.getLogger(__name__)


class StargateUtils:
    @staticmethod
    def estimate_layerzero_swap_fee(src_network: EVMNetwork, dst_network: EVMNetwork, dst_address: str) -> int:
        """ Method that estimates LayerZero fee to make the swap in native token """

        contract = src_network.w3.eth.contract(
            address=Web3.to_checksum_address(src_network.stargate_router_address),
            abi=STARGATE_ROUTER_ABI)

        quote_data = contract.functions.quoteLayerZeroFee(
            dst_network.layerzero_chain_id,  # destination chainId
            1,  # function type (1 - swap): see Bridge.sol for all types
            dst_address,  # destination of tokens
            "0x",  # payload, using abi.encode()
            [0,  # extra gas, if calling smart contract
             0,  # amount of dust dropped in destination wallet
             "0x"  # destination wallet for dust
             ]
        ).call()

        return quote_data[0]

    @staticmethod
    def _get_optimism_swap_l1_fee(optimism: Optimism, dst_network: EVMNetwork, address: str) -> int:
        # Doesn't matter in fee calculation
        amount = 100
        slippage = 0.01
        _, src_stablecoin = random.choice(list(optimism.supported_stablecoins.items()))
        _, dst_stablecoin = random.choice(list(dst_network.supported_stablecoins.items()))

        swap_tx = StargateUtils.build_swap_transaction(address, optimism, dst_network,
                                                       src_stablecoin, dst_stablecoin, amount, slippage)
        swap_l1_fee = optimism.get_l1_fee(swap_tx)
        approve_l1_fee = optimism.get_approve_l1_fee()

        l1_fee = swap_l1_fee + approve_l1_fee

        return l1_fee

    @staticmethod
    def estimate_swap_gas_price(src_network: EVMNetwork, dst_network: EVMNetwork, address: str) -> int:
        approve_gas_limit = src_network.get_approve_gas_limit()
        max_overall_gas_limit = StargateConstants.get_max_randomized_swap_gas_limit(
            src_network.name) + approve_gas_limit
        gas_price = max_overall_gas_limit * src_network.get_current_gas()

        # Optimism fee should be calculated in a different way.
        # Read more: https://community.optimism.io/docs/developers/build/transaction-fees/#
        if isinstance(src_network, Optimism):
            gas_price += StargateUtils._get_optimism_swap_l1_fee(src_network, dst_network, address)

        return gas_price

    @staticmethod
    def is_enough_native_balance_for_swap_fee(src_network: EVMNetwork, dst_network: EVMNetwork, address: str) -> bool:
        account_balance = src_network.get_balance(address)
        gas_price = StargateUtils.estimate_swap_gas_price(src_network, dst_network, address)
        layerzero_fee = StargateUtils.estimate_layerzero_swap_fee(src_network, dst_network, address)

        enough_native_token_balance = account_balance > (gas_price + layerzero_fee)

        return enough_native_token_balance

    @staticmethod
    def build_swap_transaction(address: str, src_network: EVMNetwork, dst_network: EVMNetwork,
                               src_stablecoin: Stablecoin, dst_stablecoin: Stablecoin,
                               amount: int, slippage: float) -> TxParams:
        contract = src_network.w3.eth.contract(
            address=Web3.to_checksum_address(src_network.stargate_router_address),
            abi=STARGATE_ROUTER_ABI)

        layerzero_fee = StargateUtils.estimate_layerzero_swap_fee(src_network, dst_network, address)
        nonce = src_network.get_nonce(address)
        gas_params = src_network.get_transaction_gas_params()
        amount_with_slippage = amount - int(amount * slippage)

        logger.info(f'Estimated fees. LayerZero fee: {layerzero_fee}. Gas settings: {gas_params}')
        tx = contract.functions.swap(
            dst_network.layerzero_chain_id,  # destination chainId
            src_stablecoin.stargate_pool_id,  # source poolId
            dst_stablecoin.stargate_pool_id,  # destination poolId
            address,  # refund address. extra gas (if any) is returned to this address
            amount,  # quantity to swap
            amount_with_slippage,  # the min qty you would accept on the destination
            [0,  # extra gas, if calling smart contract
             0,  # amount of dust dropped in destination wallet
             "0x"  # destination wallet for dust
             ],
            address,  # the address to send the tokens to on the destination
            "0x",  # "fee" is the native gas to pay for the cross chain message fee
        ).build_transaction(
            {
                'from': address,
                'value': layerzero_fee,
                'gas': StargateConstants.get_randomized_swap_gas_limit(src_network.name),
                **gas_params,
                'nonce': nonce
            }
        )

        return tx


class StargateBridgeHelper:

    def __init__(self, account: LocalAccount, src_network: EVMNetwork, dst_network: EVMNetwork,
                 src_stablecoin: Stablecoin, dst_stablecoin: Stablecoin, amount: int, slippage: float):
        self.account = account
        self.src_network = src_network
        self.dst_network = dst_network
        self.src_stablecoin = src_stablecoin
        self.dst_stablecoin = dst_stablecoin
        self.amount = amount
        self.slippage = slippage

    def make_bridge(self) -> bool:
        """ Method that performs bridge from src_network to dst_network """

        if not self._is_bridge_possible():
            return False

        if not self._approve_stablecoin_usage(self.amount):
            return False

        tx_hash = self._send_swap_transaction()
        result = self.src_network.wait_for_transaction(tx_hash)

        return self.src_network.check_tx_result(result, "Stargate swap")

    def _send_swap_transaction(self) -> HexBytes:
        """ Utility method that signs and sends tx - Swap src_pool_id token from src_network chain to dst_chain_id """

        tx = StargateUtils.build_swap_transaction(self.account.address, self.src_network, self.dst_network,
                                                  self.src_stablecoin, self.dst_stablecoin, self.amount, self.slippage)
        signed_tx = self.src_network.w3.eth.account.sign_transaction(tx, self.account.key)
        tx_hash = self.src_network.w3.eth.send_raw_transaction(signed_tx.rawTransaction)

        logger.info(f'Stargate swap transaction signed and sent. Hash: {tx_hash.hex()}')

        return tx_hash

    def _is_bridge_possible(self) -> bool:
        """ Method that checks account balance on the source chain and decides if it is possible to make bridge """

        if not StargateUtils.is_enough_native_balance_for_swap_fee(self.src_network, self.dst_network,
                                                                   self.account.address):
            return False

        stablecoin_balance = self.src_network.get_token_balance(self.src_stablecoin.contract_address,
                                                                self.account.address)
        if stablecoin_balance < self.amount:
            return False

        return True

    def _approve_stablecoin_usage(self, amount: int) -> bool:
        allowance = self.src_network.get_token_allowance(self.src_stablecoin.contract_address, self.account.address,
                                                         self.src_network.stargate_router_address)
        if allowance >= amount:
            return True

        tx_hash = self.src_network.approve_token_usage(self.account.key, self.src_stablecoin.contract_address,
                                                       self.src_network.stargate_router_address, amount)
        result = self.src_network.wait_for_transaction(tx_hash)

        return self.src_network.check_tx_result(result, f"Approve {self.src_stablecoin.symbol} usage")
