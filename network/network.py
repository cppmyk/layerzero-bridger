import logging
import random
import time
from enum import Enum
from typing import Dict, Union

import requests
from eth_typing import Hash32, HexStr
from hexbytes import HexBytes
from web3 import HTTPProvider, Web3
from web3.exceptions import TransactionNotFound
from web3.types import TxParams

from abi import ERC20_ABI
from base.errors import NotSupported
from utility import Stablecoin

logger = logging.getLogger(__name__)


class TransactionStatus(Enum):
    NOT_FOUND = 0
    SUCCESS = 1
    FAILED = 2


class Network:

    def __init__(self, name: str, native_token: str, rpc: str, layerzero_chain_id: int,
                 stargate_router_address: str) -> None:
        self.name = name
        self.native_token = native_token
        self.rpc = rpc
        self.layerzero_chain_id = layerzero_chain_id
        self.stargate_router_address = stargate_router_address

    def get_balance(self, address: str) -> int:
        """ Method that checks native token balance """
        raise NotSupported(f"{self.name} get_balance() is not implemented")

    def get_token_balance(self, contract_address: str, address: str) -> int:
        """ Method that checks ERC-20 token balance """
        raise NotSupported(f"{self.name} get_token_balance() is not implemented")

    def get_token_allowance(self, contract_address: str, owner: str, spender: str) -> int:
        """ Method that checks ERC-20 token allowance """
        raise NotSupported(f"{self.name} get_token_allowance() is not implemented")

    def get_current_gas(self) -> int:
        """ Method that checks network gas price """
        raise NotSupported(f"{self.name} get_current_gas() is not implemented")

    def get_nonce(self, address: str) -> int:
        """ Method that fetches account nonce """
        raise NotSupported(f"{self.name} get_nonce() is not implemented")


class EVMNetwork(Network):

    def __init__(self, name: str, native_token: str, rpc: str,
                 layerzero_chain_id: int, stargate_router_address: str,
                 supported_stablecoins: Dict[str, Stablecoin]) -> None:
        super().__init__(name, native_token, rpc, layerzero_chain_id, stargate_router_address)
        self.w3 = Web3(HTTPProvider(rpc))
        self.supported_stablecoins = supported_stablecoins

    def get_balance(self, address: str) -> int:
        """ Method that checks native token balance """

        return self.w3.eth.get_balance(Web3.to_checksum_address(address))

    def get_current_gas(self) -> int:
        """ Method that checks network gas price """

        return self.w3.eth.gas_price

    def get_transaction_gas_params(self) -> dict:
        """ Method that returns formatted gas params to be added to build_transaction """

        raise NotSupported(f"{self.name} get_transaction_gas_params() is not implemented")

    def get_nonce(self, address: str) -> int:
        """ Method that fetches account nonce """

        return self.w3.eth.get_transaction_count(Web3.to_checksum_address(address))

    @staticmethod
    def check_tx_result(result: TransactionStatus, name: str) -> bool:
        """ Utility method that checks transaction result and returns false if it's not mined or failed """

        if result == TransactionStatus.SUCCESS:
            logger.info(f"{name} transaction succeed")
            return True
        if result == TransactionStatus.NOT_FOUND:
            logger.info(f"{name} transaction can't be found in the blockchain"
                        " for a log time. Consider changing fee settings")
            return False
        if result == TransactionStatus.FAILED:
            logger.info(f"{name} transaction failed")
            return False

        return False

    def wait_for_transaction(self, tx_hash: Union[Hash32, HexBytes, HexStr], timeout: int = 300) -> TransactionStatus:
        start_time = time.time()

        logger.info(f'Waiting for transaction {tx_hash.hex()} to be mined')
        while True:
            try:
                tx_receipt = self.w3.eth.get_transaction_receipt(tx_hash)
            except TransactionNotFound:
                pass
            except requests.exceptions.HTTPError:
                time.sleep(10)
            else:
                if tx_receipt is not None:
                    if tx_receipt["status"]:
                        logger.info("Transaction mined successfully! Status: Success")
                        return TransactionStatus.SUCCESS
                    else:
                        logger.info("Transaction mined successfully! Status: Failed")
                        return TransactionStatus.FAILED

            if time.time() - start_time >= timeout:
                logger.info("Timeout reached. Transaction not mined within the specified time")
                return TransactionStatus.NOT_FOUND

            time.sleep(10)  # Wait for 10 seconds before checking again

    # MARK: ERC-20 Token functions

    def get_token_balance(self, contract_address: str, address: str) -> int:
        """ Method that checks ERC-20 token balance """

        contract = self.w3.eth.contract(address=Web3.to_checksum_address(contract_address), abi=ERC20_ABI)
        return contract.functions.balanceOf(Web3.to_checksum_address(address)).call()

    def get_token_allowance(self, contract_address: str, owner: str, spender: str) -> int:
        """ Method that checks ERC-20 token allowance """

        contract = self.w3.eth.contract(address=Web3.to_checksum_address(contract_address), abi=ERC20_ABI)
        return contract.functions.allowance(Web3.to_checksum_address(owner),
                                            Web3.to_checksum_address(spender)).call()

    def get_approve_gas_limit(self) -> int:
        raise NotSupported(f"{self.name} _get_approve_gas_limit() is not implemented")

    def _build_approve_transaction(self, address: str, contract_address: str, spender: str, amount: int) -> TxParams:
        contract = self.w3.eth.contract(address=Web3.to_checksum_address(contract_address), abi=ERC20_ABI)

        randomized_gas_limit = random.randint(int(self.get_approve_gas_limit() * 0.95), self.get_approve_gas_limit())
        gas_params = self.get_transaction_gas_params()

        tx = contract.functions.approve(spender, amount).build_transaction(
            {
                'from': address,
                'gas': randomized_gas_limit,
                **gas_params,
                'nonce': self.get_nonce(address)
            }
        )

        return tx

    def approve_token_usage(self, private_key: str, contract_address: str, spender: str, amount: int) -> HexBytes:
        """ Method that approves token usage by spender address and returns transaction hash """

        account = self.w3.eth.account.from_key(private_key)
        tx = self._build_approve_transaction(account.address, contract_address, spender, amount)

        signed_tx = self.w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)

        return tx_hash
