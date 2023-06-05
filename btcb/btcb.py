import logging
import random
import time

from eth_account.signers.local import LocalAccount
from web3.types import TxParams

from abi import BTCB_ABI
from network import EVMNetwork, Optimism, Avalanche
from btcb.constants import BTCbConstants

logger = logging.getLogger(__name__)


class BTCbUtils:
    @staticmethod
    def get_adapter_params(network: EVMNetwork, address: str) -> str:
        if isinstance(network, Optimism):
            return f"0x00020000000000000000000000000000000000000000000000000000000000" \
                   f"2dc6c00000000000000000000000000000000000000000000000000000000000000000" \
                   f"{address[2:]}"
        else:
            return f"0x000200000000000000000000000000000000000000000000000000000000000" \
                   f"3d0900000000000000000000000000000000000000000000000000000000000000000" \
                   f"{address[2:]}"

    @staticmethod
    def estimate_layerzero_bridge_fee(src_network: EVMNetwork, dst_network: EVMNetwork, dst_address: str) -> int:
        btcb_contract = src_network.w3.eth.contract(address=BTCbConstants.BTCB_CONTRACT_ADDRESS, abi=BTCB_ABI)

        to_address = '0x000000000000000000000000' + dst_address[2:]
        amount = 100  # Doesn't matter in fee calculation

        quote_data = btcb_contract.functions.estimateSendFee(dst_network.layerzero_chain_id, to_address,
                                                             amount, False,
                                                             BTCbUtils.get_adapter_params(src_network, dst_address)
                                                             ).call()
        return quote_data[0]

    @staticmethod
    def _get_optimism_bridge_l1_fee(optimism: Optimism, dst_network: EVMNetwork, address: str) -> int:
        # Doesn't matter in fee calculation
        amount = 100

        bridge_tx = BTCbUtils.build_bridge_transaction(optimism, dst_network, amount, address)
        bridge_l1_fee = optimism.get_l1_fee(bridge_tx)

        return bridge_l1_fee

    @staticmethod
    def estimate_bridge_gas_price(src_network: EVMNetwork, dst_network: EVMNetwork, address: str) -> int:
        max_overall_gas_limit = BTCbConstants.get_max_randomized_bridge_gas_limit(src_network.name)

        # Avalanche network needs BTC.b approval before bridging
        if isinstance(src_network, Avalanche):
            max_overall_gas_limit += src_network.get_approve_gas_limit()
        gas_price = max_overall_gas_limit * src_network.get_max_fee_per_gas()

        # Optimism fee should be calculated in a different way.
        # Read more: https://community.optimism.io/docs/developers/build/transaction-fees/#
        if isinstance(src_network, Optimism):
            gas_price += BTCbUtils._get_optimism_bridge_l1_fee(src_network, dst_network, address)

        return gas_price

    @staticmethod
    def is_enough_native_balance_for_bridge_fee(src_network: EVMNetwork, dst_network: EVMNetwork, address: str):
        account_balance = src_network.get_balance(address)
        gas_price = BTCbUtils.estimate_bridge_gas_price(src_network, dst_network, address)
        layerzero_fee = BTCbUtils.estimate_layerzero_bridge_fee(src_network, dst_network, address)

        enough_native_token_balance = account_balance > (gas_price + layerzero_fee)

        return enough_native_token_balance

    @staticmethod
    def get_btcb_balance(network: EVMNetwork, address: str) -> int:
        if isinstance(network, Avalanche):
            return network.get_token_balance(BTCbConstants.BTCB_BASE_AVALANCHE_CONTRACT_ADDRESS, address)

        return network.get_token_balance(BTCbConstants.BTCB_CONTRACT_ADDRESS, address)

    @staticmethod
    def build_bridge_transaction(src_network: EVMNetwork, dst_network: EVMNetwork,
                                 amount: int, address: str) -> TxParams:
        btcb_contract = src_network.w3.eth.contract(address=BTCbConstants.BTCB_CONTRACT_ADDRESS, abi=BTCB_ABI)

        layerzero_fee = BTCbUtils.estimate_layerzero_bridge_fee(src_network, dst_network, address)

        nonce = src_network.get_nonce(address)
        gas_params = src_network.get_transaction_gas_params()
        logger.info(f'Estimated fees. LayerZero fee: {layerzero_fee}. Gas settings: {gas_params}')

        tx = btcb_contract.functions.sendFrom(
            address,  # _from
            dst_network.layerzero_chain_id,  # _dstChainId
            f"0x000000000000000000000000{address[2:]}",  # _toAddress
            amount,  # _amount
            amount,  # _minAmount
            [address,  # _callParams.refundAddress
             "0x0000000000000000000000000000000000000000",  # _callParams.zroPaymentAddress
             BTCbUtils.get_adapter_params(src_network, address)]  # _callParams.adapterParams
        ).build_transaction(
            {
                'from': address,
                'value': layerzero_fee,
                'gas': BTCbConstants.get_randomized_bridge_gas_limit(src_network.name),
                **gas_params,
                'nonce': nonce
            }
        )

        return tx


class BTCbBridgeHelper:
    def __init__(self, account: LocalAccount, src_network: EVMNetwork, dst_network: EVMNetwork, amount: int) -> None:
        self.account = account
        self.src_network = src_network
        self.dst_network = dst_network
        self.amount = amount

    def make_bridge(self) -> bool:
        if not self._is_bridge_possible():
            return False

        if isinstance(self.src_network, Avalanche):
            result = self._approve_btcb_usage(self.amount)

            if not result:
                return False

            time.sleep(random.randint(10, 60))

        tx_hash = self._send_bridge_transaction()
        result = self.src_network.wait_for_transaction(tx_hash)

        return self.src_network.check_tx_result(result, "BTC.b bridge")

    def _is_bridge_possible(self) -> bool:
        """ Method that checks BTC.b balance on the source chain and decides if it is possible to make bridge """

        if not BTCbUtils.is_enough_native_balance_for_bridge_fee(self.src_network, self.dst_network,
                                                                 self.account.address):
            logger.error(f"Not enough native token balance on {self.src_network.name} network")
            return False

        btcb_balance = BTCbUtils.get_btcb_balance(self.src_network, self.account.address)
        if btcb_balance < self.amount:
            logger.error(f"Not enough BTC.b balance on {self.src_network.name} network")
            return False

        return True

    def _approve_btcb_usage(self, amount: int) -> bool:
        if not isinstance(self.src_network, Avalanche):
            raise ValueError("BTC.b needs approval only on Avalanche chain")

        allowance = self.src_network.get_token_allowance(BTCbConstants.BTCB_BASE_AVALANCHE_CONTRACT_ADDRESS,
                                                         self.account.address, BTCbConstants.BTCB_CONTRACT_ADDRESS)
        if allowance >= amount:
            return True

        tx_hash = self.src_network.approve_token_usage(self.account.key,
                                                       BTCbConstants.BTCB_BASE_AVALANCHE_CONTRACT_ADDRESS,
                                                       BTCbConstants.BTCB_CONTRACT_ADDRESS, amount)
        result = self.src_network.wait_for_transaction(tx_hash)

        return self.src_network.check_tx_result(result, f"Approve BTC.b usage")

    def _send_bridge_transaction(self):
        tx = BTCbUtils.build_bridge_transaction(self.src_network, self.dst_network, self.amount, self.account.address)

        signed_tx = self.src_network.w3.eth.account.sign_transaction(tx, self.account.key)
        tx_hash = self.src_network.w3.eth.send_raw_transaction(signed_tx.rawTransaction)

        logger.info(f'BTC.b bridge transaction signed and sent. Hash: {tx_hash.hex()}')

        return tx_hash
