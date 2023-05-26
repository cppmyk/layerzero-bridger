from typing import Dict

import web3.exceptions
from web3 import HTTPProvider, Web3

from abi import ERC20_ABI, STARGATE_ROUTER_ABI
from base.errors import NotSupported
from network.stablecoin import Stablecoin
from stargate import StargateConstants


class Network:

    def __init__(self, name: str, native_token: str, rpc: str, stargate_chain_id: int, stargate_router_address: str):
        self.name = name
        self.native_token = native_token
        self.rpc = rpc
        self.stargate_chain_id = stargate_chain_id
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
                 stargate_chain_id: int, stargate_router_address: str,
                 supported_stablecoins: Dict[str, Stablecoin]):
        super().__init__(name, native_token, rpc, stargate_chain_id, stargate_router_address)
        self.w3 = Web3(HTTPProvider(rpc))
        self.supported_stablecoins = supported_stablecoins

    def get_balance(self, address: str) -> int:
        """ Method that checks native token balance """

        return self.w3.eth.get_balance(Web3.to_checksum_address(address))

    def get_current_gas(self) -> int:
        """ Method that checks network gas price """

        return self.w3.eth.gas_price

    def get_nonce(self, address: str) -> int:
        """ Method that fetches account nonce """

        return self.w3.eth.get_transaction_count(Web3.to_checksum_address(address))

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

    def _get_approve_gas_limit(self) -> int:
        raise NotSupported(f"{self.name} _get_approve_gas_limit() is not implemented")

    def approve_token_usage(self, private_key: str, contract_address: str, spender: str, amount: int) -> bool:
        """ Method that approves token usage by spender address """

        account = self.w3.eth.account.from_key(private_key)
        contract = self.w3.eth.contract(address=Web3.to_checksum_address(contract_address), abi=ERC20_ABI)

        tx = contract.functions.approve(spender, amount).build_transaction(
            {
                'from': account.address,
                'gas': self._get_approve_gas_limit(),
                'gasPrice': int(self.get_current_gas()),
                'nonce': self.get_nonce(account.address)
            }
        )
        signed_tx = self.w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)

        try:
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        except web3.exceptions.TimeExhausted:
            print('Approve tx waiting time exceeded')
            return False

        return True

    # MARK: Stargate/L0 functions

    def estimate_swap_gas_price(self) -> int:
        approve_gas_limit = self._get_approve_gas_limit()
        overall_gas_limit = StargateConstants.SWAP_GAS_LIMIT[self.name] + approve_gas_limit

        gas_price = overall_gas_limit * self.get_current_gas()

        return gas_price

    def estimate_layerzero_swap_fee(self, dst_chain_id: int, dst_address: str) -> int:
        """ Method that estimates LayerZero fee to make the swap in native token """

        contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(self.stargate_router_address),
            abi=STARGATE_ROUTER_ABI)

        quote_data = contract.functions.quoteLayerZeroFee(
            dst_chain_id,  # destination chainId
            1,  # function type (1 - swap): see Bridge.sol for all types
            dst_address,  # destination of tokens
            "0x",  # payload, using abi.encode()
            [0,  # extra gas, if calling smart contract
             0,  # amount of dust dropped in destination wallet
             "0x"  # destination wallet for dust
             ]
        ).call()

        return quote_data[0]

    def make_stargate_swap(self, private_key: str, dst_chain_id: int, src_pool_id: int, dst_pool_id: int, amount: int,
                           min_received_amount: int, fast_gas: bool = False) -> bool:
        """ Method that swaps src_pool_id token from current chain to dst_chain_id """

        account = self.w3.eth.account.from_key(private_key)
        contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(self.stargate_router_address),
            abi=STARGATE_ROUTER_ABI)

        layerzero_fee = self.estimate_layerzero_swap_fee(dst_chain_id, account.address)
        nonce = self.get_nonce(account.address)
        gas_price = int(self.get_current_gas() * 1.2) if fast_gas else self.get_current_gas()

        print(f'Estimated fees. LayerZero fee: {layerzero_fee}. Gas price: {gas_price}')

        tx = contract.functions.swap(
            dst_chain_id,  # destination chainId
            src_pool_id,  # source poolId
            dst_pool_id,  # destination poolId
            account.address,  # refund address. extra gas (if any) is returned to this address
            amount,  # quantity to swap
            min_received_amount,  # the min qty you would accept on the destination
            [0,  # extra gas, if calling smart contract
             0,  # amount of dust dropped in destination wallet
             "0x"  # destination wallet for dust
             ],
            account.address,  # the address to send the tokens to on the destination
            "0x",  # "fee" is the native gas to pay for the cross chain message fee
        ).build_transaction(
            {
                'from': account.address,
                'value': layerzero_fee,
                'gas': StargateConstants.SWAP_GAS_LIMIT[self.name],
                'gasPrice': gas_price,
                'nonce': nonce
            }
        )
        signed_tx = self.w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)

        print(f'Hash: {tx_hash.hex()}')

        try:
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        except web3.exceptions.TimeExhausted:
            print('Bridge tx waiting time exceeded')
            return False

        return True
